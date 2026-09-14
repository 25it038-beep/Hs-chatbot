import React, { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Mic,
  MicOff,
  PhoneOff,
  Send,
  Languages,
  Sparkles,
  AlertCircle,
  Radio,
  RefreshCw,
  Wifi,
  WifiOff,
  Volume2,
  MessageSquare,
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

/** Returns a friendly label + colour class for each status */
function getStatusMeta(status: RealtimeStatus, isMuted: boolean) {
  if (status === 'speaking') {
    return { label: 'HSBot is speaking', sublabel: 'Speak to interrupt', color: 'text-primary', dot: 'bg-primary', pulse: true }
  }
  if (status === 'processing') {
    return { label: 'Thinking…', sublabel: 'Generating a reply', color: 'text-amber-400', dot: 'bg-amber-400', pulse: true }
  }
  if (status === 'connecting') {
    return { label: 'Connecting…', sublabel: 'Finding voice server', color: 'text-muted-foreground', dot: 'bg-muted-foreground', pulse: false }
  }
  if (status === 'interrupted') {
    return { label: 'Interrupted', sublabel: 'Listening to you now', color: 'text-rose-400', dot: 'bg-rose-400', pulse: false }
  }
  if (status === 'error') {
    return { label: 'Error', sublabel: 'Check connection', color: 'text-destructive', dot: 'bg-destructive', pulse: false }
  }
  if (isMuted) {
    return { label: 'Microphone muted', sublabel: 'Type below to chat', color: 'text-muted-foreground', dot: 'bg-muted-foreground', pulse: false }
  }
  // default: listening
  return { label: 'Listening…', sublabel: 'Speak now', color: 'text-emerald-400', dot: 'bg-emerald-400', pulse: true }
}

export function LiveConversationModal({
  isOpen,
  conversationId,
  onClose,
  onMessageSaved,
}: LiveConversationModalProps) {
  const [status, setStatus] = useState<RealtimeStatus>('connecting')
  const [isConnected, setIsConnected] = useState<boolean>(false)
  const [endpointName, setEndpointName] = useState<string>('')
  const [audioLevel, setAudioLevel] = useState<number>(0)
  const [userTranscript, setUserTranscript] = useState<string>('')
  const [aiResponse, setAiResponse] = useState<string>('')
  const [isMuted, setIsMuted] = useState<boolean>(false)
  const [language, setLanguage] = useState<string>('en-US')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [textInput, setTextInput] = useState<string>('')

  const clientRef = useRef<RealtimeVoiceClient | null>(null)
  const lastUserTextRef = useRef<string>('')
  const currentAiAccumulatorRef = useRef<string>('')
  const inputRef = useRef<HTMLInputElement | null>(null)

  // Map RealtimeStatus to VoiceOrb's VOICE_STATES
  const getOrbState = (st: RealtimeStatus): string => {
    switch (st) {
      case 'connecting':  return VOICE_STATES.PROCESSING
      case 'listening':   return VOICE_STATES.LISTENING
      case 'processing':  return VOICE_STATES.PROCESSING
      case 'speaking':    return VOICE_STATES.AI_SPEAKING
      case 'interrupted': return VOICE_STATES.LISTENING
      case 'error':       return VOICE_STATES.ERROR
      default:            return VOICE_STATES.IDLE
    }
  }

  const startSession = () => {
    if (clientRef.current) {
      clientRef.current.stop()
      clientRef.current = null
    }

    setErrorMessage(null)
    setUserTranscript('')
    setAiResponse('')
    setIsConnected(false)
    lastUserTextRef.current = ''
    currentAiAccumulatorRef.current = ''

    const client = new RealtimeVoiceClient(
      conversationId,
      {
        onStatusChange: (newStatus) => setStatus(newStatus),
        onConnectionChange: (connected, endpoint) => {
          setIsConnected(connected)
          if (endpoint) {
            const clean = endpoint.includes('render')
              ? 'Render Cloud'
              : endpoint.includes('localhost')
              ? 'Local Server'
              : endpoint.replace(/^https?:\/\//, '')
            setEndpointName(clean)
          }
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
        onAudioLevel: (level) => setAudioLevel(level),
        onError: (err) => setErrorMessage(err),
      },
      { language }
    )

    clientRef.current = client
    client.start()
  }

  useEffect(() => {
    if (!isOpen) {
      clientRef.current?.stop()
      clientRef.current = null
      return
    }
    startSession()
    return () => {
      clientRef.current?.stop()
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

  const handleManualInterrupt = () => clientRef.current?.interrupt()

  const handleSendText = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const trimmed = textInput.trim()
    if (!trimmed) return
    clientRef.current?.sendUtterance(trimmed)
    setTextInput('')
  }

  const handleClose = () => {
    clientRef.current?.stop()
    clientRef.current = null
    onClose()
  }

  if (!isOpen) return null

  const { label: statusLabel, sublabel, color: statusColor, dot: dotColor, pulse } = getStatusMeta(status, isMuted)
  const isAiSpeaking = status === 'speaking'
  const isListening = status === 'listening' && !isMuted

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/80 backdrop-blur-lg p-0 sm:p-4">
      <motion.div
        initial={{ opacity: 0, y: 60, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 60, scale: 0.96 }}
        transition={{ type: 'spring', stiffness: 320, damping: 28 }}
        className="relative flex flex-col w-full max-w-lg bg-card border border-border/70 rounded-t-3xl sm:rounded-3xl shadow-2xl overflow-hidden"
        style={{ maxHeight: '95dvh' }}
      >
        {/* ── Top bar: title + connection status + language picker ── */}
        <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-border/40">
          <div className="flex items-center gap-2.5">
            {/* Live indicator dot */}
            <span className="relative flex h-2.5 w-2.5 shrink-0">
              {isConnected ? (
                <>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
                </>
              ) : (
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-400 animate-pulse" />
              )}
            </span>

            <div>
              <div className="flex items-center gap-1.5 font-bold text-sm tracking-wide text-foreground">
                <Radio size={13} className="text-primary" />
                HSBot LIVE
              </div>
              <div className="flex items-center gap-1 text-[10px] text-muted-foreground mt-0.5">
                {isConnected ? (
                  <><Wifi size={9} className="text-emerald-500" /> {endpointName || 'Cloud'}</>
                ) : (
                  <><WifiOff size={9} className="text-amber-400" /> Connecting…</>
                )}
              </div>
            </div>
          </div>

          {/* Language selector */}
          <div className="flex items-center gap-1 bg-muted/50 border border-border/50 rounded-full px-2.5 py-1">
            <Languages size={11} className="text-muted-foreground mr-0.5" />
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                onClick={() => handleLanguageChange(lang.code)}
                className={`text-[11px] font-medium px-2 py-0.5 rounded-full transition-all ${
                  language === lang.code
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {lang.label.split(' ')[0]}
              </button>
            ))}
          </div>
        </div>

        {/* ── Main content ── */}
        <div className="flex flex-col items-center px-5 py-5 gap-5 flex-1 overflow-y-auto">

          {/* Status badge */}
          <div className="flex flex-col items-center gap-1">
            <div className={`flex items-center gap-2 font-semibold text-sm ${statusColor}`}>
              <span className={`h-2 w-2 rounded-full shrink-0 ${dotColor} ${pulse ? 'animate-pulse' : ''}`} />
              {statusLabel}
            </div>
            <p className="text-[11px] text-muted-foreground">{sublabel}</p>
          </div>

          {/* Voice Orb */}
          <VoiceOrb
            status={getOrbState(status)}
            audioLevel={audioLevel}
            isHandsFree={true}
            wakeWordDetected={false}
            wsConnected={isConnected}
            onToggle={() => {}}
            onInterrupt={handleManualInterrupt}
            className="w-44 h-44 sm:w-48 sm:h-48 shrink-0"
          />

          {/* Conversation feed: two clearly-labelled zones */}
          <div className="w-full flex flex-col gap-2.5">

            {/* USER zone — only visible when we have a transcript */}
            <AnimatePresence>
              {userTranscript && (
                <motion.div
                  key="user-zone"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 6 }}
                  className={`rounded-2xl border px-4 py-3 ${
                    isListening
                      ? 'border-emerald-500/40 bg-emerald-500/5'
                      : 'border-border/50 bg-muted/30'
                  }`}
                >
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Mic size={11} className={isListening ? 'text-emerald-400' : 'text-muted-foreground'} />
                    <span className={`text-[11px] font-semibold uppercase tracking-widest ${isListening ? 'text-emerald-400' : 'text-muted-foreground'}`}>
                      You
                    </span>
                  </div>
                  <p className="text-sm text-foreground/90 leading-relaxed line-clamp-3">{userTranscript}</p>
                </motion.div>
              )}
            </AnimatePresence>

            {/* HSBOT zone — only visible when AI is generating / has replied */}
            <AnimatePresence>
              {aiResponse && (
                <motion.div
                  key="ai-zone"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 6 }}
                  className={`rounded-2xl border px-4 py-3 ${
                    isAiSpeaking
                      ? 'border-primary/40 bg-primary/5'
                      : 'border-border/50 bg-muted/30'
                  }`}
                >
                  <div className="flex items-center gap-1.5 mb-1.5">
                    {isAiSpeaking ? (
                      <Volume2 size={11} className="text-primary animate-pulse" />
                    ) : (
                      <MessageSquare size={11} className="text-muted-foreground" />
                    )}
                    <span className={`text-[11px] font-semibold uppercase tracking-widest ${isAiSpeaking ? 'text-primary' : 'text-muted-foreground'}`}>
                      HSBot
                    </span>
                    {isAiSpeaking && (
                      <span className="ml-auto flex gap-0.5 items-end h-3">
                        {[0, 0.15, 0.3].map((delay) => (
                          <span
                            key={delay}
                            className="w-0.5 bg-primary rounded-full animate-bounce"
                            style={{ height: '10px', animationDelay: `${delay}s` }}
                          />
                        ))}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-foreground/90 leading-relaxed line-clamp-4">{aiResponse}</p>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Empty prompt */}
            {!userTranscript && !aiResponse && (
              <div className="text-center py-2">
                <p className="text-xs text-muted-foreground/60 italic">Speak naturally or type below to start</p>
              </div>
            )}
          </div>

          {/* Error banner */}
          {errorMessage && (
            <div className="w-full text-xs text-destructive flex items-start justify-between gap-2 bg-destructive/10 border border-destructive/20 px-3 py-2.5 rounded-xl">
              <span className="flex items-start gap-1.5">
                <AlertCircle size={13} className="shrink-0 mt-0.5" />
                {errorMessage}
              </span>
              <button
                type="button"
                onClick={startSession}
                className="text-[11px] underline font-medium hover:opacity-80 shrink-0 ml-1 whitespace-nowrap"
              >
                Retry
              </button>
            </div>
          )}
        </div>

        {/* ── Bottom panel: text input + controls ── */}
        <div className="px-5 pb-5 pt-3 border-t border-border/40 flex flex-col gap-3 bg-card/80">
          {/* Type-to-speak bar */}
          <form onSubmit={handleSendText} className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Type a message…"
              className="flex-1 bg-muted/60 border border-border/60 rounded-full px-4 py-2 text-xs text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <Button
              type="submit"
              size="sm"
              disabled={!textInput.trim()}
              className="rounded-full h-8 w-8 p-0 shadow-sm"
              title="Send message"
            >
              <Send size={13} />
            </Button>
          </form>

          {/* Action row: mute | interrupt | end */}
          <div className="flex items-center justify-between gap-3">
            {/* Mute */}
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={handleToggleMute}
              title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
              className={`rounded-full h-11 w-11 transition-all ${
                isMuted
                  ? 'bg-destructive/15 text-destructive border-destructive/30 hover:bg-destructive/25'
                  : 'bg-muted/60 hover:bg-muted'
              }`}
            >
              {isMuted ? <MicOff size={17} /> : <Mic size={17} />}
            </Button>

            {/* End session — centred, prominent */}
            <Button
              type="button"
              variant="destructive"
              onClick={handleClose}
              className="flex-1 rounded-full h-11 flex items-center justify-center gap-2 text-sm font-semibold shadow-md active:scale-95 transition-all"
            >
              <PhoneOff size={16} />
              End Session
            </Button>

            {/* Interrupt (only visible while AI is speaking) */}
            <AnimatePresence>
              {isAiSpeaking ? (
                <motion.div
                  key="interrupt"
                  initial={{ opacity: 0, scale: 0.85 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.85 }}
                >
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={handleManualInterrupt}
                    title="Stop AI speech"
                    className="rounded-full h-11 w-11 border-primary/40 text-primary hover:bg-primary/10"
                  >
                    <Sparkles size={17} />
                  </Button>
                </motion.div>
              ) : (
                // spacer so End Session stays centred
                <div className="h-11 w-11" />
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
