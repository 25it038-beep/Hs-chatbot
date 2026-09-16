/**
 * Audio Capture and Playback Manager for HSBot Live Voice.
 * Bulletproof cross-platform microphone capture, hardware rate resampling to 16kHz Int16 PCM,
 * direct RMS metering, and zero-gap queued playback for streaming TTS chunks.
 */

export class LiveVoiceAudio {
  private micContext: AudioContext | null = null
  private playbackContext: AudioContext | null = null
  private micStream: MediaStream | null = null
  private micSource: MediaStreamAudioSourceNode | null = null
  private processor: ScriptProcessorNode | null = null
  private micAnalyser: AnalyserNode | null = null
  private outputAnalyser: AnalyserNode | null = null

  // Playback state
  private scheduledSources: AudioBufferSourceNode[] = []
  private nextPlayTime: number = 0
  private isPlayingAudio: boolean = false
  private playbackQueueLength: number = 0

  // Callbacks
  public onAudioData: ((pcmBytes: Uint8Array) => void) | null = null
  public onInputLevel: ((levelDb: number) => void) | null = null
  public onOutputLevel: ((levelDb: number) => void) | null = null
  public onPlaybackStateChange: ((isPlaying: boolean, queueLength: number) => void) | null = null

  public getMicAnalyser(): AnalyserNode | null {
    return this.micAnalyser
  }

  public getOutputAnalyser(): AnalyserNode | null {
    return this.outputAnalyser
  }

  public get isMicActive(): boolean {
    return !!this.micStream && this.micStream.active
  }

  public get isPlaybackActive(): boolean {
    return this.isPlayingAudio
  }

  public get queueLength(): number {
    return this.playbackQueueLength
  }

  public get sampleRate(): number {
    return 16000
  }

  /**
   * Initializes audio contexts.
   */
  public async init(): Promise<void> {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
    if (!AudioCtx) {
      throw new Error('Web Audio API is not supported in this environment.')
    }

    if (!this.playbackContext || this.playbackContext.state === 'closed') {
      this.playbackContext = new AudioCtx({ sampleRate: 24000 })
    }
    if (!this.outputAnalyser && this.playbackContext) {
      this.outputAnalyser = this.playbackContext.createAnalyser()
      this.outputAnalyser.fftSize = 256
      this.outputAnalyser.smoothingTimeConstant = 0.4
      this.outputAnalyser.connect(this.playbackContext.destination)
    }
    if (this.playbackContext.state === 'suspended') {
      await this.playbackContext.resume()
    }
  }

