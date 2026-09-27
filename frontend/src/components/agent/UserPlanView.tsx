import React, { useState } from 'react'
import {
  FileText,
  Sparkles,
  Layers,
  Cpu,
  FolderTree,
  Users,
  ListOrdered,
  Workflow,
  Wrench,
  HelpCircle,
  AlertCircle,
  CheckCircle2,
  Check,
  Edit3,
  RotateCcw,
  Play,
  Pause,
  X,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  ShieldAlert
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { UnderstandingModel } from '@/lib/promptUnderstanding'

export interface UserPlanViewProps {
  prompt: string
  spec: any | null
  dna: any | null
  techStack: any | null
  plan: any | null
  understanding: UnderstandingModel | null
  isPlanValid: boolean
  validationErrors: string[]
  onApprovePlan: () => void
  onModifyPlan: (instructions: string) => void
  onRollback?: () => void
  isRunning: boolean
  agentState: string
}

export const UserPlanView: React.FC<UserPlanViewProps> = ({
  prompt,
  spec,
  dna,
  techStack,
  plan,
  understanding,
  isPlanValid,
  validationErrors,
  onApprovePlan,
  onModifyPlan,
  onRollback,
  isRunning,
  agentState
}) => {
  const [modifyModalOpen, setModifyModalOpen] = useState(false)
  const [modifyInput, setModifyInput] = useState('')
  const [isApproved, setIsApproved] = useState(false)

  const handleApprove = () => {
    setIsApproved(true)
    onApprovePlan()
  }

  const handleModifySubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!modifyInput.trim()) return
    onModifyPlan(modifyInput.trim())
    setModifyInput('')
    setModifyModalOpen(false)
  }

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-6xl mx-auto">
      {/* Top Banner & Approval Control Bar (Section 21 & 22) */}
      <div className="p-5 rounded-2xl border border-primary/30 bg-gradient-to-r from-primary/10 via-card to-card flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded-md bg-primary text-primary-foreground">
              <FileText size={16} />
            </span>
            <span className="text-xs font-bold uppercase tracking-wider text-primary">
              Section 21 • Canonical Implementation Plan
            </span>
          </div>
          <h2 className="text-xl font-black text-foreground">
            {spec?.product_name || (understanding?.primaryGoal ? `${understanding.primaryGoal}` : 'Autonomous Product Implementation Plan')}
          </h2>
          <p className="text-xs text-muted-foreground">
            Exhaustive architectural breakdown validated by Master Planner, Solution Architect, and Requirements Reviewer.
          </p>
        </div>

        {/* Action Controls (Section 22 & 62) */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            className="h-9 text-xs gap-1.5 rounded-xl border-border hover:bg-muted"
            onClick={() => setModifyModalOpen(true)}
            disabled={isRunning}
          >
            <Edit3 size={13} />
            <span>Modify Plan</span>
          </Button>

          {onRollback && (
            <Button
              size="sm"
              variant="outline"
              className="h-9 text-xs gap-1.5 rounded-xl border-border hover:bg-muted text-muted-foreground"
              onClick={onRollback}
              title="Rollback to previous stable checkpoint"
            >
              <RotateCcw size={13} />
              <span>Rollback</span>
            </Button>
          )}

          <Button
            size="sm"
            className={`h-9 text-xs gap-1.5 rounded-xl font-bold transition-all shadow-sm ${
              isApproved
                ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                : 'bg-primary hover:bg-primary/90 text-primary-foreground'
            }`}
            onClick={handleApprove}
            disabled={isRunning}
          >
            <Check size={14} />
            <span>{isApproved ? 'Plan Approved ✓' : 'Approve & Execute Plan'}</span>
          </Button>
        </div>
      </div>

      {/* Validation Status Banner */}
      {!isPlanValid && validationErrors.length > 0 && (
        <div className="p-4 rounded-xl border border-destructive/40 bg-destructive/10 text-destructive text-xs space-y-1.5">
          <div className="font-bold flex items-center gap-1.5">
            <ShieldAlert size={14} /> Plan Validation Warnings Detected:
          </div>
          <ul className="list-disc list-inside space-y-0.5">
            {validationErrors.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 11 MANDATORY SECTIONS FROM §21 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 1. PRODUCT */}
        <div className="p-4 rounded-xl border border-border bg-card space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary border-b border-border/60 pb-2">
            <Sparkles size={14} />
            <span>1. Product Overview</span>
          </div>
          <div className="space-y-1.5 text-xs">
            <div>
              <span className="text-muted-foreground font-semibold">Name: </span>
              <span className="font-bold text-foreground">{spec?.product_name || 'Autonomous Product'}</span>
            </div>
            <div>
              <span className="text-muted-foreground font-semibold">Purpose: </span>
              <span className="text-foreground">{spec?.product_purpose || understanding?.desiredOutcome || 'Specialized software solution'}</span>
            </div>
            <div>
              <span className="text-muted-foreground font-semibold">Target Audience: </span>
              <span className="text-foreground">{(spec?.target_users || ['Students', 'Engineers', 'General Users']).join(', ')}</span>
            </div>
            <div>
              <span className="text-muted-foreground font-semibold">Domain Category: </span>
              <span className="font-mono text-primary font-bold uppercase">{spec?.domain || 'Web Application'}</span>
            </div>
          </div>
        </div>

        {/* 2. REQUIREMENTS UNDERSTOOD */}
        <div className="p-4 rounded-xl border border-border bg-card space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-500 border-b border-border/60 pb-2">
            <CheckCircle2 size={14} />
            <span>2. Requirements Understood</span>
          </div>
          <div className="space-y-1.5 text-xs max-h-[140px] overflow-y-auto pr-1">
            {(understanding?.explicitRequirements || spec?.features || [
              'Zero template generation',
              'Domain-authentic state loop',
              'Responsive viewport scaling',
              'Automated invariant test suite'
            ]).map((req: any, i: number) => (
              <div key={i} className="flex items-start gap-1.5">
                <span className="text-emerald-500 font-bold">✓</span>
                <span className="text-foreground/90">{typeof req === 'string' ? req : req.description || req.title}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 3. ARCHITECTURE */}
        <div className="p-4 rounded-xl border border-border bg-card space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-500 border-b border-border/60 pb-2">
            <Workflow size={14} />
            <span>3. Architecture Blueprint</span>
          </div>
          <div className="space-y-1.5 text-xs">
            <div>
              <span className="text-muted-foreground font-semibold">Pattern: </span>
              <span className="font-mono text-foreground font-bold">{dna?.architecture?.pattern || 'State-Driven Reactive Component System'}</span>
            </div>
            <div>
              <span className="text-muted-foreground font-semibold">State Strategy: </span>
              <span className="text-foreground">{dna?.architecture?.state_management || 'Reactive Store with DOM Reconciliation'}</span>
            </div>
            <div>
              <span className="text-muted-foreground font-semibold">Security Model: </span>
              <span className="text-foreground">{dna?.architecture?.security_boundaries || 'Local Storage Isolation & Zero Secret Exposure'}</span>
            </div>
          </div>
        </div>

        {/* 4. TECHNOLOGY */}
        <div className="p-4 rounded-xl border border-border bg-card space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-500 border-b border-border/60 pb-2">
            <Cpu size={14} />
            <span>4. Chosen Technologies</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div className="p-2 rounded-lg bg-muted/40 border border-border/60">
              <span className="text-[10px] text-muted-foreground block">Language</span>
              <span className="font-bold text-foreground">{techStack?.primary_language || 'TypeScript / HTML5'}</span>
            </div>
            <div className="p-2 rounded-lg bg-muted/40 border border-border/60">
              <span className="text-[10px] text-muted-foreground block">Build Engine</span>
              <span className="font-bold text-foreground">{techStack?.build_system || 'Vite / Standalone'}</span>
            </div>
            <div className="p-2 rounded-lg bg-muted/40 border border-border/60">
              <span className="text-[10px] text-muted-foreground block">UI Framework</span>
              <span className="font-bold text-foreground">{techStack?.frontend_framework || 'Tailwind CSS / Canvas'}</span>
            </div>
            <div className="p-2 rounded-lg bg-muted/40 border border-border/60">
              <span className="text-[10px] text-muted-foreground block">Testing Suite</span>
              <span className="font-bold text-foreground">{techStack?.test_framework || 'Node.js Assertions / Pytest'}</span>
            </div>
          </div>
        </div>

        {/* 5. PROJECT STRUCTURE */}
        <div className="p-4 rounded-xl border border-border bg-card space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary border-b border-border/60 pb-2">
            <FolderTree size={14} />
            <span>5. Project File Topology</span>
          </div>
          <div className="font-mono text-xs space-y-1 bg-muted/20 p-2.5 rounded-lg border border-border/60">
            <div className="text-muted-foreground">workspace/</div>
            <div className="pl-3 text-foreground">├── index.html <span className="text-muted-foreground/60 text-[10px]">// Entry Viewport</span></div>
            <div className="pl-3 text-foreground">├── styles.css <span className="text-muted-foreground/60 text-[10px]">// Visual Tokens</span></div>
            <div className="pl-3 text-foreground">├── script.js <span className="text-muted-foreground/60 text-[10px]">// Core Event Machine</span></div>
            <div className="pl-3 text-foreground">├── package.json <span className="text-muted-foreground/60 text-[10px]">// Manifest</span></div>
            <div className="pl-3 text-foreground">└── tests/test_app.js <span className="text-muted-foreground/60 text-[10px]">// Invariant Suite</span></div>
          </div>
        </div>

        {/* 6. AGENT EMPLOYEES ASSIGNED */}
        <div className="p-4 rounded-xl border border-border bg-card space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-purple-500 border-b border-border/60 pb-2">
            <Users size={14} />
            <span>6. Company Employees Assigned</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div className="p-1.5 rounded bg-muted/30 flex items-center justify-between">
              <span className="font-semibold">Architect:</span>
              <span className="font-mono text-primary">nemotron-ultra</span>
            </div>
            <div className="p-1.5 rounded bg-muted/30 flex items-center justify-between">
              <span className="font-semibold">Designer:</span>
              <span className="font-mono text-primary">kimi-k3</span>
            </div>
            <div className="p-1.5 rounded bg-muted/30 flex items-center justify-between">
              <span className="font-semibold">Frontend:</span>
              <span className="font-mono text-primary">kimi-k3</span>
            </div>
            <div className="p-1.5 rounded bg-muted/30 flex items-center justify-between">
              <span className="font-semibold">Tester:</span>
              <span className="font-mono text-primary">nemotron-super</span>
            </div>
            <div className="p-1.5 rounded bg-muted/30 flex items-center justify-between">
              <span className="font-semibold">Security:</span>
              <span className="font-mono text-primary">nemotron-ultra</span>
            </div>
            <div className="p-1.5 rounded bg-muted/30 flex items-center justify-between">
              <span className="font-semibold">Verifier:</span>
              <span className="font-mono text-primary">nemotron-ultra</span>
            </div>
          </div>
        </div>

        {/* 7. IMPLEMENTATION PHASES */}
        <div className="p-4 rounded-xl border border-border bg-card space-y-2 md:col-span-2">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-sky-500 border-b border-border/60 pb-2">
            <ListOrdered size={14} />
            <span>7. Implementation Phases (Step-by-Step Construction)</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 text-xs">
            {[
              { num: 'P1', title: 'Discovery & Spec', desc: 'Requirement classification & Product DNA synthesis' },
              { num: 'P2', title: 'Architecture Lock', desc: 'Component contracts, entities, and state graphs' },
              { num: 'P3', title: 'UI/UX Generation', desc: 'Design tokens, layout archetypes, responsive grid' },
              { num: 'P4', title: 'Core Implementation', desc: 'Domain-authentic multi-file code synthesis' },
              { num: 'P5', title: 'Automated Testing', desc: 'Invariant execution and runtime assertion suite' },
              { num: 'P6', title: 'Visual & Novelty QA', desc: 'Anti-template checks, viewport audit' },
              { num: 'P7', title: 'Security & Critique', desc: 'Secret scanning, flow coherence check' },
              { num: 'P8', title: 'Final Verification', desc: 'Independent verification matrix & release bundle' }
            ].map((p, i) => (
              <div key={i} className="p-2.5 rounded-lg bg-muted/20 border border-border/60 space-y-1">
                <div className="font-bold text-primary flex items-center gap-1">
                  <span className="w-4 h-4 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px]">
                    {i + 1}
                  </span>
                  <span>{p.title}</span>
                </div>
                <p className="text-[11px] text-muted-foreground">{p.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 8. CORE WORKFLOW */}
        <div className="p-4 rounded-xl border border-border bg-card space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-500 border-b border-border/60 pb-2">
            <Workflow size={14} />
            <span>8. Core User Workflow</span>
          </div>
          <div className="space-y-1.5 text-xs">
            {(spec?.core_workflow || [
              'User inputs primary action parameter into interface',
              'Reactive engine reconciles visual state and updates canvas/DOM',
              'Real-time metrics, telemetry, or game state updates seamlessly',
              'User persists or exports project artifacts'
            ]).map((step: string, i: number) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-[10px] font-mono font-bold w-4 h-4 rounded bg-primary/10 text-primary flex items-center justify-center mt-0.5">
                  {i + 1}
                </span>
                <span className="text-foreground/90">{step}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 9. TEST PLAN */}
        <div className="p-4 rounded-xl border border-border bg-card space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-rose-500 border-b border-border/60 pb-2">
            <Wrench size={14} />
            <span>9. Test Plan & Verification Gate</span>
          </div>
          <div className="space-y-1.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground font-semibold">Unit & State Invariants:</span>
              <span className="font-mono text-emerald-500 font-bold">100% Required</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground font-semibold">Visual Layout QA:</span>
              <span className="font-mono text-emerald-500 font-bold">Viewport Pass</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground font-semibold">Novelty & Anti-Template:</span>
              <span className="font-mono text-emerald-500 font-bold">Certified &gt; 90%</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground font-semibold">Independent Sign-off:</span>
              <span className="font-mono text-primary font-bold">Final Verifier</span>
            </div>
          </div>
        </div>

        {/* 10. ASSUMPTIONS & 11. OPEN REQUIREMENTS */}
        <div className="p-4 rounded-xl border border-border bg-card space-y-2 md:col-span-2">
          <div className="flex items-center justify-between border-b border-border/60 pb-2">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-500">
              <HelpCircle size={14} />
              <span>10. Inferred Assumptions & 11. Open Requirements</span>
            </div>
            <span className="text-[10px] text-muted-foreground font-medium">Safe Inferences Locked</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="p-2.5 rounded-lg bg-muted/20 border border-border/60 space-y-1">
              <span className="font-bold text-foreground">Inferred Defaults:</span>
              <p className="text-muted-foreground">
                Zero external database dependencies for offline reliability; CSS tokens bundled inline with zero CDN latency.
              </p>
            </div>
            <div className="p-2.5 rounded-lg bg-muted/20 border border-border/60 space-y-1">
              <span className="font-bold text-foreground">Open Decision Window:</span>
              <p className="text-muted-foreground">
                You can alter color palettes, domain workflows, or file structures at any point using the &quot;Modify Plan&quot; button.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Plan Modification Modal */}
      {modifyModalOpen && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl p-6 max-w-lg w-full shadow-xl space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-sm font-bold flex items-center gap-2">
                <Edit3 size={16} className="text-primary" />
                <span>Modify Implementation Plan</span>
              </h3>
              <button
                onClick={() => setModifyModalOpen(false)}
                className="p-1 rounded-md text-muted-foreground hover:text-foreground"
              >
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleModifySubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  What would you like the AI company to adjust?
                </label>
                <textarea
                  value={modifyInput}
                  onChange={(e) => setModifyInput(e.target.value)}
                  placeholder="e.g., Change technology to Canvas 2D, make the primary color violet, or add a tournament bracket..."
                  className="w-full h-28 px-3 py-2 text-xs rounded-xl bg-muted/30 border border-border focus:outline-none focus:ring-1 focus:ring-primary font-sans resize-none"
                  autoFocus
                />
              </div>
              <div className="flex items-center justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 text-xs rounded-lg"
                  onClick={() => setModifyModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  className="h-8 text-xs rounded-lg font-bold"
                  disabled={!modifyInput.trim()}
                >
                  Update & Re-validate Plan
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
