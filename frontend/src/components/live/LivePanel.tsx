/**
 * HSBot Live Voice System - Live Conversation Panel
 * 
 * Production-grade floating modal for continuous, real-time voice conversations
 * powered exclusively by NVIDIA ASR, NVIDIA LLM, and NVIDIA TTS.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  X,
  Mic,
  MicOff,
  Square,
  RefreshCw,
  Cpu,
  Radio,
  Sliders,
  Send,
} from 'lucide-react'
import { LiveSessionManager } from '@/live/LiveSessionManager'
import { LiveState, LiveTranscriptItem, LiveAudioLevel } from '@/live/LiveTypes'
import { LiveStatus } from './LiveStatus'
import { LiveTranscript } from './LiveTranscript'
import { LiveErrorBoundary } from './LiveErrorBoundary'
import { cn } from '@/lib/utils'

interface LivePanelProps {
  isOpen: boolean
  conversationId?: string
  onClose: () => void
  onMessageSaved?: (userText: string, assistantText: string) => void
  onSaveToChat?: (userText: string, assistantText: string) => void
}

const LivePanelContent: React.FC<LivePanelProps> = ({
  isOpen,
  conversationId,
  onClose,
  onMessageSaved,
  onSaveToChat,
}) => {
  const saveCallback = onMessageSaved || onSaveToChat
  const [state, setState] = useState<LiveState>('IDLE')
  const [audioLevel, setAudioLevel] = useState<LiveAudioLevel>({ input: 0, output: 0 })
  const [transcripts, setTranscripts] = useState<LiveTranscriptItem[]>([])
  const [isMuted, setIsMuted] = useState(false)
  const [selectedVoice, setSelectedVoice] = useState('Chatterbox-Multilingual')
  const [showSettings, setShowSettings] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const sessionManagerRef = useRef<LiveSessionManager | null>(null)
  const accumulatedTurnsRef = useRef<{ user: string; assistant: string }[]>([])

  // Cleanup on unmount or close
  const cleanup = useCallback(() => {
    if (sessionManagerRef.current) {
      sessionManagerRef.current.stop()
      sessionManagerRef.current.destroy()
      sessionManagerRef.current = null
    }
    setState('IDLE')
    setAudioLevel({ input: 0, output: 0 })
  }, [])

  // Start or stop session when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      cleanup()
      return
    }

    setErrorMessage(null)
    setTranscripts([])
    accumulatedTurnsRef.current = []

    const manager = new LiveSessionManager({
      sessionId: conversationId || 'live_' + Date.now(),
      config: {
        voice: selectedVoice,
      },
      onStateChange: (newState) => {
        setState(newState)
        if (newState !== 'ERROR') {
          setErrorMessage(null)
        }
      },
      onTranscript: (item) => {
        setTranscripts((prev) => {
          // If update to in-progress assistant item
          if (!item.isFinal && item.role === 'assistant') {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant' && !last.isFinal) {
              return [...prev.slice(0, -1), item]
            }
            return [...prev, item]
          }

          // If final assistant response
          if (item.isFinal && item.role === 'assistant') {
            const withoutPartial = prev.filter((p) => p.isFinal)
            // Record completed exchange
            const lastUser = withoutPartial.filter((p) => p.role === 'user').pop()
            if (lastUser && saveCallback) {
              saveCallback(lastUser.text, item.text)
            }
            return [...withoutPartial, item]
          }

          return [...prev, item]
        })
      },
      onAudioLevel: (level) => {
        setAudioLevel(level)
      },
      onError: (err) => {
        setErrorMessage(err)
      },
    })

    sessionManagerRef.current = manager
    manager.start()

    const connectingTimeout = setTimeout(() => {
      setState((curr) => (curr === 'CONNECTING' ? 'LISTENING' : curr))
    }, 2200)

    return () => {
      clearTimeout(connectingTimeout)
      cleanup()
    }
  }, [isOpen, conversationId, selectedVoice, cleanup, saveCallback])

  const handleToggleMute = () => {
    if (sessionManagerRef.current) {
      const muted = sessionManagerRef.current.toggleMute()
      setIsMuted(muted)
    }
  }

  const handleInterrupt = () => {
    if (sessionManagerRef.current) {
      sessionManagerRef.current.interrupt()
    }
  }

  const handleRestart = () => {
    setErrorMessage(null)
    if (sessionManagerRef.current) {
      sessionManagerRef.current.start()
    }
  }

  const handleClose = () => {
    cleanup()
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className={cn(
          'relative w-full max-w-lg rounded-3xl bg-card border border-border/80 shadow-2xl overflow-hidden flex flex-col',
          'transition-all duration-300 transform scale-100 max-h-[85vh]'
        )}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border/60 bg-muted/20">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-500 border border-emerald-500/20">
              <Radio size={16} className="animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold tracking-tight text-foreground">HSBot Live Voice</h2>
                <span className="flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                  <Cpu size={10} />
                  NVIDIA NIM
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5">Parakeet ASR · Llama 3.2 · Chatterbox TTS</p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setShowSettings(!showSettings)}
              className={cn(
                'p-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-all',
                showSettings && 'bg-muted text-foreground'
              )}
              title="Voice Settings"
            >
              <Sliders size={16} />
            </button>
            <button
              type="button"
              onClick={handleClose}
              className="p-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-all"
              title="Close Live Voice"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Optional Settings Drawer */}
        {showSettings && (
          <div className="px-6 py-3 bg-muted/40 border-b border-border/40 text-xs flex items-center justify-between animate-in slide-in-from-top duration-150">
            <span className="font-medium text-foreground">NVIDIA TTS Voice</span>
            <select
              value={selectedVoice}
              onChange={(e) => setSelectedVoice(e.target.value)}
              className="px-2.5 py-1 rounded-lg bg-background border border-border text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="Chatterbox-Multilingual">Chatterbox Multilingual (Default)</option>
              <option value="English-US.Female-1">English US (Female 1)</option>
              <option value="English-US.Male-1">English US (Male 1)</option>
            </select>
          </div>
        )}

        {/* Error Alert if any */}
        {errorMessage && (
          <div className="mx-6 mt-4 p-3 rounded-2xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center justify-between">
            <span>{errorMessage}</span>
            <button
              type="button"
              onClick={handleRestart}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-destructive text-destructive-foreground font-medium hover:opacity-90"
            >
              <RefreshCw size={12} />
              Retry
            </button>
          </div>
        )}

        {/* Visualizer & Status Section */}
        <div className="py-6 flex flex-col items-center justify-center bg-gradient-to-b from-muted/10 to-transparent">
          <LiveStatus state={state} audioLevel={audioLevel} />
        </div>

        {/* Transcripts Area */}
        <div className="flex-1 overflow-hidden flex flex-col border-t border-border/40 bg-muted/10">
          <div className="px-4 py-1.5 text-[10px] font-medium tracking-wider text-muted-foreground uppercase">
            Live Conversation
          </div>
          <LiveTranscript items={transcripts} className="flex-1" />
        </div>

        {/* Action Controls Bar */}
        <div className="px-6 py-4 border-t border-border/60 bg-muted/20 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleToggleMute}
              className={cn(
                'flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium transition-all active:scale-95',
                isMuted
                  ? 'bg-destructive/10 text-destructive border border-destructive/20 hover:bg-destructive/20'
                  : 'bg-muted text-foreground hover:bg-muted/80 border border-border'
              )}
            >
              {isMuted ? <MicOff size={14} /> : <Mic size={14} />}
              <span>{isMuted ? 'Unmute' : 'Mute'}</span>
            </button>

            {state === 'CONNECTING' && (
              <button
                type="button"
                onClick={() => {
                  setState('LISTENING')
                }}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all active:scale-95"
                title="Start speaking immediately"
              >
                <Mic size={13} />
                <span>Start Speaking</span>
              </button>
            )}

            {state === 'LISTENING' && !isMuted && (
              <button
                type="button"
                onClick={() => sessionManagerRef.current?.commitTurn()}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition-all active:scale-95"
                title="Done speaking - send audio immediately"
              >
                <Send size={13} />
                <span>Done Speaking</span>
              </button>
            )}

            {state === 'SPEAKING' && (
              <button
                type="button"
                onClick={handleInterrupt}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium bg-amber-500/10 text-amber-500 border border-amber-500/20 hover:bg-amber-500/20 transition-all active:scale-95 animate-pulse"
                title="Interrupt AI speaking (Barge-in)"
              >
                <Square size={13} />
                <span>Interrupt</span>
              </button>
            )}
          </div>

          <button
            type="button"
            onClick={handleClose}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium bg-foreground text-background hover:opacity-90 transition-all active:scale-95"
          >
            End Call
          </button>
        </div>
      </div>
    </div>
  )
}

export const LivePanel: React.FC<LivePanelProps> = (props) => {
  return (
    <LiveErrorBoundary onReset={props.onClose}>
      <LivePanelContent {...props} />
    </LiveErrorBoundary>
  )
}
