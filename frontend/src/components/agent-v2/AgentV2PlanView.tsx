import React from 'react'
import { Check, Edit3, ArrowRight, ShieldCheck, Layers, Cpu, Code2, TerminalSquare, AlertCircle } from 'lucide-react'
import type { ImplementationPlan, ProductSpecification } from '@/lib/agentV2Api'

interface AgentV2PlanViewProps {
  plan: ImplementationPlan
  specification?: ProductSpecification
  onApprove: () => void
  onModify?: () => void
  onChangeRequirements?: () => void
  isApproved?: boolean
  isRunning?: boolean
}

export function AgentV2PlanView({
  plan,
  specification,
  onApprove,
  onModify,
  onChangeRequirements,
  isApproved,
  isRunning
}: AgentV2PlanViewProps) {
  return (
    <div className="p-6 max-w-5xl mx-auto w-full space-y-6 overflow-y-auto h-full">
      {/* Plan Header Card */}
      <div className="p-6 rounded-2xl bg-card border border-border/80 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Layers size={16} className="text-primary" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-primary">Implementation Blueprint</span>
          </div>
          <h3 className="text-lg font-bold text-foreground">{plan.product_name}</h3>
          <p className="text-xs text-muted-foreground mt-1 max-w-xl leading-relaxed">
            {specification?.product_purpose || 'Autonomous software product synthesized by the Virtual Engineering Organization.'}
          </p>
        </div>

        {/* Approval Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {!isApproved && !isRunning ? (
            <>
              {onChangeRequirements && (
                <button
                  onClick={onChangeRequirements}
                  className="px-3.5 py-2 text-xs font-semibold text-muted-foreground hover:text-foreground rounded-xl border border-border hover:bg-muted transition-colors"
                >
                  Change Requirements
                </button>
              )}
              <button
                onClick={onApprove}
                className="px-5 py-2.5 bg-primary text-primary-foreground font-bold text-xs rounded-xl shadow-xs hover:bg-primary/90 transition-all flex items-center gap-2"
              >
                <Check size={14} />
                <span>Approve Plan & Launch Company</span>
              </button>
            </>
          ) : (
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs bg-emerald-950/40 px-3 py-1.5 rounded-xl border border-emerald-800">
              <ShieldCheck size={15} />
              <span>Plan Approved & Active</span>
            </div>
          )}
        </div>
      </div>

      {/* Tech Stack & Architecture Split */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-2xl bg-card border border-border/70 space-y-2 text-xs">
          <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
            <Cpu size={14} />
            <span>Technology Selection</span>
          </div>
          <p className="text-foreground font-medium leading-relaxed">{plan.technology_summary}</p>
        </div>

        <div className="p-5 rounded-2xl bg-card border border-border/70 space-y-2 text-xs">
          <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs uppercase tracking-wider">
            <Layers size={14} />
            <span>System Architecture</span>
          </div>
          <p className="text-foreground font-medium leading-relaxed">{plan.architecture_summary}</p>
        </div>
      </div>

      {/* Folder Structure */}
      {plan.folder_structure && plan.folder_structure.length > 0 && (
        <div className="p-5 rounded-2xl bg-card border border-border/70 space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Planned Project File Structure
          </h4>
          <div className="flex flex-wrap gap-2 text-xs font-mono">
            {plan.folder_structure.map((f, i) => (
              <span
                key={i}
                className="px-2.5 py-1 rounded-lg bg-muted/60 text-foreground border border-border/60 flex items-center gap-1.5"
              >
                <Code2 size={12} className="text-primary" />
                <span>{f}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Execution Phases & Tasks */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
          Implementation Task Graph ({plan.tasks.length} Phases)
        </h4>

        <div className="space-y-3">
          {plan.tasks.map((task) => (
            <div
              key={task.task_id}
              className="p-4 rounded-xl bg-card border border-border/70 hover:border-border transition-all text-xs space-y-2"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-muted-foreground">{task.task_id}</span>
                  <span className="font-bold text-foreground">{task.title}</span>
                </div>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                  {task.assigned_role}
                </span>
              </div>

              <p className="text-muted-foreground text-[11px] leading-relaxed">{task.description}</p>

              <div className="flex items-center justify-between pt-2 border-t border-border/40 text-[10px] font-mono text-muted-foreground">
                <span>Verification: {task.verification_criteria}</span>
                {task.expected_files.length > 0 && (
                  <span className="text-primary">{task.expected_files.join(', ')}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
