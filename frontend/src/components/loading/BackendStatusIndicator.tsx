import React from 'react'
import {
  RefreshCw,
  Server,
  WifiOff,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Zap,
} from 'lucide-react'
import type { ConnectionInfo, ConnectionState } from '@/types/connection'
import { Button } from '@/components/ui/button'

interface BackendStatusIndicatorProps {
  connection: ConnectionInfo & { retryNow: () => Promise<void> }
}

const STATE_CONFIG: Record<
  ConnectionState,
  {
    label: string
    colorClass: string
    badgeClass: string
    ringColor: string
    description: string
    pulse: boolean
  }
> = {
  INITIALIZING: {
    label: 'Initializing Engine',
    colorClass: 'text-zinc-400',
    badgeClass: 'bg-zinc-500/10 text-zinc-300 border-zinc-700/50',
    ringColor: 'border-zinc-500/30',
    description: 'Setting up client connection protocols and environment checks...',
    pulse: true,
  },
  CONNECTING: {
    label: 'Connecting to Cloud Backend',
    colorClass: 'text-violet-400',
    badgeClass: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
    ringColor: 'border-violet-500/50 shadow-[0_0_20px_rgba(139,92,246,0.3)]',
    description: 'Reaching backend services across secure API channels...',
    pulse: true,
  },
  WAKING_UP: {
    label: 'Waking Up Backend Instance',
    colorClass: 'text-amber-400',
    badgeClass: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    ringColor: 'border-amber-500/50 shadow-[0_0_25px_rgba(245,158,11,0.35)]',
    description:
      'Cloud instance is spinning up from idle state. Cold boot typically takes 20–45 seconds. Checking automatically...',
    pulse: true,
  },
  VERIFYING_READINESS: {
    label: 'Verifying Services & AI Readiness',
    colorClass: 'text-cyan-400',
    badgeClass: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    ringColor: 'border-cyan-500/60 shadow-[0_0_25px_rgba(6,182,212,0.4)]',
    description: 'Server acknowledged. Verifying database connectivity and multi-model AI inference pipelines...',
    pulse: true,
  },
  CONNECTED: {
    label: 'System Ready • Opening Chat',
    colorClass: 'text-emerald-400',
    badgeClass: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
    ringColor: 'border-emerald-500/80 shadow-[0_0_30px_rgba(16,185,129,0.5)]',
    description: 'All services verified. Launching your personalized workspace...',
    pulse: false,
  },
  RECONNECTING: {
    label: 'Reconnecting to Server',
    colorClass: 'text-amber-400',
    badgeClass: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    ringColor: 'border-amber-500/50 shadow-[0_0_20px_rgba(245,158,11,0.3)]',
    description: 'Temporary connection interruption. Retrying in background without losing your conversation...',
    pulse: true,
  },
  CONNECTION_ERROR: {
    label: 'Connection Delayed',
    colorClass: 'text-rose-400',
    badgeClass: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    ringColor: 'border-rose-500/50 shadow-[0_0_25px_rgba(244,63,94,0.35)]',
    description: 'The backend did not respond within the expected window. Inspect details below or trigger an instant check.',
    pulse: false,
  },
}

