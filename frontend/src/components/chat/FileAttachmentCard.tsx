import React, { useState } from 'react'
import {
  Download, Check, Loader2, FileText, FileSpreadsheet, Presentation,
  Eye, X, ChevronLeft, ChevronRight, Sparkles, Layers, Palette,
  CheckCircle2, ShieldCheck, AlertTriangle
} from 'lucide-react'
import type { Attachment, DocumentPreviewResponse, SlidePreview, SectionPreview } from '@/types'
import { api } from '@/lib/api'
import { useChat } from '@/stores/chat'

interface FileAttachmentCardProps {
  attachment: Attachment
}

function formatBytes(bytes: number, decimals = 1): string {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
}

function getFormatDetails(filename: string, mimeType: string) {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  if (ext === 'pdf' || mimeType.includes('pdf')) {
    return {
      label: 'PDF Document',
      color: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
      icon: FileText,
      iconColor: 'text-rose-500',
      tag: 'pdf',
    }
  }
  if (ext === 'docx' || ext === 'doc' || mimeType.includes('word')) {
    return {
      label: 'Word Document',
      color: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
      icon: FileText,
      iconColor: 'text-blue-500',
      tag: 'docx',
    }
  }
  if (ext === 'pptx' || ext === 'ppt' || mimeType.includes('presentation')) {
    return {
      label: 'PowerPoint Deck',
      color: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
      icon: Presentation,
      iconColor: 'text-amber-500',
      tag: 'pptx',
    }
  }
  if (ext === 'xlsx' || ext === 'xls' || mimeType.includes('spreadsheet') || mimeType.includes('excel')) {
    return {
      label: 'Excel Workbook',
      color: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
      icon: FileSpreadsheet,
      iconColor: 'text-emerald-500',
      tag: 'xlsx',
    }
  }
  return {
    label: ext.toUpperCase() || 'FILE',
    color: 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20',
    icon: FileText,
    iconColor: 'text-slate-500',
    tag: ext,
  }
}

