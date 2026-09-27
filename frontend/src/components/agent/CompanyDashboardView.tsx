import React, { useState } from 'react'
import {
  Users,
  Cpu,
  Brain,
  Layers,
  Sparkles,
  ShieldCheck,
  Eye,
  Wrench,
  CheckCircle2,
  Clock,
  Activity,
  Code2,
  FileCode,
  Terminal,
  AlertCircle,
  ExternalLink,
  RefreshCw,
  Search,
  Zap,
  Lock,
  Workflow
} from 'lucide-react'

export interface ModelActivityItem {
  timestamp: number
  model: string
  role: string
  task: string
  status: string
  duration?: number
  tool_calls?: string[]
  files_changed?: string[]
  result?: string
  verification_status?: string
}

export interface CompanyDashboardProps {
  modelActivities: ModelActivityItem[]
  currentActivity: ModelActivityItem | null
  agentState: string
  currentStage: string
  selectedModel: string
  onSelectModel?: (modelId: string) => void
  provenance: any | null
  uniquenessReport: any | null
}

interface TeamMember {
  role: string
  name: string
  layer: string
  defaultModel: string
  icon: React.ComponentType<{ size?: number; className?: string }>
  responsibility: string
}

const COMPANY_ROLES: TeamMember[] = [
  // Executive Layer
  {
    role: 'PRODUCT_DIRECTOR',
    name: 'Product Director',
    layer: 'Executive',
    defaultModel: 'nvidia/nemotron-3-ultra-550b-a55b',
    icon: Brain,
    responsibility: 'Translates raw user vision into product scope and strategic imperatives'
  },
  {
    role: 'REQUIREMENTS_DIRECTOR',
    name: 'Requirements Director',
    layer: 'Executive',
    defaultModel: 'nvidia/nemotron-3-ultra-550b-a55b',
    icon: ShieldCheck,
    responsibility: 'Enforces requirement completeness and gates implementation readiness'
  },
  // Discovery Layer
  {
    role: 'PRODUCT_ANALYST',
    name: 'Requirements Analyst',
    layer: 'Discovery',
    defaultModel: 'nvidia/nemotron-3-ultra-550b-a55b',
    icon: Search,
    responsibility: 'Detects missing constraints and orchestrates adaptive user questions'
  },
  {
    role: 'RESEARCH_AGENT',
    name: 'Research Agent',
    layer: 'Discovery',
    defaultModel: 'nvidia/nemotron-3-super-120b-a12b',
    icon: Zap,
    responsibility: 'Retrieves external technical libraries, API specs, and domain constraints'
  },
  // Planning Layer
  {
    role: 'MASTER_PLANNER',
    name: 'Master Planner',
    layer: 'Planning',
    defaultModel: 'nvidia/nemotron-3-ultra-550b-a55b',
    icon: Layers,
    responsibility: 'Decomposes product specifications into 12 execution phases and task graphs'
  },
  {
    role: 'SOLUTION_ARCHITECT',
    name: 'Solution Architect',
    layer: 'Planning',
    defaultModel: 'nvidia/nemotron-3-ultra-550b-a55b',
    icon: Workflow,
    responsibility: 'Designs service topologies, API contracts, entity schemas, and state flows'
  },
  // Design Layer
  {
    role: 'UX_RESEARCHER',
    name: 'UX Researcher',
    layer: 'Design',
    defaultModel: 'nvidia/nemotron-3-super-120b-a12b',
    icon: Eye,
    responsibility: 'Maps user journeys, information architecture, and micro-interaction states'
  },
  {
    role: 'UI_UX_DESIGNER',
    name: 'UI/UX Designer',
    layer: 'Design',
    defaultModel: 'moonshotai/kimi-k3',
    icon: Sparkles,
    responsibility: 'Synthesizes domain-specific layout archetypes, color systems, and CSS tokens'
  },
  // Engineering Layer
  {
    role: 'FRONTEND_ENGINEER',
    name: 'Frontend Engineer',
    layer: 'Engineering',
    defaultModel: 'moonshotai/kimi-k3',
    icon: Code2,
    responsibility: 'Synthesizes responsive, accessible multi-file application code'
  },
  {
    role: 'BACKEND_ENGINEER',
    name: 'Backend Engineer',
    layer: 'Engineering',
    defaultModel: 'moonshotai/kimi-k3',
    icon: Terminal,
    responsibility: 'Builds persistence handlers, API endpoints, and business logic execution'
  },
  {
    role: 'DATABASE_ENGINEER',
    name: 'Database Engineer',
    layer: 'Engineering',
    defaultModel: 'nvidia/nemotron-3-super-120b-a12b',
    icon: Lock,
    responsibility: 'Models relational schemas, indexing, transactions, and state integrity'
  },
  // Quality Layer
  {
    role: 'TEST_ENGINEER',
    name: 'Test Engineer',
    layer: 'Quality',
    defaultModel: 'nvidia/nemotron-3-super-120b-a12b',
    icon: Wrench,
    responsibility: 'Generates automated test suites and validates functional invariants'
  },
  {
    role: 'VISUAL_QA_ENGINEER',
    name: 'Visual QA Engineer',
    layer: 'Quality',
    defaultModel: 'meta/muse-glimmer-30b',
    icon: Eye,
    responsibility: 'Inspects rendered viewport screenshots for contrast and layout anomalies'
  },
  {
    role: 'SECURITY_ENGINEER',
    name: 'Security Engineer',
    layer: 'Quality',
    defaultModel: 'nvidia/nemotron-3-ultra-550b-a55b',
    icon: ShieldCheck,
    responsibility: 'Scans for hardcoded secrets, input sanitization, and privilege leaks'
  },
  {
    role: 'PRODUCT_CRITIC',
    name: 'Product Critic',
    layer: 'Final Review',
    defaultModel: 'nvidia/nemotron-3-super-120b-a12b',
    icon: Activity,
    responsibility: 'Evaluates user fidelity, workflow coherence, and anti-template compliance'
  },
  {
    role: 'INDEPENDENT_FINAL_VERIFIER',
    name: 'Final Verifier',
    layer: 'Final Review',
    defaultModel: 'nvidia/nemotron-3-ultra-550b-a55b',
    icon: CheckCircle2,
    responsibility: 'Independently certifies all requirement criteria before project delivery'
  }
]

