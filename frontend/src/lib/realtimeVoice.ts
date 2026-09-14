/**
 * Real-Time Voice Conversation Client for HSBot Live Mode.
 * 
 * Features:
 * - Resilient WebSocket connection with automatic backend detection & fallback
 *   (supports local backend, Render production, custom URLs, and Vite proxy).
 * - Real microphone AudioContext & AnalyserNode for true RMS audio level visualizer.
 * - Continuous Web Speech API recognition (with partial and final transcripts).
 * - Speech-driven Natural Barge-In: Interrupts AI speech only on real user words,
 *   preventing speaker echo / acoustic feedback from self-interrupting the AI.
 * - Manual input fallback: Send real-time utterances via text even if mic or
 *   speech recognition is unavailable in the user's browser.
 * - Robust SpeechSynthesis with Chrome keep-alive watchdog and voice pre-warming.
 * - Multilingual support: English (en-US), Tamil (ta-IN), Hindi (hi-IN).
 */

export type RealtimeStatus =
  | 'connecting'
  | 'idle'
  | 'listening'
  | 'processing'
  | 'speaking'
  | 'interrupted'
  | 'error'
  | 'stopped'

export interface RealtimeVoiceCallbacks {
  onStatusChange: (status: RealtimeStatus) => void
  onUserTranscript: (text: string, isFinal: boolean) => void
  onAiChunk: (chunk: string) => void
  onAiDone: (fullText: string) => void
  onAudioLevel: (level: number) => void
  onError: (err: string) => void
  onConnectionChange?: (connected: boolean, endpoint: string) => void
}

