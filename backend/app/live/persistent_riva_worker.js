#!/usr/bin/env node
/**
 * HSBot Persistent Riva Worker (ASR + Streaming TTS)
 * 
 * Runs as a long-lived background child process communicating via line-delimited JSON on stdin/stdout.
 * Keeps gRPC connection warm so ASR and TTS execute in sub-second time without process startup penalty.
 */

const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');
const readline = require('readline');
const fs = require('fs');

function findProtoDir() {
  const candidates = [
    path.resolve(__dirname, '../../../proto'),
    path.resolve(__dirname, '../../proto'),
    path.resolve(__dirname, '../../riva_proto'),
    '/app/proto',
    '/app/riva_proto',
    path.resolve(__dirname, 'proto'),
  ];
  for (const c of candidates) {
    if (fs.existsSync(path.join(c, 'riva/proto/riva_tts.proto'))) {
      return c;
    }
  }
  return path.resolve(__dirname, '../../../proto');
}

const PROTO_DIR = findProtoDir();
const DEFAULT_KEY = process.env.NVIDIA_API_KEY || '';

const FUNCTION_TTS = process.env.NVCF_FUNCTION_TTS || 'ddacc747-1269-4fab-bfd9-8f593dead106'; // chatterbox-multilingual
const FUNCTION_ASR = process.env.NVCF_FUNCTION_ASR || 'd3fe9151-442b-4204-a70d-5fcc597fd610'; // parakeet-tdt-0.6b-en-US-asr-offline

function logErr(msg) {
  process.stderr.write('[RivaWorker] ' + msg + '\n');
}

function sendJson(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

// 1. Initialize Protos & gRPC Clients once
let ttsClient, asrClient;
try {
  const ttsDef = protoLoader.loadSync(
    path.join(PROTO_DIR, 'riva/proto/riva_tts.proto'),
    { keepCase: true, longs: String, enums: String, defaults: true, oneofs: true, includeDirs: [PROTO_DIR] }
  );
  const asrDef = protoLoader.loadSync(
    path.join(PROTO_DIR, 'riva/proto/riva_asr.proto'),
    { keepCase: true, longs: String, enums: String, defaults: true, oneofs: true, includeDirs: [PROTO_DIR] }
  );

  const ttsProto = grpc.loadPackageDefinition(ttsDef);
  const asrProto = grpc.loadPackageDefinition(asrDef);

  ttsClient = new ttsProto.nvidia.riva.tts.RivaSpeechSynthesis('grpc.nvcf.nvidia.com:443', grpc.credentials.createSsl());
  asrClient = new asrProto.nvidia.riva.asr.RivaSpeechRecognition('grpc.nvcf.nvidia.com:443', grpc.credentials.createSsl());

  logErr('gRPC clients initialized with persistent SSL channels');
} catch (err) {
  logErr('Failed to initialize gRPC: ' + err.message);
  process.exit(1);
}

// Active calls map for cancellation
const activeCalls = new Map();

function handleTtsStream(req) {
  const { id, text, voice = 'Chatterbox-Multilingual', sample_rate = 24000 } = req;
  const meta = new grpc.Metadata();
  meta.add('authorization', 'Bearer ' + DEFAULT_KEY);
  meta.add('function-id', FUNCTION_TTS);

  const t0 = Date.now();
  let chunkCount = 0;

  try {
    const call = ttsClient.SynthesizeOnline(meta);
    activeCalls.set(id, call);

    call.on('data', (resp) => {
      if (resp.audio && resp.audio.length > 0) {
        chunkCount++;
        sendJson({
          type: 'tts_chunk',
          id,
          audio: resp.audio.toString('base64'),
          chunk_index: chunkCount,
          sample_rate,
          elapsed_ms: Date.now() - t0,
        });
      }
    });

    call.on('error', (err) => {
      activeCalls.delete(id);
      sendJson({ type: 'tts_error', id, error: err.message });
    });

    call.on('end', () => {
      activeCalls.delete(id);
      sendJson({ type: 'tts_end', id, total_chunks: chunkCount, total_ms: Date.now() - t0 });
    });

    call.write({
      text: text,
      language_code: 'en-US',
      encoding: 'LINEAR_PCM',
      sample_rate_hz: sample_rate,
      voice_name: 'Chatterbox-Multilingual',
    });
    call.end();
  } catch (err) {
    activeCalls.delete(id);
    sendJson({ type: 'tts_error', id, error: err.message });
  }
}

function handleAsr(req) {
  const { id, audio, sample_rate = 16000 } = req;
  const meta = new grpc.Metadata();
  meta.add('authorization', 'Bearer ' + DEFAULT_KEY);
  meta.add('function-id', FUNCTION_ASR);

  const t0 = Date.now();
  const audioBuffer = Buffer.from(audio, 'base64');

  asrClient.Recognize(
    {
      config: {
        encoding: 'LINEAR_PCM',
        sample_rate_hertz: sample_rate,
        language_code: 'en-US',
        max_alternatives: 1,
        model: 'parakeet-tdt-0.6b-en-US-asr-offline',
      },
      audio: audioBuffer,
    },
    meta,
    { deadline: Date.now() + 15000 },
    (err, resp) => {
      if (err) {
        sendJson({ type: 'asr_error', id, error: err.message });
        return;
      }

      let text = '';
      if (resp && resp.results && resp.results.length > 0) {
        for (const res of resp.results) {
          if (res.alternatives && res.alternatives.length > 0) {
            const alt = res.alternatives[0].transcript || '';
            text += (text ? ' ' : '') + alt.trim();
          }
        }
      }
      text = text.replace(/<unk>/g, '').replace(/unk/g, '').trim();

      sendJson({
        type: 'asr_final',
        id,
        text,
        elapsed_ms: Date.now() - t0,
      });
    }
  );
}

function handleCancel(req) {
  const { id } = req;
  if (id && activeCalls.has(id)) {
    try {
      activeCalls.get(id).cancel();
    } catch {
      // ignore
    }
    activeCalls.delete(id);
  }
}

// 2. Readline on stdin
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false,
});

rl.on('line', (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;
  try {
    const req = JSON.parse(trimmed);
    if (req.action === 'tts_stream') {
      handleTtsStream(req);
    } else if (req.action === 'asr') {
      handleAsr(req);
    } else if (req.action === 'cancel') {
      handleCancel(req);
    } else if (req.action === 'ping') {
      sendJson({ type: 'pong', id: req.id });
    }
  } catch (err) {
    logErr('Failed to process input line: ' + err.message);
  }
});

// Signal ready
sendJson({ type: 'ready' });
