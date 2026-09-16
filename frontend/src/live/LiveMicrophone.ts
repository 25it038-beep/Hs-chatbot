/**
 * HSBot Live Voice System - Live Microphone Capture
 * 
 * Captures user audio from navigator.mediaDevices.getUserMedia,
 * computes realtime volume levels (RMS), and extracts 16kHz 16-bit PCM chunks.
 */

import { LiveLogger } from './LiveLogger'

export interface MicrophoneOptions {
  sampleRate?: number
  silenceTimeoutMs?: number
  onAudioChunk?: (pcmData: Int16Array, base64: string, rms: number, frameCount: number, bytesSent: number) => void
  onVolumeChange?: (volume: number, rawRms: number) => void
  onSpeechStart?: () => void
  onSpeechEnd?: () => void
  onError?: (error: Error) => void
}

/**
 * Downsamples Float32 audio buffer to 16kHz 16-bit linear PCM with window averaging
 */
function downsampleTo16k(input: Float32Array, sourceSampleRate: number): Int16Array {
  if (sourceSampleRate === 16000) {
    const pcm16 = new Int16Array(input.length)
    for (let i = 0; i < input.length; i++) {
      const s = Math.max(-1, Math.min(1, input[i]))
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
    return pcm16
  }

  const ratio = sourceSampleRate / 16000
  const newLength = Math.max(1, Math.floor(input.length / ratio))
  const result = new Int16Array(newLength)
  let offsetBuffer = 0

  for (let i = 0; i < newLength; i++) {
    const nextOffsetBuffer = Math.min(input.length, Math.round((i + 1) * ratio))
    let accum = 0
    let count = 0
    for (let j = offsetBuffer; j < nextOffsetBuffer; j++) {
      accum += input[j]
      count++
    }
    const avg = count > 0 ? accum / count : 0
    const s = Math.max(-1, Math.min(1, avg))
    result[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    offsetBuffer = nextOffsetBuffer
  }

  return result
}

export class LiveMicrophone {
  private mediaStream: MediaStream | null = null
  private audioContext: AudioContext | null = null
  private sourceNode: MediaStreamAudioSourceNode | null = null
  private processorNode: ScriptProcessorNode | null = null
  private muteGainNode: GainNode | null = null
  private isCapturing = false
  private isMuted = false
  private hasSpokenInTurn = false
  private speechFramesCount = 0
  private lastVoiceTimestamp = 0
  private silenceTimeoutMs = 1500
  private options: MicrophoneOptions

  // Real-time diagnostics & telemetry
  private audioFramesCount = 0
  private audioBytesSent = 0
  private currentRms = 0
  private micSampleRate = 16000
  private micChannels = 1

  constructor(options: MicrophoneOptions = {}) {
    this.options = {
      sampleRate: 16000,
      silenceTimeoutMs: 1500,
      ...options,
    }
    this.silenceTimeoutMs = this.options.silenceTimeoutMs || 1500
  }

  getMetrics() {
    return {
      isReady: this.isCapturing && !this.isMuted,
      sampleRate: this.micSampleRate,
      channels: this.micChannels,
      rms: this.currentRms,
      framesCount: this.audioFramesCount,
      bytesSent: this.audioBytesSent,
    }
  }

  /**
   * Adjust speech silence pause duration dynamically
   */
  setSilenceTimeout(ms: number) {
    this.silenceTimeoutMs = Math.max(600, Math.min(5000, ms))
    LiveLogger.info(`Microphone silence timeout set to: ${this.silenceTimeoutMs}ms`)
  }

  /**
   * Request microphone permissions and start audio streaming
   */
  async start(): Promise<boolean> {
    if (this.isCapturing) {
      LiveLogger.warn('Microphone already capturing')
      return true
    }

    try {
      LiveLogger.info('Requesting microphone access with echo cancellation & noise suppression...')
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })

      // Strict track verification
      const tracks = stream.getAudioTracks()
      if (!tracks || tracks.length === 0) {
        throw new Error('No audio tracks returned by microphone device')
      }
      const track = tracks[0]
      if (track.readyState !== 'live') {
        throw new Error(`Microphone track is not live (readyState: ${track.readyState})`)
      }
      if (!track.enabled) {
        track.enabled = true
      }

      this.mediaStream = stream
      this.micChannels = 1

      // Create AudioContext
      const AudioContextClass =
        window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      try {
        this.audioContext = new AudioContextClass({ sampleRate: 16000 })
      } catch {
        this.audioContext = new AudioContextClass()
      }

      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume()
      }

      this.micSampleRate = this.audioContext.sampleRate || 16000
      LiveLogger.info(`AudioContext initialized at sampleRate: ${this.micSampleRate}Hz (Tracks: ${tracks.length})`)

      this.sourceNode = this.audioContext.createMediaStreamSource(stream)
      // Buffer size 2048 gives responsive ~40ms-128ms chunks
      this.processorNode = this.audioContext.createScriptProcessor(2048, 1, 1)

      // Prevent V8 garbage collection
      try {
        ;(window as any).__hsbot_live_processor = this.processorNode
        ;(window as any).__hsbot_live_source = this.sourceNode
        ;(window as any).__hsbot_live_ctx = this.audioContext
      } catch {
        // ignore
      }

      // Small near-zero gain keeps the audio subgraph active in browser power-saving modes
      this.muteGainNode = this.audioContext.createGain()
      this.muteGainNode.gain.value = 0.00001

      this.processorNode.onaudioprocess = (event) => {
        if (!this.isCapturing || this.isMuted) {
          this.currentRms = 0
          this.options.onVolumeChange?.(0, 0)
          return
        }

        const inputChannel = event.inputBuffer.getChannelData(0)

        // 1. Calculate RMS and Peak audio levels
        let sumSquares = 0
        let peak = 0
        for (let i = 0; i < inputChannel.length; i++) {
          const val = inputChannel[i]
          const abs = Math.abs(val)
          if (abs > peak) peak = abs
          sumSquares += val * val
        }
        const rms = Math.sqrt(sumSquares / inputChannel.length)
        this.currentRms = rms

        // Non-linear responsive normalized volume (0.0 to 1.0) for visualizer
        const normalizedVolume = Math.min(1.0, Math.pow(rms * 12.0, 0.75))
        this.options.onVolumeChange?.(normalizedVolume, rms)

        // Sensitive client-side VAD: detects voice onset
        const isVoice = peak > 0.018 || rms > 0.0025 || normalizedVolume > 0.03
        if (isVoice) {
          if (!this.hasSpokenInTurn) {
            this.speechFramesCount++
            if (this.speechFramesCount >= 3) {
              this.hasSpokenInTurn = true
              this.options.onSpeechStart?.()
            }
          }
          this.lastVoiceTimestamp = Date.now()
        } else if (this.hasSpokenInTurn) {
          const timeout = this.silenceTimeoutMs || 1500
          if (Date.now() - this.lastVoiceTimestamp >= timeout) {
            this.hasSpokenInTurn = false
            this.speechFramesCount = 0
            LiveLogger.info(`Client VAD: End of speech detected after ${timeout}ms pause`)
            this.options.onSpeechEnd?.()
          }
        } else {
          if (this.speechFramesCount > 0 && Date.now() - this.lastVoiceTimestamp > 300) {
            this.speechFramesCount = 0
          }
        }

        // 2. Downsample Float32 to exactly 16000Hz 16-bit PCM
        const pcm16 = downsampleTo16k(inputChannel, this.micSampleRate)

        // 3. Convert PCM to base64
        const uint8 = new Uint8Array(pcm16.buffer, pcm16.byteOffset, pcm16.byteLength)
        let binary = ''
        const chunkSize = 8192
        for (let i = 0; i < uint8.length; i += chunkSize) {
          const sub = uint8.subarray(i, i + chunkSize)
          binary += String.fromCharCode.apply(null, Array.from(sub))
        }
        const base64 = btoa(binary)

        this.audioFramesCount++
        this.audioBytesSent += pcm16.byteLength

        this.options.onAudioChunk?.(pcm16, base64, rms, this.audioFramesCount, this.audioBytesSent)
      }

      this.sourceNode.connect(this.processorNode)
      this.processorNode.connect(this.muteGainNode)
      this.muteGainNode.connect(this.audioContext.destination)
      this.isCapturing = true

      LiveLogger.info('Microphone capture started and verified successfully')
      return true
    } catch (err: any) {
      let friendlyMessage = err?.message || String(err)
      if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError') {
        friendlyMessage = 'Microphone permission denied. Please allow microphone access in your browser settings.'
      } else if (err?.name === 'NotFoundError' || err?.name === 'DevicesNotFoundError') {
        friendlyMessage = 'No microphone device was detected on your system.'
      } else if (err?.name === 'NotReadableError' || err?.name === 'TrackStartError') {
        friendlyMessage = 'Microphone is currently in use or blocked by another application.'
      } else if (err?.name === 'OverconstrainedError') {
        friendlyMessage = 'Audio hardware does not support the requested configuration.'
      }

      const error = new Error(friendlyMessage)
      LiveLogger.error('Failed to start microphone:', error.message)
      this.options.onError?.(error)
      this.stop()
      return false
    }
  }

  /**
   * Toggle mute state
   */
  setMuted(muted: boolean) {
    this.isMuted = muted
    if (this.mediaStream) {
      this.mediaStream.getAudioTracks().forEach((track) => {
        track.enabled = !muted
      })
    }
    if (muted) {
      this.currentRms = 0
      this.options.onVolumeChange?.(0, 0)
    }
  }

  getMuted(): boolean {
    return this.isMuted
  }

  getCapturing(): boolean {
    return this.isCapturing
  }

  resetMetrics() {
    this.audioFramesCount = 0
    this.audioBytesSent = 0
    this.currentRms = 0
  }

  /**
   * Completely stop and release microphone resources
   */
  stop() {
    this.isCapturing = false

    if (this.muteGainNode) {
      try {
        this.muteGainNode.disconnect()
      } catch {
        // ignore
      }
      this.muteGainNode = null
    }

    if (this.processorNode) {
      try {
        this.processorNode.disconnect()
        this.processorNode.onaudioprocess = null
      } catch (e) {
        // ignore
      }
      this.processorNode = null
    }

    if (this.sourceNode) {
      try {
        this.sourceNode.disconnect()
      } catch (e) {
        // ignore
      }
      this.sourceNode = null
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => {
        try {
          track.stop()
        } catch (e) {
          // ignore
        }
      })
      this.mediaStream = null
    }

    if (this.audioContext) {
      try {
        if (this.audioContext.state !== 'closed') {
          this.audioContext.close()
        }
      } catch (e) {
        // ignore
      }
      this.audioContext = null
    }

    this.currentRms = 0
    this.options.onVolumeChange?.(0, 0)
    LiveLogger.info('Microphone capture stopped and released')
  }
}
