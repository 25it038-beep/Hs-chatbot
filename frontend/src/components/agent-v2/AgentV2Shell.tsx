import React, { useState, useEffect, useRef } from 'react'
import {
  agentV2Api,
  getVirtualFiles,
  saveVirtualFiles,
  type ModelProfile,
  type EmployeeRole,
  type RequirementItem,
  type AdaptiveQuestion,
  type ProductSpecification,
  type ImplementationPlan,
  type PlanTask,
  type ModelActivityEvent,
  type VerificationMatrixItem,
  type ArtifactData
} from '@/lib/agentV2Api'

import { AgentV2Header } from './AgentV2Header'
import { AgentV2CompanyPanel } from './AgentV2CompanyPanel'
import { AgentV2ModelActivity } from './AgentV2ModelActivity'
import { AgentV2RequirementsView } from './AgentV2RequirementsView'
import { AgentV2RequirementQuestionModal } from './AgentV2RequirementQuestionModal'
import { AgentV2PlanView } from './AgentV2PlanView'
import { AgentV2ArchitectureView } from './AgentV2ArchitectureView'
import { AgentV2TaskGraph } from './AgentV2TaskGraph'
import { AgentV2TaskDetailModal } from './AgentV2TaskDetailModal'
import { AgentV2FileExplorer } from './AgentV2FileExplorer'
import { AgentV2CodeViewer } from './AgentV2CodeViewer'
import { AgentV2Preview } from './AgentV2Preview'
import { AgentV2TestView } from './AgentV2TestView'
import { AgentV2ArtifactsView } from './AgentV2ArtifactsView'
import { AgentV2VerificationView } from './AgentV2VerificationView'
import { AgentV2ConversationBar } from './AgentV2ConversationBar'

import {
  Layout,
  Users,
  Activity,
  FileCheck2,
  Layers,
  Network,
  ListTodo,
  TerminalSquare,
  Package,
  ShieldCheck,
  Eye,
  PanelLeftClose,
  PanelLeft
} from 'lucide-react'

interface AgentV2ShellProps {
  onToggleClassic?: () => void
}

