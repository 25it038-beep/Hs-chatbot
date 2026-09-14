import React, { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Mic,
  MicOff,
  PhoneOff,
  Volume2,
  VolumeX,
  Languages,
  Sparkles,
  AlertCircle,
  Radio,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { VoiceOrb } from '@/components/voice/VoiceOrb'
import { RealtimeVoiceClient, RealtimeStatus } from '@/lib/realtimeVoice'
import { VOICE_STATES } from '@/lib/voice'

interface LiveConversationModalProps {
  isOpen: boolean
  conversationId: string
  onClose: () => void
  onMessageSaved?: (userText: string, assistantText: string) => void
}

const LANGUAGES = [
  { code: 'en-US', label: 'English (US)' },
  { code: 'ta-IN', label: 'தமிழ் (Tamil)' },
  { code: 'hi-IN', label: 'हिंदी (Hindi)' },
]

export function LiveConversationModal({
  isOpen,
  conversationId,
  onClose,
  onMessageSaved,
}: LiveConversationModalProps) {
  const [status, setStatus] = useState<RealtimeStatus>('listening')
  const [audioLevel, setAudioLevel] = useState<number>(0)
  const [userTranscript, setUserTranscript] = useState<string>('')
  const [aiResponse, setAiResponse] = useState<string>('')
  const [isMuted, setIsMuted] = useState<boolean>(false)
  const [language, setLanguage] = useState<string>('en-US')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const clientRef = useRef<RealtimeVoiceClient | null>(null)
  const lastUserTextRef = useRef<string>('')
  const currentAiAccumulatorRef = useRef<string>('')

  // Map RealtimeStatus to VoiceOrb's VOICE_STATES
  const getOrbState = (st: RealtimeStatus): string => {
    switch (st) {
      case 'listening':
        return VOICE_STATES.LISTENING
      case 'processing':
        return VOICE_STATES.PROCESSING
      case 'speaking':
        return VOICE_STATES.AI_SPEAKING
      case 'interrupted':
        return VOICE_STATES.LISTENING
      case 'error':
        return VOICE_STATES.ERROR
      default:
        return VOICE_STATES.IDLE
    }
  }

  useEffect(() => {
    if (!isOpen) {
      if (clientRef.current) {
        clientRef.current.stop()
        clientRef.current = null
      }
      return
    }

    setErrorMessage(null)
    setUserTranscript('')
    setAiResponse('')
    lastUserTextRef.current = ''
    currentAiAccumulatorRef.current = ''

    const client = new RealtimeVoiceClient(
      conversationId,
      {
        onStatusChange: (newStatus) => {
          setStatus(newStatus)
        },
        onUserTranscript: (text, isFinal) => {
          setUserTranscript(text)
          if (isFinal) {
            lastUserTextRef.current = text
            currentAiAccumulatorRef.current = ''
            setAiResponse('')
          }
        },
        onAiChunk: (chunk) => {
          currentAiAccumulatorRef.current += chunk
          setAiResponse(currentAiAccumulatorRef.current)
        },
        onAiDone: (fullText) => {
          setAiResponse(fullText)
          if (lastUserTextRef.current && fullText && onMessageSaved) {
            onMessageSaved(lastUserTextRef.current, fullText)
          }
        },
        onAudioLevel: (level) => {
          setAudioLevel(level)
        },
        onError: (err) => {
          setErrorMessage(err)
        },
      },
      { language }
    )

    clientRef.current = client
    client.start()

    return () => {
      client.stop()
      clientRef.current = null
    }
  }, [isOpen, conversationId])

  const handleToggleMute = () => {
    const next = !isMuted
    setIsMuted(next)
    clientRef.current?.setMute(next)
  }

  const handleLanguageChange = (newLang: string) => {
    setLanguage(newLang)
    clientRef.current?.setLanguage(newLang)
  }

  const handleManualInterrupt = () => {
    clientRef.current?.interrupt()
  }

  const handleClose = () => {
    clientRef.current?.stop()
    clientRef.current = null
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md transition-all p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 15 }}
        className="relative flex flex-col items-center justify-between w-full max-w-2xl h-[580px] bg-card/95 border border-border/80 rounded-3xl shadow-2xl overflow-hidden p-6 sm:p-8"
      >
        {/* Top Header */}
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <span className="font-semibold text-sm tracking-wide text-foreground flex items-center gap-1.5">
              <Radio size={14} className="text-primary animate-pulse" />
              HSBot LIVE
            </span>
          </div>

          {/* Language Selector */}
          <div className="flex items-center gap-1 bg-muted/60 px-2 py-1 rounded-full border border-border/60">
            <Languages size={13} className="text-muted-foreground mr-1" />
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                onClick={() => handleLanguageChange(lang.code)}
                className={`text-[11px] font-medium px-2 py-0.5 rounded-full transition-all ${
                  language === lang.code
                    ? 'bg-primary text-primary-foreground shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {lang.label.split(' ')[0]}
              </button>
            ))}
          </div>
        </div>

        {/* Center Reactive Visualizer */}
        <div className="flex flex-col items-center justify-center my-auto w-full relative">
          <VoiceOrb
            status={getOrbState(status)}
            audioLevel={audioLevel}
            isHandsFree={true}
            wakeWordDetected={false}
            wsConnected={true}
            onToggle={() => {}}
            onInterrupt={handleManualInterrupt}
            className="w-48 h-48 sm:w-56 sm:h-56"
          />

          {/* Status Label */}
          <div className="mt-4 flex items-center gap-2 text-xs sm:text-sm font-medium">
            {status === 'speaking' ? (
              <span className="text-primary flex items-center gap-1.5 animate-pulse">
                <Sparkles size={14} /> HSBot is speaking... (Speak to interrupt)
              </span>
            ) : status === 'processing' ? (
              <span className="text-amber-500 flex items-center gap-1.5">
                Thinking & fetching...
              </span>
            ) : status === 'interrupted' ? (
              <span className="text-rose-500 font-medium">Interrupted — listening to you</span>
            ) : isMuted ? (
              <span className="text-muted-foreground flex items-center gap-1">
                <MicOff size={14} /> Microphone muted
              </span>
            ) : (
              <span className="text-emerald-500 flex items-center gap-1.5">
                <Mic size={14} className="animate-pulse" /> Listening naturally...
              </span>
            )}
          </div>

          {/* Error notification if any */}
          {errorMessage && (
            <div className="mt-2 text-xs text-destructive flex items-center gap-1.5 bg-destructive/10 px-3 py-1 rounded-md max-w-md text-center">
              <AlertCircle size={13} />
              {errorMessage}
            </div>
          )}
        </div>

        {/* Real-time Subtitles / Utterance Feed */}
        <div className="w-full bg-muted/40 border border-border/50 rounded-2xl p-3.5 sm:p-4 min-h-[90px] max-h-[110px] overflow-y-auto mb-4 text-left flex flex-col justify-end">
          {userTranscript && (
            <div className="text-xs text-muted-foreground/80 mb-1 line-clamp-2">
              <span className="font-semibold text-primary/90 mr-1.5">You:</span>
              {userTranscript}
            </div>
          )}
          {aiResponse ? (
            <div className="text-xs sm:text-sm text-foreground/95 font-medium line-clamp-3">
              <span className="font-semibold text-primary mr-1.5">HSBot:</span>
              {aiResponse}
            </div>
          ) : (
            !userTranscript && (
              <p className="text-xs text-muted-foreground/50 italic text-center py-2">
                Speak naturally. Ask for time, weather, knowledge, or anything. You can interrupt anytime.
              </p>
            )
          )}
        </div>

        {/* Bottom Controls */}
        <div className="flex items-center justify-center gap-4 w-full">
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={handleToggleMute}
            className={`rounded-full h-11 w-11 transition-all ${
              isMuted
                ? 'bg-destructive/15 text-destructive border-destructive/30 hover:bg-destructive/25'
                : 'bg-muted/70 text-foreground hover:bg-muted'
            }`}
            title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
          >
            {isMuted ? <MicOff size={18} /> : <Mic size={18} />}
          </Button>

          {status === 'speaking' && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleManualInterrupt}
              className="rounded-full px-4 h-11 text-xs border-amber-500/40 text-amber-500 hover:bg-amber-500/10"
              title="Interrupt HSBot"
            >
              Interrupt
            </Button>
          )}

          <Button
            type="button"
            variant="destructive"
            onClick={handleClose}
            className="rounded-full px-6 h-11 flex items-center gap-2 text-xs font-semibold shadow-md active:scale-95 transition-all"
          >
            <PhoneOff size={16} />
            End Conversation
          </Button>
        </div>
      </motion.div>
    </div>
  )
}