function resolveWsUrl(
  baseCandidate: string,
  conversationId: string,
  language: string,
  timezone: string,
  location?: string
): string {
  let clean = baseCandidate.trim().replace(/\/+$/, '')
  let wsProto = 'ws:'

  if (clean.startsWith('https://') || clean.startsWith('wss://')) {
    wsProto = 'wss:'
  } else if (clean.startsWith('http://') || clean.startsWith('ws://')) {
    wsProto = 'ws:'
  } else if (typeof window !== 'undefined') {
    wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  }

  clean = clean.replace(/^(https?|wss?):\/\//, '').replace(/\/api$/, '')

  const shortLang = language.startsWith('ta') ? 'ta' : language.startsWith('hi') ? 'hi' : 'en'
  let url = `${wsProto}//${clean}/api/realtime/ws/${encodeURIComponent(conversationId)}?language=${encodeURIComponent(shortLang)}&timezone=${encodeURIComponent(timezone)}`
  if (location) {
    url += `&location=${encodeURIComponent(location)}`
  }
  return url
}

export class RealtimeVoiceClient {
  private conversationId: string
  private language: string
  private timezone: string
  private location?: string
  private callbacks: RealtimeVoiceCallbacks

  private ws: WebSocket | null = null
  private audioContext: AudioContext | null = null
  private analyser: AnalyserNode | null = null
  private mediaStream: MediaStream | null = null
  private animFrameId: number | null = null

  // Speech Recognition
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private recognition: any = null
  private isRecognizing = false
  private recognitionShouldRestart = false

  // State
  private currentStatus: RealtimeStatus = 'connecting'
  private isMuted = false
  private isDestroyed = false
  private activeWsEndpoint = ''
  private candidateIndex = 0

  // Speech synthesis queue & state
  private speechQueue: string[] = []
  private isSynthesizing = false
  private activeUtterance: SpeechSynthesisUtterance | null = null
  private speechKeepAliveInterval: number | null = null

  constructor(
    conversationId: string,
    callbacks: RealtimeVoiceCallbacks,
    options?: { language?: string; timezone?: string; location?: string }
  ) {
    this.conversationId = conversationId
    this.callbacks = callbacks
    this.language = options?.language || 'en-US'
    this.timezone = options?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
    this.location = options?.location

    // Warm up speech synthesis voices if available
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.getVoices()
      if ('onvoiceschanged' in window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = () => {
          window.speechSynthesis.getVoices()
        }
      }
    }
  }

  public async start(): Promise<void> {
    this.isDestroyed = false
    this.setStatus('connecting')

    // Unlock speechSynthesis on user gesture
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        window.speechSynthesis.resume()
      } catch {}
    }

    try {
      // 1. Connect WebSocket to live server (with auto-fallback)
      this.connectWebSocket()

      // 2. Initialize Speech Recognition immediately
      this.initSpeechRecognition()

      // 3. Initialize Microphone Audio Stream for visualizer in background (does not block speech recognition)
      this.initMicrophone().catch((err) => {
        console.warn('[RealtimeVoice] Audio visualizer setup note:', err)
      })
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      console.warn('[RealtimeVoice] Note during session initialization:', errorMsg)
    }
  }

  public stop(): void {
    this.isDestroyed = true
    this.recognitionShouldRestart = false

    // Stop recognition
    if (this.recognition) {
      try {
        this.recognition.abort()
      } catch {}
      this.recognition = null
    }

    // Stop audio playback
    this.stopAiSpeech()

    // Stop microphone stream & context
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop())
      this.mediaStream = null
    }
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId)
      this.animFrameId = null
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      try {
        this.audioContext.close()
      } catch {}
      this.audioContext = null
    }

    // Close WebSocket
    if (this.ws) {
      try {
        if (this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'session_end' }))
        }
        this.ws.close()
      } catch {}
      this.ws = null
    }

    this.setStatus('stopped')
    this.callbacks.onAudioLevel(0)
    this.callbacks.onConnectionChange?.(false, '')
  }

  public sendUtterance(text: string): void {
    const trimmed = text.trim()
    if (!trimmed) return

    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.callbacks.onError('Not connected to live server yet. Reconnecting...')
      this.connectWebSocket()
      return
    }

    // Stop previous AI speech on new user utterance
    this.stopAiSpeech()
    this.callbacks.onUserTranscript(trimmed, true)
    this.setStatus('processing')
    this.ws.send(JSON.stringify({ type: 'transcript_final', text: trimmed }))
  }

  public setMute(muted: boolean): void {
    this.isMuted = muted
    if (this.mediaStream) {
      this.mediaStream.getAudioTracks().forEach((t) => {
        t.enabled = !muted
      })
    }
    if (muted) {
      this.callbacks.onAudioLevel(0)
    }
  }

  public setLanguage(lang: string): void {
    this.language = lang
    if (this.recognition) {
      this.recognition.lang = lang
    }
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const shortLang = lang.startsWith('ta') ? 'ta' : lang.startsWith('hi') ? 'hi' : 'en'
      this.ws.send(JSON.stringify({ type: 'config', language: shortLang }))
    }
  }

  public interrupt(): void {
    console.log('[RealtimeVoice] Manual or natural barge-in interrupt triggered')
    this.stopAiSpeech()
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'interrupt' }))
    }
    this.setStatus('listening')
  }

  private setStatus(status: RealtimeStatus): void {
    this.currentStatus = status
    this.callbacks.onStatusChange(status)
  }

  // --- Microphone & Audio Analysis for Orb Visualizer ---
  private async initMicrophone(): Promise<void> {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      console.warn('[RealtimeVoice] getUserMedia not available')
      this.callbacks.onError('Microphone not supported on this browser or insecure connection (HTTPS required). You can type messages below.')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      this.mediaStream = stream

      const AudioContextClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext

      if (AudioContextClass) {
        const ctx = new AudioContextClass()
        if (ctx.state === 'suspended') {
          await ctx.resume().catch(() => {})
        }
        this.audioContext = ctx

        const source = ctx.createMediaStreamSource(stream)
        const analyser = ctx.createAnalyser()
        analyser.fftSize = 256
        analyser.smoothingTimeConstant = 0.5
        source.connect(analyser)
        this.analyser = analyser

        const dataArray = new Uint8Array(analyser.frequencyBinCount)

        const updateLevel = () => {
          if (this.isDestroyed || !this.analyser) return

          if (this.isMuted) {
            this.callbacks.onAudioLevel(0)
            this.animFrameId = requestAnimationFrame(updateLevel)
            return
          }

          this.analyser.getByteFrequencyData(dataArray)
          let sum = 0
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i] * dataArray[i]
          }
          const rms = Math.sqrt(sum / dataArray.length) / 255
          const normalizedLevel = Math.min(1.0, rms * 3.5)
          this.callbacks.onAudioLevel(normalizedLevel)

          // NOTE: Do NOT use RMS microphone energy for automatic barge-in while AI is speaking.
          // Laptop speaker audio bleeds into the microphone and causes acoustic self-interruption.
          // Natural barge-in is handled exclusively on recognized user speech words in recognition.onresult.

          this.animFrameId = requestAnimationFrame(updateLevel)
        }

        updateLevel()
      }
    } catch (err: unknown) {
      console.warn('[RealtimeVoice] Microphone permission or device error:', err)
      const errStr = String(err)
      if (errStr.includes('NotAllowedError') || errStr.includes('Permission')) {
        this.callbacks.onError('Microphone permission denied. Please allow microphone access in your browser or type below.')
      } else {
        this.callbacks.onError('Microphone not available. You can type messages below to talk live.')
      }
    }
  }

  // --- Speech Recognition ---
  private initSpeechRecognition(): void {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SpeechRecognitionClass = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognitionClass) {
      console.warn('[RealtimeVoice] Web SpeechRecognition is not supported in this browser.')
      this.callbacks.onError('Voice recognition is not supported in this browser. Chrome or Edge is recommended, or you can type below.')
      return
    }

    try {
      const recognition = new SpeechRecognitionClass()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = this.language
      recognition.maxAlternatives = 1

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onresult = (event: any) => {
        if (this.isMuted || this.isDestroyed) return

        let interimTranscript = ''
        let finalTranscript = ''

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const item = event.results[i]
          const text = item[0]?.transcript || ''
          if (item.isFinal) {
            finalTranscript += text
          } else {
            interimTranscript += text
          }
        }

        const activeWords = (interimTranscript || finalTranscript).trim()

        // Natural Barge-In: If user actually speaks words while AI is speaking or processing
        if (activeWords && (this.currentStatus === 'speaking' || this.currentStatus === 'processing')) {
          console.log('[RealtimeVoice] User spoke during AI output -> triggering natural barge-in')
          this.interrupt()
        }

        if (interimTranscript) {
          this.callbacks.onUserTranscript(interimTranscript, false)
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'transcript_partial', text: interimTranscript }))
          }
        }

        if (finalTranscript) {
          const cleanFinal = finalTranscript.trim()
          if (cleanFinal) {
            this.callbacks.onUserTranscript(cleanFinal, true)
            this.setStatus('processing')
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
              this.ws.send(JSON.stringify({ type: 'transcript_final', text: cleanFinal }))
            }
          }
        }
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onerror = (e: any) => {
        if (e.error === 'no-speech') return
        console.warn('[RealtimeVoice] Speech recognition error:', e.error)
        if (e.error === 'not-allowed') {
          this.callbacks.onError('Microphone permission denied. Please allow microphone access in your browser.')
        } else if (e.error === 'network') {
          this.callbacks.onError('Speech recognition network error. You can type messages below to talk live.')
        }
      }

      recognition.onend = () => {
        this.isRecognizing = false
        if (this.recognitionShouldRestart && !this.isDestroyed) {
          setTimeout(() => {
            if (this.recognitionShouldRestart && !this.isDestroyed && !this.isRecognizing) {
              try {
                recognition.start()
                this.isRecognizing = true
              } catch (startErr) {
                console.warn('[RealtimeVoice] Speech recognition restart note:', startErr)
              }
            }
          }, 150)
        }
      }

      this.recognition = recognition
      this.recognitionShouldRestart = true
      recognition.start()
      this.isRecognizing = true
    } catch (err) {
      console.warn('[RealtimeVoice] Recognition start error:', err)
      this.callbacks.onError('Failed to start speech recognition. You can type messages below.')
    }
  }

  // --- WebSocket Connection with Auto-Fallback ---
  private getCandidateUrls(): string[] {
    const candidates: string[] = []

    const envUrl = (import.meta.env.VITE_API_URL as string)?.trim()
    if (envUrl) {
      candidates.push(envUrl)
    }

    // Include Render production backend (always live)
    candidates.push('https://hs-chatbot-2.onrender.com')

    // Include local backend candidate
    candidates.push('http://localhost:8000')

    // Current origin (for Vite proxy or custom deployments)
    if (typeof window !== 'undefined' && window.location.origin) {
      candidates.push(window.location.origin)
    }

    // Deduplicate
    return Array.from(new Set(candidates.map((c) => c.replace(/\/+$/, ''))))
  }

  private connectWebSocket(): void {
    if (this.isDestroyed) return

    const candidates = this.getCandidateUrls()
    const targetBase = candidates[this.candidateIndex % candidates.length]
    const wsUrl = resolveWsUrl(targetBase, this.conversationId, this.language, this.timezone, this.location)
    this.activeWsEndpoint = targetBase

    console.log(`[RealtimeVoice] Connecting WebSocket (${this.candidateIndex + 1}/${candidates.length}): ${wsUrl}`)
    this.setStatus('connecting')

    let isEstablished = false

    try {
      const ws = new WebSocket(wsUrl)
      this.ws = ws

      ws.onopen = () => {
        isEstablished = true
        console.log(`[RealtimeVoice] Connected successfully to ${this.activeWsEndpoint}`)
        this.setStatus('listening')
        this.callbacks.onConnectionChange?.(true, this.activeWsEndpoint)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handleWsMessage(data)
        } catch (err) {
          console.error('[RealtimeVoice] Error parsing WS message:', err)
        }
      }

      ws.onerror = (err) => {
        console.warn(`[RealtimeVoice] WebSocket connection error on ${this.activeWsEndpoint}:`, err)
      }

      ws.onclose = () => {
        console.log(`[RealtimeVoice] WebSocket closed for ${this.activeWsEndpoint}`)
        this.callbacks.onConnectionChange?.(false, this.activeWsEndpoint)

        if (this.isDestroyed || this.currentStatus === 'stopped') {
          return
        }

        // If connection wasn't established, quickly try next fallback candidate
        if (!isEstablished) {
          this.candidateIndex++
          setTimeout(() => {
            if (!this.isDestroyed && this.currentStatus !== 'stopped') {
              this.connectWebSocket()
            }
          }, 800)
        } else {
          // Reconnect after brief pause
          setTimeout(() => {
            if (!this.isDestroyed && this.currentStatus !== 'stopped') {
              this.connectWebSocket()
            }
          }, 2500)
        }
      }
    } catch (err) {
      console.warn(`[RealtimeVoice] Failed to create WebSocket for ${wsUrl}:`, err)
      this.candidateIndex++
      setTimeout(() => {
        if (!this.isDestroyed) {
          this.connectWebSocket()
        }
      }, 1000)
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private handleWsMessage(msg: any): void {
    switch (msg.type) {
      case 'session_init':
        this.setStatus('listening')
        this.callbacks.onConnectionChange?.(true, this.activeWsEndpoint)
        break

      case 'status':
        if (msg.status === 'interrupted') {
          this.stopAiSpeech()
          this.setStatus('listening')
        } else if (msg.status === 'processing') {
          this.setStatus('processing')
        } else if (msg.status === 'speaking') {
          this.setStatus('speaking')
        } else if (msg.status === 'listening') {
          this.setStatus('listening')
        }
        break

      case 'ai_text_chunk':
        if (msg.chunk) {
          this.callbacks.onAiChunk(msg.chunk)
          this.enqueueSpeechText(msg.chunk)
        }
        break

      case 'ai_text_done':
        if (msg.full_text) {
          this.callbacks.onAiDone(msg.full_text)
        }
        break

      case 'error':
        this.callbacks.onError(msg.error || 'Unknown error occurred')
        this.setStatus('listening')
        break
    }
  }

  // --- Audio / TTS Playback Queue & Interruption ---
  private enqueueSpeechText(chunk: string): void {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return
    this.speechQueue.push(chunk)
    this.processSpeechQueue()
  }

  private processSpeechQueue(): void {
    if (this.isSynthesizing || this.speechQueue.length === 0 || this.isDestroyed) {
      return
    }

    const textToSpeak = this.speechQueue.join('')
    const hasBoundary = /[.!?\n]/.test(textToSpeak)
    if (!hasBoundary && textToSpeak.length < 25) {
      return
    }

    // Flush current buffer
    this.speechQueue = []
    this.isSynthesizing = true
    this.setStatus('speaking')

    const cleanText = textToSpeak.replace(/[*#_`]/g, '').trim()
    if (!cleanText) {
      this.isSynthesizing = false
      return
    }

    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      this.isSynthesizing = false
      this.setStatus('listening')
      return
    }

    const utterance = new SpeechSynthesisUtterance(cleanText)
    utterance.lang = this.language
    utterance.rate = 1.45
    utterance.pitch = 1.0

    // Voice selection matching target language
    const voices = window.speechSynthesis.getVoices()
    const matchingVoice = voices.find((v) => v.lang.startsWith(this.language.substring(0, 2)))
    if (matchingVoice) {
      utterance.voice = matchingVoice
    }

    // Chrome keep-alive watchdog
    if (this.speechKeepAliveInterval) {
      clearInterval(this.speechKeepAliveInterval)
      this.speechKeepAliveInterval = null
    }

    utterance.onstart = () => {
      this.speechKeepAliveInterval = window.setInterval(() => {
        if (!window.speechSynthesis.speaking) {
          if (this.speechKeepAliveInterval) {
            clearInterval(this.speechKeepAliveInterval)
            this.speechKeepAliveInterval = null
          }
          return
        }
        window.speechSynthesis.pause()
        window.speechSynthesis.resume()
      }, 10000)
    }

    utterance.onend = () => {
      if (this.speechKeepAliveInterval) {
        clearInterval(this.speechKeepAliveInterval)
        this.speechKeepAliveInterval = null
      }
      this.isSynthesizing = false
      this.activeUtterance = null
      if (this.speechQueue.length > 0) {
        this.processSpeechQueue()
      } else {
        this.setStatus('listening')
      }
    }

    utterance.onerror = (e) => {
      if (this.speechKeepAliveInterval) {
        clearInterval(this.speechKeepAliveInterval)
        this.speechKeepAliveInterval = null
      }
      if (e.error !== 'interrupted' && e.error !== 'canceled') {
        console.warn('[RealtimeVoice] Speech synthesis error:', e.error)
      }
      this.isSynthesizing = false
      this.activeUtterance = null
      this.setStatus('listening')
    }

    this.activeUtterance = utterance
    window.speechSynthesis.speak(utterance)
  }

  private stopAiSpeech(): void {
    if (this.speechKeepAliveInterval) {
      clearInterval(this.speechKeepAliveInterval)
      this.speechKeepAliveInterval = null
    }
    this.speechQueue = []
    this.isSynthesizing = false
    this.activeUtterance = null
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
  }
}
