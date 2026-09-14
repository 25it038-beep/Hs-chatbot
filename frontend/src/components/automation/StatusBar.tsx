import React from 'react'
import { useAutomation } from '@/stores/automation'
import { cn } from '@/lib/utils'
import { Monitor, Cpu, ShieldCheck, Mic, RefreshCw, Zap } from 'lucide-react'

export function StatusBar() {
  const { status, connected, connecting, refreshStatus } = useAutomation()

  const available = status?.automation_available ?? false

  return (
    <div className="rounded-xl border border-border/50 bg-muted/20 p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Monitor size={13} className={available ? 'text-brand' : 'text-muted-foreground/40'} />
          <span className="text-xs font-medium">
            {available ? 'Automation ready' : 'Unavailable on this backend'}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {connected && (
            <span className="flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[10px] text-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              stream
            </span>
          )}
          {connecting && (
            <span className="rounded-full bg-sky-500/10 border border-sky-500/30 px-2 py-0.5 text-[10px] text-sky-200">
              connecting...
            </span>
          )}
          <button
            onClick={() => void refreshStatus()}
            aria-label="Refresh automation status"
            className="p-1 rounded-md text-muted-foreground/50 hover:text-foreground hover:bg-muted/60 transition-all"
          >
            <RefreshCw size={11} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-lg border border-border/40 bg-background/40 px-2 py-1.5">
          <div className="flex items-center gap-1 text-[10px] text-muted-foreground/60 mb-0.5">
            <Cpu size={9} /> Executor
          </div>
          <p className="text-[11px] font-medium">
            {status?.engine?.active_processes ?? '—'}<span className="text-muted-foreground/50">/{status?.engine?.max_workers ?? '—'}</span>
          </p>
        </div>
        <div className="rounded-lg border border-border/40 bg-background/40 px-2 py-1.5">
          <div className="flex items-center gap-1 text-[10px] text-muted-foreground/60 mb-0.5">
            <ShieldCheck size={9} /> Pending
          </div>
          <p className="text-[11px] font-medium">{status?.engine?.pending_confirmations ?? '—'}</p>
        </div>
        <div className="rounded-lg border border-border/40 bg-background/40 px-2 py-1.5">
          <div className="flex items-center gap-1 text-[10px] text-muted-foreground/60 mb-0.5">
            <Mic size={9} /> Voice
          </div>
          <p className="text-[11px] font-medium capitalize">
            {status?.voice_listener?.state ?? '—'}
          </p>
        </div>
      </div>

      {!available && (
        <p className="text-[11px] leading-relaxed text-muted-foreground/70">
          OS automation only runs on the <span className="text-foreground/80 font-medium">local backend</span> (localhost:8000). The cloud backend can't touch your PC. Set Backend → Local in Settings.
        </p>
      )}

      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground/50">
        <Zap size={9} className="text-brand" />
        {status?.platform ?? 'windows'} · {status?.voice_listener?.continuous_mode ? 'continuous listening' : 'wake-word listening'}
      </div>
    </div>
  )
}