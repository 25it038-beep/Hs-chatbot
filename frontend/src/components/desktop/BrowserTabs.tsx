import React, { useEffect, useRef, useState } from 'react'
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
 * current action and queued actions (§5, §10, §13). Polls /api/browser/state. */
export function BrowserTabs() {
  const [state, setState] = useState<BrowserState | null>(null)
  const [error, setError] = useState(false)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    if (!isTauri) return
    let cancelled = false

    const poll = async () => {
      try {
        const res = await api.get<BrowserState>('/browser/state')
        if (cancelled) return
        setState(res)
        setError(false)
      } catch {
        if (!cancelled) setError(true)
      }
    }

    poll()
    timer.current = window.setInterval(poll, 2500)
    return () => {
      cancelled = true
      if (timer.current) window.clearInterval(timer.current)
    }
  }, [])

  if (!isTauri) return null
  if (!state?.browser_open) {
    return (
      <div className="flex items-center gap-2 px-3 h-7 border-b border-border bg-muted/30 text-[10px] text-muted-foreground/60">
        <Globe size={10} />
        {error ? 'Browser status unavailable' : 'Controlled browser not running — try "open Spotify"'}
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
