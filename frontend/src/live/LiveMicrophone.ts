/**
 * HSBot Live Voice System - Live Microphone Capture
 * 
 * Captures user audio from navigator.mediaDevices.getUserMedia,
 * computes realtime volume levels (RMS), and extracts 16kHz 16-bit PCM chunks.
 */

import { LiveLogger } from './LiveLogger'

export interface MicrophoneOptions {
  sampleRate?: number
  onAudioChunk?: (pcmData: Int16Array, base64: string) => void
  onVolumeChange?: (volume: number) => void // 0.0 to 1.0
  onSpeechInterim?: (text: string) => void
  onSpeechFinal?: (text: string) => void
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
  private speechRecognition: any = null
  private isCapturing = false
  private isMuted = false
  private hasSpokenInTurn = false
  private speechFramesCount = 0
  private lastVoiceTimestamp = 0
  private options: MicrophoneOptions

  constructor(options: MicrophoneOptions = {}) {
    this.options = {
      sampleRate: 16000,
      ...options,
    }
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
      LiveLogger.info('Requesting microphone access...')
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })

      this.mediaStream = stream

      // Create AudioContext (fallback to default hardware rate for maximum browser compatibility)
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      try {
        this.audioContext = new AudioContextClass({ sampleRate: 16000 })
      } catch {
        this.audioContext = new AudioContextClass()
      }

      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume()
      }

      const currentSampleRate = this.audioContext.sampleRate || 16000
      LiveLogger.info(`AudioContext initialized at sampleRate: ${currentSampleRate}Hz`)

      this.sourceNode = this.audioContext.createMediaStreamSource(stream)
      // Buffer size 2048 gives low-latency chunks (~40ms - 128ms depending on rate)
      this.processorNode = this.audioContext.createScriptProcessor(2048, 1, 1)

      // Prevent V8 from garbage-collecting ScriptProcessorNode (Chrome WebAudio bug)
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
          this.options.onVolumeChange?.(0)
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

        // Non-linear responsive normalized volume (0.0 to 1.0) for visualizer
        const normalizedVolume = Math.min(1.0, Math.pow(rms * 12.0, 0.75))
        this.options.onVolumeChange?.(normalizedVolume)

        // Sensitive client-side VAD: detects normal conversational speech accurately
        // Normal speech has peak > 0.015 or rms > 0.002
        const isVoice = peak > 0.015 || rms > 0.002 || normalizedVolume > 0.025
        if (isVoice) {
          this.hasSpokenInTurn = true
          this.speechFramesCount++
          this.lastVoiceTimestamp = Date.now()
        } else if (this.hasSpokenInTurn) {
          // Snappy conversational turn-taking: pause for >= 750ms after speech triggers turn commit
          if (Date.now() - this.lastVoiceTimestamp >= 750) {
            this.hasSpokenInTurn = false
            const frames = this.speechFramesCount
            this.speechFramesCount = 0
            if (frames >= 3) {
              LiveLogger.info('Client VAD: End of speech turn detected')
              this.options.onSpeechEnd?.()
            }
          }
        }

        // 2. Downsample Float32 from currentSampleRate to exactly 16000Hz 16-bit PCM
        const pcm16 = downsampleTo16k(inputChannel, currentSampleRate)

        // 3. Convert PCM to base64
        const uint8 = new Uint8Array(pcm16.buffer, pcm16.byteOffset, pcm16.byteLength)
        let binary = ''
        const chunkSize = 8192
        for (let i = 0; i < uint8.length; i += chunkSize) {
          const sub = uint8.subarray(i, i + chunkSize)
          binary += String.fromCharCode.apply(null, Array.from(sub))
        }
        const base64 = btoa(binary)

        this.options.onAudioChunk?.(pcm16, base64)
      }

      this.sourceNode.connect(this.processorNode)
      this.processorNode.connect(this.muteGainNode)
      this.muteGainNode.connect(this.audioContext.destination)
      this.isCapturing = true

      // Optional Browser Native SpeechRecognition for immediate, local recognition
      this.initSpeechRecognition()

      LiveLogger.info('Microphone capture started successfully')
      return true
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err))
      LiveLogger.error('Failed to start microphone:', error.message)
      this.options.onError?.(error)
      this.stop()
      return false
    }
  }

  private initSpeechRecognition() {
    try {
      const SpeechRecognitionClass =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      if (!SpeechRecognitionClass) return

      const recognition = new SpeechRecognitionClass()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'

      recognition.onresult = (event: any) => {
        if (!this.isCapturing || this.isMuted) return

        let interimText = ''
        let finalText = ''

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const res = event.results[i]
          const transcript = res[0]?.transcript || ''
          if (res.isFinal) {
            finalText += transcript
          } else {
            interimText += transcript
          }
        }

        if (interimText.trim()) {
          this.options.onSpeechInterim?.(interimText.trim())
        }
        if (finalText.trim()) {
          this.options.onSpeechFinal?.(finalText.trim())
        }
      }

      recognition.onerror = (event: any) => {
        // Speech recognition error (e.g. no-speech or network) is non-fatal; audio PCM stream continues
        LiveLogger.debug('Browser SpeechRecognition event:', event.error)
      }

      recognition.onend = () => {
        // Restart if still capturing and not muted
        if (this.isCapturing && !this.isMuted) {
          try {
            recognition.start()
          } catch {
            // ignore
          }
        }
      }

      recognition.start()
      this.speechRecognition = recognition
      LiveLogger.info('Browser SpeechRecognition initialized for rapid transcription')
    } catch (err) {
      LiveLogger.debug('Native SpeechRecognition unavailable or not permitted:', err)
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
      this.options.onVolumeChange?.(0)
    }
  }

  getMuted(): boolean {
    return this.isMuted
  }

  getCapturing(): boolean {
    return this.isCapturing
  }

  /**
   * Completely stop and release microphone resources
   */
  stop() {
    this.isCapturing = false

    if (this.speechRecognition) {
      try {
        this.speechRecognition.onend = null
        this.speechRecognition.onerror = null
        this.speechRecognition.onresult = null
        this.speechRecognition.stop()
      } catch {
        // ignore
      }
      this.speechRecognition = null
    }

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

    this.options.onVolumeChange?.(0)
    LiveLogger.info('Microphone capture stopped and released')
  }
}
