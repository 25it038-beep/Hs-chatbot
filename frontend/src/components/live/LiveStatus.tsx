/**
 * HSBot Live Voice System - Status & Waveform Visualizer
 * 
 * Displays animated status badges and reactive audio waveform bars
 * driven by real audio energy from microphone (user) or speaker (NVIDIA AI).
 */

import React from 'react'
import { LiveState, LiveAudioLevel } from '@/live/LiveTypes'
import { Mic, Volume2, Sparkles, Loader2, AlertTriangle, Radio } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LiveStatusProps {
  state: LiveState
  audioLevel: LiveAudioLevel
  className?: string
}

export const LiveStatus: React.FC<LiveStatusProps> = ({ state, audioLevel, className }) => {
  // Determine dominant volume level based on current state
  const activeLevel = state === 'SPEAKING' ? audioLevel.output : audioLevel.input
  
  // Waveform bars count
  const barCount = 16

  const getStatusBadge = () => {
    switch (state) {
      case 'CONNECTING':
        return (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-500 border border-amber-500/20">
            <Loader2 size={13} className="animate-spin" />
            <span>Connecting to NVIDIA NIM...</span>
          </div>
        )
      case 'LISTENING':
        return (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
            <Mic size={13} className={audioLevel.input > 0.04 ? 'animate-bounce text-emerald-400' : 'animate-pulse'} />
            <span>{audioLevel.input > 0.04 ? 'Hearing your voice...' : 'Listening...'}</span>
          </div>
        )
      case 'PROCESSING':
        return (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Sparkles size={13} className="animate-spin" />
            <span>Thinking (NVIDIA LLM)...</span>
          </div>
        )
      case 'SPEAKING':
        return (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <Volume2 size={13} className="animate-pulse" />
            <span>NVIDIA Voice Speaking...</span>
          </div>
        )
      case 'INTERRUPTED':
        return (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <Radio size={13} />
            <span>Interrupted</span>
          </div>
        )
      case 'ERROR':
        return (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-destructive/10 text-destructive border border-destructive/20">
            <AlertTriangle size={13} />
            <span>Connection Error</span>
          </div>
        )
      case 'IDLE':
      default:
        return (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">
            <Radio size={13} />
            <span>Idle</span>
          </div>
        )
    }
  }

  return (
    <div className={cn('flex flex-col items-center gap-4', className)}>
      {getStatusBadge()}

      {/* Reactive Audio Waveform Visualizer */}
      <div className="flex items-center justify-center gap-1.5 h-16 w-full max-w-xs px-4">
        {Array.from({ length: barCount }).map((_, idx) => {
          // Dynamic scaling with wave curvature
          const mid = barCount / 2
          const distFromCenter = Math.abs(idx - mid) / mid
          const curve = Math.cos(distFromCenter * (Math.PI / 2))

          const isListening = state === 'LISTENING'
          const isSpeaking = state === 'SPEAKING'
          const isActive = isListening || isSpeaking

          let height = 6
          if (isActive) {
            const jitter = Math.sin(idx * 1.5 + Date.now() / 100) * 0.15
            const energy = Math.max(0.1, activeLevel + jitter)
            height = Math.max(6, Math.min(54, curve * energy * 64))
          }

          return (
            <div
              key={idx}
              className={cn(
                'w-1.5 rounded-full transition-all duration-75 ease-out',
                isSpeaking
                  ? 'bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.4)]'
                  : isListening
                  ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]'
                  : state === 'PROCESSING'
                  ? 'bg-indigo-400 animate-pulse'
                  : 'bg-muted-foreground/20'
              )}
              style={{ height: `${height}px` }}
            />
          )
        })}
      </div>
    </div>
  )
}
