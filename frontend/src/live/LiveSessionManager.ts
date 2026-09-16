/**
 * HSBot Live Voice System - Live Session Manager
 * 
 * The single isolated orchestrator for live voice conversations.
 * Coordinates microphone audio capture, WebSocket connection to NVIDIA services,
 * Web Audio playback, barge-in detection, and state machine updates.
 */

import { LiveState, LiveTranscriptItem, LiveAudioLevel, LiveConfig } from './LiveTypes'
import { LiveLogger } from './LiveLogger'
import { LiveConnection } from './LiveConnection'
import { LiveMicrophone } from './LiveMicrophone'
import { LiveAudioPlayer } from './LiveAudioPlayer'
import { LiveTurnManager } from './LiveTurnManager'
import { LiveASR } from './LiveASR'
import { LiveLLM } from './LiveLLM'
import { LiveTTS } from './LiveTTS'
import { LiveRouter } from './LiveRouter'

export interface SessionManagerOptions {
  sessionId?: string
  config?: Partial<LiveConfig>
  onStateChange?: (state: LiveState) => void
  onTranscript?: (item: LiveTranscriptItem) => void
  onAudioLevel?: (level: LiveAudioLevel) => void
  onTiming?: (metrics: import('./LiveTypes').LiveTimingMetrics) => void
  onError?: (error: string) => void
}

export class LiveSessionManager {
  private sessionId: string
  private config: LiveConfig
  private turnManager: LiveTurnManager
  private connection: LiveConnection
  private microphone: LiveMicrophone
  private audioPlayer: LiveAudioPlayer
  private asr: LiveASR
  private llm: LiveLLM
  private tts: LiveTTS
  private audioLevel: LiveAudioLevel = { input: 0, output: 0 }
  private timingMetrics: import('./LiveTypes').LiveTimingMetrics = {}
  private options: SessionManagerOptions
  private isDestroyed = false
  private receivedAudioForTurn = false
  private audioFallbackTimeout: ReturnType<typeof setTimeout> | null = null
  private processingWatchdogTimeout: ReturnType<typeof setTimeout> | null = null