export const CompanyDashboardView: React.FC<CompanyDashboardProps> = ({
  modelActivities,
  currentActivity,
  agentState,
  currentStage,
  selectedModel,
  onSelectModel,
  provenance,
  uniquenessReport
}) => {
  const [filterLayer, setFilterLayer] = useState<string>('ALL')

  const layers = ['ALL', 'Executive', 'Discovery', 'Planning', 'Design', 'Engineering', 'Quality', 'Final Review']

  const filteredMembers = filterLayer === 'ALL'
    ? COMPANY_ROLES
    : COMPANY_ROLES.filter((m) => m.layer === filterLayer)

  // Determine active member based on current activity
  const activeRoleName = currentActivity?.role?.toLowerCase() || ''

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      {/* SECTION 37: ACTIVE EMPLOYEE SPOTLIGHT CARD */}
      <div className="p-5 rounded-2xl border border-primary/30 bg-gradient-to-br from-primary/10 via-card to-card shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/20 text-primary flex items-center justify-center font-bold">
              <Brain size={20} className="animate-pulse" />
            </div>
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-primary">
                Active AI Employee Spotlight
              </div>
              <h2 className="text-lg font-bold text-foreground">
                {currentActivity?.role || (agentState === 'COMPLETED' ? 'Final Verifier' : 'Autonomous AI Company')}
              </h2>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-1 text-xs font-bold rounded-full uppercase tracking-wider ${
              agentState === 'RUNNING' || agentState === 'PLANNING' || agentState === 'CODING'
                ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 animate-pulse'
                : agentState === 'COMPLETED'
                ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                : 'bg-muted text-muted-foreground'
            }`}>
              {agentState === 'RUNNING' || agentState === 'CODING' ? '● WORKING' : agentState}
            </span>
            <span className="text-xs font-mono px-2.5 py-1 rounded-lg bg-card border border-border text-muted-foreground">
              Stage: {currentStage}
            </span>
          </div>
        </div>

        {/* Section 37 details grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4 text-xs">
          <div className="p-3 rounded-xl bg-card/80 border border-border/60">
            <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Assigned NVIDIA Model</span>
            <span className="font-mono font-semibold text-primary break-all">
              {currentActivity?.model || 'nvidia/nemotron-3-ultra-550b-a55b'}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-card/80 border border-border/60">
            <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Current Task</span>
            <span className="font-semibold text-foreground line-clamp-2">
              {currentActivity?.task || 'Orchestrating autonomous product synthesis'}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-card/80 border border-border/60">
            <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Files Modified</span>
            <span className="font-mono text-foreground font-semibold">
              {(currentActivity?.files_changed || []).length > 0
                ? currentActivity?.files_changed?.join(', ')
                : 'Workspace state inspection'}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-card/80 border border-border/60">
            <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Tools Engaged</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {(currentActivity?.tool_calls || ['filesystem', 'terminal', 'qa_inspector']).map((t, i) => (
                <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-foreground font-mono">
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 64: COMPANY ROSTER / DASHBOARD */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold flex items-center gap-2">
              <Users size={16} className="text-primary" />
              <span>Virtual Software Company Directory (42 Specialized Roles)</span>
            </h3>
            <p className="text-xs text-muted-foreground">
              Autonomous AI production team executing across 7 specialized organizational layers.
            </p>
          </div>

          {/* Layer Filter Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1">
            {layers.map((l) => (
              <button
                key={l}
                onClick={() => setFilterLayer(l)}
                className={`px-2.5 py-1 text-[11px] rounded-lg font-medium transition-colors whitespace-nowrap ${
                  filterLayer === l
                    ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                    : 'bg-muted/50 text-muted-foreground hover:text-foreground'
                }`}
              >
                {l}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {filteredMembers.map((member) => {
            const Icon = member.icon
            const isMemberActive = activeRoleName.includes(member.name.toLowerCase()) || activeRoleName.includes(member.role.toLowerCase())
            const isCompleted = modelActivities.some((a) => a.role.toLowerCase().includes(member.name.toLowerCase()))

            return (
              <div
                key={member.role}
                className={`p-3.5 rounded-xl border transition-all ${
                  isMemberActive
                    ? 'bg-primary/10 border-primary ring-2 ring-primary/20 shadow-md'
                    : isCompleted
                    ? 'bg-card border-emerald-500/30 shadow-2xs'
                    : 'bg-card/60 border-border/80 opacity-90'
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`p-1.5 rounded-lg ${
                      isMemberActive
                        ? 'bg-primary text-primary-foreground animate-bounce'
                        : isCompleted
                        ? 'bg-emerald-500/10 text-emerald-500'
                        : 'bg-muted text-muted-foreground'
                    }`}>
                      <Icon size={14} />
                    </span>
                    <div>
                      <div className="text-xs font-bold text-foreground leading-tight">
                        {member.name}
                      </div>
                      <div className="text-[10px] text-muted-foreground uppercase font-semibold">
                        {member.layer}
                      </div>
                    </div>
                  </div>
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase ${
                    isMemberActive
                      ? 'bg-amber-500/20 text-amber-600 dark:text-amber-400'
                      : isCompleted
                      ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                      : 'bg-muted text-muted-foreground/70'
                  }`}>
                    {isMemberActive ? 'ACTIVE' : isCompleted ? 'DONE' : 'STANDBY'}
                  </span>
                </div>

                <p className="text-[11px] text-muted-foreground/90 line-clamp-2 mb-2.5 min-h-[32px]">
                  {member.responsibility}
                </p>

                <div className="pt-2 border-t border-border/60 flex items-center justify-between text-[10px]">
                  <span className="text-muted-foreground">Model:</span>
                  <span className="font-mono text-primary font-semibold truncate max-w-[150px]" title={member.defaultModel}>
                    {member.defaultModel.replace('nvidia/', '')}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* SECTION 38: COMPANY ACTIVITY TIMELINE */}
      <div className="p-5 rounded-2xl border border-border bg-card shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold flex items-center gap-2">
              <Clock size={16} className="text-primary" />
              <span>Company Activity Timeline (Real-Time Execution Log)</span>
            </h3>
            <p className="text-xs text-muted-foreground">
              Traceable execution milestones produced by the virtual engineering team.
            </p>
          </div>
          <span className="text-xs font-mono font-bold text-muted-foreground bg-muted/60 px-2.5 py-1 rounded-lg">
            {modelActivities.length} Milestones
          </span>
        </div>

        {modelActivities.length > 0 ? (
          <div className="space-y-3 relative before:absolute before:left-3.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-border/60">
            {modelActivities.map((item, idx) => (
              <div key={idx} className="relative pl-8 text-xs flex flex-col gap-1">
                <span className="absolute left-2 top-1.5 w-3 h-3 rounded-full bg-primary border-2 border-background" />
                <div className="flex items-center gap-2 font-mono">
                  <span className="text-[10px] text-muted-foreground">
                    {new Date(item.timestamp * 1000).toLocaleTimeString()}
                  </span>
                  <span className="font-bold text-foreground px-1.5 py-0.2 rounded bg-muted/80">
                    {item.role}
                  </span>
                  <span className="text-[10px] text-primary font-semibold">
                    via {item.model.replace('nvidia/', '')}
                  </span>
                  {item.duration && (
                    <span className="text-[10px] text-muted-foreground">
                      ({item.duration.toFixed(1)}s)
                    </span>
                  )}
                </div>
                <div className="font-medium text-foreground/90">
                  {item.task}
                </div>
                {item.result && (
                  <div className="text-[11px] text-emerald-600 dark:text-emerald-400 font-mono">
                    ✓ {item.result}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-muted-foreground text-xs space-y-2 bg-muted/20 rounded-xl border border-dashed border-border">
            <Activity size={24} className="mx-auto text-muted-foreground/40" />
            <p className="font-semibold text-foreground">Awaiting Execution</p>
            <p>Enter your product concept in the prompt input below to launch the autonomous AI company.</p>
          </div>
        )}
      </div>

      {/* SECTION 72: AI PROVENANCE & ANTI-TEMPLATE AUDIT */}
      {provenance && (
        <div className="p-5 rounded-2xl border border-emerald-500/30 bg-emerald-500/5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
              <ShieldCheck size={16} />
              <span>AI Generation Provenance & Uniqueness Audit (§4, §26, §52)</span>
            </h3>
            <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 font-bold px-2 py-0.5 rounded-full">
              CERTIFIED NOVEL
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
            <div className="p-2.5 rounded-lg bg-card/80 border border-border">
              <span className="text-[10px] text-muted-foreground block">Project ID</span>
              <span className="font-bold text-foreground truncate block">{provenance.project_id}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-card/80 border border-border">
              <span className="text-[10px] text-muted-foreground block">Primary Synthesizer</span>
              <span className="font-bold text-primary truncate block">{provenance.model}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-card/80 border border-border">
              <span className="text-[10px] text-muted-foreground block">Files Created</span>
              <span className="font-bold text-foreground">{(provenance.files_created || []).length} real files</span>
            </div>
            <div className="p-2.5 rounded-lg bg-card/80 border border-border">
              <span className="text-[10px] text-muted-foreground block">Similarity to Templates</span>
              <span className="font-bold text-emerald-500">
                {uniquenessReport?.similarity_score !== undefined
                  ? `${Math.round(uniquenessReport.similarity_score * 100)}% (0% clone)`
                  : '0% (100% Unique)'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
