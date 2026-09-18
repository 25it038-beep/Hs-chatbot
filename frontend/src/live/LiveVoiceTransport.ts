/**
 * WebSocket and HTTP Transport for HSBot Live Voice.
 * Coordinates bidirectional real-time audio communication with backend endpoints.
 */

import { LiveEngine, LiveServerMessage, LiveState } from './LiveVoiceTypes'

export class LiveVoiceTransport {
  private ws: WebSocket | null = null
  private sessionId: string = ''
  private currentEngine: LiveEngine = 'cascaded'
  private isExplicitlyClosed: boolean = false
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 3

  public onMessage: ((msg: LiveServerMessage) => void) | null = null
  public onStateChange: ((state: LiveState) => void) | null = null
  public onError: ((err: any) => void) | null = null

  constructor(sessionId: string = 'live_session_' + Date.now()) {
    this.sessionId = sessionId
  }

  public get isConnected(): boolean {
    return !!this.ws && this.ws.readyState === WebSocket.OPEN
  }

  public get engine(): LiveEngine {
    return this.currentEngine
  }

  /**
   * Dynamically builds the WebSocket URL from production backend or environment.
   */
  public getWebSocketUrl(engine: LiveEngine = 'cascaded'): string {
    const envApiUrl = (import.meta.env.VITE_API_URL as string)?.trim() || (import.meta.env.NEXT_PUBLIC_API_URL as string)?.trim()

    let wsProtocol: string
    let wsHost: string
    let apiPath = '/api'

    if (envApiUrl && (envApiUrl.startsWith('http://') || envApiUrl.startsWith('https://'))) {
      try {
        const parsed = new URL(envApiUrl)
        wsProtocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:'
        wsHost = parsed.host
        apiPath = parsed.pathname.replace(/\/+$/, '') || '/api'
        if (!apiPath.endsWith('/api') && apiPath !== '') {
          apiPath = `${apiPath}/api`
        }
      } catch {
        wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        wsHost = window.location.host
      }
    } else if (window.location.host === 'hs-chatbot-3.onrender.com' || (window.location.host.endsWith('.onrender.com') && !window.location.host.includes('hs-chatbot-2'))) {
      // Deployed static frontend on Render without local backend proxy -> routes to public backend
      wsProtocol = 'wss:'
      wsHost = 'hs-chatbot-2.onrender.com'
      apiPath = '/api'
    } else {
      // Local development (Vite proxy forwards /api and WebSockets to backend)
      wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      wsHost = window.location.host
      apiPath = '/api'
    }

    apiPath = apiPath.replace(/\/+$/, '')
    return `${wsProtocol}//${wsHost}${apiPath}/live/ws/${this.sessionId}?engine=${encodeURIComponent(engine)}`
  }

  /**
   * Connects to the Live Voice WebSocket endpoint.
   */
  public async connect(engine: LiveEngine = 'cascaded'): Promise<void> {
    this.currentEngine = engine
    this.isExplicitlyClosed = false

    if (this.ws) {
      this.disconnect()
    }

    if (this.onStateChange) {
      this.onStateChange('CONNECTING')
    }

    const wsUrl = this.getWebSocketUrl(engine)
    console.log('[LIVE-PROD]', {
      environment: import.meta.env.MODE || (window.location.hostname === 'localhost' ? 'development' : 'production'),
      origin: window.location.origin,
      secureContext: window.isSecureContext,
      backendUrl: (import.meta.env.VITE_API_URL as string) || '(derived)',
      websocketUrl: wsUrl.split('?')[0],
      connectionState: 'CONNECTING',
    })

    return new Promise<void>((resolve, reject) => {
      try {
        this.ws = new WebSocket(wsUrl)
        let resolved = false

        this.ws.onopen = () => {
          this.reconnectAttempts = 0
          if (this.onStateChange) {
            this.onStateChange('CONNECTED')
          }
          if (!resolved) {
            resolved = true
            resolve()
          }
        }

        this.ws.onmessage = (event) => {
          try {
            const msg: LiveServerMessage = JSON.parse(event.data)
            if (this.onMessage) {
              this.onMessage(msg)
            }
          } catch (err) {
            console.error('[LiveVoiceTransport] Parse error:', err)
          }
        }

        this.ws.onerror = (err) => {
          console.warn('[LiveVoiceTransport] WebSocket error:', err)
          if (this.onError) {
            this.onError(err)
          }
          if (!resolved) {
            resolved = true
            reject(new Error(`WebSocket connection to ${wsUrl.split('?')[0]} failed`))
          }
        }

        this.ws.onclose = (event) => {
          if (!resolved) {
            resolved = true
            reject(new Error(`WebSocket closed before open: code=${event.code} reason=${event.reason || 'none'}`))
          }
          if (!this.isExplicitlyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++
            const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 4000)
            setTimeout(() => {
              if (!this.isExplicitlyClosed) {
                this.connect(this.currentEngine).catch(() => {})
              }
            }, delay)
          } else {
            if (this.onStateChange) {
              this.onStateChange('DISCONNECTED')
            }
          }
        }
      } catch (err) {
        if (this.onError) {
          this.onError(err)
        }
        if (this.onStateChange) {
          this.onStateChange('ERROR')
        }
        reject(err)
      }
    })
  }

  /**
   * Sends 16-bit PCM audio frame over WebSocket.
   */
  public sendAudioChunk(pcmBytes: Uint8Array): void {
    if (!this.isConnected || !this.ws) return

    let binary = ''
    const len = pcmBytes.byteLength
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(pcmBytes[i])
    }
    const b64 = window.btoa(binary)

    this.send({
      type: 'audio_chunk',
      data: b64,
      sampleRate: 16000,
    })
  }

  /**
   * Sends user text prompt directly.
   */
  public sendTextTurn(text: string): void {
    this.send({
      type: 'turn_text',
      text: text,
    })
  }

  /**
   * Signals end of speech in speech-segmented turn mode.
   */
  public sendAudioEnd(): void {
    this.send({
      type: 'audio_end',
    })
  }

  /**
   * Sends interruption (barge-in) event.
   */
  public sendInterrupt(): void {
    this.send({
      type: 'interrupt',
    })
  }

  /**
   * Requests switching the Live Voice engine on the backend.
   */
  public switchEngine(newEngine: LiveEngine): void {
    this.currentEngine = newEngine
    this.send({
      type: 'switch_engine',
      engine: newEngine,
    })
  }

  /**
   * Retries availability check for Nemotron VoiceChat.
   */
  public retryAvailability(): void {
    this.send({
      type: 'retry',
    })
  }

  /**
   * Closes active connection.
   */
  public disconnect(): void {
    this.isExplicitlyClosed = true
    if (this.ws) {
      try {
        this.ws.close()
      } catch (_) {}
      this.ws = null
    }
    if (this.onStateChange) {
      this.onStateChange('DISCONNECTED')
    }
  }

  private send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }
}
