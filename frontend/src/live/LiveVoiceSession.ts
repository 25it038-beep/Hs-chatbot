/**
 * Live Voice Session Orchestrator for HSBot.
 * Coordinates Audio, Transport, Diagnostics, and Conversation Turns.
 */

import { LiveVoiceAudio } from './LiveVoiceAudio'
import { LiveVoiceTransport } from './LiveVoiceTransport'
import { LiveVoiceDiagnostics } from './LiveVoiceDiagnostics'
import {
  LiveEngine,
  LiveServerMessage,
  LiveState,
  LiveTurnTranscript,
  LiveVoiceConfig,
} from './LiveVoiceTypes'

export class LiveVoiceSession {
  public readonly audio: LiveVoiceAudio
  public readonly transport: LiveVoiceTransport
  public readonly diagnostics: LiveVoiceDiagnostics

  private state: LiveState = 'IDLE'
  private engine: LiveEngine = 'cascaded'
  private transcripts: LiveTurnTranscript[] = []
  private sessionId: string

  // Callbacks
  public onStateChange: ((state: LiveState) => void) | null = null
  public onTranscript: ((transcript: LiveTurnTranscript) => void) | null = null
  public onTranscriptsChange: ((all: LiveTurnTranscript[]) => void) | null = null
  public onError: ((code: string, message: string, details?: any) => void) | null = null

  constructor(sessionId: string = 'live_' + Math.random().toString(36).substring(2, 9)) {
    this.sessionId = sessionId
    this.audio = new LiveVoiceAudio()
    this.transport = new LiveVoiceTransport(sessionId)
    this.diagnostics = new LiveVoiceDiagnostics()

    this.setupBindings()
  }

  public getState(): LiveState {
    return this.state
  }

  public getEngine(): LiveEngine {
    return this.engine
  }

  public getTranscripts(): LiveTurnTranscript[] {
    return [...this.transcripts]
  }

  /**
   * Starts live session: connects transport and turns on microphone.
   */
  public async start(config?: LiveVoiceConfig): Promise<void> {
    if (config?.engine) {
      this.engine = config.engine
      this.diagnostics.setEngine(this.engine)
    }

    this.setState('CONNECTING')
    this.diagnostics.clearError()

    const wsUrl = this.transport.getWebSocketUrl(this.engine)
    console.log('[LIVE-PROD]', {
      environment: import.meta.env.MODE || (window.location.hostname === 'localhost' ? 'development' : 'production'),
      origin: window.location.origin,
      secureContext: window.isSecureContext,
      backendUrl: (import.meta.env.VITE_API_URL as string) || '(derived)',
      websocketUrl: wsUrl.split('?')[0],
      mediaDevices: !!navigator.mediaDevices,
      microphone: 'connecting',
      connectionState: 'CONNECTING',
      turnState: 'IDLE',
    })

    try {
      await this.transport.connect(this.engine)
      await this.audio.startMicrophone()
      if (this.state !== 'ERROR' && this.state !== 'SPEAKING' && !this.audio.isPlaybackActive) {
        this.setState('LISTENING')
      }
    } catch (err: any) {
      this.setState('ERROR')
      const code = err.message?.includes('WebSocket') ? 'WS_CONNECT_FAILED' : 'START_FAILED'
      this.diagnostics.recordError(code, err.message || 'Failed to start Live Voice session')
      if (this.onError) {
        this.onError(code, err.message || 'Failed to start Live Voice session')
      }
    }
  }

  /**
   * Gracefully stops the session.
   */
  public stop(): void {
    this.audio.stopMicrophone()
    this.audio.stopPlayback()
    this.transport.disconnect()
    this.setState('IDLE')
  }

  /**
   * Seamlessly switches Live Voice engine on the fly.
   */
  public switchEngine(newEngine: LiveEngine): void {
    this.engine = newEngine
    this.diagnostics.setEngine(newEngine)
    this.diagnostics.clearError()
    this.setState('LISTENING')

    if (this.transport.isConnected) {
      this.transport.switchEngine(newEngine)
    } else {
      this.transport.connect(newEngine)
    }
  }

  /**
   * Retries availability probe when in error state.
   */
  public retry(): void {
    this.diagnostics.clearError()
    this.transport.retryAvailability()
  }

  /**
   * Triggers barge-in: immediately stops assistant playback and signals backend.
   */
  public interrupt(): void {
    this.audio.stopPlayback()
    this.transport.sendInterrupt()
    this.setState('LISTENING')
  }

