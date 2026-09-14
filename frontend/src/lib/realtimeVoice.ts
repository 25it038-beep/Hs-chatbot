/**
 * Real-Time Voice Conversation Client for HSBot Live Mode.
 * 
 * Features:
 * - Real microphone AudioContext & AnalyserNode for true RMS audio level reactivity.
 * - Continuous Web Speech API recognition (with partial and final transcripts).
 * - Real-time WebSocket connection to /api/realtime/ws/{conversation_id}.
 * - Instantaneous Barge-In: If user speaks while AI is speaking, immediately aborts
 *   audio playback queue and informs backend with {"type": "interrupt"}.
 * - Zero microphone recording when Live Mode is deactivated.
 * - Multilingual support: English (en-US), Tamil (ta-IN), Hindi (hi-IN).
 */

export type RealtimeStatus = 'idle' | 'listening' | 'processing' | 'speaking' | 'interrupted' | 'error' | 'stopped'

export interface RealtimeVoiceCallbacks {
  onStatusChange: (status: RealtimeStatus) => void
  onUserTranscript: (text: string, isFinal: boolean) => void
  onAiChunk: (chunk: string) => void
  onAiDone: (fullText: string) => void
  onAudioLevel: (level: number) => void
  onError: (err: string) => void
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
  private currentStatus: RealtimeStatus = 'idle'
  private isMuted = false
  private isDestroyed = false

  // Speech synthesis queue & state
  private speechQueue: string[] = []
  private isSynthesizing = false
  private activeUtterance: SpeechSynthesisUtterance | null = null

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
  }

  public async start(): Promise<void> {
    this.isDestroyed = false
    this.setStatus('listening')

    try {
      // 1. Initialize Microphone Audio Stream & AnalyserNode
      await this.initMicrophone()

      // 2. Connect WebSocket
      this.connectWebSocket()

      // 3. Initialize Speech Recognition
      this.initSpeechRecognition()
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      console.error('[RealtimeVoice] Failed to start live session:', errorMsg)
      this.setStatus('error')
      this.callbacks.onError(errorMsg)
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
      this.mediaStream.getTracks().forEach(t => t.stop())
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
        this.ws.send(JSON.stringify({ type: 'session_end' }))
        this.ws.close()
      } catch {}
      this.ws = null
    }

    this.setStatus('stopped')
    this.callbacks.onAudioLevel(0)
  }

  public setMute(muted: boolean): void {
    this.isMuted = muted
    if (this.mediaStream) {
      this.mediaStream.getAudioTracks().forEach(t => {
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
      this.ws.send(
        JSON.stringify({
          type: 'config',
          language: lang.startsWith('ta') ? 'ta' : lang.startsWith('hi') ? 'hi' : 'en',
        })
      )
    }
  }

  public interrupt(): void {
    console.log('[RealtimeVoice] Manual barge-in interrupt triggered')
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

  // --- Microphone & Audio Analysis ---
  private async initMicrophone(): Promise<void> {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    })
    this.mediaStream = stream

    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    const ctx = new AudioContextClass()
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

      // Automatic barge-in detection on voice energy if AI is speaking
      if (this.currentStatus === 'speaking' && normalizedLevel > 0.35) {
        console.log('[RealtimeVoice] Voice energy detected during AI speech -> triggering barge-in')
        this.interrupt()
      }

      this.animFrameId = requestAnimationFrame(updateLevel)
    }

    updateLevel()
  }

  // --- Speech Recognition ---
  private initSpeechRecognition(): void {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SpeechRecognitionClass = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognitionClass) {
      console.warn('[RealtimeVoice] Web SpeechRecognition is not supported in this browser.')
      return
    }

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

      // If user speaks while AI is speaking or processing, instant barge-in!
      if ((interimTranscript || finalTranscript) && (this.currentStatus === 'speaking' || this.currentStatus === 'processing')) {
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
    }

    recognition.onend = () => {
      this.isRecognizing = false
      if (this.recognitionShouldRestart && !this.isDestroyed) {
        try {
          recognition.start()
          this.isRecognizing = true
        } catch {}
      }
    }

    this.recognition = recognition
    this.recognitionShouldRestart = true
    try {
      recognition.start()
      this.isRecognizing = true
    } catch (err) {
      console.warn('[RealtimeVoice] Recognition start error:', err)
    }
  }

  // --- WebSocket Connection ---
  private connectWebSocket(): void {
    const loc = window.location
    const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:'
    
    // Resolve host: fallback to current location or custom VITE_API_URL host
    let wsHost = loc.host
    const envUrl = (import.meta.env.VITE_API_URL as string)?.trim()
    if (envUrl && (envUrl.startsWith('http://') || envUrl.startsWith('https://'))) {
      try {
        const parsed = new URL(envUrl)
        wsHost = parsed.host
      } catch {}
    }

    const shortLang = this.language.startsWith('ta') ? 'ta' : this.language.startsWith('hi') ? 'hi' : 'en'
    const wsUrl = `${protocol}//${wsHost}/api/realtime/ws/${encodeURIComponent(this.conversationId)}?language=${encodeURIComponent(shortLang)}&timezone=${encodeURIComponent(this.timezone)}`

    const ws = new WebSocket(wsUrl)
    this.ws = ws

    ws.onopen = () => {
      console.log('[RealtimeVoice] Connected to realtime WebSocket')
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
      console.error('[RealtimeVoice] WebSocket error:', err)
    }

    ws.onclose = () => {
      console.log('[RealtimeVoice] WebSocket closed')
      if (!this.isDestroyed && this.currentStatus !== 'stopped') {
        // Try reconnecting once after delay
        setTimeout(() => {
          if (!this.isDestroyed && this.currentStatus !== 'stopped') {
            this.connectWebSocket()
          }
        }, 2000)
      }
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private handleWsMessage(msg: any): void {
    switch (msg.type) {
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
    if (!('speechSynthesis' in window)) return
    // Queue sentences or complete phrases for natural cadence
    this.speechQueue.push(chunk)
    this.processSpeechQueue()
  }

  private processSpeechQueue(): void {
    if (this.isSynthesizing || this.speechQueue.length === 0 || this.isDestroyed) {
      return
    }

    const textToSpeak = this.speechQueue.join('')
    // Only synthesize when we have punctuation or buffer is sufficiently large
    const hasBoundary = /[.!?\n]/.test(textToSpeak)
    if (!hasBoundary && textToSpeak.length < 60) {
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

    const utterance = new SpeechSynthesisUtterance(cleanText)
    utterance.lang = this.language
    utterance.rate = 1.05
    utterance.pitch = 1.0

    // Voice selection matching target language
    const voices = window.speechSynthesis.getVoices()
    const matchingVoice = voices.find(v => v.lang.startsWith(this.language.substring(0, 2)))
    if (matchingVoice) {
      utterance.voice = matchingVoice
    }

    utterance.onend = () => {
      this.isSynthesizing = false
      this.activeUtterance = null
      if (this.speechQueue.length > 0) {
        this.processSpeechQueue()
      } else {
        this.setStatus('listening')
      }
    }

    utterance.onerror = (e) => {
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
    this.speechQueue = []
    this.isSynthesizing = false
    this.activeUtterance = null
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
  }
}
