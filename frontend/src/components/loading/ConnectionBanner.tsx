import React from 'react'
import { AlertCircle, RefreshCw, WifiOff, Zap } from 'lucide-react'
import type { ConnectionInfo } from '@/types/connection'
import { Button } from '@/components/ui/button'

interface ConnectionBannerProps {
  connection: ConnectionInfo & { retryNow: () => Promise<void> }
}

export function ConnectionBanner({ connection }: ConnectionBannerProps) {
  const { state, lastError, nextRetrySeconds, retryNow } = connection

  // Only render when reconnection is occurring or connection error in active chat
  if (state === 'CONNECTED' || state === 'INITIALIZING') {
    return null
  }

  const isOffline = typeof navigator !== 'undefined' && !navigator.onLine

  return (
    <div
      role="status"
      aria-live="polite"
      className="w-full bg-amber-500/10 border-b border-amber-500/25 px-3 py-2 text-xs text-amber-200 flex items-center justify-between gap-2 shadow-xs backdrop-blur-md relative z-30 transition-all duration-300"
    >
      <div className="flex items-center gap-2 min-w-0">
        {isOffline ? (
          <WifiOff size={14} className="text-amber-400 flex-shrink-0" />
        ) : (
          <RefreshCw size={14} className="text-amber-400 animate-spin flex-shrink-0" />
        )}
        <div className="truncate">
          <span className="font-semibold text-amber-100 mr-1.5">
            {state === 'RECONNECTING'
              ? 'Reconnecting to backend...'
              : state === 'WAKING_UP'
              ? 'Waking up backend server...'
              : 'Backend connection paused.'}
          </span>
          <span className="text-amber-300/80 hidden sm:inline">
            {lastError || 'Your conversation is safely preserved.'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        {nextRetrySeconds > 0 && (
          <span className="text-[11px] text-amber-300/70 hidden xs:inline">
            Retrying in {nextRetrySeconds}s
          </span>
        )}
        <Button
          size="sm"
          variant="outline"
          className="h-6 px-2 text-[11px] border-amber-500/40 bg-amber-500/20 hover:bg-amber-500/30 text-amber-100 rounded-md"
          onClick={() => retryNow()}
        >
          Retry
        </Button>
      </div>
    </div>
  )
}
