import React from 'react'
import { X, CheckCircle2, Clock, AlertTriangle, FileCode, Layers, Cpu, ShieldCheck } from 'lucide-react'
import type { PlanTask } from '@/lib/agentV2Api'

interface AgentV2TaskDetailModalProps {
  task: PlanTask
  onClose: () => void
}

export function AgentV2TaskDetailModal({ task, onClose }: AgentV2TaskDetailModalProps) {
  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 select-none animate-in fade-in duration-150">
      <div className="bg-card border border-border w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-border bg-muted/30 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-bold text-xs font-mono">
              {task.task_id}
            </div>
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">{task.title}</h3>
              <span className="text-[11px] text-muted-foreground font-mono">{task.phase}</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 text-xs">
          <div>
            <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Description</span>
            <p className="text-foreground leading-relaxed">{task.description}</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-muted/40 rounded-xl border border-border/60">
              <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Assigned Role</span>
              <span className="font-semibold text-foreground">{task.assigned_role}</span>
            </div>
            <div className="p-3 bg-muted/40 rounded-xl border border-border/60">
              <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Execution Status</span>
              <span className="font-mono font-bold uppercase text-primary">{task.status}</span>
            </div>
          </div>

          <div>
            <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Verification Criteria</span>
            <p className="text-muted-foreground font-mono text-[11px] bg-muted/30 p-2 rounded-lg border border-border/40">
              {task.verification_criteria}
            </p>
          </div>

          {task.expected_files && task.expected_files.length > 0 && (
            <div>
              <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1.5">Affected File Deliverables</span>
              <div className="flex flex-wrap gap-1.5 font-mono text-[11px]">
                {task.expected_files.map((f, i) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-muted text-primary border border-border">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border bg-muted/20 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-primary text-primary-foreground font-semibold text-xs rounded-xl shadow-xs hover:bg-primary/90 transition-all"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  )
}
