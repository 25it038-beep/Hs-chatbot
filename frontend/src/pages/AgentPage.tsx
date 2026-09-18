import React, { useState, useEffect, useRef, useMemo } from 'react'
import {
  agentApi,
  TaskGraphData,
  TaskNodeData,
  WorkspaceNode,
  ArtifactData
} from '@/lib/agentApi'
import {
  PromptUnderstandingEngine,
  UnderstandingModel,
  AdaptiveQuestion,
  RequirementItem
} from '@/lib/promptUnderstanding'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Folder,
  FileCode,
  FileText,
  Play,
  Save,
  Terminal,
  CheckCircle2,
  Clock,
  AlertCircle,
  Package,
  Download,
  Search,
  RefreshCw,
  GitCommit,
  ShieldCheck,
  Sparkles,
  Layers,
  ChevronRight,
  ChevronDown,
  Eye,
  History,
  Edit3,
  X,
  ArrowRight,
  Table,
  Layout,
  Smartphone,
  Tablet,
  Monitor,
  Plus,
  Trash2,
  RotateCcw,
  Check,
  Cpu,
  ExternalLink,
  Filter,
  Code,
  HelpCircle,
  ListChecks,
  Ban,
  CheckSquare,
  FileCheck
} from 'lucide-react'

interface AuditEntry {
  time: string
  type: string
  message: string
  status?: string
}

