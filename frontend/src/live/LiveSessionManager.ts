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
  onDiagnostics?: (diagnostics: import('./LiveTypes').LiveDiagnostics) => void
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

  // Separate State Machines
  private connectionState: import('./LiveTypes').ConnectionState = 'DISCONNECTED'
  private asrStatus: 'idle' | 'transcribing' | 'success' | 'no_speech' | 'error' = 'idle'
  private asrTranscript = ''
  private llmStatus: 'idle' | 'streaming' | 'complete' | 'error' = 'idle'
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
        if (state === 'PROCESSING' || state === 'THINKING') {
          if (this.processingWatchdogTimeout) clearTimeout(this.processingWatchdogTimeout)
          this.processingWatchdogTimeout = setTimeout(() => {
            const curState = this.turnManager.getState()
            if ((curState === 'PROCESSING' || curState === 'THINKING') && !this.isDestroyed) {
              LiveLogger.warn('Processing watchdog: Turn took > 8.5s without response, recovering to LISTENING')
              this.turnManager.transitionTo('LISTENING', 'Watchdog recovery')
              this.notifyDiagnostics()
            }
          }, 8500)
        } else {
          if (this.processingWatchdogTimeout) {
            clearTimeout(this.processingWatchdogTimeout)
            this.processingWatchdogTimeout = null
          }
        }
        this.options.onStateChange?.(state)
        this.notifyDiagnostics()
      },
      onInterrupt: () => {
        this.audioPlayer.stop()
        this.tts.stop()
        this.connection.sendInterrupt()
        this.notifyDiagnostics()
      },
      onError: (err) => {
        this.options.onError?.(err)
        this.notifyDiagnostics()
      },
    })

    // 2. Initialize Audio Player
    this.audioPlayer = new LiveAudioPlayer({
      sampleRate: 24000,
      onPlaybackEnded: () => {
        if (this.turnManager.getState() === 'SPEAKING') {
          this.turnManager.transitionTo('LISTENING', 'AI finished speaking')
        }
        this.notifyDiagnostics()
      },
      onPlaybackStatusChange: () => {
        this.notifyDiagnostics()
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
        if (state === 'LISTENING' || state === 'USER_SPEAKING' || state === 'CONNECTING') {
          this.connection.sendAudio(base64, 16000)
        }
        this.notifyDiagnostics()
      },
      onSpeechStart: () => {
        const state = this.turnManager.getState()
        if (state === 'LISTENING') {
          this.turnManager.transitionTo('USER_SPEAKING', 'User speech detected')
          this.asrStatus = 'transcribing'
          this.notifyDiagnostics()
        }
      },
      onSpeechEnd: () => {
        const state = this.turnManager.getState()
        if (state === 'USER_SPEAKING' || state === 'LISTENING') {
          this.connection.sendCommitTurn()
          this.turnManager.transitionTo('PROCESSING', 'Speech offset detected')
          this.notifyDiagnostics()
        }
      },
      onVolumeChange: (vol, rawRms) => {
        this.audioLevel.input = vol
        this.options.onAudioLevel?.({ ...this.audioLevel })

        const state = this.turnManager.getState()
        // Deliberate barge-in if user speaks loudly while AI is speaking
        if (state === 'SPEAKING' && rawRms > 0.04) {
          this.turnManager.handleBargeIn()
        }
      },
      onError: (err) => {
        LiveLogger.error('Microphone error:', err.message)
        this.turnManager.handleError(`Microphone error: ${err.message}`)
        this.notifyDiagnostics()
      },
    })

    // 6. Initialize Connection
    this.connection = new LiveConnection(this.sessionId, {
      onOpen: () => {
        this.connectionState = 'CONNECTED'
        this.connection.sendConfig(this.config)
        this.turnManager.transitionTo('LISTENING', 'Connected to NVIDIA Live Voice')
        this.notifyDiagnostics()
      },
      onClose: () => {
        if (!this.isDestroyed && !this.connection.isConnected() && this.turnManager.getState() !== 'IDLE') {
          this.connectionState = 'RECONNECTING'
          this.turnManager.transitionTo('CONNECTING', 'Reconnecting stream')
          this.notifyDiagnostics()
        }
      },
      onError: () => {
        if (!this.connection.isConnected()) {
          this.connectionState = 'FAILED'
          this.notifyDiagnostics()
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
          if (msg.state === 'LISTENING') {
            this.asrStatus = 'idle'
            this.llmStatus = 'idle'
            this.tts.setStatus('idle')
          } else if (msg.state === 'USER_SPEAKING') {
            this.asrStatus = 'transcribing'
          } else if (msg.state === 'PROCESSING' || msg.state === 'THINKING') {
            this.llmStatus = 'streaming'
          } else if (msg.state === 'SPEAKING') {
            this.tts.setStatus('streaming')
          }
          this.notifyDiagnostics()
        }
        break

      case 'transcript':
        if (msg.role === 'user') {
          this.asrTranscript = msg.text
          this.asrStatus = 'success'
          this.asr.handleServerTranscript(msg.text, msg.isFinal)
          if (msg.isFinal) {
            const route = LiveRouter.classify(msg.text)
            if (route.intent === 'SHORT_COMMAND') {
              this.interrupt()
              return
            }
            this.turnManager.transitionTo('PROCESSING', 'User utterance received')
          }
          this.notifyDiagnostics()
        } else if (msg.role === 'assistant') {
          if (msg.isFinal) {
            this.llmStatus = 'complete'
          }
          this.options.onTranscript?.({
            id: 'ast_' + Date.now(),
            role: 'assistant',
            text: msg.text,
            isFinal: msg.isFinal,
            timestamp: Date.now(),
          })
          this.notifyDiagnostics()
        }
        break

      case 'llm_chunk':
        this.llmStatus = 'streaming'
        this.llm.appendChunk(msg.text)
        this.notifyDiagnostics()
        break

      case 'audio_chunk':
        if (this.turnManager.getState() !== 'SPEAKING' && this.turnManager.getState() !== 'INTERRUPTED') {
          this.turnManager.transitionTo('SPEAKING', 'Received NVIDIA TTS audio')
        }
        this.tts.handleAudioChunk(msg.audio, msg.sampleRate, msg.index)
        this.notifyDiagnostics()
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
        this.notifyDiagnostics()
        break

      case 'error':
        LiveLogger.error(`Server reported error: ${msg.code} - ${msg.message}`)
        this.asrStatus = 'error'
        this.llmStatus = 'error'
        this.turnManager.handleError(msg.message)
        this.notifyDiagnostics()
        break

      case 'pong':
        break
    }
  }

  getDiagnostics(): import('./LiveTypes').LiveDiagnostics {
    const micMetrics = this.microphone.getMetrics()
    const rawTurnState = this.turnManager.getState()
    const turnState: import('./LiveTypes').TurnState =
      rawTurnState === 'PROCESSING' ? 'THINKING' : (rawTurnState as import('./LiveTypes').TurnState)

    return {
      connectionState: this.connectionState,
      turnState,
      micReady: micMetrics.isReady,
      micSampleRate: micMetrics.sampleRate,
      micChannels: micMetrics.channels,
      micRms: Number(micMetrics.rms.toFixed(4)),
      audioFramesCount: micMetrics.framesCount,
      audioBytesSent: micMetrics.bytesSent,
      asrStatus: this.asrStatus,
      asrTranscript: this.asrTranscript,
      llmStatus: this.llmStatus,
      llmTtftMs: this.timingMetrics.asr_to_llm_first_token_ms,
      ttsStatus: this.tts.getStatus(),
      ttsBytesReceived: this.tts.getBytesReceived(),
      playbackStatus: this.audioPlayer.getPlaybackStatus(),
      totalTurnLatencyMs: this.timingMetrics.total_latency_ms,
    }
  }

  private notifyDiagnostics() {
    if (this.options.onDiagnostics) {
      this.options.onDiagnostics(this.getDiagnostics())
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
      this.connectionState = 'CONNECTING'
      this.turnManager.transitionTo('CONNECTING', 'Starting session')
      this.notifyDiagnostics()

      // Unlock Web Audio context inside user gesture
      this.audioPlayer.unlock()

      // Start microphone first
      const micSuccess = await this.microphone.start()
      if (!micSuccess) {
        this.connectionState = 'FAILED'
        this.turnManager.transitionTo('ERROR', 'Microphone permission denied')
        this.notifyDiagnostics()
        return false
      }

      // Connect
      this.connection.connect()

      // Watchdog: If state is still CONNECTING after 2.0 seconds, transition to LISTENING
      setTimeout(() => {
        if (!this.isDestroyed && this.turnManager.getState() === 'CONNECTING') {
          this.turnManager.transitionTo('LISTENING', 'Ready to speak')
          this.notifyDiagnostics()
        }
      }, 2000)

      return true
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      this.connectionState = 'FAILED'
      this.turnManager.transitionTo('ERROR', errorMsg)
      this.notifyDiagnostics()
      return false
    }
  }

  /**
   * Stop session and release all audio and network resources
   */
  stop(): void {
    LiveLogger.info('Stopping live session manager')
    if (this.processingWatchdogTimeout) {
      clearTimeout(this.processingWatchdogTimeout)
      this.processingWatchdogTimeout = null
    }
    this.tts.stop()
    this.microphone.stop()
    this.audioPlayer.stop()
    this.connection.disconnect()
    this.turnManager.reset()
    this.connectionState = 'DISCONNECTED'
    this.audioLevel = { input: 0, output: 0 }
    this.options.onAudioLevel?.({ ...this.audioLevel })
    this.notifyDiagnostics()
  }

  /**
   * Instant barge-in / interrupt
   */
  interrupt(): void {
    this.tts.stop()
    this.audioPlayer.stop()
    this.connection.sendInterrupt()
    this.llm.reset()
    this.turnManager.transitionTo('LISTENING', 'User interrupted')
    this.notifyDiagnostics()
  }

  /**
   * Manually commit speech turn (e.g. user clicks "Done Speaking")
   */
  commitTurn(): void {
    const state = this.turnManager.getState()
    if (state === 'LISTENING' || state === 'USER_SPEAKING') {
      this.connection.sendCommitTurn()
      this.turnManager.transitionTo('PROCESSING', 'Manual commit')
      this.notifyDiagnostics()
    }
  }

  /**
   * Toggle microphone mute state
   */
  toggleMute(): boolean {
    const nextMuted = !this.microphone.getMuted()
    this.microphone.setMuted(nextMuted)
    this.notifyDiagnostics()
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
