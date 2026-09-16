import path from 'path'
import fs from 'fs'
import * as grpc from '@grpc/grpc-js'
import * as protoLoader from '@grpc/proto-loader'

const NVIDIA_API_KEY =
  process.env.NVIDIA_API_KEY ||
  (process.env.NVIDIA_API_KEYS ? process.env.NVIDIA_API_KEYS.split(',')[0].trim() : '') ||
  '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'

const NVCF_GRPC_ENDPOINT = 'grpc.nvcf.nvidia.com:443'
const ASR_FUNCTION_ID_PRIMARY = 'd3fe9151-442b-4204-a70d-5fcc597fd610' // parakeet-tdt-0.6b-en-US-asr-offline
const ASR_FUNCTION_ID_FALLBACK = '1598d209-5e27-4d3c-8079-4751568b1081' // ai-parakeet-ctc-1_1b-asr
const TTS_FUNCTION_ID = 'ddacc747-1269-4fab-bfd9-8f593dead106' // chatterbox-multilingual

function getProtoDir(): string {
  const candidates = [
    path.resolve(process.cwd(), 'proto'),
    path.resolve(process.cwd(), 'backend/riva_proto'),
    path.resolve(process.cwd(), '../proto'),
    path.resolve(process.cwd(), '../backend/riva_proto'),
    '/app/applet/proto',
    '/app/applet/backend/riva_proto',
  ]
  for (const c of candidates) {
    try {
      if (fs.existsSync(path.join(c, 'riva/proto/riva_tts.proto'))) {
        return c
      }
    } catch {
      // continue
    }
  }
  return path.resolve(process.cwd(), 'proto')
}

// Helper: Convert raw 16-bit PCM to RIFF WAV
export function pcmToWav(
  pcmBuffer: Buffer,
  sampleRate = 24000,
  numChannels = 1,
  bitDepth = 16
): Buffer {
  const byteRate = (sampleRate * numChannels * bitDepth) / 8
  const blockAlign = (numChannels * bitDepth) / 8
  const dataLength = pcmBuffer.length
  const buffer = Buffer.alloc(44 + dataLength)

  buffer.write('RIFF', 0)
  buffer.writeUInt32LE(36 + dataLength, 4)
  buffer.write('WAVE', 8)
  buffer.write('fmt ', 12)
  buffer.writeUInt32LE(16, 16)
  buffer.writeUInt16LE(1, 20) // PCM
  buffer.writeUInt16LE(numChannels, 22)
  buffer.writeUInt32LE(sampleRate, 24)
  buffer.writeUInt32LE(byteRate, 28)
  buffer.writeUInt16LE(blockAlign, 32)
  buffer.writeUInt16LE(bitDepth, 34)
  buffer.write('data', 36)
  buffer.writeUInt32LE(dataLength, 40)
  pcmBuffer.copy(buffer, 44)

  return buffer
}

let geminiQuotaBlockedUntil = 0

class NvidiaLiveService {
  private asrClient: any = null
  private ttsClient: any = null

  private getAsrClient() {
    if (!this.asrClient) {
      const protoDir = getProtoDir()
      const packageDef = protoLoader.loadSync(
        path.join(protoDir, 'riva/proto/riva_asr.proto'),
        {
          keepCase: true,
          longs: String,
          enums: String,
          defaults: true,
          oneofs: true,
          includeDirs: [protoDir],
        }
      )
      const proto = grpc.loadPackageDefinition(packageDef) as any
      this.asrClient = new proto.nvidia.riva.asr.RivaSpeechRecognition(
        NVCF_GRPC_ENDPOINT,
        grpc.credentials.createSsl()
      )
    }
    return this.asrClient
  }