export function BackendStatusIndicator({ connection }: BackendStatusIndicatorProps) {
  const { state, elapsedSeconds, attemptCount, nextRetrySeconds, retryNow, lastError, diagnostics } = connection
  const cfg = STATE_CONFIG[state] || STATE_CONFIG.INITIALIZING
  const isWaking = state !== 'CONNECTED' && (state === 'WAKING_UP' || elapsedSeconds >= 8)
  const showTroubleshoot = state !== 'CONNECTED' && (state === 'CONNECTION_ERROR' || elapsedSeconds >= 35)

  return (
    <div className="w-full flex flex-col items-center text-center">
      {/* Distinctive Animated Identity Element */}
      <div className="relative mb-6 flex items-center justify-center">
        {/* Ambient atmospheric aura */}
        <div
          className={`absolute -inset-4 rounded-3xl blur-2xl opacity-40 transition-all duration-700 ${
            state === 'CONNECTED'
              ? 'bg-emerald-500/40'
              : state === 'WAKING_UP'
              ? 'bg-amber-500/30'
              : state === 'CONNECTION_ERROR'
              ? 'bg-rose-500/30'
              : 'bg-brand/30'
          }`}
        />

        {/* Outer orbital rings */}
        <div
          className={`relative w-20 h-20 sm:w-24 sm:h-24 rounded-2xl p-1 border transition-all duration-700 flex items-center justify-center bg-card/80 backdrop-blur-xl ${cfg.ringColor}`}
        >
          {/* Logo container */}
          <div className="w-full h-full rounded-xl overflow-hidden relative shadow-inner">
            <img
              src="/logo.jpg"
              alt="HSBot Logo"
              className="w-full h-full object-cover select-none"
              draggable={false}
            />

            {/* Shimmer overlay */}
            {cfg.pulse && (
              <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/10 to-transparent animate-pulse pointer-events-none" />
            )}
          </div>

          {/* Status badge node */}
          <div className="absolute -bottom-1 -right-1 p-1 rounded-full bg-background border border-border shadow-md">
            {state === 'CONNECTED' ? (
              <CheckCircle2 size={16} className="text-emerald-400" />
            ) : state === 'CONNECTION_ERROR' ? (
              <AlertCircle size={16} className="text-rose-400" />
            ) : (
              <div className="w-4 h-4 rounded-full bg-brand/20 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-brand animate-ping" />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Brand Heading */}
      <div className="space-y-1 mb-4">
        <div className="flex items-center justify-center gap-2">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            HS Bot
          </h1>
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-brand/15 text-brand border border-brand/25">
            AI Assistant
          </span>
        </div>
        <p className="text-xs sm:text-sm text-muted-foreground max-w-sm">
          Autonomous intelligence powered by HS AI Solutions
        </p>
      </div>

      {/* Connection State Badge */}
      <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-medium mb-3 backdrop-blur-md shadow-xs transition-colors duration-300">
        <span className={`inline-flex items-center gap-1.5 font-semibold ${cfg.colorClass}`}>
          <span className="relative flex h-2 w-2">
            {cfg.pulse && (
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${cfg.colorClass.replace('text-', 'bg-')}`} />
            )}
            <span className={`relative inline-flex rounded-full h-2 w-2 ${cfg.colorClass.replace('text-', 'bg-')}`} />
          </span>
          {cfg.label}
        </span>
      </div>

      {/* Indeterminate Animated Progress Bar */}
      <div className="w-full max-w-xs sm:max-w-sm mb-4">
        <div className="h-1.5 w-full bg-muted/60 rounded-full overflow-hidden relative border border-border/40">
          {state === 'CONNECTED' ? (
            <div className="h-full w-full bg-emerald-500 transition-all duration-500" />
          ) : (
            <div className="h-full bg-gradient-to-r from-transparent via-brand to-transparent w-1/2 rounded-full animate-indeterminate-shimmer" />
          )}
        </div>
      </div>

      {/* Explanatory Description */}
      <p className="text-xs sm:text-sm text-muted-foreground/85 max-w-md mb-4 px-2 leading-relaxed">
        {cfg.description}
      </p>

      {/* Metrics Row (Elapsed Time, Attempt Count, Retry countdown) */}
      <div className="flex items-center justify-center gap-3 sm:gap-4 text-[11px] text-muted-foreground/70 mb-5 flex-wrap">
        <span className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-muted/40 border border-border/40">
          <Clock size={11} className="opacity-70" />
          <span>Elapsed: <strong>{elapsedSeconds}s</strong></span>
        </span>

        <span className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-muted/40 border border-border/40">
          <Server size={11} className="opacity-70" />
          <span>Probe #{attemptCount}</span>
        </span>

        {state !== 'CONNECTED' && nextRetrySeconds > 0 && (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-muted/40 border border-border/40">
            <RefreshCw size={11} className="animate-spin opacity-70" />
            <span>Next in {nextRetrySeconds}s</span>
          </span>
        )}
      </div>

      {/* Reassuring Render Cold Start Notice */}
      {isWaking && (
        <div className="w-full max-w-md p-3 sm:p-3.5 rounded-xl border border-amber-500/25 bg-amber-500/5 text-left mb-4 backdrop-blur-sm transition-all duration-300">
          <div className="flex items-start gap-2.5">
            <Zap size={15} className="text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-muted-foreground leading-relaxed">
              <strong className="text-foreground block font-medium mb-0.5">
                Cloud Spin-Up in Progress
              </strong>
              Render instances spin down automatically when idle to optimize resources. HS Bot is warming up the container. The interface will transition immediately once live.
            </div>
          </div>
        </div>
      )}

      {/* Troubleshooting and Manual Retry Panel */}
      {showTroubleshoot && (
        <div className="w-full max-w-md p-3.5 rounded-xl border border-border bg-card/80 text-left mb-4 shadow-sm backdrop-blur-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <AlertCircle size={13} className="text-amber-400" />
              Troubleshooting Assistance
            </span>
            <span className="text-[10px] text-muted-foreground/60">
              {diagnostics.online ? 'Network: Online' : 'Network: Offline'}
            </span>
          </div>

          <p className="text-xs text-muted-foreground mb-3 leading-relaxed">
            {lastError || 'Connecting took longer than usual. You can trigger an immediate manual check without reloading.'}
          </p>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              className="h-8 text-xs gap-1.5 border-brand/40 bg-brand/10 hover:bg-brand/20 text-foreground"
              onClick={() => retryNow()}
            >
              <RefreshCw size={12} />
              <span>Retry Connection Now</span>
            </Button>
            <span className="text-[11px] text-muted-foreground/60 truncate">
              Auto-checking in background
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
