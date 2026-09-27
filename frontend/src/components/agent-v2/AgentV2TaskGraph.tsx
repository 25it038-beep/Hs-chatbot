import React from 'react'
import { CheckCircle2, Clock, Play, AlertCircle, ShieldCheck, ArrowRight, UserCheck } from 'lucide-react'
import type { PlanTask } from '@/lib/agentV2Api'

interface AgentV2TaskGraphProps {
  tasks: PlanTask[]
  onSelectTask: (task: PlanTask) => void
  selectedTaskId?: string
}

export function AgentV2TaskGraph({ tasks, onSelectTask, selectedTaskId }: AgentV2TaskGraphProps) {
  const getStatusIcon = (status: PlanTask['status']) => {
    switch (status) {
      case 'completed':
      case 'verified':
        return <CheckCircle2 size={14} className="text-emerald-400" />
      case 'running':
        return <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
      case 'failed':
        return <AlertCircle size={14} className="text-rose-400" />
      default:
        return <Clock size={14} className="text-muted-foreground/60" />
    }
  }

  const getStatusColor = (status: PlanTask['status']) => {
    switch (status) {
      case 'completed':
      case 'verified':
        return 'border-emerald-500/30 bg-emerald-950/10'
      case 'running':
        return 'border-cyan-500/50 bg-cyan-950/20 shadow-xs'
      case 'failed':
        return 'border-rose-500/50 bg-rose-950/20'
      default:
        return 'border-border/60 bg-card/40'
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto w-full space-y-4 overflow-y-auto h-full">
      <div className="flex items-center justify-between pb-2 border-b border-border text-xs text-muted-foreground">
        <span className="font-bold uppercase tracking-wider text-[10px]">Execution Task Graph ({tasks.length} Nodes)</span>
        <span className="text-[11px] font-mono">Click any task node for full telemetry</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {tasks.map((task) => {
          const isSelected = selectedTaskId === task.task_id

          return (
            <div
              key={task.task_id}
              onClick={() => onSelectTask(task)}
              className={`p-4 rounded-xl border transition-all cursor-pointer text-xs space-y-2.5 ${getStatusColor(
                task.status
              )} ${isSelected ? 'ring-1 ring-primary border-primary' : 'hover:border-border'}`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {getStatusIcon(task.status)}
                  <span className="font-mono text-[10px] text-muted-foreground">{task.task_id}</span>
                  <span className="font-bold text-foreground truncate">{task.title}</span>
                </div>
                <span className="text-[10px] font-mono uppercase font-bold text-primary">
                  {task.status}
                </span>
              </div>

              <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                {task.description}
              </p>

              <div className="flex items-center justify-between pt-2 border-t border-border/30 text-[10px] font-mono text-muted-foreground">
                <div className="flex items-center gap-1">
                  <UserCheck size={11} />
                  <span>{task.assigned_role}</span>
                </div>
                {task.dependencies && task.dependencies.length > 0 && (
                  <span>Deps: {task.dependencies.join(', ')}</span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
