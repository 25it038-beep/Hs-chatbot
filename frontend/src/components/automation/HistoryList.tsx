import React from 'react'
import { useAutomation, type LogEntry } from '@/stores/automation'
import { cn } from '@/lib/utils'
import { CheckCircle2, XCircle } from 'lucide-react'

const RISK_DOT: Record<string, string> = {
  low: 'bg-emerald-400',
  medium: 'bg-amber-400',
  high: 'bg-orange-400',
  critical: 'bg-red-400',
}

export function HistoryList() {
  const { history } = useAutomation()

  if (history.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border/50 p-4 text-center">
        <p className="text-xs text-muted-foreground/50">No actions executed yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-1.5">
      {history.map((entry, i) => {
        const time = new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        const ms = entry.execution_time_ms != null ? `${entry.execution_time_ms.toFixed(0)}ms` : null
        return (
          <div key={`${entry.action_id}-${i}`} className="flex items-start gap-2.5 rounded-xl border border-border/40 bg-background/40 p-2.5">
            {entry.success ? (
              <CheckCircle2 size={13} className="text-emerald-400 mt-0.5 flex-shrink-0" />
            ) : (
              <XCircle size={13} className="text-red-400 mt-0.5 flex-shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', RISK_DOT[entry.risk_level] ?? 'bg-muted-foreground/40')} />
                <span className="text-[12px] font-medium truncate">{entry.explanation ?? entry.intent}</span>
                {ms && <span className="text-[10px] text-muted-foreground/50 font-mono flex-shrink-0">{ms}</span>}
              </div>
              {entry.target && (
                <p className="text-[11px] text-muted-foreground/60 truncate mt-0.5">
                  {entry.intent} → {entry.target}
                </p>
              )}
              {!entry.success && entry.error && (
                <p className="text-[11px] text-red-300/80 truncate mt-0.5">{entry.error}</p>
              )}
            </div>
            <span className="text-[10px] text-muted-foreground/40 font-mono flex-shrink-0 mt-0.5">{time}</span>
          </div>
        )
      })}
    </div>
  )
}