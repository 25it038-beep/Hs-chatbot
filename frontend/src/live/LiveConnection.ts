/**
 * HSBot Live Voice System - Live Connection (WebSocket with Robust HTTP/SSE Fallback)
 * 
 * Manages the bidirectional stream to NVIDIA NIM voice services.
 * Automatically tries low-latency WebSocket first. If the proxy, Cloud Run,
 * or browser environment blocks or delays the WebSocket handshake (>2s),
 * it immediately and transparently transitions to HTTP/SSE streaming so the
 * user NEVER gets stuck on "Connecting to NVIDIA NIM...".
 */

import { ClientLiveMessage, ServerLiveMessage, LiveConfig } from './LiveTypes'
import { LiveLogger } from './LiveLogger'

export interface ConnectionCallbacks {
  onOpen: () => void
  onClose: (event: CloseEvent) => void
  onMessage: (message: ServerLiveMessage) => void
  onError: (error: Event) => void
}

export class LiveConnection {
  private ws: WebSocket | null = null
  private sessionId: string
  private callbacks: ConnectionCallbacks
  private pingInterval: number | null = null
  private connectionTimeout: number | null = null
  private reconnectAttempts = 0
  private readonly maxReconnectAttempts = 3
  private isExplicitlyClosed = false

  // HTTP Fallback State
  private isHttpFallback = false
  private httpAudioChunks: string[] = []
  private httpTurnAbortController: AbortController | null = null
  private currentConfig: Partial<LiveConfig> = {}

  constructor(sessionId: string, callbacks: ConnectionCallbacks) {
    this.sessionId = sessionId
    this.callbacks = callbacks
  }

  connect(): void {
    if (this.isHttpFallback) {
      LiveLogger.info('Live connection is running in HTTP/SSE fallback mode')
      this.callbacks.onOpen()
      this.callbacks.onMessage({
        type: 'status',
        state: 'LISTENING',
        message: 'Connected to NVIDIA NIM',
      })
      return
    }

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      LiveLogger.warn('WebSocket already connected or connecting')
      return
    }

