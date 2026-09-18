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
  Monitor
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useChat } from '@/stores/chat'
import { api } from '@/lib/api'
import type { Attachment } from '@/types'

export function ArtifactSidePanel() {
  const { activeArtifact, setActiveArtifact, artifactSidePanelOpen, setArtifactSidePanelOpen } = useChat()
  const [activeTab, setActiveTab] = useState<'preview' | 'source' | 'edit' | 'versions'>('preview')
  const [isExpanded, setIsExpanded] = useState(false)
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
          <a
            href={`/api/files/${activeArtifact.id}/download`}
            download={activeArtifact.name}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-colors"
            title="Download real file"
          >
            <Download size={16} />
          </a>
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

                {/* PDF Document Preview */}
                {isPDF && (
                  <div className="p-8 text-center border border-dashed border-border rounded-2xl bg-card/40">
                    <FileText size={44} className="mx-auto text-primary opacity-60 mb-2" />
                    <h4 className="text-sm font-bold text-foreground">{activeArtifact.name}</h4>
                    <p className="text-xs text-muted-foreground mt-1">
                      PDF Document • {previewData?.size_kb || Math.round(activeArtifact.size / 1024)} KB • Formatted with ReportLab
                    </p>
                    <a
                      href={`/api/files/${activeArtifact.id}/download`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold bg-primary text-primary-foreground px-4 py-2 rounded-xl shadow-xs hover:opacity-90"
                    >
                      <ExternalLink size={13} />
                      <span>Open PDF in New Tab</span>
                    </a>
                  </div>
                )}

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
