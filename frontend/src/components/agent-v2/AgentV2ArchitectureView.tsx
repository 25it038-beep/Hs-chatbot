import React from 'react'
import { Layers, ArrowDown, Database, Cpu, Layout, HardDrive, Share2, CheckCircle2 } from 'lucide-react'
import type { ProductSpecification } from '@/lib/agentV2Api'

interface AgentV2ArchitectureViewProps {
  specification?: ProductSpecification
}

export function AgentV2ArchitectureView({ specification }: AgentV2ArchitectureViewProps) {
  const pName = specification?.product_name || 'Autonomous Application'
  const domain = specification?.domain || 'web_app'
  const entities = specification?.entities || ['WorkspaceRecord', 'InteractionEntry', 'SystemConfig']

  return (
    <div className="p-6 max-w-4xl mx-auto w-full space-y-6 overflow-y-auto h-full">
      <div className="p-5 rounded-2xl bg-card border border-border/80 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <Layers size={16} className="text-primary" />
          <h3 className="text-sm font-bold text-foreground">Dynamic System Architecture</h3>
        </div>
        <p className="text-xs text-muted-foreground">
          Architectural boundaries and reactive contracts synthesized specifically for {pName}.
        </p>
      </div>

      {/* Layer 1: Client Interface Layer */}
      <div className="p-5 rounded-2xl bg-card border border-primary/30 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layout size={14} className="text-primary" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
              Layer 1: Responsive Viewport & UI Components
            </h4>
          </div>
          <span className="text-[10px] font-mono text-primary font-bold">1440px Desktop / Mobile</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="p-3 bg-muted/40 rounded-xl border border-border/60">
            <span className="font-semibold block text-foreground mb-1">Control Toolbar</span>
            <span className="text-[11px] text-muted-foreground">Action buttons, search query inputs, category filter pills</span>
          </div>
          <div className="p-3 bg-muted/40 rounded-xl border border-border/60">
            <span className="font-semibold block text-foreground mb-1">Interactive Canvas / Grid</span>
            <span className="text-[11px] text-muted-foreground">Dynamic state representation, animations, data item cards</span>
          </div>
          <div className="p-3 bg-muted/40 rounded-xl border border-border/60">
            <span className="font-semibold block text-foreground mb-1">Telemetry & Stats Bar</span>
            <span className="text-[11px] text-muted-foreground">Tabular figures, live counters, status badges</span>
          </div>
        </div>
      </div>

      <div className="flex justify-center text-muted-foreground/60">
        <ArrowDown size={20} />
      </div>

      {/* Layer 2: Reactive State Machine & Event Dispatch */}
      <div className="p-5 rounded-2xl bg-card border border-indigo-500/30 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu size={14} className="text-indigo-400" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
              Layer 2: Reactive State Machine (script.js)
            </h4>
          </div>
          <span className="text-[10px] font-mono text-indigo-400 font-bold">Client Event Loop</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div className="p-3 bg-muted/40 rounded-xl border border-border/60">
            <span className="font-semibold block text-foreground mb-1">Event Listeners & Dispatchers</span>
            <span className="text-[11px] text-muted-foreground">Keyboard shortcuts, click handlers, resize events, drag interactions</span>
          </div>
          <div className="p-3 bg-muted/40 rounded-xl border border-border/60">
            <span className="font-semibold block text-foreground mb-1">State Mutation & Diff Engine</span>
            <span className="text-[11px] text-muted-foreground">Pure functional transforms without unhandled edge cases</span>
          </div>
        </div>
      </div>

      <div className="flex justify-center text-muted-foreground/60">
        <ArrowDown size={20} />
      </div>

      {/* Layer 3: Domain Entity Contracts & Storage */}
      <div className="p-5 rounded-2xl bg-card border border-emerald-500/30 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database size={14} className="text-emerald-400" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
              Layer 3: Domain Entity Contracts & Local Persistence
            </h4>
          </div>
          <span className="text-[10px] font-mono text-emerald-400 font-bold">LocalStorage / JSON</span>
        </div>
        <div className="flex flex-wrap gap-2 text-xs font-mono">
          {entities.map((ent, i) => (
            <span
              key={i}
              className="px-3 py-1.5 rounded-xl bg-muted/60 text-foreground border border-border/60 flex items-center gap-1.5"
            >
              <CheckCircle2 size={12} className="text-emerald-400" />
              <span>{ent} Schema</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
