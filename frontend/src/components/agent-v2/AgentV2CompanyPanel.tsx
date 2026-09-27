import React from 'react'
import {
  Users,
  Cpu,
  CheckCircle2,
  Clock,
  Sparkles,
  Shield,
  Layers,
  Code2,
  Eye,
  FileCheck2,
  TerminalSquare
} from 'lucide-react'
import type { EmployeeRole } from '@/lib/agentV2Api'

interface AgentV2CompanyPanelProps {
  roles: EmployeeRole[]
  activeEmployeeRole?: string
  currentTaskDescription?: string
}

export function AgentV2CompanyPanel({
  roles,
  activeEmployeeRole,
  currentTaskDescription
}: AgentV2CompanyPanelProps) {
  const getRoleIcon = (roleName: string) => {
    const lower = roleName.toLowerCase()
    if (lower.includes('architect')) return <Layers size={14} className="text-indigo-400" />
    if (lower.includes('designer') || lower.includes('ui')) return <Sparkles size={14} className="text-pink-400" />
    if (lower.includes('frontend') || lower.includes('code') || lower.includes('engineer'))
      return <Code2 size={14} className="text-cyan-400" />
    if (lower.includes('test')) return <TerminalSquare size={14} className="text-amber-400" />
    if (lower.includes('visual') || lower.includes('qa')) return <Eye size={14} className="text-purple-400" />
    if (lower.includes('verifier') || lower.includes('security'))
      return <Shield size={14} className="text-emerald-400" />
    return <Users size={14} className="text-slate-400" />
  }

  return (
    <div className="flex flex-col h-full bg-card/40 border-r border-border w-72 flex-shrink-0 select-none">
      {/* Panel Header */}
      <div className="p-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users size={15} className="text-primary" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">AI Product Company</h3>
        </div>
        <span className="text-[10px] font-mono bg-muted px-1.5 py-0.5 rounded text-muted-foreground font-semibold">
          {roles.length} Employees
        </span>
      </div>

      {/* Active Employee Spotlight (if currently executing) */}
      {activeEmployeeRole && (
        <div className="p-3 bg-primary/5 border-b border-primary/20 animate-in fade-in duration-200">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-bold uppercase tracking-widest text-primary flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-primary animate-ping" />
              Active Assignment
            </span>
            <span className="text-[10px] font-mono text-primary font-bold">RUNNING</span>
          </div>
          <p className="text-xs font-bold text-foreground">{activeEmployeeRole}</p>
          {currentTaskDescription && (
            <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2 leading-relaxed">
              {currentTaskDescription}
            </p>
          )}
        </div>
      )}

      {/* Employee List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {roles.map((emp) => {
          const isActive =
            activeEmployeeRole &&
            (activeEmployeeRole.toLowerCase().includes(emp.role_name.toLowerCase()) ||
              emp.role_name.toLowerCase().includes(activeEmployeeRole.toLowerCase()))

          return (
            <div
              key={emp.role}
              className={`p-2.5 rounded-xl border transition-all text-xs ${
                isActive
                  ? 'bg-card border-primary/50 shadow-sm shadow-primary/5'
                  : 'bg-card/50 border-border/60 hover:border-border hover:bg-card/80'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="p-1.5 rounded-lg bg-muted/60 flex-shrink-0">
                    {getRoleIcon(emp.role_name)}
                  </div>
                  <div className="min-w-0">
                    <h4 className="font-semibold text-foreground truncate text-xs">{emp.role_name}</h4>
                    <div className="flex items-center gap-1 mt-0.5 text-[10px] font-mono text-muted-foreground">
                      <Cpu size={10} />
                      <span className="truncate">{emp.model}</span>
                    </div>
                  </div>
                </div>

                {isActive ? (
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse mt-1 flex-shrink-0" />
                ) : (
                  <span className="text-[10px] text-muted-foreground font-mono mt-0.5">Ready</span>
                )}
              </div>

              <p className="text-[11px] text-muted-foreground/80 mt-2 leading-snug line-clamp-2">
                {emp.responsibility}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
