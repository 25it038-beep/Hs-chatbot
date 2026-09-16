/**
 * HSBot Live Voice System - Live TTS Handler
 * 
 * Exclusively handles receiving streaming synthesized audio chunks from NVIDIA Chatterbox TTS
 * and streaming them directly to LiveAudioPlayer via Web Audio API.
 * NO browser speechSynthesis fallback.
 */

import { LiveAudioPlayer } from './LiveAudioPlayer'
import { LiveLogger } from './LiveLogger'

export class LiveTTS {
  private player: LiveAudioPlayer
  private chunkIndex = 0
  private ttsBytesReceived = 0
  private ttsStatus: 'idle' | 'synthesizing' | 'streaming' | 'complete' | 'error' = 'idle'

  constructor(player: LiveAudioPlayer) {
    this.player = player
  }

  handleAudioChunk(audioBase64: string, sampleRate = 24000, index = 0) {
    if (!audioBase64) return

    const byteLen = Math.floor((audioBase64.length * 3) / 4)
    this.ttsBytesReceived += byteLen
    this.chunkIndex = index
    this.ttsStatus = 'streaming'

    LiveLogger.debug(`Received NVIDIA TTS audio chunk #${index} (${byteLen} bytes)`)
    this.player.queueAudio(audioBase64, sampleRate)
  }

  setStatus(status: 'idle' | 'synthesizing' | 'streaming' | 'complete' | 'error') {
    this.ttsStatus = status
  }

  getStatus() {
    return this.ttsStatus
  }

  getBytesReceived() {
    return this.ttsBytesReceived
  }

  resetTurn() {
    this.chunkIndex = 0
    this.ttsBytesReceived = 0
    this.ttsStatus = 'idle'
  }

  stop() {
    this.player.stop()
    this.chunkIndex = 0
    this.ttsStatus = 'idle'
  }

  getChunkIndex(): number {
    return this.chunkIndex
  }
}