  constructor(options: SessionManagerOptions = {}) {
    this.options = options
    this.sessionId = options.sessionId || 'session_' + Math.random().toString(36).substring(2, 9)

    this.config = {
      sampleRate: 16000,
      language: 'en-US',
      voice: 'Chatterbox-Multilingual',
      vadThreshold: 0.20,
      silenceDurationMs: 1500,
      ...options.config,
    }

    // 1. Initialize Turn Manager
    this.turnManager = new LiveTurnManager({
      onStateChange: (state) => {
        if (state === 'PROCESSING') {
          if (this.processingWatchdogTimeout) clearTimeout(this.processingWatchdogTimeout)
          this.processingWatchdogTimeout = setTimeout(() => {
            if (this.turnManager.getState() === 'PROCESSING' && !this.isDestroyed) {
              LiveLogger.warn('Processing watchdog: Turn took > 8.5s without response, recovering to LISTENING')
              this.turnManager.transitionTo('LISTENING', 'Watchdog recovery')
            }
          }, 8500)
        } else {
          if (this.processingWatchdogTimeout) {
            clearTimeout(this.processingWatchdogTimeout)
            this.processingWatchdogTimeout = null
          }
        }
        this.options.onStateChange?.(state)
      },
      onInterrupt: () => {
        this.audioPlayer.stop()
        this.connection.sendInterrupt()
      },
      onError: (err) => {
        this.options.onError?.(err)
      },
    })

    // 2. Initialize Audio Player
    this.audioPlayer = new LiveAudioPlayer({
      sampleRate: 24000,
      onPlaybackEnded: () => {
        if (this.turnManager.getState() === 'SPEAKING') {
          this.turnManager.transitionTo('LISTENING', 'AI finished speaking')
        }
      },
      onVolumeChange: (vol) => {
        this.audioLevel.output = vol
        this.options.onAudioLevel?.({ ...this.audioLevel })
      },
      onError: (err) => {
        LiveLogger.error('Audio player error:', err.message)
      },
    })

    // 3. Initialize TTS helper
    this.tts = new LiveTTS(this.audioPlayer)

    // 4. Initialize ASR & LLM helpers
    this.asr = new LiveASR((item) => {
      this.options.onTranscript?.(item)
    })

    this.llm = new LiveLLM(
      (_chunk, fullText) => {
        this.options.onTranscript?.({
          id: 'ast_live',
          role: 'assistant',
          text: fullText,
          isFinal: false,
          timestamp: Date.now(),
        })
      },
      (finalItem) => {
        this.options.onTranscript?.(finalItem)
      }
    )

    // 5. Initialize Microphone Capture
    this.microphone = new LiveMicrophone({
      sampleRate: 16000,
      silenceTimeoutMs: this.config.silenceDurationMs || 1500,
      onAudioChunk: (_pcm, base64) => {
        const state = this.turnManager.getState()
        if (state === 'LISTENING' || state === 'CONNECTING') {
          this.connection.sendAudio(base64, 16000)
        }
      },
      onSpeechInterim: (text) => {
        const state = this.turnManager.getState()
        if (state === 'LISTENING' || state === 'CONNECTING') {
          this.asr.handleServerTranscript(text, false)
        }
      },
      onSpeechFinal: (text) => {
        const state = this.turnManager.getState()
        if (state === 'LISTENING' || state === 'CONNECTING') {
          this.timingMetrics = {}
          this.asr.handleServerTranscript(text, true)
          // Forward recognized speech to server for immediate LLM processing
          this.connection.sendUserSpeech(text)
          this.turnManager.transitionTo('PROCESSING', 'User speech recognized')
        }
      },
      onSpeechEnd: () => {
        const state = this.turnManager.getState()
        if (state === 'LISTENING' || state === 'CONNECTING') {
          this.timingMetrics = {}
          this.connection.sendCommitTurn()
        }
      },
      onVolumeChange: (vol) => {
        this.audioLevel.input = vol
        this.options.onAudioLevel?.({ ...this.audioLevel })

        const state = this.turnManager.getState()
        // Only barge-in if the user speaks loudly and deliberately (>0.35) while AI is speaking
        if (state === 'SPEAKING' && vol > 0.35) {
          this.turnManager.handleBargeIn()
        }
      },
      onError: (err) => {
        LiveLogger.error('Microphone error:', err.message)
        this.turnManager.handleError(`Microphone access error: ${err.message}`)
      },
    })

    // 6. Initialize Connection (WebSocket with transparent HTTP/SSE fallback)
    this.connection = new LiveConnection(this.sessionId, {
      onOpen: () => {
        this.connection.sendConfig(this.config)
        this.turnManager.transitionTo('LISTENING', 'Connected to NVIDIA Live Voice')
      },
      onClose: () => {
        if (!this.isDestroyed && !this.connection.isConnected() && this.turnManager.getState() !== 'IDLE') {
          this.turnManager.transitionTo('CONNECTING', 'Reconnecting stream')
        }
      },
      onError: () => {
        if (!this.connection.isConnected()) {
          LiveLogger.warn('Connection error occurred while disconnected')
        }
      },
      onMessage: (msg) => {
        this.handleServerMessage(msg)
      },
    })
  }

  private handleServerMessage(msg: import('./LiveTypes').ServerLiveMessage) {
    switch (msg.type) {
      case 'status':
        if (msg.state) {
          this.turnManager.transitionTo(msg.state, msg.message)
        }
        break

      case 'transcript':
        if (msg.role === 'user') {
          this.asr.handleServerTranscript(msg.text, msg.isFinal)
          if (msg.isFinal) {
            // Check fast router intent
            const route = LiveRouter.classify(msg.text)
            if (route.intent === 'SHORT_COMMAND') {
              this.interrupt()
              return
            }
            this.turnManager.transitionTo('PROCESSING', 'User utterance received')
          }
        } else if (msg.role === 'assistant') {
          this.options.onTranscript?.({
            id: 'ast_' + Date.now(),
            role: 'assistant',
            text: msg.text,
            isFinal: msg.isFinal,
            timestamp: Date.now(),
          })

          if (msg.isFinal && msg.text) {
            this.receivedAudioForTurn = false
            if (this.audioFallbackTimeout) {
              clearTimeout(this.audioFallbackTimeout)
            }
            this.audioFallbackTimeout = setTimeout(() => {
              if (!this.receivedAudioForTurn && !this.isDestroyed && this.turnManager.getState() !== 'INTERRUPTED') {
                this.turnManager.transitionTo('SPEAKING', 'Speaking response')
                this.tts.speakFallback(msg.text, () => {
                  if (this.turnManager.getState() === 'SPEAKING') {
                    this.turnManager.transitionTo('LISTENING', 'AI finished speaking')
                  }
                })
              }
            }, 650)
          }
        }
        break

      case 'llm_chunk':
        this.llm.appendChunk(msg.text)
        break

      case 'audio_chunk':
        this.receivedAudioForTurn = true
        if (this.audioFallbackTimeout) {
          clearTimeout(this.audioFallbackTimeout)
          this.audioFallbackTimeout = null
        }
        if (this.turnManager.getState() !== 'SPEAKING' && this.turnManager.getState() !== 'INTERRUPTED') {
          this.turnManager.transitionTo('SPEAKING', 'Received audio response')
        }
        this.tts.handleAudioChunk(msg.audio, msg.sampleRate, msg.index)
        break

      case 'timing':
        if (msg.metric === 'asr_to_llm_first_token_ms') {
          this.timingMetrics.asr_to_llm_first_token_ms = msg.value
        } else if (msg.metric === 'llm_first_token_to_tts_first_audio_ms') {
          this.timingMetrics.llm_first_token_to_tts_first_audio_ms = msg.value
        } else if (msg.metric === 'total_latency_ms') {
          this.timingMetrics.total_latency_ms = msg.value
        }
        this.options.onTiming?.({ ...this.timingMetrics })
        break

      case 'error':
        LiveLogger.error(`Server reported error: ${msg.code} - ${msg.message}`)
        this.turnManager.handleError(msg.message)
        break

      case 'pong':
        break
    }
  }

