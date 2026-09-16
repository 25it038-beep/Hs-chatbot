/**
 * HSBot Speech Engine
 * Provides client-side Speech Recognition (Speech-to-Text) and Speech Synthesis (Text-to-Speech)
 * using Web Speech APIs with robust fallback and cross-browser reliability.
 */

import { create } from 'zustand'

// Check browser support
export function isSpeechRecognitionSupported(): boolean {
  if (typeof window === 'undefined') return false
  return Boolean(
    (window as any).SpeechRecognition ||
    (window as any).webkitSpeechRecognition
  )
}

export function isSpeechSynthesisSupported(): boolean {
  if (typeof window === 'undefined') return false
  return 'speechSynthesis' in window && typeof window.SpeechSynthesisUtterance !== 'undefined'
}

/**
 * Clean markdown and technical syntax so synthesized voice sounds natural and conversational
 */
export function cleanTextForSpeech(text: string): string {
  if (!text) return ''

  let cleaned = text
    // Remove code blocks
    .replace(/```[\s\S]*?```/g, ' [code block omitted] ')
    // Remove inline code
    .replace(/`([^`]+)`/g, '$1')
    // Remove markdown links [title](url) -> title
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Remove raw URLs
    .replace(/https?:\/\/\S+/g, 'link')
    // Remove HTML tags
    .replace(/<[^>]*>/g, '')
    // Remove markdown headers
    .replace(/#{1,6}\s+/g, '')
    // Remove bold and italic markers
    .replace(/[*_]{1,3}([^*_]+)[*_]{1,3}/g, '$1')
    // Remove blockquotes
    .replace(/^\s*>\s+/gm, '')
    // Remove bullet points / numbering
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    // Remove horizontal rules
    .replace(/^[-*_]{3,}\s*$/gm, '')
    // Replace multiple newlines or spaces with single space
    .replace(/\s+/g, ' ')
    .trim()

  return cleaned
}

// Keepalive timer for Chrome SpeechSynthesis bug (pauses after 15 seconds)
let chromeKeepaliveTimer: ReturnType<typeof setInterval> | null = null

function startChromeKeepalive() {
  stopChromeKeepalive()
  chromeKeepaliveTimer = setInterval(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      if (window.speechSynthesis.speaking && !window.speechSynthesis.paused) {
        window.speechSynthesis.pause()
        window.speechSynthesis.resume()
      }
    }
  }, 10000)
}

function stopChromeKeepalive() {
  if (chromeKeepaliveTimer) {
    clearInterval(chromeKeepaliveTimer)
    chromeKeepaliveTimer = null
  }
}

export interface VoiceStoreState {
  // Recognition (STT)
  isListening: boolean
  recognitionSupported: boolean
  interimTranscript: string
  recognitionError: string | null
  
  // Synthesis (TTS)
  isSpeaking: boolean
  speakingMessageId: string | null
  synthesisSupported: boolean
  autoSpeak: boolean
  speechRate: number
  speechPitch: number
  selectedVoiceURI: string | null
  availableVoices: SpeechSynthesisVoice[]

  // Actions
  setAutoSpeak: (enabled: boolean) => void
  setSpeechRate: (rate: number) => void
  setSpeechPitch: (pitch: number) => void
  setSelectedVoiceURI: (uri: string | null) => void
  loadVoices: () => void
  startListening: (onResult?: (text: string, isFinal: boolean) => void) => boolean
  stopListening: () => void
  speakText: (text: string, messageId?: string) => Promise<void>
  stopSpeaking: () => void
}

let activeRecognition: any = null

export const useVoiceStore = create<VoiceStoreState>((set, get) => ({
  isListening: false,
  recognitionSupported: isSpeechRecognitionSupported(),
  interimTranscript: '',
  recognitionError: null,

  isSpeaking: false,
  speakingMessageId: null,
  synthesisSupported: isSpeechSynthesisSupported(),
  autoSpeak: typeof window !== 'undefined' ? localStorage.getItem('hsbot_auto_speak') === 'true' : false,
  speechRate: 1.0,
  speechPitch: 1.0,
  selectedVoiceURI: typeof window !== 'undefined' ? localStorage.getItem('hsbot_voice_uri') : null,
  availableVoices: [],

  setAutoSpeak: (enabled: boolean) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('hsbot_auto_speak', String(enabled))
    }
    set({ autoSpeak: enabled })
  },

  setSpeechRate: (rate: number) => {
    set({ speechRate: rate })
  },

  setSpeechPitch: (pitch: number) => {
    set({ speechPitch: pitch })
  },

  setSelectedVoiceURI: (uri: string | null) => {
    if (typeof window !== 'undefined' && uri) {
      localStorage.setItem('hsbot_voice_uri', uri)
    }
    set({ selectedVoiceURI: uri })
  },

  loadVoices: () => {
    if (!isSpeechSynthesisSupported()) return
    const voices = window.speechSynthesis.getVoices()
    if (voices && voices.length > 0) {
      set({ availableVoices: voices })
    }
  },

  startListening: (onResult?: (text: string, isFinal: boolean) => void) => {
    if (!isSpeechRecognitionSupported()) {
      set({ recognitionError: 'Speech recognition is not supported in this browser.' })
      return false
    }

    // If already listening, stop previous
    if (activeRecognition) {
      try {
        activeRecognition.stop()
      } catch {
        // ignore
      }
      activeRecognition = null
    }

    try {
      const SpeechRecognitionCtor =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      const recognition = new SpeechRecognitionCtor()

      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'

      recognition.onstart = () => {
        set({ isListening: true, interimTranscript: '', recognitionError: null })
      }

      recognition.onresult = (event: any) => {
        let interim = ''
        let final = ''

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0]?.transcript || ''
          if (event.results[i].isFinal) {
            final += transcript
          } else {
            interim += transcript
          }
        }

        set({ interimTranscript: interim })

        if (final && onResult) {
          onResult(final, true)
        } else if (interim && onResult) {
          onResult(interim, false)
        }
      }

      recognition.onerror = (event: any) => {
        console.warn('[Speech] Recognition error:', event.error)
        if (event.error === 'not-allowed') {
          set({ recognitionError: 'Microphone permission denied. Please allow microphone access.' })
        } else if (event.error !== 'no-speech') {
          set({ recognitionError: `Speech recognition error: ${event.error}` })
        }
        set({ isListening: false })
      }

      recognition.onend = () => {
        set({ isListening: false, interimTranscript: '' })
        activeRecognition = null
      }

      activeRecognition = recognition
      recognition.start()
      return true
    } catch (err: any) {
      console.error('[Speech] Failed to start recognition:', err)
      set({ isListening: false, recognitionError: err.message || 'Could not start microphone' })
      return false
    }
  },

  stopListening: () => {
    if (activeRecognition) {
      try {
        activeRecognition.stop()
      } catch {
        // ignore
      }
      activeRecognition = null
    }
    set({ isListening: false, interimTranscript: '' })
  },

  speakText: async (text: string, messageId?: string) => {
    if (!isSpeechSynthesisSupported()) return

    const { stopSpeaking, speechRate, speechPitch, selectedVoiceURI, availableVoices } = get()

    // Stop current speech first
    stopSpeaking()

    const cleaned = cleanTextForSpeech(text)
    if (!cleaned) return

    return new Promise<void>((resolve) => {
      try {
        window.speechSynthesis.cancel()

        const utterance = new SpeechSynthesisUtterance(cleaned)
        utterance.rate = speechRate
        utterance.pitch = speechPitch

        // Pick preferred voice if selected, otherwise prioritize natural English voice
        let voice: SpeechSynthesisVoice | undefined
        if (selectedVoiceURI) {
          voice = availableVoices.find((v) => v.voiceURI === selectedVoiceURI)
        }
        if (!voice && availableVoices.length > 0) {
          // Prefer natural or high-quality voice
          voice =
            availableVoices.find((v) => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Neural') || v.name.includes('Google') || v.name.includes('Samantha'))) ||
            availableVoices.find((v) => v.lang.startsWith('en')) ||
            availableVoices[0]
        }
        if (voice) {
          utterance.voice = voice
        }

        utterance.onstart = () => {
          set({ isSpeaking: true, speakingMessageId: messageId || 'global' })
          startChromeKeepalive()
        }

        utterance.onend = () => {
          stopChromeKeepalive()
          set({ isSpeaking: false, speakingMessageId: null })
          resolve()
        }

        utterance.onerror = (e) => {
          console.warn('[Speech] Speech synthesis error:', e)
          stopChromeKeepalive()
          set({ isSpeaking: false, speakingMessageId: null })
          resolve()
        }

        window.speechSynthesis.speak(utterance)
      } catch (err) {
        console.error('[Speech] Failed to speak:', err)
        stopChromeKeepalive()
        set({ isSpeaking: false, speakingMessageId: null })
        resolve()
      }
    })
  },

  stopSpeaking: () => {
    stopChromeKeepalive()
    if (isSpeechSynthesisSupported()) {
      try {
        window.speechSynthesis.cancel()
      } catch {
        // ignore
      }
    }
    set({ isSpeaking: false, speakingMessageId: null })
  },
}))

// Initialize voices listener if in browser
if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
  const populate = () => {
    useVoiceStore.getState().loadVoices()
  }
  populate()
  if (window.speechSynthesis.onvoiceschanged !== undefined) {
    window.speechSynthesis.onvoiceschanged = populate
  }
}
