import React, { useEffect, useRef, useState, useCallback } from 'react'
import { Globe, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'
import { isTauri } from '@/lib/tauri'

interface BrowserTab {
  id: string
  title: string
  url: string
  active: boolean
  service: string | null
}

interface BrowserState {
  browser_open: boolean
  active_tab: string | null
  tabs: BrowserTab[]
  current_action: string | null
  queued_actions: string[]
}

/** Live view of the controlled Chrome session — multi-tab list, active tab,
 * current action and queued actions (§5, §10, §13). Polls /api/browser/state with exponential backoff. */
export function BrowserTabs() {
  const [state, setState] = useState<BrowserState | null>(null)
  const [diagnostics, setDiagnostics] = useState<any>(null)
  const [error, setError] = useState(false)
  const timer = useRef<number | null>(null)
  const diagTimer = useRef<number | null>(null)
  const pollIntervalRef = useRef(2500)
  const diagIntervalRef = useRef(2500)
  const consecutiveErrors = useRef(0)
  const isPolling = useRef(false)
  const isDiagPolling = useRef(false)

  const poll = useCallback(async () => {
    if (!isTauri || isPolling.current) return
    isPolling.current = true
    try {
      const res = await api.get<BrowserState>('/browser/state')
      setState(res)
      setError(false)
      consecutiveErrors.current = 0
      // Reset to base interval on success
      pollIntervalRef.current = 2500
    } catch {
      consecutiveErrors.current += 1
      // Exponential backoff: 2.5s, 5s, 10s, 20s, 30s (max)
      const backoffMultiplier = Math.min(2 ** consecutiveErrors.current, 12)
      pollIntervalRef.current = Math.min(2500 * backoffMultiplier, 30000)
      if (consecutiveErrors.current <= 2) {
        setError(false) // Don't show error immediately
      } else {
        setError(true)
      }
    } finally {
      isPolling.current = false
      // Reschedule with new interval
      if (timer.current) window.clearTimeout(timer.current)
      timer.current = window.setTimeout(poll, pollIntervalRef.current)
    }
  }, [])

  const pollDiagnostics = useCallback(async () => {
    if (!isTauri || isDiagPolling.current) return
    isDiagPolling.current = true
    try {
      const res = await api.get<any>('/browser/diagnostics')
      setDiagnostics(res)
    } catch {
      setDiagnostics({
        Backend: 'FAILED',
        WebSocket: 'NOT CONNECTED',
        'Browser Agent': 'FAILED',
        Chrome: 'NOT CONNECTED',
      })
    } finally {
      isDiagPolling.current = false
      // Diagnostics poll less frequently, max 30s
      if (diagTimer.current) window.clearTimeout(diagTimer.current)
      diagTimer.current = window.setTimeout(pollDiagnostics, 5000)
    }
  }, [])

  useEffect(() => {
    if (!isTauri) return
    let cancelled = false

    const startPolling = () => {
      poll()
      pollDiagnostics()
    }

    startPolling()

    return () => {
      cancelled = true
      if (timer.current) window.clearTimeout(timer.current)
      if (diagTimer.current) window.clearTimeout(diagTimer.current)
    }
  }, [poll, pollDiagnostics])

  if (!isTauri) return null
  if (!state?.browser_open) {
    const backendStatus = diagnostics?.Backend || 'FAILED'
    const wsStatus = diagnostics?.WebSocket || 'NOT CONNECTED'
    const agentStatus = diagnostics?.['Browser Agent'] || 'FAILED'
    const chromeStatus = diagnostics?.Chrome || 'NOT CONNECTED'

    return (
      <div className="flex flex-col gap-1 px-3 py-1.5 border-b border-border bg-muted/30 text-[10px] text-muted-foreground/60 select-none">
        <div className="flex items-center gap-2">
          <Globe size={10} className="text-muted-foreground/50" />
          <span>Controlled browser not running — try "open Spotify"</span>
        </div>
        <div className="flex items-center gap-x-3 gap-y-1 flex-wrap mt-0.5 text-[9px] font-mono">
          <span>Backend: <strong className={backendStatus === 'CONNECTED' ? 'text-green-500' : 'text-red-500'}>{backendStatus}</strong></span>
          <span>WebSocket: <strong className={wsStatus === 'CONNECTED' ? 'text-green-500' : 'text-red-500'}>{wsStatus}</strong></span>
          <span>Browser Agent: <strong className={agentStatus === 'READY' ? 'text-green-500' : 'text-red-500'}>{agentStatus}</strong></span>
          <span>Chrome: <strong className={chromeStatus === 'READY' ? 'text-green-500' : 'text-red-500'}>{chromeStatus}</strong></span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1.5 px-2 h-8 border-b border-border bg-muted/30 overflow-x-auto">
      <Globe size={11} className="text-muted-foreground/50 flex-shrink-0" />
      {state.tabs.map(tab => (
        <span
          key={tab.id}
          title={tab.url}
          className={cn(
            'flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] whitespace-nowrap border max-w-[130px]',
            tab.active
              ? 'bg-card border-foreground/25 text-foreground'
              : 'border-transparent text-muted-foreground/70',
          )}
        >
          <span className="truncate">{tab.title || tab.url}</span>
        </span>
      ))}
      {state.current_action && (
        <span className="flex items-center gap-1 text-[10px] text-brand ml-auto flex-shrink-0">
          <Loader2 size={9} className="animate-spin" />
          {state.current_action}
        </span>
      )}
      {state.queued_actions.length > 0 && (
        <span className="text-[10px] text-muted-foreground/50 flex-shrink-0">
          +{state.queued_actions.length} queued
        </span>
      )}
    </div>
  )
}