  private getTtsClient() {
    if (!this.ttsClient) {
      const protoDir = getProtoDir()
      const packageDef = protoLoader.loadSync(
        path.join(protoDir, 'riva/proto/riva_tts.proto'),
        {
          keepCase: true,
          longs: String,
          enums: String,
          defaults: true,
          oneofs: true,
          includeDirs: [protoDir],
        }
      )
      const proto = grpc.loadPackageDefinition(packageDef) as any
      this.ttsClient = new proto.nvidia.riva.tts.RivaSpeechSynthesis(
        NVCF_GRPC_ENDPOINT,
        grpc.credentials.createSsl()
      )
    }
    return this.ttsClient
  }

  /**
   * Transcribe 16kHz raw PCM speech to text
   */
  async transcribePCM(pcmBuffer: Buffer, language = 'en-US'): Promise<string> {
    if (!pcmBuffer || pcmBuffer.length < 3200) {
      return ''
    }

    // 1. Primary: Native low-latency NVIDIA Riva Parakeet ASR via gRPC (~1.0s)
    try {
      const client = this.getAsrClient()
      const makeCall = (functionId: string): Promise<string> => {
        return new Promise((resolve, reject) => {
          const meta = new grpc.Metadata()
          meta.add('authorization', `Bearer ${NVIDIA_API_KEY}`)
          meta.add('function-id', functionId)

          const req = {
            config: {
              encoding: 'LINEAR_PCM',
              sample_rate_hertz: 16000,
              language_code: language,
              max_alternatives: 1,
              model: 'parakeet-tdt-0.6b-en-US-asr-offline',
            },
            audio: pcmBuffer,
          }

          client.Recognize(req, meta, { deadline: Date.now() + 5000 }, (err: any, resp: any) => {
            if (err) return reject(err)
            const transcript =
              resp?.results
                ?.map((r: any) => r.alternatives?.[0]?.transcript)
                .filter(Boolean)
                .join(' ') || ''
            const cleaned = transcript.replace(/<unk>|unk/gi, '').trim()
            resolve(cleaned)
          })
        })
      }

      const res = await makeCall(ASR_FUNCTION_ID_PRIMARY)
      if (res && res.length > 0) return res
      return ''
    } catch (rivaErr: any) {
      console.warn('[NvidiaLiveService] Riva ASR error:', rivaErr?.message)
      return ''
    }
  }

  /**
   * Helper: Normalize voice to valid Riva TTS model voice
   */
  private normalizeVoice(voiceName?: string): string {
    if (!voiceName) return 'Chatterbox-Multilingual'
    const v = voiceName.toLowerCase()
    if (v.includes('chatterbox') || v.includes('english') || v.includes('female') || v.includes('male') || v.includes('default')) {
      return 'Chatterbox-Multilingual'
    }
    return voiceName
  }

  /**
   * Synthesize text to WAV audio using NVIDIA Riva Chatterbox TTS
   */
  async synthesizeSpeech(
    text: string,
    voiceName = 'Chatterbox-Multilingual',
    sampleRate = 24000
  ): Promise<Buffer> {
    const client = this.getTtsClient()
    const targetVoice = this.normalizeVoice(voiceName)

    const doCall = (voiceToUse: string): Promise<Buffer> => {
      return new Promise((resolve, reject) => {
        const meta = new grpc.Metadata()
        meta.add('authorization', `Bearer ${NVIDIA_API_KEY}`)
        meta.add('function-id', TTS_FUNCTION_ID)

        const req = {
          text,
          language_code: 'en-US',
          encoding: 'LINEAR_PCM',
          sample_rate_hz: sampleRate,
          voice_name: voiceToUse,
        }

        client.Synthesize(req, meta, { deadline: Date.now() + 15000 }, (err: any, resp: any) => {
          if (err) {
            return reject(err)
          }
          if (!resp?.audio || resp.audio.length === 0) {
            return reject(new Error('NVIDIA Riva TTS returned empty audio'))
          }

          const wavBuffer = pcmToWav(resp.audio, sampleRate, 1, 16)
          resolve(wavBuffer)
        })
      })
    }

    try {
      return await doCall(targetVoice)
    } catch {
      if (targetVoice !== 'Chatterbox-Multilingual') {
        return await doCall('Chatterbox-Multilingual')
      }
      return await doCall('')
    }
  }

