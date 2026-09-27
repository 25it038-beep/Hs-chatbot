import React from 'react'
import { Cpu, CheckCircle2, Clock, TerminalSquare, FileCode, AlertTriangle, Layers } from 'lucide-react'
import type { ModelActivityEvent } from '@/lib/agentV2Api'

interface AgentV2ModelActivityProps {
  activities: ModelActivityEvent[]
}

export function AgentV2ModelActivity({ activities }: AgentV2ModelActivityProps) {
  if (!activities || activities.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center text-muted-foreground h-full">
        <Cpu size={24} className="opacity-30 mb-2" />
        <p className="text-xs font-medium">No model inference calls recorded yet.</p>
        <p className="text-[11px] text-muted-foreground/60 mt-1 max-w-xs">
          When the company executes work, real model calls and latency metrics stream here live.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3 p-4 overflow-y-auto h-full">
      <div className="flex items-center justify-between pb-2 border-b border-border text-xs text-muted-foreground">
        <span className="font-bold uppercase tracking-wider text-[10px]">Real Model Inference Log</span>
        <span className="font-mono text-[10px] bg-muted px-2 py-0.5 rounded font-semibold">
          {activities.length} Events
        </span>
      </div>

      {activities.map((act, idx) => {
        const timeStr = new Date(act.timestamp * 1000).toLocaleTimeString()
        const isPass = act.verification_status === 'PASS'

        return (
          <div
            key={idx}
            className="p-3.5 rounded-xl border border-border/70 bg-card/60 shadow-xs hover:border-border transition-all text-xs"
          >
            {/* Header: Time, Model, Status */}
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] text-muted-foreground">{timeStr}</span>
                <span className="font-bold text-foreground text-xs">{act.role}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] bg-muted/80 text-foreground px-2 py-0.5 rounded font-semibold border border-border/50">
                  {act.model}
                </span>
                {act.status === 'RUNNING' ? (
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                ) : isPass ? (
                  <CheckCircle2 size={13} className="text-emerald-500" />
                ) : (
                  <AlertTriangle size={13} className="text-amber-500" />
                )}
              </div>
            </div>

            {/* Task description */}
            <p className="text-foreground text-xs font-medium leading-relaxed">{act.task}</p>

            {/* Result & Telemetry */}
            {act.result && (
              <p className="text-[11px] text-muted-foreground mt-1.5 font-mono leading-snug bg-muted/30 p-2 rounded-lg border border-border/40">
                {act.result}
              </p>
            )}

            {/* Footer metrics: Duration, Tools, Files */}
            <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground mt-2.5 pt-2 border-t border-border/40">
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <Clock size={11} />
                  <span>{act.duration > 0 ? `${act.duration}s` : 'active'}</span>
                </span>
                {act.tool_calls && act.tool_calls.length > 0 && (
                  <span className="flex items-center gap-1">
                    <TerminalSquare size={11} />
                    <span>{act.tool_calls.join(', ')}</span>
                  </span>
                )}
              </div>
              {act.files_changed && act.files_changed.length > 0 && (
                <span className="flex items-center gap-1 text-primary">
                  <FileCode size={11} />
                  <span>{act.files_changed.length} files</span>
                </span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
