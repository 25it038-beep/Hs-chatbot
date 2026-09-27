import React from 'react'
import { CheckCircle2, AlertCircle, HelpCircle, FileCheck2, ArrowRight } from 'lucide-react'
import type { RequirementItem, ProductSpecification } from '@/lib/agentV2Api'

interface AgentV2RequirementsViewProps {
  requirements: RequirementItem[]
  specification?: ProductSpecification
  onResolveMissing?: () => void
  hasMissingDecision?: boolean
}

export function AgentV2RequirementsView({
  requirements,
  specification,
  onResolveMissing,
  hasMissingDecision
}: AgentV2RequirementsViewProps) {
  const getStatusBadge = (status: RequirementItem['status']) => {
    switch (status) {
      case 'KNOWN':
        return <span className="text-[10px] font-mono font-semibold text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800">KNOWN</span>
      case 'INFERRED':
        return <span className="text-[10px] font-mono font-semibold text-cyan-400 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-800">INFERRED</span>
      case 'MISSING':
        return <span className="text-[10px] font-mono font-semibold text-rose-400 bg-rose-950/40 px-2 py-0.5 rounded border border-rose-800">MISSING</span>
      case 'AMBIGUOUS':
        return <span className="text-[10px] font-mono font-semibold text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800">AMBIGUOUS</span>
      default:
        return <span className="text-[10px] font-mono font-semibold text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">{status}</span>
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto w-full space-y-6 overflow-y-auto h-full">
      {/* Overview Banner */}
      <div className="p-5 rounded-2xl bg-card border border-border/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FileCheck2 size={16} className="text-primary" />
            <h3 className="text-sm font-bold text-foreground">Requirement Sufficiency Engine</h3>
          </div>
          <p className="text-xs text-muted-foreground">
            Classifies project criteria into KNOWN, INFERRED, and MISSING before major implementation.
          </p>
        </div>

        {hasMissingDecision && onResolveMissing && (
          <button
            onClick={onResolveMissing}
            className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-xs font-semibold shadow-xs flex items-center gap-1.5 transition-all flex-shrink-0"
          >
            <span>Resolve Missing Decision</span>
            <ArrowRight size={13} />
          </button>
        )}
      </div>

      {/* Product Specification Summary */}
      {specification && (
        <div className="p-5 rounded-2xl bg-card border border-border/80 shadow-xs space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Product Specification Contract
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="p-3 bg-muted/30 rounded-xl border border-border/40">
              <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Product Name</span>
              <span className="font-semibold text-foreground">{specification.product_name}</span>
            </div>
            <div className="p-3 bg-muted/30 rounded-xl border border-border/40">
              <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Domain Classification</span>
              <span className="font-semibold text-foreground capitalize">{specification.domain}</span>
            </div>
            <div className="p-3 bg-muted/30 rounded-xl border border-border/40">
              <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Data Model</span>
              <span className="font-semibold text-foreground">{specification.data_persistence}</span>
            </div>
          </div>

          {/* Core Workflow list */}
          {specification.core_workflow && specification.core_workflow.length > 0 && (
            <div>
              <span className="text-[11px] font-semibold text-muted-foreground block mb-2">Core Workflow Transitions:</span>
              <div className="flex flex-wrap gap-2">
                {specification.core_workflow.map((wf, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-xs bg-muted/40 px-3 py-1.5 rounded-lg border border-border/60">
                    <span className="font-mono text-primary font-bold">{i + 1}.</span>
                    <span className="text-foreground">{wf}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Classified Requirements Table */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
          Requirement Traceability & Criteria ({requirements.length})
        </h4>

        <div className="space-y-2">
          {requirements.map((req, i) => (
            <div
              key={i}
              className="p-4 rounded-xl bg-card border border-border/70 hover:border-border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-foreground">{req.field}</span>
                  {getStatusBadge(req.status)}
                </div>
                <p className="text-muted-foreground text-[11px] leading-relaxed">{req.detail}</p>
                {req.acceptance_criteria && (
                  <p className="text-[10px] text-primary/80 font-mono mt-1">
                    Acceptance Criteria: {req.acceptance_criteria}
                  </p>
                )}
              </div>

              {req.priority && (
                <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border self-start sm:self-auto">
                  {req.priority}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