  /**
   * Synthesize text and return base64 PCM + metadata
   */
  async synthesizePCM(
    text: string,
    voiceName = 'Chatterbox-Multilingual',
    sampleRate = 24000
  ): Promise<{ audioBase64: string; bytes: number; sampleRate: number }> {
    const client = this.getTtsClient()
    const targetVoice = this.normalizeVoice(voiceName)

    const doCall = (voiceToUse: string): Promise<{ audioBase64: string; bytes: number; sampleRate: number }> => {
      return new Promise((resolve, reject) => {
        const meta = new grpc.Metadata()
        meta.add('authorization', `Bearer ${NVIDIA_API_KEY}`)
        meta.add('function-id', TTS_FUNCTION_ID)

        const req = {
          text,
          language_code: 'en-US',
          encoding: 'LINEAR_PCM',
          sample_rate_hz: sampleRate,
          voice_name: voiceToUse,
        }

        client.Synthesize(req, meta, { deadline: Date.now() + 15000 }, (err: any, resp: any) => {
          if (err) {
            return reject(err)
          }
          const audioBuffer = resp?.audio || Buffer.alloc(0)
          resolve({
            audioBase64: audioBuffer.toString('base64'),
            bytes: audioBuffer.length,
            sampleRate,
          })
        })
      })
    }

    try {
      return await doCall(targetVoice)
    } catch {
      if (targetVoice !== 'Chatterbox-Multilingual') {
        return await doCall('Chatterbox-Multilingual')
      }
      return await doCall('')
    }
  }

  /**
   * Stream synthesize text in real-time via SynthesizeOnline gRPC
   */
  streamSynthesizePCM(
    text: string,
    voiceName = 'Chatterbox-Multilingual',
    sampleRate = 24000,
    onAudioChunk?: (chunkB64: string) => void
  ): Promise<void> {
    const client = this.getTtsClient()

    return new Promise((resolve, reject) => {
      const meta = new grpc.Metadata()
      meta.add('authorization', `Bearer ${NVIDIA_API_KEY}`)
      meta.add('function-id', TTS_FUNCTION_ID)

      try {
        const call = client.SynthesizeOnline(meta)

        call.on('data', (resp: any) => {
          if (resp?.audio && resp.audio.length > 0 && onAudioChunk) {
            onAudioChunk(resp.audio.toString('base64'))
          }
        })

        call.on('error', (err: any) => {
          reject(err)
        })

        call.on('end', () => {
          resolve()
        })

        call.write({
          text,
          language_code: 'en-US',
          encoding: 'LINEAR_PCM',
          sample_rate_hz: sampleRate,
          voice_name: voiceName,
        })
        call.end()
      } catch (err) {
        reject(err)
      }
    })
  }

  /**
   * Call NVIDIA LLM for conversational voice response
   */
  async chatCompletion(messages: any[], stream = false) {
    const res = await fetch('https://integrate.api.nvidia.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${NVIDIA_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'meta/llama-3.2-11b-vision-instruct',
        messages,
        temperature: 0.6,
        max_tokens: 150,
        stream,
      }),
    })

    if (!res.ok) {
      console.warn(`[NvidiaLiveService] Primary LLM failed (${res.status}), trying fallback model meta/llama-3.2-90b-vision-instruct...`)
      try {
        const fallbackRes = await fetch('https://integrate.api.nvidia.com/v1/chat/completions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${NVIDIA_API_KEY}`,
          },
          body: JSON.stringify({
            model: 'meta/llama-3.2-90b-vision-instruct',
            messages,
            temperature: 0.6,
            max_tokens: 150,
            stream,
          }),
        })
        if (fallbackRes.ok) return fallbackRes
      } catch {
        // continue to error
      }
      const errText = await res.text()
      throw new Error(`NVIDIA LLM API error ${res.status}: ${errText}`)
    }

    return res
  }
}

export const nvidiaLiveService = new NvidiaLiveService()
