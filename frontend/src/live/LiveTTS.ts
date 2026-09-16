/**
 * HSBot Live Voice System - Live TTS Handler
 * 
 * Coordinates receiving synthesized audio chunks from NVIDIA TTS and passing to Audio Player.
 */

import { LiveAudioPlayer } from './LiveAudioPlayer'
import { LiveLogger } from './LiveLogger'
import { cleanTextForSpeech } from '@/lib/speech'

export class LiveTTS {
  private player: LiveAudioPlayer
  private chunkIndex = 0
  private isFallbackSpeaking = false

  constructor(player: LiveAudioPlayer) {
    this.player = player
  }

  handleAudioChunk(audioBase64: string, sampleRate = 24000, index = 0) {
    LiveLogger.debug(`Received TTS audio chunk #${index} (${audioBase64.length} chars)`)
    // If fallback was speaking, cancel it in favor of native stream
    if (this.isFallbackSpeaking && typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel()
      this.isFallbackSpeaking = false
    }
    this.chunkIndex = index
    this.player.queueAudio(audioBase64, sampleRate)
  }

  speakFallback(text: string, onEnd?: () => void) {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      onEnd?.()
      return
    }

    const cleaned = cleanTextForSpeech(text)
    if (!cleaned) {
      onEnd?.()
      return
    }

    try {
      window.speechSynthesis.cancel()
      window.speechSynthesis.resume()
      const utterance = new SpeechSynthesisUtterance(cleaned)
      utterance.rate = 1.05
      this.isFallbackSpeaking = true

      // Chrome keeps SpeechSynthesis active through keep-alive resume
      const resumeInterval = setInterval(() => {
        if (!this.isFallbackSpeaking) {
          clearInterval(resumeInterval)
        } else {
          window.speechSynthesis.resume()
        }
      }, 500)

      utterance.onend = () => {
        clearInterval(resumeInterval)
        this.isFallbackSpeaking = false
        onEnd?.()
      }

      utterance.onerror = () => {
        clearInterval(resumeInterval)
        this.isFallbackSpeaking = false
        onEnd?.()
      }

      window.speechSynthesis.speak(utterance)
    } catch (err) {
      this.isFallbackSpeaking = false
      onEnd?.()
    }
  }

  stop() {
    this.player.stop()
    this.chunkIndex = 0
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
    this.isFallbackSpeaking = false
  }

  getChunkIndex(): number {
    return this.chunkIndex
  }
}
