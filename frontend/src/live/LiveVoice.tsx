/**
 * HSBot Live Voice Component.
 * Self-contained real-time voice interface featuring:
 * - NVIDIA Nemotron VoiceChat (Primary) with honest unavailability prompt
 * - Cascaded NVIDIA Live (Riva ASR + LLM + Riva FastPitch TTS) fallback
 * - 14-metric real-time diagnostics telemetry
 * - Zero-simulation contract
 * - Isolated React Error Boundary
 */

import React, { Component, ErrorInfo, ReactNode, useEffect, useRef, useState } from 'react'
import {
  Mic,
  MicOff,
  Radio,
  X,
  RefreshCw,
  Zap,
  Activity,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  ArrowRight,
  Square,
  Send,
  Volume2,
  VolumeX,
  PhoneOff,
} from 'lucide-react'

import { LiveVoiceSession } from './LiveVoiceSession'
import { LiveDiagnosticsData, LiveEngine, LiveState, LiveTurnTranscript } from './LiveVoiceTypes'
import { VoiceSphere3D } from './VoiceSphere3D'

// ==========================================
// 1. ISOLATED REACT ERROR BOUNDARY
// ==========================================

interface ErrorBoundaryProps {
  children: ReactNode
  onReset?: () => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class LiveErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[LiveErrorBoundary] Caught live voice error:', error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
    if (this.props.onReset) {
      this.props.onReset()
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center p-8 bg-card rounded-2xl border border-destructive/30 text-center space-y-4 max-w-md mx-auto my-auto shadow-2xl">
          <div className="p-3 bg-destructive/10 rounded-full text-destructive">
            <AlertTriangle size={32} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">Live Voice Subsystem Error</h3>
            <p className="text-sm text-muted-foreground mt-1">
              {this.state.error?.message || 'An unexpected error occurred in the live voice subsystem.'}
            </p>
          </div>
          <button
            onClick={this.handleReset}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-all"
          >
            <RefreshCw size={14} />
            <span>Reset Live Voice</span>
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

// ==========================================
// 2. MAIN LIVE VOICE COMPONENT
// ==========================================

export interface LiveVoiceProps {
  isOpen: boolean
  onClose: () => void
  onSaveToChat?: (userText: string, assistantText: string) => void
  initialEngine?: LiveEngine
}

export function LiveVoiceInner({
  isOpen,
  onClose,
  onSaveToChat,
  initialEngine = 'cascaded',
}: LiveVoiceProps) {
  const [session, setSession] = useState<LiveVoiceSession | null>(null)
  const [liveState, setLiveState] = useState<LiveState>('IDLE')
  const [engine, setEngine] = useState<LiveEngine>(initialEngine)
  const [transcripts, setTranscripts] = useState<LiveTurnTranscript[]>([])
  const [diagnostics, setDiagnostics] = useState<LiveDiagnosticsData | null>(null)
  const [showDiagnostics, setShowDiagnostics] = useState(false)
  const [showTranscripts, setShowTranscripts] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [manualInput, setManualInput] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [errorCode, setErrorCode] = useState<string | null>(null)
  const [errorDetails, setErrorDetails] = useState<any>(null)
  const [selectedLanguage, setSelectedLanguage] = useState<'en' | 'ta'>('en')
  const [isTamilAvailable, setIsTamilAvailable] = useState<boolean>(false)

  const transcriptEndRef = useRef<HTMLDivElement>(null)

  // Query live language capabilities
  useEffect(() => {
    if (!isOpen) return
    const envUrl = (import.meta.env.VITE_API_URL as string)?.trim() || ''
    const base = envUrl.replace(/\/+$/, '')
    fetch(`${base}/api/live/languages`)
      .then((res) => res.json())
      .then((data) => {
        const ta = data?.languages?.find((l: any) => l.code === 'ta')
        setIsTamilAvailable(Boolean(ta?.supported))
      })
      .catch(() => {
        setIsTamilAvailable(false)
      })
  }, [isOpen])

  // Initialize Session with NVIDIA Riva
  useEffect(() => {
    if (!isOpen) {
      if (session) {
        session.stop()
        setSession(null)
      }
      return
    }

    const sess = new LiveVoiceSession()
    setSession(sess)

    sess.onStateChange = (st) => setLiveState(st)
    sess.onTranscriptsChange = (ts) => setTranscripts([...ts])
    sess.onError = (code, msg, details) => {
      setErrorCode(code)
      setErrorMessage(msg)
      setErrorDetails(details)
    }

    const unsubscribeDiag = sess.diagnostics.subscribe((data) => {
      setDiagnostics(data)
      setEngine(data.engine)
    })

    // Start with NVIDIA Riva cascaded engine
    sess.start({ engine: initialEngine })

    return () => {
      unsubscribeDiag()
      sess.stop()
    }
  }, [isOpen])

  // Auto-scroll transcripts
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcripts])