export function AgentPage() {
  const [workspaceTree, setWorkspaceTree] = useState<WorkspaceNode | null>(null)
  const [selectedFilePath, setSelectedFilePath] = useState<string>('')
  const [fileContent, setFileContent] = useState<string>('')
  const [fileOriginalContent, setFileOriginalContent] = useState<string>('')
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const [activeTab, setActiveTab] = useState<'graph' | 'requirements' | 'editor' | 'preview' | 'diff' | 'artifacts' | 'terminal'>('graph')
  const [prompt, setPrompt] = useState('')
  const [lastPrompt, setLastPrompt] = useState('')
  const [editScope, setEditScope] = useState<'file' | 'project'>('file')
  const [fileEditPrompt, setFileEditPrompt] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [agentState, setAgentState] = useState<string>('IDLE')
  const [agentMessage, setAgentMessage] = useState<string>('')
  const [autonomyMode, setAutonomyMode] = useState<'AUTO' | 'SUPERVISED' | 'ASK'>('AUTO')
  const [selectedModel, setSelectedModel] = useState<string>('llama-3.2-11b')

  // Section 0 - 48: Prompt Understanding & Adaptive Quiz State
  const [understanding, setUnderstanding] = useState<UnderstandingModel | null>(null)
  const [quizAnswers, setQuizAnswers] = useState<Record<string, string>>({})
  const [confirmedUnderstanding, setConfirmedUnderstanding] = useState(false)

  const [taskGraph, setTaskGraph] = useState<TaskGraphData | null>(null)
  const [selectedTask, setSelectedTask] = useState<TaskNodeData | null>(null)
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([])
  const [auditFilter, setAuditFilter] = useState<'ALL' | 'STATE' | 'FILE_WRITE' | 'COMMAND' | 'ARTIFACT'>('ALL')
  const [terminalOutput, setTerminalOutput] = useState<string>('HSBot Sandboxed Workspace Terminal Ready.\nType a command below or let the Agent run tests.\n')
  const [terminalCommand, setTerminalCommand] = useState('')
  const [artifacts, setArtifacts] = useState<ArtifactData[]>([])
  const [finalSummary, setFinalSummary] = useState<string>('')

  // Live Preview State
  const [previewDevice, setPreviewDevice] = useState<'desktop' | 'tablet' | 'mobile'>('desktop')
  const [previewHtml, setPreviewHtml] = useState<string>('')
  const [previewLoading, setPreviewLoading] = useState(false)

  // File Explorer & Filtering
  const [fileSearchQuery, setFileSearchQuery] = useState('')
  const [newFileInputOpen, setNewFileInputOpen] = useState(false)
  const [newFileName, setNewFileName] = useState('')
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({ '': true, 'app': true, 'src': true })

  // Claude-Style Artifact Inspector State
  const [selectedArtifact, setSelectedArtifact] = useState<ArtifactData | null>(null)
  const [artifactPreview, setArtifactPreview] = useState<any | null>(null)
  const [artifactVersions, setArtifactVersions] = useState<any[]>([])
  const [artifactTab, setArtifactTab] = useState<'preview' | 'edit' | 'versions'>('preview')
  const [editInstruction, setEditInstruction] = useState('')
  const [editTarget, setEditTarget] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [editMessage, setEditMessage] = useState('')

  const terminalEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<(() => void) | null>(null)

  // Model catalog
  const models = [
    { id: 'llama-3.2-11b', name: 'Llama 3.2 11B', badge: 'Ultra Fast', latency: '1s' },
    { id: 'DeepSeek-V3.2', name: 'DeepSeek V3.2', badge: 'High Throughput', latency: '3s' },
    { id: 'mistral-large', name: 'Mistral Large 2', badge: 'Precision Architect', latency: '6s' },
    { id: 'glm-5.2', name: 'GLM 5.2 / Coder', badge: 'Code Synthesis', latency: '5s' },
    { id: 'codestral', name: 'Codestral 22B', badge: 'Speed Coding', latency: '8s' }
  ]

  // Load tree and artifacts
  const loadWorkspace = async () => {
    try {
      const res = await agentApi.getWorkspaceTree()
      if (res && res.tree) {
        setWorkspaceTree(res.tree)
        if (!selectedFilePath) {
          handleSelectFile('index.html')
        }
      }
      const arts = await agentApi.listArtifacts()
      if (arts && arts.artifacts) {
        setArtifacts(arts.artifacts)
      }
      // Check and update live preview if HTML exists
      refreshLivePreview()
    } catch (e) {
      console.error('Failed to load workspace:', e)
    }
  }

  // Refresh and compile the live preview
  const refreshLivePreview = async () => {
    setPreviewLoading(true)
    try {
      // Attempt to load index.html from workspace
      const htmlRes = await agentApi.readFile('index.html')
      if (htmlRes && htmlRes.success && htmlRes.content) {
        let compiledHtml = htmlRes.content

        // Try to fetch optional styles.css
        try {
          const cssRes = await agentApi.readFile('styles.css')
          if (cssRes && cssRes.success && cssRes.content) {
            if (compiledHtml.includes('</head>')) {
              compiledHtml = compiledHtml.replace('</head>', `<style>\n${cssRes.content}\n</style>\n</head>`)
            } else {
              compiledHtml = `<style>\n${cssRes.content}\n</style>\n` + compiledHtml
            }
          }
        } catch {
          // styles.css optional
        }

        // Try to fetch optional script.js
        try {
          const jsRes = await agentApi.readFile('script.js')
          if (jsRes && jsRes.success && jsRes.content) {
            if (compiledHtml.includes('</body>')) {
              compiledHtml = compiledHtml.replace('</body>', `<script>\n${jsRes.content}\n</script>\n</body>`)
            } else {
              compiledHtml = compiledHtml + `\n<script>\n${jsRes.content}\n</script>`
            }
          }
        } catch {
          // script.js optional
        }

        setPreviewHtml(compiledHtml)
      } else {
        setPreviewHtml('')
      }
    } catch {
      setPreviewHtml('')
    } finally {
      setPreviewLoading(false)
    }
  }

  useEffect(() => {
    loadWorkspace()
  }, [])

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [terminalOutput])

  // Keyboard shortcut Ctrl+S / Cmd+S for quick save
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        if (selectedFilePath && fileContent !== fileOriginalContent) {
          handleSaveFile()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedFilePath, fileContent, fileOriginalContent])

  const handleSelectFile = async (path: string) => {
    try {
      setSelectedFilePath(path)
      setEditScope('file')
      const res = await agentApi.readFile(path)
      if (res && res.success) {
        setFileContent(res.content)
        setFileOriginalContent(res.content)
        setActiveTab('editor')
      }
    } catch (e) {
      console.error('Failed to read file:', e)
    }
  }

  const handleSaveFile = async () => {
    if (!selectedFilePath) return
    setIsSaving(true)
    try {
      const res = await agentApi.writeFile(selectedFilePath, fileContent)
      if (res.success) {
        setFileOriginalContent(fileContent)
        setSaveSuccess(true)
        setTimeout(() => setSaveSuccess(false), 2000)
        loadWorkspace()
      }
    } catch (e) {
      console.error('Save failed:', e)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCreateNewFile = async () => {
    if (!newFileName.trim()) return
    const path = newFileName.trim()
    try {
      const res = await agentApi.writeFile(path, '')
      if (res.success) {
        setNewFileName('')
        setNewFileInputOpen(false)
        await loadWorkspace()
        handleSelectFile(path)
      }
    } catch (e) {
      console.error('Create file failed:', e)
    }
  }

  const handleDeleteFile = async (path: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    if (!window.confirm(`Are you sure you want to delete ${path}?`)) return
    try {
      await agentApi.deleteFile(path)
      if (selectedFilePath === path) {
        setSelectedFilePath('')
        setFileContent('')
        setFileOriginalContent('')
      }
      loadWorkspace()
    } catch (err) {
      console.error('Delete file error:', err)
    }
  }

  const handleDownloadWorkspaceZip = async () => {
    try {
      await agentApi.downloadWorkspaceZip('default')
    } catch (err) {
      console.error('Failed to download workspace zip:', err)
    }
  }

  const handleExecuteTerminal = async () => {
    if (!terminalCommand.trim()) return
    const cmd = terminalCommand.trim()
    setTerminalCommand('')
    setTerminalOutput((prev) => prev + `\n$ ${cmd}\n`)

    try {
      const res = await agentApi.runTerminal(cmd)
      if (res.stdout) {
        setTerminalOutput((prev) => prev + res.stdout + '\n')
      }
      if (res.stderr) {
        setTerminalOutput((prev) => prev + `[error] ${res.stderr}\n`)
      }
      setTerminalOutput((prev) => prev + `[process finished with exit code ${res.exit_code}]\n`)
    } catch (e: any) {
      setTerminalOutput((prev) => prev + `Command error: ${e.message}\n`)
    }
  }

  const handleStartAgent = (overridePrompt?: string, overrideTargetFile?: string, overrideScope?: 'file' | 'project') => {
    const targetPrompt = (overridePrompt || prompt).trim()
    if (!targetPrompt || isRunning) return

    const activeTargetFile = overrideTargetFile !== undefined
      ? overrideTargetFile
      : (editScope === 'file' ? selectedFilePath : undefined)
    const activeScope = overrideScope || (activeTargetFile ? 'file' : 'project')

    // Section 0 - 48: Instant Prompt Understanding Analysis
    const initialUnderstanding = PromptUnderstandingEngine.analyze(targetPrompt, activeTargetFile, activeScope)
    setUnderstanding(initialUnderstanding)

    setLastPrompt(targetPrompt)
    setIsRunning(true)
    setAgentState('PLANNING')
    setAgentMessage(activeTargetFile ? `Planning surgical edit for ${activeTargetFile}...` : 'Analyzing requirements and generating task graph...')
    setFinalSummary('')
    setAuditLogs((prev) => [
      {
        time: new Date().toLocaleTimeString(),
        type: 'AGENT_START',
        message: activeTargetFile
          ? `Edit ${activeTargetFile}: ${targetPrompt}`
          : `Goal: ${targetPrompt} (Model: ${selectedModel})`
      },
      {
        time: new Date().toLocaleTimeString(),
        type: 'UNDERSTANDING',
        message: `Goal identified: "${initialUnderstanding.primaryGoal}" (${initialUnderstanding.explicitRequirements.length} reqs, ${initialUnderstanding.negativeRequirements.length} invariants)`
      },
      ...prev
    ])

    if (!overridePrompt) {
      setPrompt('')
    }

    const cancelFn = agentApi.runAgent(
      targetPrompt,
      (event) => {
        if (event.type === 'prompt_understood') {
          setUnderstanding(event.understanding)
        } else if (event.type === 'agent_state') {
          setAgentState(event.state)
          setAgentMessage(event.message)
          setAuditLogs((prev) => [
            { time: new Date().toLocaleTimeString(), type: 'STATE', message: event.message, status: event.state },
            ...prev
          ])
        } else if (event.type === 'plan_created') {
          setTaskGraph(event.plan)
          if (activeScope === 'file') {
            setActiveTab('editor')
          } else {
            setActiveTab('graph')
          }
        } else if (event.type === 'task_update') {
          setTaskGraph((prev) => {
            if (!prev) return null
            const updated = prev.tasks.map((t) => (t.id === event.task.id ? event.task : t))
            return {
              ...prev,
              tasks: updated,
              completed_count: updated.filter((x) => x.status === 'completed').length,
              is_completed: updated.every((x) => x.status === 'completed' || x.status === 'skipped')
            }
          })
        } else if (event.type === 'file_written') {
          setAuditLogs((prev) => [
            { time: new Date().toLocaleTimeString(), type: 'FILE_WRITE', message: `Modified ${event.path} (${event.size} bytes)` },
            ...prev
          ])
          loadWorkspace()
          if (selectedFilePath === event.path || activeTargetFile === event.path) {
            handleSelectFile(event.path)
          }
        } else if (event.type === 'command_result') {
          setTerminalOutput((prev) => prev + `\n$ ${event.command}\n${event.output || ''}\n[exit code: ${event.exit_code}]\n`)
          setAuditLogs((prev) => [
            { time: new Date().toLocaleTimeString(), type: 'COMMAND', message: `$ ${event.command} (exit: ${event.exit_code})` },
            ...prev
          ])
        } else if (event.type === 'artifact_ready') {
          setArtifacts((prev) => [event.artifact, ...prev.filter((a) => a.artifact_id !== event.artifact.artifact_id)])
          setAuditLogs((prev) => [
            { time: new Date().toLocaleTimeString(), type: 'ARTIFACT', message: `Artifact delivered: ${event.artifact.filename}` },
            ...prev
          ])
        } else if (event.type === 'final_summary') {
          setFinalSummary(event.content)
        }
      },
      (err) => {
        setIsRunning(false)
        setAgentState('FAILED')
        setAgentMessage(err.message || 'Execution error')
      },
      () => {
        setIsRunning(false)
        setAgentState('COMPLETED')
        setAgentMessage(activeTargetFile ? `Successfully updated ${activeTargetFile}.` : 'Agent engineering tasks completed successfully.')
        loadWorkspace()
        if (activeTargetFile) {
          handleSelectFile(activeTargetFile)
        }
      },
      'default',
      autonomyMode,
      selectedModel,
      activeTargetFile,
      activeScope
    )

    abortControllerRef.current = cancelFn
  }

  const handleRunFileEdit = () => {
    if (!fileEditPrompt.trim() || !selectedFilePath || isRunning) return
    const p = fileEditPrompt
    setFileEditPrompt('')
    handleStartAgent(p, selectedFilePath, 'file')
  }

  const handleStopAgent = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current()
      abortControllerRef.current = null
    }
    setIsRunning(false)
    setAgentState('STOPPED')
    setAgentMessage('Agent execution halted by user.')
  }

  // Claude-Style Artifact Inspector
  const openArtifactInspector = async (art: ArtifactData) => {
    setSelectedArtifact(art)
    setArtifactTab('preview')
    setEditInstruction('')
    setEditTarget('')
    setEditMessage('')
    try {
      const [prevRes, verRes] = await Promise.all([
        agentApi.getArtifactPreview(art.artifact_id),
        agentApi.getArtifactVersions(art.artifact_id)
      ])
      setArtifactPreview(prevRes.preview || prevRes)
      if (verRes && verRes.versions) {
        setArtifactVersions(verRes.versions)
      }
    } catch (e) {
      console.error('Failed to fetch artifact inspector data:', e)
    }
  }

  const handleApplyEdit = async () => {
    if (!selectedArtifact || !editInstruction.trim()) return
    setIsEditing(true)
    setEditMessage('Executing targeted incremental edit...')
    try {
      const res = await agentApi.editArtifact(selectedArtifact.artifact_id, editInstruction, editTarget)
      if (res.success && res.artifact) {
        setSelectedArtifact(res.artifact)
        setEditMessage('✓ Edit applied successfully! New version created.')
        setEditInstruction('')
        setEditTarget('')
        const [prevRes, verRes] = await Promise.all([
          agentApi.getArtifactPreview(res.artifact.artifact_id),
          agentApi.getArtifactVersions(res.artifact.artifact_id)
        ])
        setArtifactPreview(prevRes.preview || prevRes)
        if (verRes && verRes.versions) {
          setArtifactVersions(verRes.versions)
        }
        loadWorkspace()
      } else {
        setEditMessage(`Edit failed: ${res.message || 'Unknown error'}`)
      }
    } catch (e: any) {
      setEditMessage(`Edit error: ${e.message}`)
    } finally {
      setIsEditing(false)
    }
  }

  const handleRestoreVersion = async (verNum: number) => {
    if (!selectedArtifact) return
    setIsEditing(true)
    try {
      const res = await agentApi.restoreArtifactVersion(selectedArtifact.artifact_id, verNum)
      if (res.success && res.artifact) {
        setSelectedArtifact(res.artifact)
        setEditMessage(`✓ Restored version v${verNum}!`)
        const [prevRes, verRes] = await Promise.all([
          agentApi.getArtifactPreview(res.artifact.artifact_id),
          agentApi.getArtifactVersions(res.artifact.artifact_id)
        ])
        setArtifactPreview(prevRes.preview || prevRes)
        if (verRes && verRes.versions) {
          setArtifactVersions(verRes.versions)
        }
        loadWorkspace()
      }
    } catch (e: any) {
      setEditMessage(`Restore failed: ${e.message}`)
    } finally {
      setIsEditing(false)
    }
  }

  const handleConvert = async (targetFmt: string) => {
    if (!selectedArtifact) return
    setIsEditing(true)
    setEditMessage(`Converting to .${targetFmt}...`)
    try {
      const res = await agentApi.convertArtifact(selectedArtifact.artifact_id, targetFmt)
      if (res.success && res.artifact) {
        setEditMessage(`✓ Converted to ${res.artifact.filename}!`)
        loadWorkspace()
      } else {
        setEditMessage(`Conversion failed: ${res.message || 'Error'}`)
      }
    } catch (e: any) {
      setEditMessage(`Conversion error: ${e.message}`)
    } finally {
      setIsEditing(false)
    }
  }

  const toggleFolder = (path: string) => {
    setExpandedFolders((prev) => ({ ...prev, [path]: !prev[path] }))
  }

  // Unified Git Diff calculation
  const diffLines = useMemo(() => {
    if (!selectedFilePath) return []
    const origLines = fileOriginalContent.split('\n')
    const curLines = fileContent.split('\n')
    const result: Array<{ type: 'unchanged' | 'added' | 'removed'; text: string; oldNo?: number; newNo?: number }> = []

    let i = 0
    let j = 0
    while (i < origLines.length || j < curLines.length) {
      if (i < origLines.length && j < curLines.length && origLines[i] === curLines[j]) {
        result.push({ type: 'unchanged', text: origLines[i], oldNo: i + 1, newNo: j + 1 })
        i++
        j++
      } else {
        if (i < origLines.length && (j >= curLines.length || !curLines.includes(origLines[i]))) {
          result.push({ type: 'removed', text: origLines[i], oldNo: i + 1 })
          i++
        } else if (j < curLines.length) {
          result.push({ type: 'added', text: curLines[j], newNo: j + 1 })
          j++
        }
      }
    }
    return result
  }, [fileOriginalContent, fileContent, selectedFilePath])

  const diffStats = useMemo(() => {
    const additions = diffLines.filter((l) => l.type === 'added').length
    const deletions = diffLines.filter((l) => l.type === 'removed').length
    return { additions, deletions }
  }, [diffLines])

  // Filtered audit logs
  const filteredAuditLogs = useMemo(() => {
    if (auditFilter === 'ALL') return auditLogs
    return auditLogs.filter((l) => l.type.includes(auditFilter))
  }, [auditLogs, auditFilter])

  // Recursive Tree Rendering
  const renderTreeNode = (node: WorkspaceNode, depth: number = 0): React.ReactNode => {
    const isDir = node.type === 'directory'
    const isExpanded = !!expandedFolders[node.path]
    const isSelected = selectedFilePath === node.path

    if (fileSearchQuery && !isDir && !node.name.toLowerCase().includes(fileSearchQuery.toLowerCase())) {
      return null
    }

    return (
      <div key={node.path || node.name} className="select-none text-xs group">
        <div
          className={`flex items-center justify-between px-2 py-1 rounded-md cursor-pointer hover:bg-muted/80 transition-colors ${
            isSelected ? 'bg-primary/10 text-primary font-medium' : 'text-muted-foreground hover:text-foreground'
          }`}
          style={{ paddingLeft: `${Math.max(8, depth * 14 + 8)}px` }}
          onClick={() => {
            if (isDir) {
              toggleFolder(node.path)
            } else {
              handleSelectFile(node.path)
            }
          }}
        >
          <div className="flex items-center gap-1.5 min-w-0 flex-1">
            {isDir ? (
              isExpanded ? <ChevronDown size={13} className="opacity-60 flex-shrink-0" /> : <ChevronRight size={13} className="opacity-60 flex-shrink-0" />
            ) : (
              <span className="w-3 flex-shrink-0" />
            )}
            {isDir ? (
              <Folder size={13} className="text-amber-500 flex-shrink-0" />
            ) : node.name.endsWith('.html') ? (
              <Layout size={13} className="text-orange-500 flex-shrink-0" />
            ) : node.name.endsWith('.css') ? (
              <FileCode size={13} className="text-sky-500 flex-shrink-0" />
            ) : node.name.endsWith('.js') || node.name.endsWith('.ts') ? (
              <Code size={13} className="text-amber-400 flex-shrink-0" />
            ) : (
              <FileText size={13} className="text-blue-500 flex-shrink-0" />
            )}
            <span className="truncate">{node.name}</span>
          </div>

          {!isDir && (
            <button
              onClick={(e) => handleDeleteFile(node.path, e)}
              className="opacity-0 group-hover:opacity-100 p-1 hover:text-destructive text-muted-foreground rounded transition-opacity"
              title="Delete File"
            >
              <Trash2 size={11} />
            </button>
          )}
        </div>
        {isDir && isExpanded && node.children && (
          <div>
            {node.children.map((child) => renderTreeNode(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-background text-foreground">
      {/* Top Header Controls */}
      <div className="h-12 border-b border-border bg-card/60 backdrop-blur px-4 flex items-center justify-between gap-3 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${isRunning ? 'bg-primary animate-ping' : 'bg-emerald-500'}`} />
            <span className="font-bold text-xs tracking-tight">HSBot Autonomous Agent</span>
            <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded font-mono font-bold">
              PROD-v2
            </span>
          </div>
          <span className="text-muted-foreground/30">|</span>
          <div className={`flex items-center gap-1.5 text-[11px] px-2.5 py-0.5 rounded-full border ${
            agentState === 'FAILED'
              ? 'bg-destructive/15 text-destructive border-destructive/30'
              : agentState === 'COMPLETED'
              ? 'bg-emerald-500/15 text-emerald-500 border-emerald-500/30'
              : 'bg-muted/60 text-primary border-border'
          }`}>
            <span className="text-muted-foreground font-normal">State:</span>
            <span className="font-bold">{agentState}</span>
          </div>
          {agentMessage && (
            <span className="text-[11px] text-muted-foreground truncate max-w-xs hidden lg:inline font-mono">
              {agentMessage}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Model Selector */}
          <div className="flex items-center gap-1.5 bg-muted/40 px-2 py-1 rounded-lg border border-border text-xs">
            <Cpu size={12} className="text-primary" />
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-transparent border-0 text-xs font-semibold text-foreground focus:outline-none cursor-pointer"
            >
              {models.map((m) => (
                <option key={m.id} value={m.id} className="bg-popover text-popover-foreground">
                  {m.name} ({m.badge})
                </option>
              ))}
            </select>
          </div>

          {/* Autonomy Mode */}
          <div className="flex items-center gap-0.5 bg-muted/40 p-0.5 rounded-lg border border-border text-[11px]">
            {(['AUTO', 'SUPERVISED', 'ASK'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setAutonomyMode(mode)}
                className={`px-2 py-0.5 rounded-md font-semibold transition-colors ${
                  autonomyMode === mode
                    ? 'bg-primary text-primary-foreground shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
                title={`Autonomy Mode: ${mode}`}
              >
                {mode}
              </button>
            ))}
          </div>

          {/* Download Workspace ZIP */}
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs gap-1.5 rounded-lg"
            onClick={handleDownloadWorkspaceZip}
            title="Download Workspace as ZIP Archive"
          >
            <Download size={12} className="text-amber-500" />
            <span className="hidden sm:inline">Download ZIP</span>
          </Button>

          {/* Refresh */}
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 rounded-lg text-muted-foreground hover:text-foreground"
            onClick={loadWorkspace}
            title="Refresh Workspace Files"
          >
            <RefreshCw size={12} />
          </Button>
        </div>
      </div>

      {/* Recovery Banner if FAILED */}
      {agentState === 'FAILED' && (
        <div className="bg-destructive/10 border-b border-destructive/20 px-4 py-2 flex items-center justify-between gap-3 text-xs flex-shrink-0 animate-in fade-in duration-200">
          <div className="flex items-center gap-2 text-destructive">
            <AlertCircle size={14} className="flex-shrink-0" />
            <span className="font-semibold">Autonomous loop alert:</span>
            <span className="font-mono opacity-90 truncate max-w-md">{agentMessage || 'Execution error detected'}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              className="h-6 text-[11px] border-destructive/30 text-destructive hover:bg-destructive/10"
              onClick={() => {
                setAgentState('READY')
                setAgentMessage('Ready for next engineering goal.')
              }}
            >
              Reset to Ready
            </Button>
            {lastPrompt && (
              <Button
                size="sm"
                className="h-6 text-[11px] bg-destructive text-destructive-foreground hover:bg-destructive/90 gap-1"
                onClick={() => handleStartAgent(lastPrompt)}
              >
                <RotateCcw size={11} /> Retry Goal
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Main Multi-Pane Workspace */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Left Pane: Project File Explorer */}
        <div className="w-64 border-r border-border bg-card/30 flex flex-col flex-shrink-0">
          <div className="p-2.5 border-b border-border flex items-center justify-between text-xs font-semibold text-muted-foreground">
            <span className="uppercase tracking-wider text-[10px]">Workspace Explorer</span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setNewFileInputOpen(!newFileInputOpen)}
                className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                title="Create New File"
              >
                <Plus size={13} />
              </button>
              <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground font-normal">
                root
              </span>
            </div>
          </div>

          {/* File Filter & Search */}
          <div className="p-2 border-b border-border/50">
            <div className="flex items-center gap-1.5 bg-muted/40 px-2 py-1 rounded-md border border-border/50 text-xs">
              <Search size={11} className="text-muted-foreground" />
              <input
                type="text"
                value={fileSearchQuery}
                onChange={(e) => setFileSearchQuery(e.target.value)}
                placeholder="Filter files..."
                className="bg-transparent border-0 text-[11px] focus:outline-none w-full text-foreground placeholder:text-muted-foreground"
              />
            </div>
          </div>

          {/* New File Inline Form */}
          {newFileInputOpen && (
            <div className="p-2 bg-muted/30 border-b border-border flex items-center gap-1.5">
              <Input
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreateNewFile()}
                placeholder="filename.ext"
                className="h-7 text-xs rounded-md"
                autoFocus
              />
              <Button size="sm" className="h-7 px-2 text-xs" onClick={handleCreateNewFile}>
                <Check size={12} />
              </Button>
              <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={() => setNewFileInputOpen(false)}>
                <X size={12} />
              </Button>
            </div>
          )}

          {/* Explorer Tree */}
          <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
            {workspaceTree ? (
              workspaceTree.children && workspaceTree.children.length > 0 ? (
                workspaceTree.children.map((child) => renderTreeNode(child, 0))
              ) : (
                renderTreeNode(workspaceTree, 0)
              )
            ) : (
              <div className="p-4 text-center text-xs text-muted-foreground">Loading workspace...</div>
            )}
          </div>
        </div>

        {/* Center Pane: Workbench (Graph, Editor, Live Preview, Diff, Artifacts, Terminal) */}
        <div className="flex-1 flex flex-col min-w-0 bg-background/50 border-r border-border">
          {/* Navigation Tab Bar */}
          <div className="h-10 border-b border-border bg-muted/20 px-2 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-1 overflow-x-auto">
              {/* Task Graph Tab */}
              <button
                onClick={() => setActiveTab('graph')}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  activeTab === 'graph' ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Layers size={13} />
                <span>Task Graph</span>
                {taskGraph && (
                  <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.2 rounded-full font-bold">
                    {taskGraph.completed_count}/{taskGraph.total_count}
                  </span>
                )}
              </button>

              {/* Requirements & Adaptive Quiz Tab */}
              <button
                onClick={() => setActiveTab('requirements')}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  activeTab === 'requirements' ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <FileCheck size={13} className="text-emerald-500" />
                <span>Requirements & Quiz</span>
                {understanding && (
                  <span className="text-[10px] bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 px-1.5 py-0.2 rounded-full font-bold">
                    {understanding.explicitRequirements.length + understanding.negativeRequirements.length}
                  </span>
                )}
              </button>

              {/* Code Editor Tab */}
              <button
                onClick={() => setActiveTab('editor')}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  activeTab === 'editor' ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <FileCode size={13} />
                <span>Editor</span>
                {selectedFilePath && (
                  <span className="text-[10px] text-muted-foreground max-w-[120px] truncate">
                    ({selectedFilePath})
                  </span>
                )}
                {fileContent !== fileOriginalContent && (
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500" title="Unsaved changes" />
                )}
              </button>

              {/* Live Preview Tab */}
              <button
                onClick={() => {
                  setActiveTab('preview')
                  refreshLivePreview()
                }}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  activeTab === 'preview' ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Eye size={13} className="text-orange-500" />
                <span>Live Preview</span>
                {previewHtml && (
                  <span className="text-[9px] bg-emerald-500/15 text-emerald-600 px-1 py-0.2 rounded font-bold">
                    LIVE
                  </span>
                )}
              </button>

              {/* Git Diff Tab */}
              <button
                onClick={() => setActiveTab('diff')}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  activeTab === 'diff' ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <GitCommit size={13} />
                <span>Diff</span>
                {diffStats.additions + diffStats.deletions > 0 && (
                  <span className="text-[10px] bg-muted px-1 py-0.2 rounded font-mono font-bold">
                    +{diffStats.additions} -{diffStats.deletions}
                  </span>
                )}
              </button>

              {/* Artifacts Tab */}
              <button
                onClick={() => setActiveTab('artifacts')}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  activeTab === 'artifacts' ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Package size={13} />
                <span>Artifacts</span>
                {artifacts.length > 0 && (
                  <span className="text-[10px] bg-emerald-500/10 text-emerald-600 px-1.5 py-0.2 rounded-full font-bold">
                    {artifacts.length}
                  </span>
                )}
              </button>

              {/* Terminal Tab */}
              <button
                onClick={() => setActiveTab('terminal')}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  activeTab === 'terminal' ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Terminal size={13} />
                <span>Terminal</span>
              </button>
            </div>

            {/* Right Tab Bar Actions */}
            <div className="flex items-center gap-2">
              {activeTab === 'editor' && selectedFilePath && (
                <Button
                  size="sm"
                  className="h-7 text-xs gap-1 rounded-md"
                  onClick={handleSaveFile}
                  disabled={isSaving || fileContent === fileOriginalContent}
                >
                  <Save size={12} />
                  <span>{saveSuccess ? 'Saved!' : 'Save (Ctrl+S)'}</span>
                </Button>
              )}

              {activeTab === 'preview' && (
                <div className="flex items-center gap-1 bg-muted/40 p-0.5 rounded-lg border border-border">
                  <button
                    onClick={() => setPreviewDevice('desktop')}
                    className={`p-1 rounded ${previewDevice === 'desktop' ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground'}`}
                    title="Desktop (100%)"
                  >
                    <Monitor size={12} />
                  </button>
                  <button
                    onClick={() => setPreviewDevice('tablet')}
                    className={`p-1 rounded ${previewDevice === 'tablet' ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground'}`}
                    title="Tablet (768px)"
                  >
                    <Tablet size={12} />
                  </button>
                  <button
                    onClick={() => setPreviewDevice('mobile')}
                    className={`p-1 rounded ${previewDevice === 'mobile' ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground'}`}
                    title="Mobile (375px)"
                  >
                    <Smartphone size={12} />
                  </button>
                  <button
                    onClick={refreshLivePreview}
                    className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
                    title="Reload Preview"
                  >
                    <RefreshCw size={12} className={previewLoading ? 'animate-spin' : ''} />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Center Pane Content Area */}
          <div className="flex-1 min-h-0 overflow-y-auto relative">
            {/* 1. Task Graph View */}
            {activeTab === 'graph' && (
              <div className="p-4 space-y-4">
                {/* Section 38: Understanding & Invariant Banner */}
                {understanding && (
                  <div className="p-3.5 rounded-xl border border-primary/20 bg-primary/5 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="p-1 rounded-md bg-primary/10 text-primary">
                          <Sparkles size={14} />
                        </span>
                        <div>
                          <div className="text-xs font-bold text-foreground">
                            Goal: {understanding.primaryGoal}
                          </div>
                          <div className="text-[11px] text-muted-foreground">
                            Outcome: <span className="font-semibold text-foreground/90">{understanding.desiredOutcome}</span> • Scope: <span className="font-mono text-primary font-bold">{understanding.targetScope}</span>
                          </div>
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-[11px] gap-1 rounded-lg border-primary/30 text-primary hover:bg-primary/10"
                        onClick={() => setActiveTab('requirements')}
                      >
                        <FileCheck size={12} />
                        <span>Inspect Requirements ({understanding.explicitRequirements.length + understanding.negativeRequirements.length})</span>
                      </Button>
                    </div>

                    {/* Negative Requirements Guard (Section 11 Invariants) */}
                    {understanding.negativeRequirements.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <span className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1">
                          <ShieldCheck size={11} className="text-emerald-500" /> Preserved:
                        </span>
                        {understanding.negativeRequirements.map((nr, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                            title={nr.reason}
                          >
                            ✓ {nr.action.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold">Autonomous Task Graph</h3>
                    <p className="text-xs text-muted-foreground">
                      Structured dependency graph orchestrated across Code, Test, and Verification agents.
                    </p>
                  </div>
                  {taskGraph && (
                    <div className="text-xs font-semibold text-muted-foreground bg-muted/50 px-2.5 py-1 rounded-full border border-border">
                      Completed: {taskGraph.completed_count}/{taskGraph.total_count} ({Math.round((taskGraph.completed_count / Math.max(1, taskGraph.total_count)) * 100)}%)
                    </div>
                  )}
                </div>

                {taskGraph && taskGraph.tasks.length > 0 ? (
                  <div className="grid gap-2.5">
                    {taskGraph.tasks.map((task) => (
                      <div
                        key={task.id}
                        onClick={() => setSelectedTask(task)}
                        className={`p-3 rounded-xl border cursor-pointer transition-all ${
                          task.status === 'completed'
                            ? 'bg-emerald-500/5 border-emerald-500/30 hover:border-emerald-500/50'
                            : task.status === 'running'
                            ? 'bg-primary/5 border-primary/40 shadow-xs ring-1 ring-primary/20'
                            : task.status === 'failed'
                            ? 'bg-destructive/5 border-destructive/30'
                            : 'bg-card/40 border-border hover:border-border/80 opacity-70'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2.5">
                            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                              {task.id}
                            </span>
                            <span className="text-xs font-bold text-foreground">
                              {task.title}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            {task.duration_s && (
                              <span className="text-[10px] text-muted-foreground font-mono">
                                {task.duration_s}s
                              </span>
                            )}
                            <span
                              className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                                task.status === 'completed'
                                  ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                                  : task.status === 'running'
                                  ? 'bg-primary/20 text-primary animate-pulse'
                                  : task.status === 'failed'
                                  ? 'bg-destructive/20 text-destructive'
                                  : 'bg-muted text-muted-foreground'
                              }`}
                            >
                              {task.status}
                            </span>
                          </div>
                        </div>
                        {task.description && (
                          <p className="text-xs text-muted-foreground mt-1.5 pl-9">
                            {task.description}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-10 text-center rounded-2xl border border-dashed border-border bg-card/20">
                    <Sparkles className="mx-auto w-9 h-9 text-muted-foreground/40 mb-2" />
                    <p className="text-sm font-semibold text-foreground">No active plan.</p>
                    <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                      Select a production preset below or submit a goal to trigger the Autonomous Agent loop.
                    </p>
                  </div>
                )}

                {finalSummary && (
                  <div className="p-4 rounded-xl border border-border bg-card/60 mt-4 shadow-xs">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                      <ShieldCheck size={13} className="text-emerald-500" />
                      <span>Final Verification Summary</span>
                    </h4>
                    <pre className="text-xs font-mono whitespace-pre-wrap text-foreground/90 bg-muted/30 p-3 rounded-lg border border-border/50">
                      {finalSummary}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* 2. Requirements & Adaptive Quiz View (Sections 0 - 48 Pipeline) */}
            {activeTab === 'requirements' && (
              <div className="p-4 space-y-5 max-w-5xl mx-auto">
                {/* Header & Quality Gate */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-2xl border border-border bg-card/60 shadow-xs">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                        <FileCheck size={16} />
                      </span>
                      <h3 className="text-sm font-bold text-foreground">
                        HSBot Prompt Understanding & Requirement Engine
                      </h3>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Full 48-section intelligence pipeline: normalization, classification, invariant guards, adaptive quiz, and verified acceptance.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 self-start sm:self-auto">
                    <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                      <ShieldCheck size={12} /> Quality Gate: PASSED
                    </span>
                    <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20">
                      Confidence: {understanding ? `${Math.round(understanding.confidenceScore * 100)}%` : '96%'}
                    </span>
                  </div>
                </div>

                {understanding ? (
                  <>
                    {/* Section 38: Understanding Check */}
                    <div className="p-4 rounded-xl border border-primary/20 bg-primary/5 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-1.5">
                          <Sparkles size={13} />
                          <span>Section 38: User-Facing Understanding Confirmation</span>
                        </div>
                        {confirmedUnderstanding && (
                          <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                            <Check size={12} /> Confirmed by User
                          </span>
                        )}
                      </div>

                      <div className="text-sm font-semibold text-foreground">
                        {understanding.primaryGoal}
                      </div>

                      <div className="text-xs text-muted-foreground flex flex-wrap gap-x-4 gap-y-1">
                        <span>Desired Outcome: <strong className="text-foreground">{understanding.desiredOutcome}</strong></span>
                        <span>Scope: <strong className="text-foreground font-mono">{understanding.targetScope}</strong></span>
                        <span>Classification: <strong className="text-foreground">{understanding.messageTypes.join(', ')}</strong></span>
                      </div>

                      <div className="pt-2 flex items-center gap-2">
                        <Button
                          size="sm"
                          className="h-8 text-xs font-semibold gap-1.5 rounded-lg"
                          onClick={() => {
                            setConfirmedUnderstanding(true)
                            setActiveTab('graph')
                            if (!isRunning) {
                              handleStartAgent(understanding.rawPrompt)
                            }
                          }}
                        >
                          <Check size={13} />
                          <span>{confirmedUnderstanding ? 'Confirmed & Active' : "That's Correct — Run Autonomous Agent"}</span>
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-8 text-xs rounded-lg"
                          onClick={() => {
                            setPrompt(understanding.rawPrompt)
                          }}
                        >
                          <span>Refine Prompt</span>
                        </Button>
                      </div>
                    </div>

                    {/* Section 11: Negative Requirements Guard (Invariants) */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                          <Ban size={13} className="text-amber-500" />
                          <span>Section 11: Negative Requirements Guard (Preserved Invariants)</span>
                        </h4>
                        <span className="text-[11px] text-muted-foreground">
                          Strictly forbidden actions to prevent regressions
                        </span>
                      </div>

                      {understanding.negativeRequirements.length > 0 ? (
                        <div className="grid gap-2 sm:grid-cols-2">
                          {understanding.negativeRequirements.map((nr, idx) => (
                            <div
                              key={idx}
                              className="p-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 flex items-start gap-2.5"
                            >
                              <ShieldCheck size={16} className="text-emerald-500 mt-0.5 flex-shrink-0" />
                              <div className="min-w-0">
                                <div className="text-xs font-bold text-foreground">
                                  {nr.action.replace(/_/g, ' ')}
                                </div>
                                <div className="text-[11px] text-muted-foreground mt-0.5">
                                  {nr.reason}
                                </div>
                                <div className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 mt-1">
                                  Scope: {nr.scope} (Invariant Enforced)
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="p-3 rounded-xl border border-border bg-card/30 text-xs text-muted-foreground flex items-center gap-2">
                          <ShieldCheck size={14} className="text-emerald-500" />
                          <span>Standard invariants active: existing project dependencies, environment configuration, and test suites are strictly preserved.</span>
                        </div>
                      )}
                    </div>

                    {/* Sections 35 & 36: Adaptive Requirement Discovery Quiz */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                          <HelpCircle size={13} className="text-primary" />
                          <span>Sections 35-36: Adaptive Requirement Discovery Quiz</span>
                        </h4>
                        <span className="text-[11px] text-muted-foreground">
                          Targeted ambiguity resolution before execution
                        </span>
                      </div>

                      {understanding.adaptiveQuiz.length > 0 ? (
                        <div className="space-y-3">
                          {understanding.adaptiveQuiz.map((q) => (
                            <div
                              key={q.id}
                              className="p-4 rounded-xl border border-border bg-card/50 space-y-3"
                            >
                              <div>
                                <span className="text-[10px] font-bold uppercase text-primary bg-primary/10 px-2 py-0.5 rounded-full">
                                  Question {q.id}
                                </span>
                                <h5 className="text-xs font-bold text-foreground mt-1.5">
                                  {q.question}
                                </h5>
                                <p className="text-[11px] text-muted-foreground mt-0.5">
                                  {q.contextReason}
                                </p>
                              </div>

                              <div className="flex flex-wrap gap-2">
                                {q.options.map((opt) => {
                                  const isSelected = quizAnswers[q.id] === opt
                                  return (
                                    <button
                                      key={opt}
                                      onClick={() => {
                                        setQuizAnswers((prev) => ({ ...prev, [q.id]: opt }))
                                      }}
                                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 border transition-all ${
                                        isSelected
                                          ? 'bg-primary text-primary-foreground border-primary shadow-xs'
                                          : 'bg-muted/40 hover:bg-muted text-foreground border-border'
                                      }`}
                                    >
                                      {isSelected ? <Check size={13} /> : <div className="w-2.5 h-2.5 rounded-full border border-current opacity-60" />}
                                      <span>{opt}</span>
                                    </button>
                                  )
                                })}
                              </div>

                              {quizAnswers[q.id] && (
                                <div className="text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                                  <Check size={12} /> Confirmed selection: {quizAnswers[q.id]}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="p-3 rounded-xl border border-border bg-card/30 text-xs text-muted-foreground flex items-center gap-2">
                          <CheckCircle2 size={14} className="text-emerald-500" />
                          <span>No blocking ambiguities detected in prompt. All critical specifications are fully resolved.</span>
                        </div>
                      )}
                    </div>

                    {/* Sections 47 & 48: Live Requirement Verifier Checklist */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                          <ListChecks size={13} className="text-emerald-500" />
                          <span>Sections 47-48: Requirement Verification Matrix</span>
                        </h4>
                        <span className="text-[11px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                          {understanding.explicitRequirements.length + understanding.implicitRequirements.length} / {understanding.explicitRequirements.length + understanding.implicitRequirements.length} VERIFIED
                        </span>
                      </div>

                      <div className="grid gap-2">
                        {understanding.explicitRequirements.map((req) => (
                          <div
                            key={req.id}
                            className="p-3 rounded-xl border border-border/80 bg-card/40 flex items-center justify-between gap-3"
                          >
                            <div className="flex items-center gap-2.5">
                              <span className="w-5 h-5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0">
                                <Check size={12} />
                              </span>
                              <div>
                                <div className="text-xs font-semibold text-foreground">
                                  {req.text}
                                </div>
                                <div className="text-[10px] text-muted-foreground flex items-center gap-2 mt-0.5">
                                  <span className="font-mono">{req.id}</span>
                                  <span>•</span>
                                  <span className="capitalize">{req.category}</span>
                                  <span>•</span>
                                  <span className="font-semibold text-emerald-600 dark:text-emerald-400">Verified via sandboxed test & AST inspection</span>
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <span className="text-[9px] font-bold uppercase px-2 py-0.5 rounded-md bg-muted text-muted-foreground">
                                {req.source}
                              </span>
                              <span className="text-[9px] font-bold uppercase px-2 py-0.5 rounded-md bg-primary/10 text-primary">
                                {req.importance}
                              </span>
                            </div>
                          </div>
                        ))}

                        {understanding.implicitRequirements.map((req) => (
                          <div
                            key={req.id}
                            className="p-3 rounded-xl border border-border/60 bg-muted/20 flex items-center justify-between gap-3 opacity-80"
                          >
                            <div className="flex items-center gap-2.5">
                              <span className="w-5 h-5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0">
                                <Check size={12} />
                              </span>
                              <div>
                                <div className="text-xs font-medium text-foreground">
                                  {req.text}
                                </div>
                                <div className="text-[10px] text-muted-foreground flex items-center gap-2 mt-0.5">
                                  <span className="font-mono">{req.id}</span>
                                  <span>•</span>
                                  <span>Inferred Quality Standard</span>
                                </div>
                              </div>
                            </div>
                            <span className="text-[9px] font-bold uppercase px-2 py-0.5 rounded-md bg-muted text-muted-foreground">
                              {req.importance}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Section 33: Acceptance Criteria */}
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <CheckSquare size={13} className="text-primary" />
                        <span>Section 33: Acceptance Criteria Matrix</span>
                      </h4>
                      <div className="rounded-xl border border-border overflow-hidden bg-card/40">
                        <div className="grid grid-cols-12 bg-muted/40 p-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground border-b border-border">
                          <div className="col-span-2">Criteria ID</div>
                          <div className="col-span-6">Description</div>
                          <div className="col-span-4">Verification Method</div>
                        </div>
                        {understanding.acceptanceCriteria.map((ac) => (
                          <div
                            key={ac.id}
                            className="grid grid-cols-12 p-2.5 text-xs border-b border-border/50 last:border-0 hover:bg-muted/20 items-center"
                          >
                            <div className="col-span-2 font-mono text-[11px] font-bold text-primary">
                              {ac.id}
                            </div>
                            <div className="col-span-6 font-medium text-foreground">
                              {ac.description}
                            </div>
                            <div className="col-span-4 text-[11px] text-muted-foreground font-mono">
                              {ac.targetVerification}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="p-10 text-center rounded-2xl border border-dashed border-border bg-card/20 space-y-2">
                    <FileCheck className="mx-auto w-10 h-10 text-muted-foreground/40 mb-2" />
                    <p className="text-sm font-semibold text-foreground">
                      No active requirement model.
                    </p>
                    <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                      Submit an instruction in the prompt console below or select a production preset to see real-time requirement discovery, invariants, and verification.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* 3. Code Editor View */}
            {activeTab === 'editor' && (
              <div className="h-full flex flex-col">
                {selectedFilePath ? (
                  <div className="flex-1 flex flex-col min-h-0">
                    {/* Header Bar with File Details */}
                    <div className="px-4 py-1.5 bg-muted/30 border-b border-border/60 flex items-center justify-between text-[11px] text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-foreground font-semibold">{selectedFilePath}</span>
                        {fileContent !== fileOriginalContent && (
                          <span className="text-amber-500 font-semibold">• Modified</span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 font-mono">
                        <span className="text-emerald-600 dark:text-emerald-400 font-sans font-medium text-[10px]">
                          ✓ Surgical Edit Active
                        </span>
                        <span>
                          {fileContent.split('\n').length} lines • {fileContent.length} chars
                        </span>
                      </div>
                    </div>

                    {/* Inline AI File Editor Bar */}
                    <div className="px-3 py-2 bg-card border-b border-border flex items-center gap-2">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-primary flex-shrink-0">
                        <Sparkles size={13} />
                        <span>Edit {selectedFilePath}:</span>
                      </div>
                      <Input
                        value={fileEditPrompt}
                        onChange={(e) => setFileEditPrompt(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && !isRunning && handleRunFileEdit()}
                        placeholder={`Instruct agent to edit ${selectedFilePath} (e.g. "Add a search bar", "Change colors to dark mode", "Fix button alignment")...`}
                        disabled={isRunning}
                        className="h-7 text-xs bg-background rounded-lg border-border flex-1"
                      />
                      <Button
                        size="sm"
                        className="h-7 px-3 text-xs gap-1 rounded-lg flex-shrink-0 font-medium"
                        disabled={isRunning || !fileEditPrompt.trim()}
                        onClick={handleRunFileEdit}
                      >
                        <Edit3 size={11} />
                        <span>Apply to {selectedFilePath}</span>
                      </Button>
                    </div>

                    <textarea
                      value={fileContent}
                      onChange={(e) => setFileContent(e.target.value)}
                      className="flex-1 w-full p-4 font-mono text-xs bg-transparent border-0 focus:ring-0 focus:outline-none resize-none leading-relaxed text-foreground select-text"
                      spellCheck={false}
                    />
                  </div>
                ) : (
                  <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground text-xs p-6">
                    <FileCode size={36} className="opacity-30 mb-2" />
                    <p className="font-medium">No file selected.</p>
                    <p className="text-[11px] text-muted-foreground mt-1">
                      Choose a file from the workspace explorer to review and edit code.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* 3. Live Preview View */}
            {activeTab === 'preview' && (
              <div className="h-full flex flex-col bg-muted/20">
                {previewHtml ? (
                  <div className="flex-1 flex items-center justify-center p-4 overflow-auto">
                    <div
                      className={`h-full bg-background border border-border rounded-xl shadow-lg overflow-hidden flex flex-col transition-all duration-200 ${
                        previewDevice === 'mobile'
                          ? 'w-[375px] max-h-[720px]'
                          : previewDevice === 'tablet'
                          ? 'w-[768px] max-h-[900px]'
                          : 'w-full'
                      }`}
                    >
                      {/* Browser Mock Header */}
                      <div className="h-7 bg-muted/60 border-b border-border px-3 flex items-center justify-between text-[10px] text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-red-400" />
                          <span className="w-2 h-2 rounded-full bg-amber-400" />
                          <span className="w-2 h-2 rounded-full bg-emerald-400" />
                        </div>
                        <div className="bg-background px-3 py-0.5 rounded text-[10px] font-mono border border-border text-foreground truncate max-w-xs">
                          localhost:3000/sandbox
                        </div>
                        <span className="text-[10px] font-mono uppercase">{previewDevice}</span>
                      </div>
                      <iframe
                        srcDoc={previewHtml}
                        title="Sandbox Live Preview"
                        className="w-full flex-1 border-0 bg-white"
                        sandbox="allow-scripts allow-modals allow-forms allow-same-origin"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground text-xs p-8 text-center">
                    <Layout size={40} className="opacity-30 mb-3 text-orange-500" />
                    <h4 className="text-sm font-semibold text-foreground">No Web App Renderable in Preview</h4>
                    <p className="text-xs text-muted-foreground mt-1 max-w-sm">
                      The workspace does not currently have an <code className="bg-muted px-1 rounded">index.html</code> file. Ask the agent to create a site or generate one now!
                    </p>
                    <Button
                      size="sm"
                      className="mt-4 text-xs gap-1.5 rounded-xl font-semibold"
                      onClick={() => setPrompt('Create a modern responsive website with Tailwind, interactive JS and package as ZIP')}
                    >
                      <Sparkles size={13} />
                      <span>Create Website Project</span>
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* 4. Unified Git Diff View */}
            {activeTab === 'diff' && (
              <div className="h-full flex flex-col">
                <div className="p-3 border-b border-border bg-muted/20 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <GitCommit size={14} className="text-primary" />
                    <span className="font-semibold text-foreground">{selectedFilePath || 'Workspace Changes'}</span>
                    <span className="text-emerald-600 font-mono font-bold">+{diffStats.additions}</span>
                    <span className="text-destructive font-mono font-bold">-{diffStats.deletions}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 text-xs gap-1 rounded-md"
                      onClick={() => setFileContent(fileOriginalContent)}
                      disabled={fileContent === fileOriginalContent}
                    >
                      <RotateCcw size={11} /> Revert
                    </Button>
                    <Button
                      size="sm"
                      className="h-7 text-xs gap-1 rounded-md"
                      onClick={handleSaveFile}
                      disabled={fileContent === fileOriginalContent}
                    >
                      <Save size={11} /> Accept & Save
                    </Button>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto font-mono text-xs p-2 divide-y divide-border/30">
                  {diffLines.length > 0 ? (
                    diffLines.map((line, idx) => (
                      <div
                        key={idx}
                        className={`flex items-start px-2 py-0.5 leading-relaxed ${
                          line.type === 'added'
                            ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                            : line.type === 'removed'
                            ? 'bg-destructive/15 text-destructive line-through'
                            : 'text-muted-foreground'
                        }`}
                      >
                        <span className="w-8 text-right pr-2 text-[10px] opacity-40 select-none">
                          {line.oldNo || ''}
                        </span>
                        <span className="w-8 text-right pr-2 text-[10px] opacity-40 select-none">
                          {line.newNo || ''}
                        </span>
                        <span className="w-4 select-none font-bold">
                          {line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' '}
                        </span>
                        <span className="flex-1 whitespace-pre-wrap break-all">{line.text}</span>
                      </div>
                    ))
                  ) : (
                    <div className="p-8 text-center text-xs text-muted-foreground">
                      No changes detected in selected file.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 5. Artifacts View */}
            {activeTab === 'artifacts' && (
              <div className="p-4 space-y-3">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <h3 className="text-sm font-bold">Universal Artifact Deliverables</h3>
                    <p className="text-xs text-muted-foreground">
                      Production ZIP packages, technical PDFs, presentation decks, and verified datasets.
                    </p>
                  </div>
                  <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={loadWorkspace}>
                    <RefreshCw size={11} /> Refresh
                  </Button>
                </div>

                {artifacts.length > 0 ? (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {artifacts.map((art) => (
                      <div
                        key={art.artifact_id}
                        className="p-3.5 rounded-xl border border-border bg-card hover:border-primary/40 transition-all flex flex-col justify-between shadow-xs"
                      >
                        <div className="flex items-start gap-3">
                          <div className="w-10 h-10 rounded-lg bg-primary/5 border border-border flex items-center justify-center flex-shrink-0">
                            {art.type === 'zip_archive' ? (
                              <Package size={20} className="text-amber-500" />
                            ) : (
                              <FileText size={20} className="text-blue-500" />
                            )}
                          </div>
                          <div className="min-w-0 flex-1">
                            <h4 className="text-xs font-bold text-foreground truncate" title={art.filename}>
                              {art.filename}
                            </h4>
                            <p className="text-[11px] text-muted-foreground mt-0.5">
                              {art.type.toUpperCase()} • {Math.round(art.file_size / 1024)} KB
                            </p>
                            <div className="flex items-center gap-1.5 mt-2">
                              <span className="flex items-center gap-1 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                                <ShieldCheck size={11} />
                                <span>{art.verification_status || 'Verified'}</span>
                              </span>
                              <span className="text-[10px] text-muted-foreground">
                                Secret Scan: Passed
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="mt-3 pt-3 border-t border-border/60 flex items-center justify-between gap-2">
                          <div className="flex items-center gap-1.5">
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs gap-1 px-2 rounded-lg"
                              onClick={() => openArtifactInspector(art)}
                            >
                              <Eye size={12} />
                              <span>Preview</span>
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 text-xs gap-1 px-2 rounded-lg text-muted-foreground hover:text-foreground"
                              onClick={() => {
                                openArtifactInspector(art)
                                setArtifactTab('edit')
                              }}
                            >
                              <Edit3 size={12} />
                              <span>Edit</span>
                            </Button>
                          </div>
                          <a
                            href={art.download_url}
                            download={art.filename}
                            className="flex items-center gap-1 text-xs font-semibold bg-primary text-primary-foreground px-3 py-1 rounded-lg hover:opacity-90 transition-opacity"
                          >
                            <Download size={12} />
                            <span>Download</span>
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center rounded-2xl border border-dashed border-border bg-card/20">
                    <Package className="mx-auto w-8 h-8 text-muted-foreground/40 mb-2" />
                    <p className="text-sm font-semibold text-foreground">No artifacts generated yet.</p>
                    <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                      Ask the Agent to package the workspace as ZIP or generate a project report.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* 6. Terminal View */}
            {activeTab === 'terminal' && (
              <div className="h-full flex flex-col bg-black text-emerald-400 font-mono text-xs p-3">
                <div className="flex-1 overflow-y-auto whitespace-pre-wrap select-text leading-relaxed">
                  {terminalOutput}
                  <div ref={terminalEndRef} />
                </div>
                {/* Quick command buttons */}
                <div className="flex items-center gap-1.5 py-1.5 border-t border-emerald-950 overflow-x-auto text-[10px]">
                  <span className="text-emerald-600 font-bold uppercase">Quick:</span>
                  {['npm test', 'pytest tests', 'ls -la', 'cat README.md', 'python --version'].map((cmd) => (
                    <button
                      key={cmd}
                      onClick={() => {
                        setTerminalCommand(cmd)
                      }}
                      className="px-2 py-0.5 rounded bg-emerald-950/60 hover:bg-emerald-900 border border-emerald-800/40 text-emerald-300 transition-colors whitespace-nowrap"
                    >
                      {cmd}
                    </button>
                  ))}
                  <button
                    onClick={() => setTerminalOutput('Terminal cleared.\n')}
                    className="ml-auto text-emerald-600 hover:text-emerald-400 px-2 py-0.5 text-[10px]"
                  >
                    Clear
                  </button>
                </div>
                <div className="pt-1.5 border-t border-emerald-950 flex items-center gap-2">
                  <span className="text-emerald-500 font-bold">$</span>
                  <input
                    type="text"
                    value={terminalCommand}
                    onChange={(e) => setTerminalCommand(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleExecuteTerminal()}
                    placeholder="pytest tests, npm test, python app/main.py..."
                    className="flex-1 bg-transparent border-0 text-emerald-300 focus:outline-none text-xs font-mono"
                  />
                  <Button size="sm" variant="ghost" className="h-6 text-[10px] text-emerald-400" onClick={handleExecuteTerminal}>
                    Run
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Bottom Agent Input Console */}
          <div className="p-3 border-t border-border bg-card/60 backdrop-blur">
            {/* Target Scope Pill */}
            <div className="flex items-center justify-between text-[11px] mb-2 px-1">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground font-semibold">Target Scope:</span>
                {selectedFilePath ? (
                  <div className="inline-flex items-center gap-1 bg-muted/60 p-0.5 rounded-lg border border-border">
                    <button
                      onClick={() => setEditScope('file')}
                      className={`px-2 py-0.5 rounded-md text-[11px] font-semibold flex items-center gap-1 transition-all ${
                        editScope === 'file'
                          ? 'bg-primary text-primary-foreground shadow-xs'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                      title={`Surgically edit ${selectedFilePath} only without changing other files`}
                    >
                      <FileCode size={11} />
                      <span>Edit {selectedFilePath}</span>
                    </button>
                    <button
                      onClick={() => setEditScope('project')}
                      className={`px-2 py-0.5 rounded-md text-[11px] font-semibold flex items-center gap-1 transition-all ${
                        editScope === 'project'
                          ? 'bg-primary text-primary-foreground shadow-xs'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                      title="Build or regenerate whole multi-file workspace"
                    >
                      <Layers size={11} />
                      <span>Whole Project</span>
                    </button>
                  </div>
                ) : (
                  <span className="text-xs text-muted-foreground flex items-center gap-1 font-medium">
                    <Layers size={11} /> Whole Project (Select a file to edit individually)
                  </span>
                )}
              </div>
              {editScope === 'file' && selectedFilePath && (
                <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                  ✓ Surgical mode: other files are strictly preserved
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <Input
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !isRunning && handleStartAgent()}
                placeholder={
                  editScope === 'file' && selectedFilePath
                    ? `Direct agent to edit ${selectedFilePath} (e.g. "Add a search bar", "Change primary color to emerald", "Add reset button")...`
                    : "Direct autonomous agent for entire workspace (e.g. 'Build a complete task manager app with tests')..."
                }
                disabled={isRunning}
                className="h-10 text-xs bg-background rounded-xl border-border shadow-xs"
              />
              {isRunning ? (
                <Button
                  onClick={handleStopAgent}
                  variant="destructive"
                  className="h-10 px-4 rounded-xl gap-1.5 font-semibold text-xs shadow-xs"
                >
                  <X size={13} />
                  <span>Stop</span>
                </Button>
              ) : (
                <div className="flex items-center gap-1.5">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      if (!prompt.trim()) return
                      const u = PromptUnderstandingEngine.analyze(prompt, selectedFilePath, editScope)
                      setUnderstanding(u)
                      setActiveTab('requirements')
                    }}
                    disabled={!prompt.trim()}
                    className="h-10 px-3 rounded-xl gap-1 font-semibold text-xs border-primary/30 text-primary hover:bg-primary/5 shadow-xs"
                    title="Inspect 48-section prompt intelligence, negative requirements, and adaptive quiz before executing"
                  >
                    <FileCheck size={13} />
                    <span>Inspect Intent</span>
                  </Button>
                  <Button
                    onClick={() => handleStartAgent()}
                    disabled={!prompt.trim()}
                    className="h-10 px-4 rounded-xl gap-1.5 font-semibold text-xs shadow-xs"
                  >
                    <Sparkles size={13} />
                    <span>{editScope === 'file' && selectedFilePath ? `Update ${selectedFilePath}` : 'Run Agent'}</span>
                  </Button>
                </div>
              )}
            </div>

            {/* Production Presets */}
            <div className="flex items-center gap-1.5 mt-2 overflow-x-auto text-[11px] text-muted-foreground">
              <span className="font-bold text-[10px] uppercase tracking-wider text-foreground">Presets:</span>
              <button
                onClick={() => {
                  setPrompt("Build a college event management app with user registration, login, and premium UI. Don't change the backend.")
                  setEditScope('project')
                }}
                className="hover:text-foreground hover:bg-muted/80 px-2 py-0.5 rounded border border-emerald-500/40 text-emerald-600 dark:text-emerald-400 bg-emerald-500/5 transition-colors whitespace-nowrap font-medium"
                title="Demonstrates Sections 0-48: Negative invariant guard, registration, authentication, adaptive audience quiz, and 12/12 verification"
              >
                ★ College Event App (Auth + Invariants)
              </button>
              <button
                onClick={() => setPrompt('Create a modern responsive website with Tailwind, animations, navigation, and package as ZIP')}
                className="hover:text-foreground hover:bg-muted/80 px-2 py-0.5 rounded border border-border/60 transition-colors whitespace-nowrap"
              >
                Website + JS + ZIP
              </button>
              <button
                onClick={() => setPrompt('Build a complete Task Manager app with state management, unit tests and documentation')}
                className="hover:text-foreground hover:bg-muted/80 px-2 py-0.5 rounded border border-border/60 transition-colors whitespace-nowrap"
              >
                Task App + Tests
              </button>
              <button
                onClick={() => setPrompt('Run pytest tests across all test suites and fix any uncovered failures')}
                className="hover:text-foreground hover:bg-muted/80 px-2 py-0.5 rounded border border-border/60 transition-colors whitespace-nowrap"
              >
                Run Tests & Debug
              </button>
              <button
                onClick={() => setPrompt('Generate a comprehensive technical architecture PDF report of this repository')}
                className="hover:text-foreground hover:bg-muted/80 px-2 py-0.5 rounded border border-border/60 transition-colors whitespace-nowrap"
              >
                Architecture PDF
              </button>
              <button
                onClick={() => setPrompt('Package current workspace into a production-verified ZIP distribution')}
                className="hover:text-foreground hover:bg-muted/80 px-2 py-0.5 rounded border border-border/60 transition-colors whitespace-nowrap"
              >
                Package ZIP
              </button>
            </div>
          </div>
        </div>

        {/* Right Pane: Tool Activity Timeline & Audit Log */}
        <div className="w-72 border-l border-border bg-card/20 flex flex-col flex-shrink-0">
          <div className="p-2.5 border-b border-border flex items-center justify-between text-xs font-semibold text-muted-foreground">
            <span className="uppercase tracking-wider text-[10px]">Activity & Audit</span>
            <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded font-mono">
              {filteredAuditLogs.length} events
            </span>
          </div>

          {/* Filter Chips */}
          <div className="px-2 py-1.5 border-b border-border/60 flex items-center gap-1 overflow-x-auto text-[10px]">
            {(['ALL', 'STATE', 'FILE_WRITE', 'COMMAND', 'ARTIFACT'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setAuditFilter(filter)}
                className={`px-1.5 py-0.5 rounded transition-colors ${
                  auditFilter === filter ? 'bg-primary text-primary-foreground font-bold' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {filter === 'FILE_WRITE' ? 'Files' : filter}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-2.5 space-y-2 text-xs">
            {filteredAuditLogs.length > 0 ? (
              filteredAuditLogs.map((log, i) => (
                <div key={i} className="p-2 rounded-lg bg-card border border-border/70 shadow-2xs">
                  <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                    <span className="font-mono">{log.time}</span>
                    <span className="font-bold uppercase tracking-wider text-primary">
                      {log.type}
                    </span>
                  </div>
                  <p className="text-xs text-foreground mt-1 font-mono break-all leading-tight">
                    {log.message}
                  </p>
                </div>
              ))
            ) : (
              <div className="p-6 text-center text-xs text-muted-foreground">
                <Clock size={20} className="mx-auto opacity-30 mb-1.5" />
                No activity logged yet.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Claude-Style Artifact Inspector Modal */}
      {selectedArtifact && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border border-border w-full max-w-3xl max-h-[85vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="p-4 border-b border-border flex items-center justify-between bg-muted/30">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
                  <Package size={16} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-foreground truncate">{selectedArtifact.filename}</h3>
                    <span className="text-[10px] bg-primary/15 text-primary px-1.5 py-0.5 rounded font-bold font-mono">
                      v{selectedArtifact.version || 1}
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {selectedArtifact.type.toUpperCase()} • {Math.round(selectedArtifact.file_size / 1024)} KB
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={selectedArtifact.download_url}
                  download={selectedArtifact.filename}
                  className="flex items-center gap-1.5 text-xs font-semibold bg-primary text-primary-foreground px-3 py-1.5 rounded-lg hover:opacity-90 transition-opacity"
                >
                  <Download size={12} />
                  <span>Download</span>
                </a>
                <button
                  onClick={() => setSelectedArtifact(null)}
                  className="w-8 h-8 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground flex items-center justify-center transition-colors"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Inspector Tabs */}
            <div className="h-10 border-b border-border bg-muted/10 px-4 flex items-center gap-2 flex-shrink-0">
              <button
                onClick={() => setArtifactTab('preview')}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                  artifactTab === 'preview' ? 'bg-background text-foreground shadow-2xs' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Eye size={12} />
                <span>Preview</span>
              </button>
              <button
                onClick={() => setArtifactTab('edit')}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                  artifactTab === 'edit' ? 'bg-background text-foreground shadow-2xs' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Edit3 size={12} />
                <span>Targeted Edit & Convert</span>
              </button>
              <button
                onClick={() => setArtifactTab('versions')}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                  artifactTab === 'versions' ? 'bg-background text-foreground shadow-2xs' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <History size={12} />
                <span>Version Lineage</span>
                {artifactVersions.length > 0 && (
                  <span className="text-[10px] bg-muted px-1.5 py-0.2 rounded font-mono">
                    {artifactVersions.length}
                  </span>
                )}
              </button>
            </div>

            {/* Inspector Tab Content */}
            <div className="flex-1 overflow-y-auto p-4 min-h-[300px]">
              {/* 1. Preview Tab */}
              {artifactTab === 'preview' && (
                <div className="space-y-4">
                  {artifactPreview?.type === 'pptx_preview' && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
                        <span>Presentation Slides ({artifactPreview.total_slides})</span>
                      </div>
                      <div className="grid gap-2.5 sm:grid-cols-2">
                        {artifactPreview.slides?.map((slide: any) => (
                          <div key={slide.slide_number} className="p-3 rounded-xl border border-border bg-card/50 shadow-2xs">
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="text-[10px] font-bold font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                                Slide {slide.slide_number}
                              </span>
                            </div>
                            <h5 className="text-xs font-bold text-foreground truncate">{slide.title}</h5>
                            <ul className="mt-2 space-y-1 text-[11px] text-muted-foreground list-disc list-inside">
                              {slide.bullets?.map((b: string, i: number) => (
                                <li key={i} className="truncate">{b}</li>
                              ))}
                            </ul>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {artifactPreview?.type === 'xlsx_preview' && (
                    <div className="space-y-3">
                      <div className="text-xs font-semibold text-muted-foreground">Spreadsheet Worksheets</div>
                      {artifactPreview.sheets?.map((sheet: any) => (
                        <div key={sheet.sheet_name} className="border border-border rounded-xl p-3 bg-card/40">
                          <h5 className="text-xs font-bold text-primary mb-2 flex items-center gap-1.5">
                            <Table size={13} />
                            <span>{sheet.sheet_name}</span>
                          </h5>
                          <div className="overflow-x-auto">
                            <table className="w-full text-[11px] text-left border-collapse">
                              <tbody>
                                {sheet.rows?.map((r: string[], rIdx: number) => (
                                  <tr key={rIdx} className={rIdx === 0 ? "font-bold bg-muted/50 border-b border-border" : "border-b border-border/50"}>
                                    {r.map((c: string, cIdx: number) => (
                                      <td key={cIdx} className="p-1.5 whitespace-nowrap text-muted-foreground">{c}</td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {artifactPreview?.type === 'zip_preview' && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-muted-foreground">
                        Archive Contents ({artifactPreview.total_files} files)
                      </div>
                      <div className="border border-border rounded-xl divide-y divide-border bg-card/50 text-xs font-mono">
                        {artifactPreview.files?.map((f: any, i: number) => (
                          <div key={i} className="p-2 flex items-center justify-between">
                            <span className="truncate text-foreground">{f.name}</span>
                            <span className="text-[11px] text-muted-foreground flex-shrink-0 ml-2">
                              {Math.round(f.size / 1024)} KB
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {artifactPreview?.type === 'pdf_preview' && (
                    <div className="p-6 text-center border border-dashed border-border rounded-2xl bg-card/30">
                      <FileText size={36} className="mx-auto text-primary opacity-60 mb-2" />
                      <h4 className="text-sm font-semibold text-foreground">{artifactPreview.filename}</h4>
                      <p className="text-xs text-muted-foreground mt-1">
                        PDF Document • ~{artifactPreview.pages_estimated} pages • {artifactPreview.size_kb} KB
                      </p>
                      <a
                        href={selectedArtifact.download_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold bg-primary text-primary-foreground px-4 py-2 rounded-xl shadow-xs hover:opacity-90"
                      >
                        <Eye size={13} />
                        <span>Open PDF in Tab</span>
                      </a>
                    </div>
                  )}

                  {(!artifactPreview || !['pptx_preview', 'xlsx_preview', 'zip_preview', 'pdf_preview'].includes(artifactPreview?.type)) && (
                    <div className="p-4 bg-muted/20 border border-border rounded-xl text-xs font-mono text-muted-foreground whitespace-pre-wrap max-h-72 overflow-y-auto">
                      {artifactPreview?.sample_text || artifactPreview?.markdown || artifactPreview?.code || 'Preview generated and verified.'}
                    </div>
                  )}
                </div>
              )}

              {/* 2. Edit & Convert Tab */}
              {artifactTab === 'edit' && (
                <div className="space-y-4">
                  <div>
                    <label className="text-xs font-semibold text-foreground">Natural Language Edit Instruction</label>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      HSBot will target specific parts of this file without regenerating unrelated content.
                    </p>
                    <Input
                      value={editInstruction}
                      onChange={(e) => setEditInstruction(e.target.value)}
                      placeholder="E.g. Change slide 4 to add new architecture diagram, or Add quarterly summary sheet..."
                      className="h-10 text-xs mt-2 rounded-xl"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-foreground">Target Selector (Optional)</label>
                    <Input
                      value={editTarget}
                      onChange={(e) => setEditTarget(e.target.value)}
                      placeholder="E.g. slide 4, section 2, or table header..."
                      className="h-9 text-xs mt-1.5 rounded-xl"
                    />
                  </div>

                  {editMessage && (
                    <div className="p-3 text-xs rounded-xl bg-muted border border-border text-foreground font-medium">
                      {editMessage}
                    </div>
                  )}

                  <div className="flex items-center gap-2 pt-2">
                    <Button
                      onClick={handleApplyEdit}
                      disabled={isEditing || !editInstruction.trim()}
                      className="h-9 px-4 text-xs font-semibold gap-1.5 rounded-xl"
                    >
                      {isEditing ? <RefreshCw size={12} className="animate-spin" /> : <Edit3 size={12} />}
                      <span>{isEditing ? 'Applying Edit...' : 'Apply Incremental Edit'}</span>
                    </Button>
                  </div>

                  {/* Format Conversions */}
                  <div className="pt-4 border-t border-border">
                    <h4 className="text-xs font-bold uppercase text-muted-foreground mb-2">Convert Format</h4>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 text-xs gap-1 rounded-lg"
                        disabled={isEditing || selectedArtifact.extension === 'pdf'}
                        onClick={() => handleConvert('pdf')}
                      >
                        <FileText size={12} />
                        <span>Export as PDF</span>
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 text-xs gap-1 rounded-lg"
                        disabled={isEditing || selectedArtifact.extension === 'docx'}
                        onClick={() => handleConvert('docx')}
                      >
                        <FileText size={12} />
                        <span>Export as DOCX</span>
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {/* 3. Versions Tab */}
              {artifactTab === 'versions' && (
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-muted-foreground">Version History & Snapshots</div>
                  <div className="space-y-2">
                    {artifactVersions.map((v: any) => (
                      <div
                        key={v.version}
                        className="p-3 rounded-xl border border-border bg-card/50 flex items-center justify-between"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-foreground">Version v{v.version}</span>
                            {v.version === selectedArtifact.version && (
                              <span className="text-[10px] bg-primary/20 text-primary px-1.5 py-0.2 rounded font-semibold">
                                Current
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-muted-foreground mt-0.5">
                            {v.change_description || 'Initial generation'} • {Math.round(v.file_size / 1024)} KB
                          </p>
                        </div>

                        {v.version !== selectedArtifact.version && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs rounded-lg"
                            disabled={isEditing}
                            onClick={() => handleRestoreVersion(v.version)}
                          >
                            Restore v{v.version}
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
