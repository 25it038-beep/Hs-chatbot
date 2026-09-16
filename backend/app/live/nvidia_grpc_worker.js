#!/usr/bin/env node
/**
 * NVIDIA Riva gRPC Worker for HSBot Live Voice
 * 
 * Bridges NVIDIA Cloud Functions (NVCF) gRPC services:
 * - ASR: NVIDIA Parakeet TDT 0.6B / Whisper Large v3 (grpc.nvcf.nvidia.com:443)
 * - TTS: NVIDIA Chatterbox Multilingual (grpc.nvcf.nvidia.com:443)
 */

const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');
const fs = require('fs');

const PROTO_DIR = path.resolve(__dirname, '../../../proto');
const DEFAULT_KEY = process.env.NVIDIA_API_KEY || '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';

// Function IDs on NVCF
const FUNCTION_TTS = process.env.NVCF_FUNCTION_TTS || 'ddacc747-1269-4fab-bfd9-8f593dead106'; // chatterbox-multilingual
const FUNCTION_ASR = process.env.NVCF_FUNCTION_ASR || 'd3fe9151-442b-4204-a70d-5fcc597fd610'; // parakeet-tdt-0.6b-en-US-asr-offline

function loadProtos() {
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

  const ttsClient = new ttsProto.nvidia.riva.tts.RivaSpeechSynthesis(
    'grpc.nvcf.nvidia.com:443',
    grpc.credentials.createSsl()
  );
  const asrClient = new asrProto.nvidia.riva.asr.RivaSpeechRecognition(
    'grpc.nvcf.nvidia.com:443',
    grpc.credentials.createSsl()
  );

  return { ttsClient, asrClient };
}

async function handleTTS(text, voice = 'Chatterbox-Multilingual', sampleRate = 24000) {
  const { ttsClient } = loadProtos();
  const meta = new grpc.Metadata();
  meta.add('authorization', 'Bearer ' + DEFAULT_KEY);
  meta.add('function-id', FUNCTION_TTS);

  return new Promise((resolve, reject) => {
    ttsClient.Synthesize(
      {
        text: text,
        language_code: 'en-US',
        encoding: 'LINEAR_PCM',
        sample_rate_hz: sampleRate,
        voice_name: voice,
      },
      meta,
      { deadline: Date.now() + 20000 },
      (err, resp) => {
        if (err) {
          return reject(err);
        }
        const audioBuffer = resp.audio || Buffer.alloc(0);
        resolve({
          success: true,
          audio: audioBuffer.toString('base64'),
          bytes: audioBuffer.length,
          sampleRate: sampleRate,
        });
      }
    );
  });
}

async function handleASR(audioBuffer, sampleRate = 16000) {
  const { asrClient } = loadProtos();
  const meta = new grpc.Metadata();
  meta.add('authorization', 'Bearer ' + DEFAULT_KEY);
  meta.add('function-id', FUNCTION_ASR);

  return new Promise((resolve, reject) => {
    asrClient.Recognize(
      {
        config: {
          encoding: 'LINEAR_PCM',
          sample_rate_hertz: sampleRate,
          language_code: 'en-US',
          max_alternatives: 1,
          model: 'parakeet-tdt-0.6b-en-US-asr-offline',
        },
        audio: audioBuffer,
      },
      meta,
      { deadline: Date.now() + 20000 },
      (err, resp) => {
        if (err) {
          return reject(err);
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

        // Clean out any unknown token artifacts
        text = text.replace(/unk/g, '').trim();

        resolve({
          success: true,
          text: text,
          results: resp.results,
        });
      }
    );
  });
}

async function main() {
  const command = process.argv[2];

  if (command === 'tts') {
    const text = process.argv[3] || 'Hello';
    const voice = process.argv[4] || 'Chatterbox-Multilingual';
    try {
      const res = await handleTTS(text, voice);
      console.log(JSON.stringify(res));
      process.exit(0);
    } catch (e) {
      console.log(JSON.stringify({ success: false, error: e.message || String(e) }));
      process.exit(1);
    }
  } else if (command === 'asr') {
    const audioPathOrBase64 = process.argv[3];
    let audioBuffer;

    if (!audioPathOrBase64) {
      // Read from stdin
      const chunks = [];
      process.stdin.on('data', (chunk) => chunks.push(chunk));
      process.stdin.on('end', async () => {
        const fullBuf = Buffer.concat(chunks);
        try {
          const res = await handleASR(fullBuf);
          console.log(JSON.stringify(res));
          process.exit(0);
        } catch (e) {
          console.log(JSON.stringify({ success: false, error: e.message || String(e) }));
          process.exit(1);
        }
      });
      return;
    }

    if (fs.existsSync(audioPathOrBase64)) {
      audioBuffer = fs.readFileSync(audioPathOrBase64);
    } else {
      audioBuffer = Buffer.from(audioPathOrBase64, 'base64');
    }

    try {
      const res = await handleASR(audioBuffer);
      console.log(JSON.stringify(res));
      process.exit(0);
    } catch (e) {
      console.log(JSON.stringify({ success: false, error: e.message || String(e) }));
      process.exit(1);
    }
  } else {
    console.log(JSON.stringify({ success: false, error: `Unknown command: ${command}. Use 'tts' or 'asr'.` }));
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}