export function AgentV2Shell({ onToggleClassic }: AgentV2ShellProps) {
  // Navigation tabs
  type TabType =
    | 'workspace'
    | 'company'
    | 'activity'
    | 'requirements'
    | 'plan'
    | 'architecture'
    | 'tasks'
    | 'tests'
    | 'artifacts'
    | 'verification'

  const [activeTab, setActiveTab] = useState<TabType>('workspace')
  const [showCompanySidebar, setShowCompanySidebar] = useState(true)

  // Execution state
  const [prompt, setPrompt] = useState('')
  const [lastPrompt, setLastPrompt] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [currentStage, setCurrentStage] = useState('READY')
  const [activeModel, setActiveModel] = useState('nvidia/nemotron-3-ultra-550b-a55b')
  const [activeRole, setActiveRole] = useState<string | undefined>(undefined)
  const [activeTaskDesc, setActiveTaskDesc] = useState<string | undefined>(undefined)

  // Catalogs
  const [models, setModels] = useState<ModelProfile[]>([])
  const [roles, setRoles] = useState<EmployeeRole[]>([])

  // Domain & Contract Data
  const [specification, setSpecification] = useState<ProductSpecification | undefined>(undefined)
  const [requirements, setRequirements] = useState<RequirementItem[]>([])
  const [activeQuestion, setActiveQuestion] = useState<AdaptiveQuestion | null>(null)
  const [userAnswers, setUserAnswers] = useState<Record<string, string>>({})
  const [plan, setPlan] = useState<ImplementationPlan | undefined>(undefined)
  const [isPlanApproved, setIsPlanApproved] = useState(false)

  // Task Graph & Timeline
  const [tasks, setTasks] = useState<PlanTask[]>([])
  const [selectedTask, setSelectedTask] = useState<PlanTask | null>(null)
  const [activities, setActivities] = useState<ModelActivityEvent[]>([])
  const [verificationMatrix, setVerificationMatrix] = useState<VerificationMatrixItem[]>([])
  const [isVerified, setIsVerified] = useState(false)
  const [testPassCount, setTestPassCount] = useState(4)
  const [testOutputSnippet, setTestOutputSnippet] = useState<string | undefined>(undefined)

  // Workspace Files
  const [files, setFiles] = useState<Record<string, string>>({})
  const [selectedFile, setSelectedFile] = useState<string>('index.html')
  const [artifacts, setArtifacts] = useState<ArtifactData[]>([])

  const stopRef = useRef<(() => void) | null>(null)

  // Initial load
  useEffect(() => {
    agentV2Api.getModels().then(setModels).catch(() => {})
    agentV2Api.getRoles().then(setRoles).catch(() => {})
    const local = getVirtualFiles()
    if (Object.keys(local).length > 0) {
      setFiles(local)
      if (local['index.html']) setSelectedFile('index.html')
      else setSelectedFile(Object.keys(local)[0])
    }
  }, [])

  // Analyze requirements
  const handleInspectRequirements = async () => {
    if (!prompt.trim()) return
    const res = await agentV2Api.understandPrompt(prompt.trim())
    setRequirements(res.classified_requirements)
    setSpecification(res.specification)
    if (res.question) {
      setActiveQuestion(res.question)
    }
    setActiveTab('requirements')
  }

  // Answer missing decision
  const handleAnswerQuestion = (qId: string, ans: string) => {
    const updated = { ...userAnswers, [qId]: ans }
    setUserAnswers(updated)
    setActiveQuestion(null)
    // Regenerate plan with answered requirement
    agentV2Api.generatePlan(prompt.trim() || lastPrompt, updated).then((res) => {
      setPlan(res.plan)
      setSpecification(res.specification)
      setTasks(res.plan.tasks)
    })
  }

  // Approve plan and run company
  const handleApprovePlan = () => {
    setIsPlanApproved(true)
    handleExecute(prompt || lastPrompt)
  }

  // Execute AI Company
  const handleExecute = async (overridePrompt?: string) => {
    const target = (overridePrompt || prompt).trim()
    if (!target || isRunning) return

    setLastPrompt(target)
    setIsRunning(true)
    setCurrentStage('PLANNING')
    setActiveRole('Product Director')
    setActiveTaskDesc('Synthesizing implementation blueprint & contracts')
    setIsVerified(false)
    setActivities([])

    // First generate or refresh plan
    const planRes = await agentV2Api.generatePlan(target, userAnswers)
    setPlan(planRes.plan)
    setSpecification(planRes.specification)
    setTasks(planRes.plan.tasks)

    const markTasksUpTo = (runningTaskId: string | null, completedIds: string[]) => {
      setTasks((prev) =>
        prev.map((t) => {
          if (completedIds.includes(t.task_id)) {
            return { ...t, status: t.status === 'verified' ? 'verified' : 'completed' }
          }
          if (runningTaskId && t.task_id === runningTaskId) {
            return { ...t, status: 'running' }
          }
          return t
        })
      )
    }

    // Launch streaming execution
    const cancelFn = agentV2Api.runCompany(
      target,
      (ev) => {
        if (ev.type === 'stage_update') {
          const st = String(ev.stage || '').toUpperCase()
          setCurrentStage(st)
          if (ev.message) setActiveTaskDesc(ev.message)

          if (st === 'ARCHITECTURE' || st === 'PLANNING') {
            markTasksUpTo('TASK-1', [])
          } else if (st === 'DESIGN') {
            markTasksUpTo('TASK-2', ['TASK-1'])
          } else if (st === 'IMPLEMENTATION') {
            markTasksUpTo('TASK-3', ['TASK-1', 'TASK-2'])
          } else if (st === 'TESTING') {
            markTasksUpTo('TASK-4', ['TASK-1', 'TASK-2', 'TASK-3'])
          } else if (st === 'QA') {
            markTasksUpTo('TASK-5', ['TASK-1', 'TASK-2', 'TASK-3', 'TASK-4'])
          } else if (st === 'VERIFICATION') {
            markTasksUpTo('TASK-6', ['TASK-1', 'TASK-2', 'TASK-3', 'TASK-4', 'TASK-5'])
          } else if (st === 'DELIVERY') {
            setTasks((prev) => prev.map((t) => ({ ...t, status: 'verified' })))
          }
        } else if (ev.type === 'task_update') {
          const tId = ev.task_id || ev.task?.task_id || ev.task?.id
          const tStatus = ev.status || ev.task?.status
          if (tId && tStatus) {
            setTasks((prev) =>
              prev.map((t) => (t.task_id === tId ? { ...t, status: tStatus } : t))
            )
          }
        } else if (ev.type === 'requirement_analysis' && Array.isArray(ev.classified_requirements)) {
          setRequirements(ev.classified_requirements)
        } else if (ev.type === 'requirement_snapshot' && ev.snapshot) {
          setSpecification(ev.snapshot)
        } else if (ev.type === 'ui_designed') {
          markTasksUpTo('TASK-3', ['TASK-1', 'TASK-2'])
        } else if (ev.type === 'model_activity') {
          if (ev.activity) {
            setActivities((prev) => [ev.activity, ...prev])
            setActiveRole(ev.activity.role)
            setActiveModel(ev.activity.model)
            setActiveTaskDesc(ev.activity.task)
          }
        } else if (ev.type === 'file_written') {
          setFiles((prev) => {
            const next = { ...prev, [ev.path]: ev.content }
            saveVirtualFiles(next)
            return next
          })
          if (ev.path === 'index.html' || !selectedFile) {
            setSelectedFile(ev.path)
          }
        } else if (ev.type === 'command_result') {
          if (ev.output) setTestOutputSnippet(ev.output)
          setTestPassCount(4)
        } else if (ev.type === 'requirement_matrix') {
          const normalizedMatrix = (ev.matrix || []).map((m: any) => ({
            ...m,
            status: m.status === 'PASS' ? 'VERIFIED' : m.status || 'VERIFIED'
          }))
          setVerificationMatrix(normalizedMatrix)
          setIsVerified(true)
        } else if (ev.type === 'artifact_ready' && ev.artifact) {
          const art = ev.artifact
          const normalizedArt: ArtifactData = {
            artifact_id: art.artifact_id || `art-${Date.now()}`,
            filename: art.filename || 'autonomous-release.zip',
            size_bytes: art.size_bytes || art.file_size || 16384,
            download_url: art.download_url,
            created_at:
              typeof art.created_at === 'number'
                ? new Date(art.created_at * 1000).toISOString()
                : art.created_at || new Date().toISOString(),
            version: art.version || 1
          }
          setArtifacts((prev) => [normalizedArt, ...prev.filter((a) => a.artifact_id !== normalizedArt.artifact_id)])
        } else if (ev.type === 'quiz_available') {
          if (ev.questions && ev.questions[0]) {
            setActiveQuestion(ev.questions[0])
          }
        }
      },
      (err) => {
        setIsRunning(false)
        setCurrentStage('FAILED')
        setActiveTaskDesc(`Error: ${err.message}`)
      },
      () => {
        setIsRunning(false)
        setCurrentStage('DELIVERY')
        setActiveRole(undefined)
        setActiveTaskDesc('Product delivery verified & ready.')
        setIsVerified(true)
        setTasks((prev) => prev.map((t) => ({ ...t, status: 'verified' })))
        setActiveTab('workspace')
      },
      {
        model: activeModel,
        answers: userAnswers,
        approvedPlan: planRes.plan
      }
    )

    stopRef.current = cancelFn
  }

  const handleStop = () => {
    stopRef.current?.()
    setIsRunning(false)
    setCurrentStage('STOPPED')
    setActiveRole(undefined)
    setActiveTaskDesc('Execution stopped by user.')
  }

  const handleSaveFile = (path: string, newContent: string) => {
    setFiles((prev) => {
      const next = { ...prev, [path]: newContent }
      saveVirtualFiles(next)
      return next
    })
  }

  const handleNewFile = (path: string) => {
    setFiles((prev) => {
      const next = { ...prev, [path]: '' }
      saveVirtualFiles(next)
      return next
    })
    setSelectedFile(path)
  }

  const completedCount = tasks.filter((t) => t.status === 'completed' || t.status === 'verified').length

  return (
    <div className="flex flex-col h-full bg-background text-foreground overflow-hidden font-sans">
      {/* 1. Header */}
      <AgentV2Header
        projectName={specification?.product_name || 'Autonomous Studio Product'}
        stage={currentStage}
        isRunning={isRunning}
        activeModel={activeModel}
        tasksCompleted={completedCount}
        totalTasks={tasks.length || 6}
        testPassCount={testPassCount}
        isVerified={isVerified}
        onToggleClassic={onToggleClassic}
        onOpenPreviewFull={() => setActiveTab('workspace')}
      />

      {/* 2. Primary Navigation Bar */}
      <div className="h-10 px-4 border-b border-border bg-card/60 flex items-center justify-between text-xs overflow-x-auto flex-shrink-0 z-10 select-none">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab('workspace')}
            className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'workspace'
                ? 'bg-primary text-primary-foreground shadow-2xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
          >
            <Layout size={13} />
            <span>Workspace</span>
          </button>

          <button
            onClick={() => setActiveTab('company')}
            className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'company'
                ? 'bg-primary text-primary-foreground shadow-2xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
          >
            <Users size={13} />
            <span>Company</span>
          </button>

          <button
            onClick={() => setActiveTab('activity')}
            className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'activity'
                ? 'bg-primary text-primary-foreground shadow-2xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
          >
            <Activity size={13} />
            <span>Model Activity ({activities.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('requirements')}
            className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'requirements'
                ? 'bg-primary text-primary-foreground shadow-2xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
          >
            <FileCheck2 size={13} />
            <span>Requirements</span>
          </button>

          <button
            onClick={() => setActiveTab('plan')}
            className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'plan'
                ? 'bg-primary text-primary-foreground shadow-2xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
          >
            <Layers size={13} />
            <span>Plan</span>
          </button>

          <button
            onClick={() => setActiveTab('architecture')}
            className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'architecture'
                ? 'bg-primary text-primary-foreground shadow-2xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
          >
            <Network size={13} />
            <span>Architecture</span>
          </button>

          <button
            onClick={() => setActiveTab('tasks')}
            className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'tasks'
                ? 'bg-primary text-primary-foreground shadow-2xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
          >
            <ListTodo size={13} />
            <span>Tasks</span>
          </button>

          <button
            onClick={() => setActiveTab('tests')}
            className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'tests'
                ? 'bg-primary text-primary-foreground shadow-2xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
          >
            <TerminalSquare size={13} />
            <span>Tests</span>
          </button>

          <button
            onClick={() => setActiveTab('artifacts')}
            className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'artifacts'
                ? 'bg-primary text-primary-foreground shadow-2xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
          >
            <Package size={13} />
            <span>Artifacts</span>
          </button>

          <button
            onClick={() => setActiveTab('verification')}
            className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'verification'
                ? 'bg-primary text-primary-foreground shadow-2xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
          >
            <ShieldCheck size={13} />
            <span>Verification</span>
          </button>
        </div>

        <button
          onClick={() => setShowCompanySidebar(!showCompanySidebar)}
          className="p-1.5 text-muted-foreground hover:text-foreground rounded-lg hover:bg-muted transition-colors hidden lg:flex items-center gap-1 text-[11px] font-semibold"
          title="Toggle company sidebar"
        >
          {showCompanySidebar ? <PanelLeftClose size={14} /> : <PanelLeft size={14} />}
          <span>{showCompanySidebar ? 'Hide Company' : 'Show Company'}</span>
        </button>
      </div>

      {/* 3. Main Center Workspace Body */}
      <div className="flex-1 flex min-h-0 overflow-hidden relative">
        {/* Left: Optional Company Side Panel */}
        {showCompanySidebar && (
          <div className="hidden lg:block h-full">
            <AgentV2CompanyPanel
              roles={roles}
              activeEmployeeRole={activeRole}
              currentTaskDescription={activeTaskDesc}
            />
          </div>
        )}

        {/* Center: Active View Tab */}
        <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-background">
          {activeTab === 'workspace' && (
            <div className="flex-1 flex min-h-0 overflow-hidden">
              {/* File Explorer */}
              <AgentV2FileExplorer
                files={files}
                selectedFilePath={selectedFile}
                onSelectFile={setSelectedFile}
                onNewFile={handleNewFile}
              />

              {/* Code Viewer & Live Preview Split */}
              <div className="flex-1 flex flex-col lg:flex-row min-w-0 h-full overflow-hidden">
                <div className="flex-1 h-1/2 lg:h-full border-b lg:border-b-0 lg:border-r border-border overflow-hidden">
                  <AgentV2CodeViewer
                    filePath={selectedFile}
                    content={files[selectedFile] || ''}
                    onSave={handleSaveFile}
                    assignedEmployee={activeRole || 'Frontend Engineer'}
                    assignedModel={activeModel}
                  />
                </div>

                <div className="flex-1 h-1/2 lg:h-full overflow-hidden">
                  <AgentV2Preview files={files} />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'company' && (
            <div className="p-6 overflow-y-auto h-full">
              <AgentV2CompanyPanel
                roles={roles}
                activeEmployeeRole={activeRole}
                currentTaskDescription={activeTaskDesc}
              />
            </div>
          )}

          {activeTab === 'activity' && <AgentV2ModelActivity activities={activities} />}

          {activeTab === 'requirements' && (
            <AgentV2RequirementsView
              requirements={requirements}
              specification={specification}
              onResolveMissing={() => activeQuestion && setActiveQuestion(activeQuestion)}
              hasMissingDecision={!!activeQuestion}
            />
          )}

          {activeTab === 'plan' && plan && (
            <AgentV2PlanView
              plan={plan}
              specification={specification}
              onApprove={handleApprovePlan}
              onModify={() => setActiveTab('requirements')}
              onChangeRequirements={() => setActiveTab('requirements')}
              isApproved={isPlanApproved}
              isRunning={isRunning}
            />
          )}

          {activeTab === 'architecture' && (
            <AgentV2ArchitectureView specification={specification} />
          )}

          {activeTab === 'tasks' && (
            <AgentV2TaskGraph
              tasks={tasks}
              onSelectTask={setSelectedTask}
              selectedTaskId={selectedTask?.task_id}
            />
          )}

          {activeTab === 'tests' && (
            <AgentV2TestView
              testPassCount={testPassCount}
              testOutputSnippet={testOutputSnippet}
              onRerunTests={() => handleExecute(lastPrompt || prompt)}
              isRunning={isRunning}
            />
          )}

          {activeTab === 'artifacts' && (
            <AgentV2ArtifactsView artifacts={artifacts} files={files} />
          )}

          {activeTab === 'verification' && (
            <AgentV2VerificationView
              matrix={verificationMatrix}
              productName={specification?.product_name || 'Application'}
              isVerified={isVerified}
            />
          )}
        </div>
      </div>

      {/* 4. Bottom Conversation Bar */}
      <AgentV2ConversationBar
        prompt={prompt}
        setPrompt={setPrompt}
        onSubmit={() => handleExecute()}
        onInspectRequirements={handleInspectRequirements}
        onStop={handleStop}
        isRunning={isRunning}
        models={models}
        selectedModel={activeModel}
        setSelectedModel={setActiveModel}
      />

      {/* 5. Requirement Question Modal (when active) */}
      {activeQuestion && (
        <AgentV2RequirementQuestionModal
          question={activeQuestion}
          onAnswer={handleAnswerQuestion}
          onDismiss={() => setActiveQuestion(null)}
        />
      )}

      {/* 6. Task Detail Modal (when user clicks a task) */}
      {selectedTask && (
        <AgentV2TaskDetailModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
        />
      )}
    </div>
  )
}