  if (!isOpen) return null

  const handleRetry = () => {
    setErrorMessage(null)
    setErrorCode(null)
    setErrorDetails(null)
    if (session) {
      session.retry()
    }
  }

  const handleToggleMute = () => {
    if (!session) return
    if (isMuted) {
      session.audio.startMicrophone().then(() => setIsMuted(false)).catch(() => {})
    } else {
      session.audio.stopMicrophone()
      setIsMuted(true)
    }
  }

  const handleSendManual = (e: React.FormEvent) => {
    e.preventDefault()
    if (!manualInput.trim() || !session) return
    session.sendText(manualInput)
    setManualInput('')
  }

  const handleBargeIn = () => {
    if (session) {
      session.interrupt()
    }
  }

  const handleSaveAndClose = () => {
    if (onSaveToChat && transcripts.length > 0) {
      const userParts = transcripts.filter((t) => t.role === 'user').map((t) => t.text).join('\n')
      const assistantParts = transcripts.filter((t) => t.role === 'assistant').map((t) => t.text).join('\n')
      onSaveToChat(userParts || 'Live voice conversation', assistantParts || '(No assistant speech)')
    }
    onClose()
  }

  // Determine user speech from real microphone dB
  const isMicSpeaking = (diagnostics?.micInputLevel || -100) > -44