  /**
   * Starts microphone recording with hardware-native sample rate and resamples to 16kHz mono.
   */
  public async startMicrophone(): Promise<void> {
    await this.init()

    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
    // Do not force sampleRate on micContext constructor - use native hardware rate to avoid browser muting
    if (!this.micContext || this.micContext.state === 'closed') {
      this.micContext = new AudioCtx()
    }
    if (this.micContext.state === 'suspended') {
      await this.micContext.resume()
    }

    this.micStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    })

    this.micSource = this.micContext.createMediaStreamSource(this.micStream)
    
    // Connect Web Audio Analyser for 3D sphere reactivity
    this.micAnalyser = this.micContext.createAnalyser()
    this.micAnalyser.fftSize = 256
    this.micAnalyser.smoothingTimeConstant = 0.4
    this.micSource.connect(this.micAnalyser)

    // Buffer size 4096 gives ~85ms updates at 48kHz
    this.processor = this.micContext.createScriptProcessor(4096, 1, 1)

    const actualSampleRate = this.micContext.sampleRate

    this.processor.onaudioprocess = (e) => {
      const inputData = e.inputBuffer.getChannelData(0)
      if (!inputData || inputData.length === 0) return

      // 1. Direct RMS calculation from real audio samples
      let sumSq = 0
      for (let i = 0; i < inputData.length; i++) {
        sumSq += inputData[i] * inputData[i]
      }
      const rms = Math.sqrt(sumSq / inputData.length)
      const levelDb = rms > 0.00001 ? Math.max(-100, Math.round(20 * Math.log10(rms))) : -100

      if (this.onInputLevel) {
        this.onInputLevel(levelDb)
      }

      // 2. High-quality resampling to 16kHz Int16 linear PCM
      const pcm16 = this.resampleTo16kPCM(inputData, actualSampleRate)
      if (this.onAudioData) {
        this.onAudioData(new Uint8Array(pcm16.buffer))
      }
    }

    this.micSource.connect(this.processor)
    this.processor.connect(this.micContext.destination)
  }

  /**
   * Stops microphone capture and releases hardware track.
   */
  public stopMicrophone(): void {
    if (this.processor) {
      this.processor.disconnect()
      this.processor.onaudioprocess = null
      this.processor = null
    }
    if (this.micSource) {
      this.micSource.disconnect()
      this.micSource = null
    }
    if (this.micStream) {
      this.micStream.getTracks().forEach((track) => track.stop())
      this.micStream = null
    }
    if (this.micContext) {
      this.micContext.close().catch(() => {})
      this.micContext = null
    }
    if (this.micAnalyser) {
      try { this.micAnalyser.disconnect() } catch (_) {}
      this.micAnalyser = null
    }
    if (this.onInputLevel) {
      this.onInputLevel(-100)
    }
  }

  /**
   * Plays a streaming 16-bit PCM audio chunk seamlessly without gaps.
   */
  public async playChunk(pcmBuffer: ArrayBuffer, sampleRate: number = 24000): Promise<void> {
    await this.init()
    if (!this.playbackContext) return

    const int16Array = new Int16Array(pcmBuffer)
    const float32Array = new Float32Array(int16Array.length)
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0
    }

    if (this.playbackContext.state === 'suspended') {
      await this.playbackContext.resume()
    }

    const audioBuffer = this.playbackContext.createBuffer(1, float32Array.length, sampleRate)
    audioBuffer.getChannelData(0).set(float32Array)

    const source = this.playbackContext.createBufferSource()
    source.buffer = audioBuffer
    
    // Always connect directly to destination for crystal clear speaker output
    source.connect(this.playbackContext.destination)
    
    // Also connect to outputAnalyser for 3D sphere reactivity
    if (this.outputAnalyser) {
      try {
        source.connect(this.outputAnalyser)
      } catch (_) {}
    }

    const now = this.playbackContext.currentTime
    const startTime = Math.max(now + 0.005, this.nextPlayTime)
    source.start(startTime)

    this.nextPlayTime = startTime + audioBuffer.duration
    this.scheduledSources.push(source)
    this.playbackQueueLength++
    this.isPlayingAudio = true

    if (this.onPlaybackStateChange) {
      this.onPlaybackStateChange(true, this.playbackQueueLength)
    }

    source.onended = () => {
      const idx = this.scheduledSources.indexOf(source)
      if (idx !== -1) {
        this.scheduledSources.splice(idx, 1)
      }
      this.playbackQueueLength = Math.max(0, this.playbackQueueLength - 1)
      if (this.scheduledSources.length === 0) {
        this.isPlayingAudio = false
        this.nextPlayTime = 0
        if (this.onPlaybackStateChange) {
          this.onPlaybackStateChange(false, 0)
        }
      }
    }
  }

  /**
   * Immediately terminates all playing and queued audio (Barge-in).
   */
  public stopPlayback(): void {
    for (const source of this.scheduledSources) {
      try {
        source.stop()
        source.disconnect()
      } catch (_) {}
    }
    this.scheduledSources = []
    this.nextPlayTime = 0
    this.playbackQueueLength = 0
    this.isPlayingAudio = false

    if (this.onPlaybackStateChange) {
      this.onPlaybackStateChange(false, 0)
    }
    if (this.onOutputLevel) {
      this.onOutputLevel(-100)
    }
  }

  /**
   * Closes all audio contexts and cleans up resources.
   */
  public dispose(): void {
    this.stopMicrophone()
    this.stopPlayback()
    if (this.outputAnalyser) {
      try { this.outputAnalyser.disconnect() } catch (_) {}
      this.outputAnalyser = null
    }
    if (this.playbackContext) {
      this.playbackContext.close().catch(() => {})
      this.playbackContext = null
    }
  }

  private resampleTo16kPCM(input: Float32Array, inputSampleRate: number): Int16Array {
    if (inputSampleRate === 16000) {
      return this.floatTo16BitPCM(input)
    }
    const ratio = inputSampleRate / 16000
    const outputLength = Math.round(input.length / ratio)
    const output = new Int16Array(outputLength)
    for (let i = 0; i < outputLength; i++) {
      const srcIndex = i * ratio
      const indexFloor = Math.floor(srcIndex)
      const frac = srcIndex - indexFloor
      const s0 = input[indexFloor] || 0
      const s1 = input[indexFloor + 1] !== undefined ? input[indexFloor + 1] : s0
      const interp = s0 + frac * (s1 - s0)
      const s = Math.max(-1, Math.min(1, interp))
      output[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
    return output
  }

  private floatTo16BitPCM(input: Float32Array): Int16Array {
    const output = new Int16Array(input.length)
    for (let i = 0; i < input.length; i++) {
      const s = Math.max(-1, Math.min(1, input[i]))
      output[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
    return output
  }
}
