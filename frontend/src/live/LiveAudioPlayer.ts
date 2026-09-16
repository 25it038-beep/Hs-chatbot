/**
 * HSBot Live Voice System - Live Audio Player
 * 
 * Manages playback of raw PCM audio chunks from NVIDIA TTS via the Web Audio API.
 * Supports seamless queuing, volume analysis for visualizers, and instant barge-in cancellation.
 */

import { LiveLogger } from './LiveLogger'

export interface AudioPlayerOptions {
  sampleRate?: number
  onPlaybackEnded?: () => void
  onVolumeChange?: (volume: number) => void
  onError?: (error: Error) => void
}

export class LiveAudioPlayer {
  private audioContext: AudioContext | null = null
  private analyserNode: AnalyserNode | null = null
  private scheduledSources: AudioBufferSourceNode[] = []
  private nextStartTime = 0
  private isPlaying = false
  private options: AudioPlayerOptions
  private animFrameId: number | null = null

  constructor(options: AudioPlayerOptions = {}) {
    this.options = {
      sampleRate: 24000, // NVIDIA Chatterbox Multilingual TTS native rate
      ...options,
    }
  }

  /**
   * Unlock and warm up AudioContext on direct user click/gesture
   */
  unlock() {
    try {
      this.initContext()
      if (this.audioContext && this.audioContext.state === 'suspended') {
        this.audioContext.resume().catch(() => {})
        const osc = this.audioContext.createBufferSource()
        const emptyBuf = this.audioContext.createBuffer(1, 1, 24000)
        osc.buffer = emptyBuf
        osc.connect(this.audioContext.destination)
        osc.start(0)
      }
    } catch {
      // ignore
    }
  }

  private initContext() {
    if (!this.audioContext || this.audioContext.state === 'closed') {
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      this.audioContext = new AudioContextClass({
        sampleRate: this.options.sampleRate || 24000,
      })
      this.analyserNode = this.audioContext.createAnalyser()
      this.analyserNode.fftSize = 256
      this.analyserNode.connect(this.audioContext.destination)
      this.startMeter()
    }
  }

  private startMeter() {
    if (this.animFrameId) return

    const dataArray = new Uint8Array(this.analyserNode ? this.analyserNode.frequencyBinCount : 128)

    const checkVolume = () => {
      if (!this.isPlaying || !this.analyserNode) {
        this.options.onVolumeChange?.(0)
        this.animFrameId = requestAnimationFrame(checkVolume)
        return
      }

      this.analyserNode.getByteFrequencyData(dataArray)
      let sum = 0
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i]
      }
      const avg = sum / dataArray.length
      const normalized = Math.min(1.0, avg / 128.0)
      this.options.onVolumeChange?.(normalized)

      this.animFrameId = requestAnimationFrame(checkVolume)
    }

    this.animFrameId = requestAnimationFrame(checkVolume)
  }

  /**
   * Enqueue a raw PCM chunk (base64 string or ArrayBuffer)
   */
  async queueAudio(pcmData: string | ArrayBuffer, sampleRate = 24000): Promise<void> {
    try {
      this.initContext()
      if (!this.audioContext) return

      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume()
      }

      let arrayBuffer: ArrayBuffer
      if (typeof pcmData === 'string') {
        // Base64 to ArrayBuffer
        const binaryString = atob(pcmData)
        const len = binaryString.length
        const bytes = new Uint8Array(len)
        for (let i = 0; i < len; i++) {
          bytes[i] = binaryString.charCodeAt(i)
        }
        arrayBuffer = bytes.buffer
      } else {
        arrayBuffer = pcmData
      }

      // Convert 16-bit signed PCM to Float32
      const int16Array = new Int16Array(arrayBuffer)
      if (int16Array.length === 0) return

      const float32Array = new Float32Array(int16Array.length)
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7fff)
      }

      // Create AudioBuffer
      const audioBuffer = this.audioContext.createBuffer(1, float32Array.length, sampleRate)
      audioBuffer.copyToChannel(float32Array, 0)

      // Schedule seamless continuous playback
      const sourceNode = this.audioContext.createBufferSource()
      sourceNode.buffer = audioBuffer

      if (this.analyserNode) {
        sourceNode.connect(this.analyserNode)
      } else {
        sourceNode.connect(this.audioContext.destination)
      }

      const currentTime = this.audioContext.currentTime
      const startTime = Math.max(currentTime, this.nextStartTime)
      sourceNode.start(startTime)

      this.nextStartTime = startTime + audioBuffer.duration
      this.isPlaying = true
      this.scheduledSources.push(sourceNode)

      sourceNode.onended = () => {
        const idx = this.scheduledSources.indexOf(sourceNode)
        if (idx !== -1) {
          this.scheduledSources.splice(idx, 1)
        }

        if (this.scheduledSources.length === 0) {
          this.isPlaying = false
          this.options.onVolumeChange?.(0)
          this.options.onPlaybackEnded?.()
        }
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err))
      LiveLogger.error('Error queuing audio chunk:', error.message)
      this.options.onError?.(error)
    }
  }

  /**
   * Instantly halt playback and cancel all scheduled audio (barge-in / interrupt)
   */
  stop() {
    LiveLogger.debug('Stopping audio player, clearing queued buffers')
    for (const source of this.scheduledSources) {
      try {
        source.onended = null
        source.stop()
        source.disconnect()
      } catch (e) {
        // ignore
      }
    }
    this.scheduledSources = []
    this.isPlaying = false
    this.nextStartTime = 0

    this.options.onVolumeChange?.(0)
  }

  destroy() {
    this.stop()
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId)
      this.animFrameId = null
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      try {
        this.audioContext.close()
      } catch (e) {
        // ignore
      }
      this.audioContext = null
    }
  }

  getIsPlaying(): boolean {
    return this.isPlaying
  }
}