  /**
   * Start live voice session: Connects WebSocket and acquires microphone
   */
  async start(): Promise<boolean> {
    if (this.isDestroyed) {
      LiveLogger.error('Cannot start destroyed session manager')
      return false
    }

    try {
      this.turnManager.transitionTo('CONNECTING', 'Starting session')

      // Unlock Web Audio context inside user gesture
      this.audioPlayer.unlock()

      // Start microphone first
      const micSuccess = await this.microphone.start()
      if (!micSuccess) {
        this.turnManager.transitionTo('ERROR', 'Microphone permission denied')
        return false
      }

      // Connect
      this.connection.connect()

      // Watchdog: If state is still CONNECTING after 2.5 seconds, transition to LISTENING
      setTimeout(() => {
        if (!this.isDestroyed && this.turnManager.getState() === 'CONNECTING') {
          this.turnManager.transitionTo('LISTENING', 'Ready to speak')
        }
      }, 2500)

      return true
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      this.turnManager.transitionTo('ERROR', errorMsg)
      return false
    }
  }

  /**
   * Stop session and release all audio and network resources
   */
  stop(): void {
    LiveLogger.info('Stopping live session manager')
    if (this.audioFallbackTimeout) {
      clearTimeout(this.audioFallbackTimeout)
      this.audioFallbackTimeout = null
    }
    this.tts.stop()
    this.microphone.stop()
    this.audioPlayer.stop()
    this.connection.disconnect()
    this.turnManager.reset()
    this.audioLevel = { input: 0, output: 0 }
    this.options.onAudioLevel?.({ ...this.audioLevel })
  }

  /**
   * Instant barge-in / interrupt
   */
  interrupt(): void {
    if (this.audioFallbackTimeout) {
      clearTimeout(this.audioFallbackTimeout)
      this.audioFallbackTimeout = null
    }
    this.tts.stop()
    this.audioPlayer.stop()
    this.connection.sendInterrupt()
    this.llm.reset()
    this.turnManager.transitionTo('LISTENING', 'User interrupted')
  }

  /**
   * Manually commit speech turn (e.g. user clicks "Done Speaking")
   */
  commitTurn(): void {
    if (this.turnManager.getState() === 'LISTENING') {
      this.connection.sendCommitTurn()
    }
  }

  /**
   * Toggle microphone mute state
   */
  toggleMute(): boolean {
    const nextMuted = !this.microphone.getMuted()
    this.microphone.setMuted(nextMuted)
    return nextMuted
  }

  isMuted(): boolean {
    return this.microphone.getMuted()
  }

  /**
   * Dynamically adjust silence duration for conversational pacing
   */
  setSilenceDuration(ms: number): void {
    this.config.silenceDurationMs = ms
    this.microphone.setSilenceTimeout(ms)
    this.connection.sendConfig({ silenceDurationMs: ms })
  }

  /**
   * Dynamically adjust selected TTS voice
   */
  setVoice(voice: string): void {
    this.config.voice = voice
    this.connection.sendConfig({ voice })
  }

  getState(): LiveState {
    return this.turnManager.getState()
  }

  getSessionId(): string {
    return this.sessionId
  }

  destroy(): void {
    this.isDestroyed = true
    this.stop()
    this.audioPlayer.destroy()
  }
}