export function FileAttachmentCard({ attachment }: FileAttachmentCardProps) {
  const [downloading, setDownloading] = useState(false)
  const [downloaded, setDownloaded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Preview Modal States
  const [previewOpen, setPreviewOpen] = useState(false)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [previewData, setPreviewData] = useState<DocumentPreviewResponse | null>(null)
  const [activeSlideIndex, setActiveSlideIndex] = useState(0)

  const { sendMessage } = useChat()
  const fmt = getFormatDetails(attachment.name, attachment.type)
  const Icon = fmt.icon

  const handleDownload = async (e?: React.MouseEvent) => {
    if (e) e.preventDefault()
    if (downloading) return
    setDownloading(true)
    setError(null)
    try {
      await api.downloadFile(attachment.id, attachment.name)
      setDownloaded(true)
      setTimeout(() => setDownloaded(false), 3000)
    } catch (err: any) {
      console.error('File download error:', err)
      setError('Download failed')
      const token = localStorage.getItem('access_token')
      const q = token ? `?token=${encodeURIComponent(token)}` : ''
      window.open(`/api/files/${attachment.id}/download${q}`, '_blank')
    } finally {
      setDownloading(false)
    }
  }

  const { setActiveArtifact, setArtifactSidePanelOpen } = useChat()

  const handleOpenPreview = async () => {
    // Open Claude-Style Artifact Side Panel
    if (setActiveArtifact && setArtifactSidePanelOpen) {
      setActiveArtifact(attachment)
      setArtifactSidePanelOpen(true)
    }

    setPreviewOpen(true)
    if (!previewData) {
      setLoadingPreview(true)
      try {
        const resp = await api.getFilePreview(attachment.id)
        setPreviewData(resp)
        setActiveSlideIndex(0)
      } catch (err) {
        console.error('Failed to load preview:', err)
      } finally {
        setLoadingPreview(false)
      }
    }
  }

  const handleRedesign = (prompt: string) => {
    setPreviewOpen(false)
    sendMessage(prompt)
  }

  const slides = previewData?.preview?.slides || []
  const activeSlide: SlidePreview | undefined = slides[activeSlideIndex]
  const isDarkPalette = previewData?.preview?.is_dark || false
  const palette = previewData?.preview?.palette

  return (
    <>
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 my-2.5 rounded-xl border border-border bg-card/85 shadow-sm max-w-xl transition-all hover:border-primary/40 hover:shadow-md">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <div className={`p-2.5 rounded-lg border flex items-center justify-center shrink-0 ${fmt.color}`}>
            <Icon size={22} className={fmt.iconColor} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-[13px] sm:text-sm font-medium text-foreground truncate block select-all">
                {attachment.name}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
              <span className="font-semibold uppercase text-[10px] tracking-wider px-1.5 py-0.5 rounded bg-muted/60">
                {fmt.label}
              </span>
              {attachment.size > 0 && <span>• {formatBytes(attachment.size)}</span>}
              {attachment.verification?.passed ? (
                <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold bg-emerald-500/10 px-1.5 py-0.5 rounded text-[10px]">
                  <ShieldCheck size={11} />
                  <span>Verified ({attachment.verification.overall_score}%)</span>
                </span>
              ) : (
                <span className="text-emerald-600 dark:text-emerald-400 font-medium">• Professional Design</span>
              )}
              {error && <span className="text-destructive">• {error}</span>}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto">
          {/* Preview Button */}
          <button
            onClick={handleOpenPreview}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-border bg-muted/50 hover:bg-muted text-foreground transition-all shrink-0 active:scale-95"
            title="Inspect slide & document preview"
          >
            <Eye size={13} className="text-muted-foreground" />
            <span>Preview</span>
          </button>

          {/* Download Button */}
          <button
            onClick={handleDownload}
            disabled={downloading}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all shrink-0 justify-center ${
              downloaded
                ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/30'
                : 'bg-primary text-primary-foreground hover:opacity-90 shadow-sm active:scale-95'
            }`}
            title={`Download ${attachment.name}`}
          >
            {downloading ? (
              <>
                <Loader2 size={13} className="animate-spin" />
                <span>Downloading...</span>
              </>
            ) : downloaded ? (
              <>
                <Check size={13} />
                <span>Downloaded</span>
              </>
            ) : (
              <>
                <Download size={13} />
                <span>Download</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Interactive Preview Modal */}
      {previewOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-card border border-border w-full max-w-4xl rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-border bg-muted/20">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className={`p-1.5 rounded-md border ${fmt.color}`}>
                  <Icon size={16} className={fmt.iconColor} />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-foreground truncate">
                    {previewData?.filename || attachment.name}
                  </h3>
                  <p className="text-[11px] text-muted-foreground flex items-center gap-2">
                    <span>{fmt.label}</span>
                    {previewData?.design_spec?.palette_name && (
                      <span className="capitalize">• Theme: {previewData.design_spec.palette_name.replace('_', ' ')}</span>
                    )}
                    {previewData?.design_spec?.template && (
                      <span className="capitalize">• Template: {previewData.design_spec.template}</span>
                    )}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleDownload()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-primary text-primary-foreground hover:opacity-90 transition-all shadow-sm"
                >
                  <Download size={13} />
                  <span>Download File</span>
                </button>
                <button
                  onClick={() => setPreviewOpen(false)}
                  className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {/* Quality Verification Badge & Report Banner */}
              {previewData?.verification && (
                <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-500/5 flex flex-col gap-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ShieldCheck size={16} className="text-emerald-500" />
                      <span className="text-xs font-semibold text-foreground">
                        Quality Verification: {previewData.verification.overall_score}%
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-medium">
                        {previewData.verification.passed ? 'PASSED' : 'COMPLETED'}
                      </span>
                    </div>
                    <span className="text-[11px] text-muted-foreground">
                      {previewData.verification.checks.filter(c => c.status === 'PASSED').length} of {previewData.verification.checks.length} checks verified
                    </span>
                  </div>

                  {previewData.verification.verified_checklist?.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1">
                      {previewData.verification.verified_checklist.map((item, i) => (
                        <div key={i} className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                          <CheckCircle2 size={12} className="text-emerald-500 shrink-0" />
                          <span className="truncate">{item}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {loadingPreview ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3 text-muted-foreground">
                  <Loader2 size={24} className="animate-spin text-primary" />
                  <span className="text-xs">Loading presentation and document preview...</span>
                </div>
              ) : fmt.tag === 'pptx' && slides.length > 0 ? (
                /* Presentation Slide Previewer */
                <div className="space-y-4">
                  {/* Slide Canvas Simulator (16:9) */}
                  <div
                    className={`aspect-video w-full rounded-xl border p-6 sm:p-8 flex flex-col justify-between shadow-inner relative overflow-hidden transition-all ${
                      isDarkPalette ? 'bg-[#0B1020] text-slate-100 border-slate-800' : 'bg-slate-50 text-slate-900 border-slate-200'
                    }`}
                    style={{
                      borderColor: palette?.border || undefined,
                      backgroundColor: palette?.background || undefined,
                      color: palette?.text || undefined,
                    }}
                  >
                    {/* Top Slide Accent Bar */}
                    <div
                      className="absolute top-0 left-0 right-0 h-1.5"
                      style={{ backgroundColor: palette?.accent || '#2563EB' }}
                    />

                    {/* Slide Header */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span
                          className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                          style={{
                            backgroundColor: palette?.accent ? `${palette.accent}20` : '#2563EB20',
                            color: palette?.accent || '#2563EB',
                          }}
                        >
                          Slide 0{activeSlideIndex + 1} • {activeSlide?.layout || 'Standard'}
                        </span>
                        <span className="text-[10px] opacity-60 font-mono">16:9 Widescreen</span>
                      </div>
                      <h4 className="text-xl sm:text-2xl font-bold tracking-tight line-clamp-2">
                        {activeSlide?.title}
                      </h4>
                    </div>

                    {/* Slide Dynamic Content Simulation */}
                    <div className="my-auto py-3">
                      {activeSlide?.layout === 'kpis' && activeSlide.kpis ? (
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                          {activeSlide.kpis.map((k, kIdx) => (
                            <div
                              key={kIdx}
                              className="p-3 rounded-lg border text-center"
                              style={{
                                backgroundColor: palette?.card_bg || '#FFFFFF',
                                borderColor: palette?.border || '#E2E8F0',
                              }}
                            >
                              <div className="text-2xl sm:text-3xl font-extrabold" style={{ color: palette?.accent || '#2563EB' }}>
                                {k.metric}
                              </div>
                              <div className="text-xs font-semibold mt-1">{k.label}</div>
                            </div>
                          ))}
                        </div>
                      ) : activeSlide?.layout === 'process_workflow' && activeSlide.steps ? (
                        <div className="flex items-center gap-2 overflow-x-auto py-2">
                          {activeSlide.steps.map((st, sIdx) => (
                            <React.Fragment key={sIdx}>
                              <div
                                className="flex-1 min-w-[120px] p-3 rounded-lg border"
                                style={{
                                  backgroundColor: palette?.card_bg || '#FFFFFF',
                                  borderColor: palette?.border || '#E2E8F0',
                                }}
                              >
                                <div
                                  className="w-5 h-5 rounded-full text-white text-[10px] font-bold flex items-center justify-center mb-1.5"
                                  style={{ backgroundColor: palette?.accent || '#2563EB' }}
                                >
                                  {sIdx + 1}
                                </div>
                                <div className="text-xs font-bold truncate">{st.title}</div>
                                {st.description && <div className="text-[10px] opacity-75 truncate">{st.description}</div>}
                              </div>
                              {activeSlide.steps && sIdx < activeSlide.steps.length - 1 && (
                                <span className="text-muted-foreground font-bold shrink-0">→</span>
                              )}
                            </React.Fragment>
                          ))}
                        </div>
                      ) : activeSlide?.cards && activeSlide.cards.length > 0 ? (
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          {activeSlide.cards.map((c, cIdx) => (
                            <div
                              key={cIdx}
                              className="p-3 rounded-lg border"
                              style={{
                                backgroundColor: palette?.card_bg || '#FFFFFF',
                                borderColor: palette?.border || '#E2E8F0',
                              }}
                            >
                              <div className="text-xs font-bold mb-1.5" style={{ color: palette?.accent || '#2563EB' }}>
                                {c.title}
                              </div>
                              {c.points?.map((pt, ptIdx) => (
                                <div key={ptIdx} className="text-[11px] opacity-80 leading-relaxed">• {pt}</div>
                              ))}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="space-y-2 max-w-xl">
                          {(activeSlide?.preview_points || ['Professional strategic insights.']).map((pt, pIdx) => (
                            <div key={pIdx} className="flex items-start gap-2 text-xs sm:text-sm leading-relaxed">
                              <span style={{ color: palette?.accent || '#2563EB' }}>•</span>
                              <span>{pt}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Slide Footer */}
                    <div className="flex items-center justify-between text-[10px] opacity-50 pt-2 border-t border-border/40">
                      <span>HSBot Document & Presentation Engine</span>
                      <span>Page {activeSlideIndex + 1} of {slides.length}</span>
                    </div>
                  </div>

                  {/* Slide Navigation Pagination */}
                  <div className="flex items-center justify-between gap-2 pt-2">
                    <button
                      onClick={() => setActiveSlideIndex(Math.max(0, activeSlideIndex - 1))}
                      disabled={activeSlideIndex === 0}
                      className="p-1.5 rounded-lg border border-border hover:bg-muted disabled:opacity-30 transition-all text-xs flex items-center gap-1"
                    >
                      <ChevronLeft size={14} />
                      <span>Prev</span>
                    </button>

                    <div className="flex items-center gap-1.5 flex-wrap justify-center">
                      {slides.map((s, idx) => (
                        <button
                          key={idx}
                          onClick={() => setActiveSlideIndex(idx)}
                          className={`w-7 h-7 rounded-lg text-xs font-semibold transition-all ${
                            activeSlideIndex === idx
                              ? 'bg-primary text-primary-foreground shadow-sm'
                              : 'bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground'
                          }`}
                        >
                          {String(idx + 1).padStart(2, '0')}
                        </button>
                      ))}
                    </div>

                    <button
                      onClick={() => setActiveSlideIndex(Math.min(slides.length - 1, activeSlideIndex + 1))}
                      disabled={activeSlideIndex === slides.length - 1}
                      className="p-1.5 rounded-lg border border-border hover:bg-muted disabled:opacity-30 transition-all text-xs flex items-center gap-1"
                    >
                      <span>Next</span>
                      <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              ) : fmt.tag in {'pdf': 1, 'docx': 1} ? (
                /* PDF / DOCX Previewer */
                <div className="space-y-3">
                  <div className="p-4 rounded-xl border border-border bg-muted/20 flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-bold text-foreground">Document Outline</h4>
                      <p className="text-xs text-muted-foreground">
                        Includes Executive Cover Page, Table of Contents, Callout Boxes & Styled Headers.
                      </p>
                    </div>
                    <span className="text-xs font-semibold px-2 py-1 rounded bg-muted">
                      {previewData?.preview?.sections?.length || 3} Sections
                    </span>
                  </div>

                  <div className="space-y-2">
                    {(previewData?.preview?.sections || []).map((sec: SectionPreview, idx: number) => (
                      <div key={idx} className="p-3.5 rounded-lg border border-border bg-card hover:border-primary/30 transition-all">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-xs font-bold text-primary flex items-center gap-1.5">
                            <span className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px]">
                              {idx + 1}
                            </span>
                            {sec.heading}
                          </span>
                          <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                            {sec.has_kpis && <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600">KPIs</span>}
                            {sec.has_callout && <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600">Callout</span>}
                            {sec.has_table && <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-600">Table</span>}
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                          {sec.preview_text}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                /* Excel / Spreadsheet Preview */
                <div className="space-y-3">
                  <div className="p-3.5 rounded-xl border border-border bg-muted/20">
                    <h4 className="text-sm font-bold text-foreground">Workbook Structure</h4>
                    <p className="text-xs text-muted-foreground">
                      Structured with KPI summary banner, themed primary header, and auto-adjusted columns.
                    </p>
                  </div>
                  {previewData?.preview?.sheets?.map((sh, sIdx) => (
                    <div key={sIdx} className="border border-border rounded-lg overflow-hidden">
                      <div className="bg-muted px-3 py-1.5 text-xs font-semibold text-foreground flex items-center justify-between">
                        <span>Sheet: {sh.sheet_name}</span>
                        <span className="text-[11px] text-muted-foreground">{sh.row_count} rows</span>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-primary/10 text-primary text-[11px] font-bold">
                            <tr>
                              {sh.headers.map((h, hIdx) => (
                                <th key={hIdx} className="px-3 py-2 border-b border-border">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {sh.sample_rows.map((r, rIdx) => (
                              <tr key={rIdx} className={rIdx % 2 === 0 ? 'bg-card' : 'bg-muted/30'}>
                                {r.map((c, cIdx) => (
                                  <td key={cIdx} className="px-3 py-1.5 border-b border-border/50 text-[11px] text-muted-foreground">
                                    {c}
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

              {/* Redesign & Style Controls */}
              <div className="pt-3 border-t border-border">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground mb-2">
                  <Sparkles size={13} className="text-primary" />
                  <span>One-Click AI Redesign:</span>
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                  <button
                    onClick={() => handleRedesign('make it dark theme')}
                    className="px-2.5 py-1 rounded-full text-[11px] font-medium border border-border bg-muted/50 hover:bg-muted text-foreground transition-all active:scale-95"
                  >
                    🌙 Dark Theme
                  </button>
                  <button
                    onClick={() => handleRedesign('use corporate blue')}
                    className="px-2.5 py-1 rounded-full text-[11px] font-medium border border-border bg-muted/50 hover:bg-muted text-foreground transition-all active:scale-95"
                  >
                    💼 Executive Blue
                  </button>
                  <button
                    onClick={() => handleRedesign('make it minimal monochrome')}
                    className="px-2.5 py-1 rounded-full text-[11px] font-medium border border-border bg-muted/50 hover:bg-muted text-foreground transition-all active:scale-95"
                  >
                    ⚪ Minimal Monochrome
                  </button>
                  <button
                    onClick={() => handleRedesign('use emerald theme')}
                    className="px-2.5 py-1 rounded-full text-[11px] font-medium border border-border bg-muted/50 hover:bg-muted text-foreground transition-all active:scale-95"
                  >
                    🌿 Emerald Intelligence
                  </button>
                  <button
                    onClick={() => handleRedesign('make it more visual with diagrams')}
                    className="px-2.5 py-1 rounded-full text-[11px] font-medium border border-border bg-muted/50 hover:bg-muted text-foreground transition-all active:scale-95"
                  >
                    📊 More Diagrams
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
