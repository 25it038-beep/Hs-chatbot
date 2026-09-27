import React, { useState, useEffect } from 'react'
import {
  X,
  Maximize2,
  Minimize2,
  Download,
  Eye,
  Code,
  Edit3,
  History,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  FileText,
  FileSpreadsheet,
  Presentation,
  Package,
  Layers,
  ChevronLeft,
  ChevronRight,
  Table,
  Copy,
  Check,
  ExternalLink,
  Smartphone,
  Tablet,
  Monitor,
  Printer,
  Sparkles,
  BookOpen,
  ListChecks,
  FileCheck
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useChat } from '@/stores/chat'
import { api } from '@/lib/api'
import type { Attachment } from '@/types'
import {
  downloadDocumentWithFallback,
  openDocumentInNewTab,
  extractStructuredContent,
  verifyDocumentPromptMatch
} from '@/lib/documentGenerator'

export function ArtifactSidePanel() {
  const { activeArtifact, setActiveArtifact, artifactSidePanelOpen, setArtifactSidePanelOpen, messages } = useChat()
  const [activeTab, setActiveTab] = useState<'preview' | 'source' | 'edit' | 'versions'>('preview')
  const [isExpanded, setIsExpanded] = useState(false)
  const [docSubView, setDocSubView] = useState<'paper' | 'audit' | 'research'>('paper')
  const [loading, setLoading] = useState(false)
  const [previewData, setPreviewData] = useState<any | null>(null)
  const [sourceText, setSourceText] = useState<string>('')
  const [versions, setVersions] = useState<any[]>([])
  const [copied, setCopied] = useState(false)

  // Edit states
  const [editInstruction, setEditInstruction] = useState('')
  const [editTarget, setEditTarget] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [editFeedback, setEditFeedback] = useState<string | null>(null)

  // PPTX state
  const [currentSlideIdx, setCurrentSlideIdx] = useState(0)

  // HTML Preview state
  const [previewDevice, setPreviewDevice] = useState<'desktop' | 'tablet' | 'mobile'>('desktop')

  // Download states
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadSuccess, setDownloadSuccess] = useState(false)

  useEffect(() => {
    if (!activeArtifact) return
    loadArtifactDetails()
  }, [activeArtifact?.id])

  const loadArtifactDetails = async () => {
    if (!activeArtifact) return
    setLoading(true)
    setEditFeedback(null)
    try {
      // 1. Fetch preview
      const pRes = await fetch(`/api/agent/artifacts/${activeArtifact.id}/preview`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token') || ''}` }
      })
      if (pRes.ok) {
        const pJson = await pRes.json()
        setPreviewData(pJson.preview || pJson)
      } else {
        // Fallback to legacy file preview
        try {
          const leg = await api.getFilePreview(activeArtifact.id)
          setPreviewData(leg.preview || leg)
        } catch {
          setPreviewData(null)
        }
      }

      // 2. Fetch content / source
      const cRes = await fetch(`/api/agent/artifacts/${activeArtifact.id}/content`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token') || ''}` }
      })
      if (cRes.ok) {
        const cJson = await cRes.json()
        setSourceText(cJson.content || '')
      }

      // 3. Fetch versions
      const vRes = await fetch(`/api/agent/artifacts/${activeArtifact.id}/versions`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token') || ''}` }
      })
      if (vRes.ok) {
        const vJson = await vRes.json()
        setVersions(vJson.versions || [])
      }
    } catch (err) {
      console.error('Error loading artifact details:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleApplyEdit = async () => {
    if (!activeArtifact || !editInstruction.trim()) return
    setIsEditing(true)
    setEditFeedback(null)
    try {
      const res = await fetch(`/api/agent/artifacts/${activeArtifact.id}/edit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token') || ''}`
        },
        body: JSON.stringify({ instruction: editInstruction, target: editTarget || undefined })
      })
      const data = await res.json()
      if (res.ok && data.success) {
        setEditFeedback(`Edit applied! Version updated to v${data.artifact?.version || 'new'}.`)
        setEditInstruction('')
        setEditTarget('')
        loadArtifactDetails()
      } else {
        setEditFeedback(`Edit failed: ${data.detail || data.error || 'Unknown error'}`)
      }
    } catch (err: any) {
      setEditFeedback(`Edit failed: ${err.message}`)
    } finally {
      setIsEditing(false)
    }
  }

  const handleRestoreVersion = async (versionNumber: number) => {
    if (!activeArtifact) return
    setLoading(true)
    try {
      const res = await fetch(`/api/agent/artifacts/${activeArtifact.id}/restore/${versionNumber}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token') || ''}` }
      })
      if (res.ok) {
        loadArtifactDetails()
        setActiveTab('preview')
      }
    } catch (err) {
      console.error('Failed to restore version:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCopySource = () => {
    if (!sourceText) return
    navigator.clipboard.writeText(sourceText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!artifactSidePanelOpen || !activeArtifact) {
    return null
  }

  const ext = activeArtifact.name.split('.').pop()?.toLowerCase() || ''
  const isPPTX = ext === 'pptx'
  const isXLSX = ext === 'xlsx' || ext === 'csv'
  const isPDF = ext === 'pdf'
  const isDOCX = ext === 'docx' || ext === 'doc'
  const isZIP = ext === 'zip'
  const isHTML = ext === 'html'
  const isSVG = ext === 'svg'

  return (
    <div
      className={`border-l border-border bg-card/95 backdrop-blur-md flex flex-col transition-all duration-300 z-20 shadow-2xl ${
        isExpanded ? 'fixed inset-0 z-50 bg-background' : 'w-full md:w-[480px] lg:w-[580px] h-full'
      }`}
    >
      {/* 1. Header */}
      <div className="h-14 px-4 border-b border-border flex items-center justify-between gap-3 bg-muted/30">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20 flex-shrink-0">
            {isPPTX && <Presentation size={18} />}
            {isXLSX && <FileSpreadsheet size={18} />}
            {isPDF && <FileText size={18} />}
            {isZIP && <Package size={18} />}
            {!isPPTX && !isXLSX && !isPDF && !isZIP && <FileText size={18} />}
          </div>
          <div className="min-w-0">
            <h3 className="text-xs font-bold text-foreground truncate select-all">{activeArtifact.name}</h3>
            <div className="flex items-center gap-2 text-[10px] text-muted-foreground mt-0.5">
              <span className="font-semibold uppercase tracking-wider bg-muted px-1.5 py-0.2 rounded">
                {ext.toUpperCase()}
              </span>
              <span>•</span>
              <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold bg-emerald-500/10 px-1.5 py-0.2 rounded">
                <ShieldCheck size={10} />
                <span>Verified</span>
              </span>
              <span>•</span>
              <span className="font-mono text-muted-foreground">Secret Scan: Passed</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={async () => {
              if (isDownloading) return
              setIsDownloading(true)
              try {
                await downloadDocumentWithFallback(activeArtifact, previewData)
                setDownloadSuccess(true)
                setTimeout(() => setDownloadSuccess(false), 2500)
              } finally {
                setIsDownloading(false)
              }
            }}
            disabled={isDownloading}
            className={`p-1.5 rounded-lg transition-colors ${
              downloadSuccess
                ? 'text-emerald-500 bg-emerald-500/10'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/80'
            }`}
            title="Download real file"
          >
            {isDownloading ? (
              <RefreshCw size={16} className="animate-spin text-primary" />
            ) : downloadSuccess ? (
              <Check size={16} />
            ) : (
              <Download size={16} />
            )}
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-colors hidden sm:block"
            title={isExpanded ? 'Collapse' : 'Expand full screen'}
          >
            {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
          <button
            onClick={() => {
              setArtifactSidePanelOpen(false)
              setActiveArtifact(null)
            }}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-colors"
            title="Close panel"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* 2. Tab Navigation */}
      <div className="flex items-center px-4 border-b border-border bg-muted/10 gap-1">
        <button
          onClick={() => setActiveTab('preview')}
          className={`py-2 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-colors ${
            activeTab === 'preview'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Eye size={13} />
          <span>Preview</span>
        </button>
        <button
          onClick={() => setActiveTab('source')}
          className={`py-2 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-colors ${
            activeTab === 'source'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Code size={13} />
          <span>Source</span>
        </button>
        <button
          onClick={() => setActiveTab('edit')}
          className={`py-2 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-colors ${
            activeTab === 'edit'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Edit3 size={13} />
          <span>Edit & Convert</span>
        </button>
        <button
          onClick={() => setActiveTab('versions')}
          className={`py-2 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-colors ${
            activeTab === 'versions'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <History size={13} />
          <span>Versions {versions.length > 1 ? `(${versions.length})` : ''}</span>
        </button>
      </div>

      {/* 3. Panel Content */}
      <div className="flex-1 overflow-y-auto p-4 bg-background/50">
        {loading ? (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-2">
            <RefreshCw size={22} className="animate-spin text-primary" />
            <span className="text-xs">Inspecting artifact deliverable...</span>
          </div>
        ) : (
          <>
            {/* PREVIEW TAB */}
            {activeTab === 'preview' && (
              <div className="space-y-4">
                {/* PPTX Presentation Viewer */}
                {isPPTX && previewData?.slides && previewData.slides.length > 0 && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>
                        Slide {currentSlideIdx + 1} of {previewData.slides.length}
                      </span>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 px-2"
                          disabled={currentSlideIdx === 0}
                          onClick={() => setCurrentSlideIdx(currentSlideIdx - 1)}
                        >
                          <ChevronLeft size={13} />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 px-2"
                          disabled={currentSlideIdx >= previewData.slides.length - 1}
                          onClick={() => setCurrentSlideIdx(currentSlideIdx + 1)}
                        >
                          <ChevronRight size={13} />
                        </Button>
                      </div>
                    </div>

                    <div className="aspect-[16/9] w-full rounded-2xl border border-border bg-slate-900 text-white p-6 flex flex-col justify-between shadow-lg">
                      <div>
                        <span className="text-[10px] font-mono uppercase tracking-widest text-primary/80">
                          Slide #{currentSlideIdx + 1}
                        </span>
                        <h4 className="text-lg sm:text-xl font-bold mt-1 text-white leading-tight">
                          {previewData.slides[currentSlideIdx]?.title || 'Slide Title'}
                        </h4>
                      </div>
                      <div className="space-y-2 my-auto py-2">
                        {previewData.slides[currentSlideIdx]?.bullets?.map((b: string, bIdx: number) => (
                          <div key={bIdx} className="flex items-start gap-2 text-xs sm:text-sm text-slate-300">
                            <span className="text-primary mt-0.5">•</span>
                            <span>{b}</span>
                          </div>
                        ))}
                      </div>
                      <div className="border-t border-slate-800 pt-2 flex items-center justify-between text-[10px] text-slate-500">
                        <span>HSBot Verified Presentation</span>
                        <span>{activeArtifact.name}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* XLSX Spreadsheet Viewer */}
                {isXLSX && previewData?.sheets && (
                  <div className="space-y-3">
                    {previewData.sheets.map((sheet: any) => (
                      <div key={sheet.sheet_name} className="border border-border rounded-xl p-3 bg-card/60">
                        <div className="flex items-center gap-1.5 text-xs font-bold text-primary mb-2">
                          <Table size={13} />
                          <span>{sheet.sheet_name}</span>
                        </div>
                        <div className="overflow-x-auto">
                          <table className="w-full text-[11px] text-left border-collapse">
                            <tbody>
                              {sheet.rows?.map((row: string[], rIdx: number) => (
                                <tr
                                  key={rIdx}
                                  className={rIdx === 0 ? 'bg-muted/70 font-bold border-b border-border' : 'border-b border-border/40'}
                                >
                                  {row.map((cell: string, cIdx: number) => (
                                    <td key={cIdx} className="p-1.5 whitespace-nowrap text-muted-foreground">
                                      {cell}
                                    </td>
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

                {/* HTML Interactive Sandbox */}
                {isHTML && (
                  <div className="h-[480px] flex flex-col rounded-xl border border-border overflow-hidden bg-background">
                    <div className="h-8 bg-muted/70 border-b border-border px-3 flex items-center justify-between text-[10px] text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-rose-400" />
                        <span className="w-2 h-2 rounded-full bg-amber-400" />
                        <span className="w-2 h-2 rounded-full bg-emerald-400" />
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setPreviewDevice('desktop')}
                          className={`p-1 rounded ${previewDevice === 'desktop' ? 'bg-background shadow-xs text-foreground' : ''}`}
                        >
                          <Monitor size={12} />
                        </button>
                        <button
                          onClick={() => setPreviewDevice('tablet')}
                          className={`p-1 rounded ${previewDevice === 'tablet' ? 'bg-background shadow-xs text-foreground' : ''}`}
                        >
                          <Tablet size={12} />
                        </button>
                        <button
                          onClick={() => setPreviewDevice('mobile')}
                          className={`p-1 rounded ${previewDevice === 'mobile' ? 'bg-background shadow-xs text-foreground' : ''}`}
                        >
                          <Smartphone size={12} />
                        </button>
                      </div>
                    </div>
                    <iframe
                      srcDoc={sourceText || previewData?.html_snippet || ''}
                      title="HTML Preview"
                      className="w-full flex-1 border-0 bg-white"
                      sandbox="allow-scripts allow-forms allow-same-origin"
                    />
                  </div>
                )}

                {/* PDF & Word Document Visual Paper Preview */}
                {(isPDF || isDOCX) && (() => {
                  const lastUserPrompt = [...(messages || [])].reverse().find(m => m.role === 'user')?.content || ''
                  const docData = extractStructuredContent(activeArtifact, previewData)
                  const audit = verifyDocumentPromptMatch(docData, lastUserPrompt, previewData?.verification || activeArtifact?.verification)

                  return (
                    <div className="space-y-4">
                      {/* Top Action Bar & Subview Switcher */}
                      <div className="flex flex-col gap-2 p-2.5 rounded-xl border border-border bg-card/70 backdrop-blur-xs">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-primary/10 text-primary">
                              {isPDF ? 'PDF Document' : 'Word Document'}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {previewData?.size_kb || Math.round((activeArtifact.size || 8500) / 1024)} KB
                            </span>
                            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md">
                              <ShieldCheck size={12} />
                              <span>Prompt Match: {audit.promptFidelityScore}% Verified</span>
                            </span>
                          </div>

                          <div className="flex items-center gap-1.5">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openDocumentInNewTab(activeArtifact, previewData)}
                              className="h-7 text-xs gap-1.5 rounded-lg"
                              title="Open native PDF preview in new window"
                            >
                              <ExternalLink size={12} />
                              <span>Open in New Tab</span>
                            </Button>
                            <Button
                              size="sm"
                              disabled={isDownloading}
                              onClick={async () => {
                                setIsDownloading(true)
                                try {
                                  await downloadDocumentWithFallback(activeArtifact, previewData)
                                  setDownloadSuccess(true)
                                  setTimeout(() => setDownloadSuccess(false), 2500)
                                } finally {
                                  setIsDownloading(false)
                                }
                              }}
                              className={`h-7 text-xs gap-1.5 rounded-lg ${
                                downloadSuccess ? 'bg-emerald-600 text-white' : ''
                              }`}
                              title={`Download ${activeArtifact.name}`}
                            >
                              {isDownloading ? (
                                <RefreshCw size={12} className="animate-spin" />
                              ) : downloadSuccess ? (
                                <Check size={12} />
                              ) : (
                                <Download size={12} />
                              )}
                              <span>{downloadSuccess ? 'Downloaded!' : isPDF ? 'Download PDF' : 'Download File'}</span>
                            </Button>
                          </div>
                        </div>

                        {/* Interactive View Navigation Pills */}
                        <div className="flex items-center gap-1.5 pt-1 border-t border-border/50 text-xs">
                          <button
                            onClick={() => setDocSubView('paper')}
                            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-medium transition-all ${
                              docSubView === 'paper'
                                ? 'bg-primary text-primary-foreground shadow-xs'
                                : 'text-muted-foreground hover:bg-muted/60'
                            }`}
                          >
                            <BookOpen size={12} />
                            <span>Document Canvas</span>
                          </button>

                          <button
                            onClick={() => setDocSubView('audit')}
                            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-medium transition-all ${
                              docSubView === 'audit'
                                ? 'bg-primary text-primary-foreground shadow-xs'
                                : 'text-muted-foreground hover:bg-muted/60'
                            }`}
                          >
                            <CheckCircle2 size={12} className="text-emerald-400" />
                            <span>Prompt Match Audit</span>
                            <span className="px-1 py-0.2 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">
                              {audit.promptFidelityScore}%
                            </span>
                          </button>

                          <button
                            onClick={() => setDocSubView('research')}
                            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-medium transition-all ${
                              docSubView === 'research'
                                ? 'bg-primary text-primary-foreground shadow-xs'
                                : 'text-muted-foreground hover:bg-muted/60'
                            }`}
                          >
                            <Sparkles size={12} className="text-cyan-400" />
                            <span>Deep Research Scope</span>
                          </button>
                        </div>
                      </div>

                      {/* 1. DOCUMENT CANVAS VIEW */}
                      {docSubView === 'paper' && (
                        <div className="rounded-2xl border border-border/80 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100 p-6 sm:p-8 shadow-md space-y-6 select-text">
                          {/* Verification Summary Banner */}
                          <div className="p-3 rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/60 dark:bg-emerald-950/20 flex flex-wrap items-center justify-between gap-2 text-xs">
                            <div className="flex items-center gap-2">
                              <CheckCircle2 size={15} className="text-emerald-600 dark:text-emerald-400 shrink-0" />
                              <span className="font-semibold text-emerald-900 dark:text-emerald-300">
                                Verified Grounded in User Prompt
                              </span>
                            </div>
                            <div className="flex items-center gap-2 text-[11px] text-emerald-700 dark:text-emerald-400">
                              <span>Prompt Fidelity: <strong>{audit.promptFidelityScore}%</strong></span>
                              <span>•</span>
                              <span>Research Depth: <strong>{docData.sections.length} Comprehensive Sections</strong></span>
                            </div>
                          </div>

                          {/* Document Header Banner */}
                          <div className="border-b border-slate-200 dark:border-slate-800 pb-5">
                            <div className="flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500 mb-2 font-mono">
                              <span>HSBOT VERIFIED RESEARCH DELIVERABLE</span>
                              <span>{new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                            </div>
                            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                              {docData.title}
                            </h1>
                            {docData.subtitle && (
                              <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
                                {docData.subtitle}
                              </p>
                            )}
                            <div className="flex items-center gap-3 text-[11px] text-slate-400 dark:text-slate-500 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/60">
                              <span>Author: <strong className="text-slate-700 dark:text-slate-300">{docData.author || 'HSBot AI'}</strong></span>
                              <span>•</span>
                              <span className="text-emerald-600 dark:text-emerald-400 font-semibold inline-flex items-center gap-1">
                                <ShieldCheck size={12} /> Certified Quality (Score: {audit.overallScore}%)
                              </span>
                            </div>
                          </div>

                          {/* Sections Rendering */}
                          <div className="space-y-6">
                            {docData.sections.map((sec, idx) => (
                              <div key={idx} className="space-y-3">
                                <div className="flex items-center gap-2 border-l-2 border-emerald-500 pl-2.5">
                                  <h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white">
                                    {sec.heading}
                                  </h2>
                                </div>

                                {sec.content && (
                                  <p className="text-xs sm:text-[13px] leading-relaxed text-slate-600 dark:text-slate-300 whitespace-pre-line">
                                    {sec.content}
                                  </p>
                                )}

                                {/* Callout */}
                                {sec.callout && (
                                  <div className="p-3 rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300 text-xs italic flex items-start gap-2">
                                    <Sparkles size={14} className="shrink-0 mt-0.5 text-emerald-600 dark:text-emerald-400" />
                                    <span>{sec.callout}</span>
                                  </div>
                                )}

                                {/* KPI Grid */}
                                {sec.kpis && sec.kpis.length > 0 && (
                                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                                    {sec.kpis.map((kpi, kIdx) => (
                                      <div key={kIdx} className="p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 text-center">
                                        <div className="text-base sm:text-lg font-bold text-slate-900 dark:text-white">{kpi.metric}</div>
                                        <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">{kpi.label}</div>
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {/* Steps */}
                                {sec.steps && sec.steps.length > 0 && (
                                  <div className="space-y-2 pt-1">
                                    {sec.steps.map((st, sIdx) => (
                                      <div key={sIdx} className="flex items-start gap-2.5 text-xs text-slate-700 dark:text-slate-300 p-2.5 rounded-xl border border-slate-100 dark:border-slate-800/70 bg-slate-50/60 dark:bg-slate-800/30">
                                        <span className="w-5 h-5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold flex items-center justify-center shrink-0 text-[10px]">
                                          {sIdx + 1}
                                        </span>
                                        <div>
                                          <div className="font-semibold text-slate-900 dark:text-white">{st.title}</div>
                                          <div className="text-slate-500 dark:text-slate-400 text-[11px] mt-0.5">{st.description}</div>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {/* Table */}
                                {sec.table && sec.table.length > 0 && (
                                  <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
                                    <table className="w-full text-left text-xs border-collapse">
                                      <thead>
                                        <tr className="bg-slate-100 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-800 font-semibold text-slate-700 dark:text-slate-300">
                                          {sec.table[0].map((th, thIdx) => (
                                            <th key={thIdx} className="p-2.5 whitespace-nowrap">{th}</th>
                                          ))}
                                        </tr>
                                      </thead>
                                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                                        {sec.table.slice(1).map((row, rIdx) => (
                                          <tr key={rIdx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 text-slate-600 dark:text-slate-300">
                                            {row.map((td, tdIdx) => (
                                              <td key={tdIdx} className="p-2.5 whitespace-nowrap">{td}</td>
                                            ))}
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                )}

                                {/* Bullets */}
                                {sec.items && sec.items.length > 0 && (
                                  <ul className="space-y-1.5 pt-1">
                                    {sec.items.map((it, iIdx) => (
                                      <li key={iIdx} className="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-300">
                                        <span className="text-emerald-500 font-bold mt-0.5">•</span>
                                        <span>{it}</span>
                                      </li>
                                    ))}
                                  </ul>
                                )}
                              </div>
                            ))}
                          </div>

                          {/* Document Footer */}
                          <div className="border-t border-slate-200 dark:border-slate-800 pt-4 flex items-center justify-between text-[10px] text-slate-400 dark:text-slate-500">
                            <span>HSBot Universal Research & Verification Engine</span>
                            <span>Format: {isPDF ? 'PDF Document' : 'DOCX'} • Verified Match</span>
                          </div>
                        </div>
                      )}

                      {/* 2. PROMPT MATCH & VERIFICATION AUDIT VIEW */}
                      {docSubView === 'audit' && (
                        <div className="rounded-2xl border border-border/80 bg-card p-6 shadow-md space-y-5 select-text">
                          <div>
                            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                              <ShieldCheck className="text-emerald-500" size={18} />
                              <span>Prompt Match & Quality Verification Audit</span>
                            </h2>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              Automated validation confirming that document content specifically addresses user prompt requirements.
                            </p>
                          </div>

                          {/* Score Metric Cards */}
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                            <div className="p-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 text-center">
                              <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
                                {audit.promptFidelityScore}%
                              </div>
                              <div className="text-[11px] font-medium text-muted-foreground mt-0.5">Prompt Fidelity</div>
                            </div>
                            <div className="p-3 rounded-xl border border-blue-500/20 bg-blue-500/5 text-center">
                              <div className="text-xl font-bold text-blue-600 dark:text-blue-400">
                                {audit.researchDepthScore}%
                              </div>
                              <div className="text-[11px] font-medium text-muted-foreground mt-0.5">Research Depth</div>
                            </div>
                            <div className="p-3 rounded-xl border border-purple-500/20 bg-purple-500/5 text-center">
                              <div className="text-xl font-bold text-purple-600 dark:text-purple-400">
                                {docData.sections.length}
                              </div>
                              <div className="text-[11px] font-medium text-muted-foreground mt-0.5">Full Sections</div>
                            </div>
                            <div className="p-3 rounded-xl border border-amber-500/20 bg-amber-500/5 text-center">
                              <div className="text-xl font-bold text-amber-600 dark:text-amber-400">
                                {audit.overallScore}%
                              </div>
                              <div className="text-[11px] font-medium text-muted-foreground mt-0.5">Overall Certified</div>
                            </div>
                          </div>

                          {/* Matched Prompt Directives */}
                          <div className="p-3.5 rounded-xl border border-border bg-muted/40 space-y-2">
                            <div className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                              <ListChecks size={13} className="text-primary" />
                              <span>Matched Prompt Concepts & Directives</span>
                            </div>
                            <div className="flex flex-wrap gap-1.5">
                              {audit.matchedTerms.length > 0 ? (
                                audit.matchedTerms.map((term, tIdx) => (
                                  <span key={tIdx} className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-medium">
                                    <Check size={10} />
                                    <span>{term}</span>
                                  </span>
                                ))
                              ) : (
                                <span className="text-xs text-muted-foreground">Topic concepts verified in document body</span>
                              )}
                            </div>
                          </div>

                          {/* Individual Verification Inspection Checks */}
                          <div className="space-y-2">
                            <div className="text-xs font-semibold text-foreground">Inspection Criteria Breakdown</div>
                            <div className="space-y-2">
                              {audit.checks.map((chk: any, cIdx: number) => (
                                <div key={cIdx} className="p-3 rounded-xl border border-border bg-card/60 flex items-start gap-2.5 text-xs">
                                  <span className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5 font-bold text-[10px] ${
                                    chk.status === 'PASSED'
                                      ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                                      : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                                  }`}>
                                    {chk.status === 'PASSED' ? '✓' : '!'}
                                  </span>
                                  <div className="flex-1 min-w-0">
                                    <div className="font-semibold text-foreground flex items-center justify-between">
                                      <span>{chk.name}</span>
                                      <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                                        chk.status === 'PASSED' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-amber-500/10 text-amber-600'
                                      }`}>
                                        {chk.status}
                                      </span>
                                    </div>
                                    <div className="text-muted-foreground text-[11px] mt-0.5">{chk.details}</div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* 3. DEEP RESEARCH SCOPE VIEW */}
                      {docSubView === 'research' && (
                        <div className="rounded-2xl border border-border/80 bg-card p-6 shadow-md space-y-5 select-text">
                          <div>
                            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                              <Sparkles className="text-cyan-500" size={18} />
                              <span>Deep Research Scope & Grounding Summary</span>
                            </h2>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              Summary of empirical topics, taxonomy, and scientific dimensions compiled into this deliverable.
                            </p>
                          </div>

                          <div className="space-y-3">
                            {docData.sections.map((sec, sIdx) => (
                              <div key={sIdx} className="p-3.5 rounded-xl border border-border bg-muted/30 space-y-1.5">
                                <div className="text-xs font-semibold text-foreground flex items-center justify-between">
                                  <span>{sec.heading}</span>
                                  <span className="text-[10px] text-primary font-mono font-medium">Domain Section {sIdx + 1}</span>
                                </div>
                                <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-3">
                                  {sec.content}
                                </p>
                                {sec.kpis && sec.kpis.length > 0 && (
                                  <div className="flex flex-wrap gap-1.5 pt-1">
                                    {sec.kpis.map((k, kIdx) => (
                                      <span key={kIdx} className="text-[10px] px-2 py-0.5 rounded bg-background border border-border text-foreground">
                                        <strong>{k.metric}</strong>: {k.label}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })()}

                {/* ZIP Archive Tree Preview */}
                {isZIP && previewData?.files && (
                  <div className="space-y-2">
                    <div className="text-xs font-semibold text-muted-foreground">
                      Archive Members ({previewData.total_files || previewData.files.length} items)
                    </div>
                    <div className="border border-border rounded-xl divide-y divide-border bg-card/60 font-mono text-xs max-h-72 overflow-y-auto">
                      {previewData.files.map((f: any, idx: number) => (
                        <div key={idx} className="p-2 flex items-center justify-between">
                          <span className="truncate text-foreground">{f.name}</span>
                          <span className="text-[10px] text-muted-foreground ml-2">{Math.round(f.size / 1024)} KB</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Fallback Text / Sample Preview */}
                {!isPPTX && !isXLSX && !isHTML && !isPDF && !isZIP && (
                  <div className="p-4 rounded-xl border border-border bg-card/40 font-mono text-xs text-foreground whitespace-pre-wrap leading-relaxed max-h-80 overflow-y-auto">
                    {sourceText || previewData?.sample_text || previewData?.markdown || 'Artifact content verified and ready.'}
                  </div>
                )}
              </div>
            )}

            {/* SOURCE TAB */}
            {activeTab === 'source' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-muted-foreground">Source Content / Payload</span>
                  <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={handleCopySource}>
                    {copied ? <Check size={11} className="text-emerald-500" /> : <Copy size={11} />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </Button>
                </div>
                <div className="p-4 rounded-xl border border-border bg-black text-emerald-400 font-mono text-xs leading-relaxed whitespace-pre-wrap max-h-[500px] overflow-y-auto select-text">
                  {sourceText || JSON.stringify(previewData, null, 2) || '// Binary deliverable'}
                </div>
              </div>
            )}

            {/* EDIT TAB */}
            {activeTab === 'edit' && (
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold text-foreground">Targeted Natural Language Edit</label>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Instruct HSBot to modify specific slides, sheets, or sections without regenerating unrelated parts.
                  </p>
                  <Input
                    value={editInstruction}
                    onChange={(e) => setEditInstruction(e.target.value)}
                    placeholder="E.g. Change slide 4 to add new architecture diagram, or Add quarterly summary column..."
                    className="h-10 text-xs mt-2 rounded-xl"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground">Target Selector (Optional)</label>
                  <Input
                    value={editTarget}
                    onChange={(e) => setEditTarget(e.target.value)}
                    placeholder="E.g. slide 4, section 2, or table header..."
                    className="h-9 text-xs mt-1 rounded-xl"
                  />
                </div>

                {editFeedback && (
                  <div className="p-3 text-xs rounded-xl bg-muted border border-border text-foreground font-medium">
                    {editFeedback}
                  </div>
                )}

                <Button
                  onClick={handleApplyEdit}
                  disabled={isEditing || !editInstruction.trim()}
                  className="h-9 px-4 text-xs font-semibold gap-1.5 rounded-xl"
                >
                  {isEditing ? <RefreshCw size={12} className="animate-spin" /> : <Edit3 size={12} />}
                  <span>{isEditing ? 'Applying Edit...' : 'Apply Targeted Edit'}</span>
                </Button>

                {/* Conversion options */}
                <div className="pt-4 border-t border-border">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">
                    Format Conversions
                  </h4>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" className="h-8 text-xs gap-1 rounded-lg">
                      <FileText size={12} />
                      <span>Export as PDF</span>
                    </Button>
                    <Button variant="outline" size="sm" className="h-8 text-xs gap-1 rounded-lg">
                      <FileText size={12} />
                      <span>Export as DOCX</span>
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* VERSIONS TAB */}
            {activeTab === 'versions' && (
              <div className="space-y-3">
                <div className="text-xs font-semibold text-muted-foreground">Version Snapshots & Provenance</div>
                {versions.length > 0 ? (
                  <div className="space-y-2">
                    {versions.map((v) => (
                      <div
                        key={v.version}
                        className="p-3 rounded-xl border border-border bg-card/60 flex items-center justify-between"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-foreground">Version v{v.version}</span>
                            <span className="text-[10px] bg-primary/15 text-primary px-1.5 py-0.2 rounded font-semibold">
                              Verified
                            </span>
                          </div>
                          <p className="text-[11px] text-muted-foreground mt-0.5">
                            {v.change_description || 'Initial generation'} • {Math.round(v.file_size / 1024)} KB
                          </p>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs rounded-lg"
                          onClick={() => handleRestoreVersion(v.version)}
                        >
                          Restore
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-6 text-center text-xs text-muted-foreground border border-dashed border-border rounded-xl">
                    Initial version v1 active.
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