    this.isExplicitlyClosed = false
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/live/ws/${this.sessionId}`

    LiveLogger.info(`Attempting Live WebSocket connection: ${wsUrl}`)

    // 2-second connection watchdog: if WebSocket takes > 2s to open, fallback to HTTP/SSE immediately
    this.clearConnectionTimeout()
    this.connectionTimeout = window.setTimeout(() => {
      LiveLogger.warn('WebSocket handshake timed out (>2s). Falling back to HTTP Live Mode.')
      this.fallbackToHttp('WebSocket handshake timed out')
    }, 2000)

    try {
      this.ws = new WebSocket(wsUrl)
      this.ws.binaryType = 'arraybuffer'

      this.ws.onopen = () => {
        this.clearConnectionTimeout()
        LiveLogger.info('Live WebSocket connected successfully')
        this.reconnectAttempts = 0
        this.startHeartbeat()
        this.callbacks.onOpen()
      }

      this.ws.onmessage = (event) => {
        try {
          if (typeof event.data === 'string') {
            const parsed = JSON.parse(event.data) as ServerLiveMessage
            this.callbacks.onMessage(parsed)
          }
        } catch (err) {
          LiveLogger.error('Failed to parse server message:', err)
        }
      }

      this.ws.onerror = (event) => {
        LiveLogger.warn('Live WebSocket error, checking fallback', event)
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
          this.fallbackToHttp('WebSocket error during handshake')
        } else {
          this.callbacks.onError(event)
        }
      }

      this.ws.onclose = (event) => {
        this.clearConnectionTimeout()
        this.stopHeartbeat()

        if (!this.isExplicitlyClosed && !this.isHttpFallback) {
          LiveLogger.info(`WebSocket closed before established (code: ${event.code}), switching to HTTP fallback`)
          this.fallbackToHttp(`WebSocket closed (code: ${event.code})`)
        } else if (this.isExplicitlyClosed) {
          this.callbacks.onClose(event)
        }
      }
    } catch (err) {
      LiveLogger.error('Fatal error initializing WebSocket, falling back to HTTP:', err)
      this.fallbackToHttp('WebSocket initialization failed')
    }
  }

  /**
   * Transparently activate HTTP live turn mode
   */
  private fallbackToHttp(reason: string): void {
    this.clearConnectionTimeout()
    this.stopHeartbeat()
    if (this.ws) {
      try {
        this.ws.close()
      } catch {
        // ignore
      }
      this.ws = null
    }

    this.isHttpFallback = true
    LiveLogger.info(`Live Voice connected via HTTP/SSE streaming (${reason})`)

    // Notify backend session
    fetch('/api/live/session/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionId: this.sessionId, config: this.currentConfig }),
    }).catch(() => {
      // ignore network log
    })

    // Immediately trigger onOpen and transition UI to LISTENING
    this.callbacks.onOpen()
    this.callbacks.onMessage({
      type: 'status',
      state: 'LISTENING',
      message: 'Connected to NVIDIA NIM',
    })
  }

  private clearConnectionTimeout(): void {
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout)
      this.connectionTimeout = null
    }
  }

  send(message: ClientLiveMessage): void {
    if (this.isHttpFallback) {
      if (message.type === 'audio') {
        this.httpAudioChunks.push(message.data)
        // Keep at most ~120 chunks (about 6 seconds of speech) to bound memory
        if (this.httpAudioChunks.length > 120) {
          this.httpAudioChunks.shift()
        }
      } else if (message.type === 'commit_turn') {
        this.sendCommitTurn()
      } else if (message.type === 'user_speech') {
        this.sendUserSpeech(message.text)
      } else if (message.type === 'interrupt') {
        this.sendInterrupt()
      } else if (message.type === 'config') {
        this.currentConfig = { ...this.currentConfig, ...message.config }
      }
      return
    }

    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return
    }
    try {
      this.ws.send(JSON.stringify(message))
    } catch (err) {
      LiveLogger.error('Failed to send WebSocket message:', err)
    }
  }

  sendAudio(base64Data: string, sampleRate = 16000): void {
    if (this.isHttpFallback) {
      this.httpAudioChunks.push(base64Data)
      // Allow up to 600 chunks (~25-30 seconds of speech at 16kHz)
      if (this.httpAudioChunks.length > 600) {
        this.httpAudioChunks.shift()
      }
      return
    }

    this.send({
      type: 'audio',
      data: base64Data,
      sampleRate,
    })
  }

  sendUserSpeech(text: string): void {
    if (this.isHttpFallback) {
      this.httpAudioChunks = []
      this.executeHttpTurn({ text })
      return
    }

    this.send({
      type: 'user_speech',
      text,
    })
  }

  sendCommitTurn(): void {
    if (this.isHttpFallback) {
      if (this.httpAudioChunks.length > 0) {
        const chunks = [...this.httpAudioChunks]
        this.httpAudioChunks = []
        this.executeHttpTurn({ audioChunks: chunks })
      }
      return
    }

    this.send({
      type: 'commit_turn',
    })
  }

  sendInterrupt(): void {
    if (this.isHttpFallback) {
      if (this.httpTurnAbortController) {
        this.httpTurnAbortController.abort()
        this.httpTurnAbortController = null
      }
      this.httpAudioChunks = []
      this.callbacks.onMessage({
        type: 'status',
        state: 'LISTENING',
        message: 'Interrupted by user',
      })
      return
    }

    this.send({ type: 'interrupt' })
  }

  sendConfig(config: Partial<LiveConfig>): void {
    this.currentConfig = { ...this.currentConfig, ...config }
    if (!this.isHttpFallback) {
      this.send({ type: 'config', config })
    }
  }

  /**
   * Execute speech turn via SSE streaming over HTTP
   */
  private async executeHttpTurn(params: { text?: string; audioChunks?: string[] }): Promise<void> {
    if (this.httpTurnAbortController) {
      this.httpTurnAbortController.abort()
    }
    this.httpTurnAbortController = new AbortController()
    const signal = this.httpTurnAbortController.signal

    try {
      this.callbacks.onMessage({
        type: 'status',
        state: 'PROCESSING',
        message: params.text ? 'Thinking (NVIDIA NIM)...' : 'Transcribing speech...',
      })

      const res = await fetch('/api/live/turn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sessionId: this.sessionId,
          text: params.text,
          audioChunks: params.audioChunks,
          voice: this.currentConfig.voice || 'Chatterbox-Multilingual',
        }),
        signal,
      })

      if (!res.ok) {
        throw new Error(`HTTP turn request failed: ${res.statusText}`)
      }

      const reader = res.body?.getReader()
      if (!reader) {
        throw new Error('No response body stream received from server')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.substring(6)
            if (dataStr === '[DONE]') continue
            try {
              const parsed = JSON.parse(dataStr) as ServerLiveMessage
              this.callbacks.onMessage(parsed)
            } catch {
              // ignore malformed JSON chunk
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        LiveLogger.info('HTTP live turn aborted by user')
        return
      }
      LiveLogger.error('HTTP Live turn error:', err)
      this.callbacks.onMessage({
        type: 'status',
        state: 'LISTENING',
        message: 'Ready',
      })
    } finally {
      this.httpTurnAbortController = null
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.pingInterval = window.setInterval(() => {
      this.send({ type: 'ping', timestamp: Date.now() })
    }, 5000)
  }

  private stopHeartbeat(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  disconnect(): void {
    this.isExplicitlyClosed = true
    this.clearConnectionTimeout()
    this.stopHeartbeat()
    if (this.httpTurnAbortController) {
      this.httpTurnAbortController.abort()
      this.httpTurnAbortController = null
    }
    this.httpAudioChunks = []

    if (this.ws) {
      try {
        this.ws.close()
      } catch {
        // ignore
      }
      this.ws = null
    }
    LiveLogger.info('Live Connection disconnected')
  }

  isConnected(): boolean {
    return this.isHttpFallback || (this.ws !== null && this.ws.readyState === WebSocket.OPEN)
  }
}
