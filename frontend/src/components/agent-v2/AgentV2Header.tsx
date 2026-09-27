import React from 'react'
import {
  Layers,
  Cpu,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCcw,
  Sparkles,
  ShieldCheck,
  Activity,
  Maximize2
} from 'lucide-react'

interface AgentV2HeaderProps {
  projectName: string
  stage: string
  isRunning: boolean
  activeModel: string
  tasksCompleted: number
  totalTasks: number
  testPassCount: number
  isVerified: boolean
  onToggleClassic?: () => void
  onOpenPreviewFull?: () => void
}

export function AgentV2Header({
  projectName,
  stage,
  isRunning,
  activeModel,
  tasksCompleted,
  totalTasks,
  testPassCount,
  isVerified,
  onToggleClassic,
  onOpenPreviewFull
}: AgentV2HeaderProps) {
  const getStageBadgeColor = (s: string) => {
    switch (s.toUpperCase()) {
      case 'DELIVERY':
      case 'VERIFIED':
        return 'text-emerald-400 bg-emerald-950/40 border-emerald-800'
      case 'IMPLEMENTATION':
      case 'CODING':
        return 'text-cyan-400 bg-cyan-950/40 border-cyan-800'
      case 'TESTING':
        return 'text-amber-400 bg-amber-950/40 border-amber-800'
      case 'PLANNING':
      case 'ARCHITECTURE':
        return 'text-indigo-400 bg-indigo-950/40 border-indigo-800'
      default:
        return 'text-slate-300 bg-slate-900 border-slate-800'
    }
  }

  const progressPercent = totalTasks > 0 ? Math.round((tasksCompleted / totalTasks) * 100) : 0

  return (
    <header className="h-14 border-b border-border bg-card/80 backdrop-blur-md px-4 flex items-center justify-between gap-4 flex-shrink-0 z-20">
      {/* Left: Brand & Product Name */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary font-bold text-xs">
            V2
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold tracking-tight text-foreground uppercase">AI Company</span>
              <span className="text-[10px] text-muted-foreground font-mono">Autonomous Studio</span>
            </div>
            <h2 className="text-sm font-semibold text-foreground truncate max-w-[220px] sm:max-w-xs">
              {projectName || 'New Product Initiative'}
            </h2>
          </div>
        </div>
      </div>

      {/* Center: Stage, Progress & Model Telemetry */}
      <div className="hidden md:flex items-center gap-4 text-xs font-mono">
        {/* Current Stage */}
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-muted-foreground font-sans uppercase">Phase:</span>
          <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${getStageBadgeColor(stage)}`}>
            {stage || 'READY'}
          </span>
        </div>

        {/* Real Model Indicator */}
        <div className="flex items-center gap-1.5 bg-muted/40 px-2.5 py-1 rounded border border-border/60">
          <Cpu size={12} className={isRunning ? 'text-cyan-400 animate-pulse' : 'text-muted-foreground'} />
          <span className="text-[11px] text-foreground font-semibold">{activeModel || 'codestral'}</span>
        </div>

        {/* Progress Bar */}
        <div className="flex items-center gap-2 min-w-[120px]">
          <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300 rounded-full"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <span className="text-[10px] text-muted-foreground tabular-nums font-bold">
            {tasksCompleted}/{totalTasks || 6}
          </span>
        </div>

        {/* Test State */}
        {testPassCount > 0 && (
          <div className="flex items-center gap-1 text-emerald-500 font-semibold text-[11px]">
            <CheckCircle2 size={12} />
            <span>{testPassCount} assertions</span>
          </div>
        )}

        {/* Verification Status */}
        {isVerified && (
          <div className="flex items-center gap-1 text-emerald-400 text-[11px] font-semibold">
            <ShieldCheck size={13} />
            <span>Verified</span>
          </div>
        )}
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-2">
        {onOpenPreviewFull && (
          <button
            onClick={onOpenPreviewFull}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded-lg hover:bg-muted transition-colors"
            title="Open Preview Fullscreen"
          >
            <Maximize2 size={15} />
          </button>
        )}
        {onToggleClassic && (
          <button
            onClick={onToggleClassic}
            className="px-2.5 py-1 text-[11px] text-muted-foreground hover:text-foreground rounded-md border border-border/70 hover:bg-muted transition-colors font-medium"
            title="Switch back to Classic Agent view"
          >
            Classic View
          </button>
        )}
      </div>
    </header>
  )
}