  // Compute readable status text per specification
  const getStatusDisplay = () => {
    if (liveState === 'SPEAKING') return 'AI Speaking'
    if (liveState === 'PROCESSING') return 'Processing...'
    if (liveState === 'ERROR') return 'Engine Error'
    if (liveState === 'CONNECTING') return 'Listening...'
    if (liveState === 'LISTENING') {
      return isMicSpeaking ? 'User Speaking' : 'Listening...'
    }
    return 'Listening...'
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="relative flex flex-col w-full max-w-3xl h-[88vh] max-h-[820px] bg-card/95 border border-border/80 rounded-2xl shadow-2xl overflow-hidden backdrop-saturate-150">
        
        {/* HEADER */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border/60 bg-muted/30">
          <div className="flex items-center gap-3">
            <div className="relative flex items-center justify-center w-8 h-8 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
              <Radio size={16} className={liveState === 'SPEAKING' || liveState === 'LISTENING' ? 'animate-pulse' : ''} />
              <span className={`absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full ${
                liveState === 'ERROR' ? 'bg-destructive' :
                liveState === 'SPEAKING' ? 'bg-emerald-400 animate-ping' :
                liveState === 'LISTENING' ? 'bg-emerald-500' : 'bg-muted-foreground'
              }`} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-foreground tracking-tight">HSBot Live Voice</h2>
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400 text-[10px] font-bold uppercase tracking-wider shadow-xs">
                  <Zap size={10} className="text-blue-500 animate-pulse" />
                  <span>NVIDIA Riva Live</span>
                  <span className="text-[9px] opacity-75 font-normal lowercase">(female)</span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                <span>Status:</span>
                <span className="font-medium text-foreground">
                  {liveState === 'CONNECTING' && 'Connecting to NVIDIA...'}
                  {liveState === 'CONNECTED' && 'Connected'}
                  {liveState === 'LISTENING' && 'Listening (Say something)...'}
                  {liveState === 'PROCESSING' && 'Thinking (NVIDIA NIM)...'}
                  {liveState === 'SPEAKING' && 'Speaking (Streaming Audio)...'}
                  {liveState === 'INTERRUPTED' && 'Interrupted'}
                  {liveState === 'ERROR' && 'Engine Error'}
                  {liveState === 'IDLE' && 'Ready'}
                </span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Language Selector (English Default / Tamil Opt-In) */}
            <div className="flex items-center gap-1 bg-muted/60 p-1 rounded-lg border border-border/60 text-xs">
              <button
                type="button"
                onClick={() => {
                  setSelectedLanguage('en')
                  setErrorCode(null)
                  setErrorMessage(null)
                }}
                className={`px-2.5 py-1 rounded-md font-medium text-[11px] transition-all ${
                  selectedLanguage === 'en'
                    ? 'bg-primary text-primary-foreground shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
                title="English (NVIDIA Parakeet + Chatterbox)"
              >
                English
              </button>
              <button
                type="button"
                disabled={!isTamilAvailable}
                onClick={() => {
                  if (!isTamilAvailable) {
                    setErrorCode('TAMIL_VOICE_UNAVAILABLE')
                    setErrorMessage('Tamil voice is currently unavailable: NVIDIA hosted Chatterbox does not provide a verified ta-IN voice model.')
                  } else {
                    setSelectedLanguage('ta')
                  }
                }}
                className={`px-2.5 py-1 rounded-md font-medium text-[11px] transition-all flex items-center gap-1.5 ${
                  selectedLanguage === 'ta'
                    ? 'bg-primary text-primary-foreground shadow-xs'
                    : isTamilAvailable
                    ? 'text-muted-foreground hover:text-foreground'
                    : 'text-muted-foreground/50 cursor-not-allowed opacity-60'
                }`}
                title={isTamilAvailable ? 'Tamil' : 'Tamil (Unavailable on NVIDIA hosted models)'}
              >
                <span>Tamil</span>
                {!isTamilAvailable && (
                  <span className="text-[8px] uppercase tracking-wider px-1 py-0.5 rounded bg-muted-foreground/20 text-muted-foreground font-semibold">
                    Unavailable
                  </span>
                )}
              </button>
            </div>

            <button
              onClick={() => setShowDiagnostics(!showDiagnostics)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                showDiagnostics
                  ? 'bg-primary/10 border-primary/30 text-primary'
                  : 'bg-muted/60 border-border text-muted-foreground hover:text-foreground'
              }`}
              title="Toggle 14-Metric Telemetry"
            >
              <Activity size={13} />
              <span>Diagnostics</span>
              {showDiagnostics ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>

            <button
              onClick={handleSaveAndClose}
              className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
              title="Close Live Voice"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* ERROR NOTIFICATION BANNER */}
        {errorCode && (
          <div className="p-3 mx-6 mt-3 rounded-xl border border-destructive/40 bg-destructive/10 text-destructive animate-in slide-in-from-top-2 duration-200">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <AlertTriangle size={16} />
                <span className="text-xs font-medium">{errorMessage || errorCode}</span>
              </div>
              <button
                type="button"
                onClick={handleRetry}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-destructive text-destructive-foreground text-xs font-medium hover:bg-destructive/90"
              >
                <RefreshCw size={11} />
                <span>Retry</span>
              </button>
            </div>
          </div>
        )}

        {/* 14-METRIC DIAGNOSTICS DRAWER */}
        {showDiagnostics && diagnostics && (
          <div className="px-6 py-3 border-b border-border/40 bg-muted/40 text-xs overflow-x-auto">
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">1. Engine</span>
                <p className="font-medium truncate text-foreground">{diagnostics.engine}</p>
              </div>
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">2. State</span>
                <p className="font-medium text-foreground">{diagnostics.connectionState}</p>
              </div>
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">3. WS Latency</span>
                <p className="font-medium text-foreground">{diagnostics.wsLatencyMs}ms</p>
              </div>
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">4. Mic Active</span>
                <p className="font-medium text-foreground">{diagnostics.micActive ? 'Yes' : 'No'}</p>
              </div>
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">5. Sample Rate</span>
                <p className="font-medium text-foreground">{diagnostics.micSampleRate}Hz</p>
              </div>
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">6. Mic Level</span>
                <p className="font-medium text-foreground">{diagnostics.micInputLevel} dB</p>
              </div>
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">7. Audio Output</span>
                <p className="font-medium text-foreground">{diagnostics.audioOutputActive ? 'Playing' : 'Idle'}</p>
              </div>
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">8. Audio Queue</span>
                <p className="font-medium text-foreground">{diagnostics.audioBufferQueueLength} chunks</p>
              </div>
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">9. ASR Latency</span>
                <p className="font-medium text-foreground">{diagnostics.asrLatencyMs > 0 ? `${diagnostics.asrLatencyMs}ms` : '—'}</p>
              </div>
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">10. TTFT (LLM)</span>
                <p className="font-medium text-foreground">{diagnostics.llmFirstTokenLatencyMs > 0 ? `${diagnostics.llmFirstTokenLatencyMs}ms` : '—'}</p>
              </div>
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">11. TTS 1st Audio</span>
                <p className="font-medium text-foreground">{diagnostics.ttsFirstAudioLatencyMs > 0 ? `${diagnostics.ttsFirstAudioLatencyMs}ms` : '—'}</p>
              </div>
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">12. Total Latency</span>
                <p className="font-medium text-foreground">{diagnostics.totalTurnLatencyMs > 0 ? `${diagnostics.totalTurnLatencyMs}ms` : '—'}</p>
              </div>
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">13. Packets</span>
                <p className="font-medium text-foreground">{diagnostics.packetCount}</p>
              </div>
              <div className="p-2 rounded-lg bg-card/60 border border-border/50">
                <span className="text-[10px] text-muted-foreground uppercase font-bold">14. Last Error</span>
                <p className="font-medium truncate text-destructive">{diagnostics.lastErrorCode || 'None'}</p>
              </div>
            </div>
          </div>
        )}

        {/* CONVERSATION TRANSCRIPT & VISUALIZER */}
        <div className="flex-1 flex flex-col items-center justify-between p-6 overflow-hidden relative">
          
          {/* Subtle dark cinematic radial lighting */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/5 via-background/40 to-background pointer-events-none" />

          {/* Transcript overlay if expanded */}
          {showTranscripts && (
            <div className="absolute inset-x-6 top-4 bottom-24 z-20 flex flex-col rounded-2xl bg-card/95 border border-border/80 shadow-2xl p-4 backdrop-blur-xl animate-in fade-in zoom-in-95 duration-200">
              <div className="flex items-center justify-between pb-3 border-b border-border/60 mb-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Live Conversation History ({transcripts.length})
                </span>
                <button
                  onClick={() => setShowTranscripts(false)}
                  className="p-1 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground"
                >
                  <X size={14} />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                {transcripts.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-8">No speech recorded yet.</p>
                ) : (
                  transcripts.map((t) => (
                    <div
                      key={t.id}
                      className={`flex flex-col ${t.role === 'user' ? 'items-end' : 'items-start'}`}
                    >
                      <span className="text-[10px] text-muted-foreground mb-1 px-1">
                        {t.role === 'user' ? 'You' : 'HSBot'}
                      </span>
                      <div
                        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm shadow-xs ${
                          t.role === 'user'
                            ? 'bg-primary text-primary-foreground rounded-br-none'
                            : 'bg-muted/80 border border-border/60 text-foreground rounded-bl-none'
                        }`}
                      >
                        <p className="whitespace-pre-wrap leading-relaxed">{t.text}</p>
                      </div>
                    </div>
                  ))
                )}
                <div ref={transcriptEndRef} />
              </div>
            </div>
          )}

          {/* TOP ORB SECTION */}
          <div className="w-full flex-1 flex flex-col items-center justify-center relative z-10 my-auto">
            {/* 3D FULL-COLOR LIVING AI SPHERE */}
            <VoiceSphere3D
              state={liveState}
              micAnalyser={session ? session.audio.getMicAnalyser() : null}
              outputAnalyser={session ? session.audio.getOutputAnalyser() : null}
              size={330}
              className="my-2 drop-shadow-2xl"
            />

            {/* STATUS & SUBTITLE PER SPEC */}
            <div className="flex flex-col items-center justify-center mt-3 text-center space-y-1.5">
              <h3 className="text-xl font-medium tracking-tight text-foreground flex items-center gap-2">
                <span>{getStatusDisplay()}</span>
              </h3>
              <p className="text-xs text-muted-foreground/80 font-normal">
                {liveState === 'SPEAKING'
                  ? 'HSBot is speaking with NVIDIA FastPitch'
                  : liveState === 'PROCESSING'
                  ? 'Synthesizing response...'
                  : isMuted
                  ? 'Microphone is muted'
                  : 'Speak naturally into your mic'}
              </p>

              {/* Interrupt (Barge-in) when AI is speaking */}
              {liveState === 'SPEAKING' && (
                <button
                  onClick={handleBargeIn}
                  className="mt-2 flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-destructive/15 text-destructive border border-destructive/30 text-xs font-medium hover:bg-destructive/25 transition-all shadow-xs animate-in fade-in"
                >
                  <Square size={12} />
                  <span>Interrupt (Barge-in)</span>
                </button>
              )}
            </div>
          </div>

          {/* LATEST TRANSCRIPT SNIPPET PREVIEW (if not expanded) */}
          {!showTranscripts && transcripts.length > 0 && (
            <div
              onClick={() => setShowTranscripts(true)}
              className="w-full max-w-md cursor-pointer px-4 py-2 rounded-xl bg-card/60 hover:bg-card/90 border border-border/50 text-xs text-muted-foreground hover:text-foreground text-center truncate transition-all duration-200 mb-2 shadow-xs"
              title="Click to view full conversation history"
            >
              <span className="font-semibold text-foreground mr-1.5">
                {transcripts[transcripts.length - 1].role === 'user' ? 'You:' : 'HSBot:'}
              </span>
              <span>{transcripts[transcripts.length - 1].text}</span>
            </div>
          )}

        </div>

        {/* BOTTOM CONTROLS (Mute, End Call, Transcripts, and Input) */}
        <div className="p-4 border-t border-border/60 bg-muted/30 relative z-20 flex flex-col gap-3">
          {/* Main Action Buttons: Mute & End Call */}
          <div className="flex items-center justify-center gap-4">
            <button
              type="button"
              onClick={handleToggleMute}
              className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-medium text-sm transition-all shadow-xs cursor-pointer ${
                isMuted
                  ? 'bg-amber-500/15 border border-amber-500/30 text-amber-600 dark:text-amber-400 hover:bg-amber-500/25'
                  : 'bg-card border border-border hover:bg-muted text-foreground'
              }`}
            >
              {isMuted ? <MicOff size={18} /> : <Mic size={18} />}
              <span>{isMuted ? 'Unmute' : 'Mute'}</span>
            </button>

            <button
              type="button"
              onClick={handleSaveAndClose}
              className="flex items-center gap-2 px-7 py-2.5 rounded-xl font-medium text-sm bg-destructive hover:bg-destructive/90 text-destructive-foreground transition-all shadow-md cursor-pointer"
            >
              <PhoneOff size={18} />
              <span>End Call</span>
            </button>

            <button
              type="button"
              onClick={() => setShowTranscripts(!showTranscripts)}
              className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl border border-border bg-card hover:bg-muted text-xs font-medium text-muted-foreground hover:text-foreground transition-all"
            >
              <span>History ({transcripts.length})</span>
            </button>
          </div>

          {/* Optional manual text input */}
          <form onSubmit={handleSendManual} className="flex items-center gap-2 pt-1 border-t border-border/30">
            <input
              type="text"
              value={manualInput}
              onChange={(e) => setManualInput(e.target.value)}
              placeholder="Or type a live message directly..."
              className="flex-1 px-3.5 py-2 rounded-lg bg-background/80 border border-border text-xs text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary/40 transition-all"
            />
            <button
              type="submit"
              disabled={!manualInput.trim()}
              className="p-2 rounded-lg bg-primary text-primary-foreground disabled:opacity-40 hover:bg-primary/90 transition-all shadow-xs"
            >
              <Send size={14} />
            </button>
          </form>
        </div>

      </div>
    </div>
  )
}

/**
 * Top-level exported LiveVoice component wrapped in LiveErrorBoundary.
 */
export function LiveVoice(props: LiveVoiceProps) {
  return (
    <LiveErrorBoundary>
      <LiveVoiceInner {...props} />
    </LiveErrorBoundary>
  )
}

export default LiveVoice