  /**
   * Sends user text turn directly.
   */
  public sendText(text: string): void {
    if (!text.trim()) return

    const userTranscript: LiveTurnTranscript = {
      id: 'usr_' + Date.now(),
      role: 'user',
      text: text.trim(),
      isFinal: true,
      timestamp: Date.now(),
      engine: this.engine,
    }
    this.addTranscript(userTranscript)

    this.setState('PROCESSING')
    this.transport.sendTextTurn(text.trim())
  }

  private setupBindings(): void {
    // 1. Audio Data from Microphone -> Transport
    this.audio.onAudioData = (pcmBytes) => {
      this.transport.sendAudioChunk(pcmBytes)
      this.diagnostics.incrementPacketCount()
    }

    // 2. Audio Level Meters
    this.audio.onInputLevel = (levelDb) => {
      this.diagnostics.setInputLevel(levelDb)
      this.diagnostics.setMicState(this.audio.isMicActive, this.audio.sampleRate)

      // Barge-in auto detection: if user speaks louder than -32 dB while assistant is playing
      if (levelDb > -32 && this.state === 'SPEAKING' && this.audio.isPlaybackActive) {
        this.interrupt()
      }
    }

    this.audio.onPlaybackStateChange = (isPlaying, queueLength) => {
      this.diagnostics.setPlaybackState(isPlaying, queueLength)
      if (isPlaying && this.state !== 'SPEAKING') {
        this.setState('SPEAKING')
      } else if (!isPlaying && this.state === 'SPEAKING') {
        this.setState('LISTENING')
      }
    }

    // 3. Transport Messages -> Session Orchestration
    this.transport.onMessage = (msg: LiveServerMessage) => {
      this.handleServerMessage(msg)
    }

    this.transport.onStateChange = (tState) => {
      this.diagnostics.setConnectionState(tState)
      if (tState === 'CONNECTED' && this.state === 'CONNECTING') {
        this.setState('LISTENING')
      } else if (tState === 'DISCONNECTED' && this.state !== 'IDLE') {
        this.setState('DISCONNECTED')
      }
    }

    this.transport.onError = (err) => {
      this.diagnostics.recordError('WS_ERROR', 'WebSocket communication error', err)
    }
  }

  private handleServerMessage(msg: LiveServerMessage): void {
    switch (msg.type) {
      case 'status':
        if (msg.state) {
          this.setState(msg.state)
        }
        break

      case 'transcript':
        if (msg.role && msg.text) {
          const item: LiveTurnTranscript = {
            id: 'tr_' + Date.now() + '_' + Math.random().toString(36).substring(2, 5),
            role: msg.role,
            text: msg.text,
            isFinal: !!msg.isFinal,
            timestamp: Date.now(),
            engine: this.engine,
          }
          this.addTranscript(item)
        }
        break

      case 'audio_chunk':
        if (msg.audio) {
          const binaryStr = window.atob(msg.audio)
          const bytes = new Uint8Array(binaryStr.length)
          for (let i = 0; i < binaryStr.length; i++) {
            bytes[i] = binaryStr.charCodeAt(i)
          }
          this.audio.playChunk(bytes.buffer, msg.sampleRate || 24000)
        }
        break

      case 'timing':
        if (msg.metric && msg.value !== undefined) {
          this.diagnostics.recordTiming(msg.metric, msg.value)
        }
        break

      case 'engine_switched':
        if (msg.engine) {
          this.engine = msg.engine
          this.diagnostics.setEngine(msg.engine)
        }
        break

      case 'error':
        this.setState('ERROR')
        this.diagnostics.recordError(msg.code || 'UNKNOWN_ERROR', msg.message || 'Error occurred', msg.details)
        if (this.onError) {
          this.onError(msg.code || 'UNKNOWN_ERROR', msg.message || 'Error occurred', msg.details)
        }
        break

      default:
        break
    }
  }

  private setState(newState: LiveState): void {
    this.state = newState
    this.diagnostics.setConnectionState(newState)
    if (this.onStateChange) {
      this.onStateChange(newState)
    }
  }

  private addTranscript(item: LiveTurnTranscript): void {
    // If last transcript is non-final for same role, update it
    const last = this.transcripts[this.transcripts.length - 1]
    if (last && last.role === item.role && !last.isFinal) {
      this.transcripts[this.transcripts.length - 1] = item
    } else {
      this.transcripts.push(item)
    }

    if (this.onTranscript) {
      this.onTranscript(item)
    }
    if (this.onTranscriptsChange) {
      this.onTranscriptsChange([...this.transcripts])
    }
  }
}
