import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText, Code, Table, Image as ImageIcon, Archive, Music, File,
  X, Copy, Check, Sparkles, Send, FileCode, Layers, Info, Hash,
  Database, AlignLeft
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { formatBytes } from '@/lib/downloader'
import { ParsedFileMetadata, getFileCategoryBadgeStyle } from '@/lib/fileEngine'

interface FileEngineModalProps {
  fileMeta: ParsedFileMetadata | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onApplyPrompt?: (prompt: string) => void
}

export function FileEngineModal({
  fileMeta,
  open,
  onOpenChange,
  onApplyPrompt,
}: FileEngineModalProps) {
  const [activeTab, setActiveTab] = useState<'preview' | 'metadata' | 'actions'>('preview')
  const [copied, setCopied] = useState(false)

  if (!fileMeta) return null

  const badge = getFileCategoryBadgeStyle(fileMeta.category)

  const handleCopyText = () => {
    if (fileMeta.previewText) {
      navigator.clipboard.writeText(fileMeta.previewText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleSelectPrompt = (prompt: string) => {
    onApplyPrompt?.(prompt)
    onOpenChange(false)
  }

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4">
          <motion.div
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => onOpenChange(false)}
          />

          <motion.div
            className="relative w-full max-w-2xl max-h-[85vh] rounded-2xl border border-border bg-card shadow-2xl flex flex-col overflow-hidden z-10"
            initial={{ opacity: 0, scale: 0.95, y: 15 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 15 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            role="dialog"
            aria-label="File Engine Inspector"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-border/80 bg-muted/20">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary flex-shrink-0">
                  {fileMeta.category === 'code' ? (
                    <Code size={20} />
                  ) : fileMeta.category === 'data' ? (
                    <Table size={20} />
                  ) : fileMeta.category === 'image' ? (
                    <ImageIcon size={20} />
                  ) : (
                    <FileText size={20} />
                  )}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-semibold text-foreground truncate max-w-xs sm:max-w-md">
                      {fileMeta.name}
                    </h3>
                    <span className={`text-[10px] font-semibold border px-2 py-0.5 rounded-full ${badge.badgeClass}`}>
                      {fileMeta.language || badge.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                    <span>{formatBytes(fileMeta.size)}</span>
                    {fileMeta.lineCount && <span>• {fileMeta.lineCount} lines</span>}
                    {fileMeta.estimatedTokens && <span>• ~{fileMeta.estimatedTokens} tokens</span>}
                  </div>
                </div>
              </div>

              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground"
                onClick={() => onOpenChange(false)}
              >
                <X size={16} />
              </Button>
            </div>

            {/* Navigation Tabs */}
            <div className="flex items-center gap-2 px-5 py-2 border-b border-border/60 bg-muted/10 text-xs">
              <button
                onClick={() => setActiveTab('preview')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                  activeTab === 'preview'
                    ? 'bg-background text-foreground shadow-xs font-semibold'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Content Preview
              </button>
              <button
                onClick={() => setActiveTab('metadata')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                  activeTab === 'metadata'
                    ? 'bg-background text-foreground shadow-xs font-semibold'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                File Metrics
              </button>
              <button
                onClick={() => setActiveTab('actions')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
                  activeTab === 'actions'
                    ? 'bg-background text-foreground shadow-xs font-semibold'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Sparkles size={12} className="text-brand" />
                <span>AI Prompt Engine</span>
              </button>
            </div>

            {/* Tab Body */}
            <div className="flex-1 overflow-y-auto p-5">
              {activeTab === 'preview' && (
                <div className="space-y-4">
                  {fileMeta.category === 'image' && fileMeta.imagePreviewUrl && (
                    <div className="flex flex-col items-center justify-center p-4 bg-muted/30 rounded-xl border border-border">
                      <img
                        src={fileMeta.imagePreviewUrl}
                        alt={fileMeta.name}
                        className="max-h-[380px] w-auto object-contain rounded-lg shadow-md"
                      />
                    </div>
                  )}

                  {fileMeta.dataPreview && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>Showing first {fileMeta.dataPreview.rows.length} of {fileMeta.dataPreview.totalRows} records</span>
                        <span className="font-mono">{fileMeta.dataPreview.headers.length} Columns</span>
                      </div>
                      <div className="overflow-x-auto rounded-xl border border-border bg-card">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-muted/60 text-muted-foreground border-b border-border">
                            <tr>
                              {fileMeta.dataPreview.headers.map((h, i) => (
                                <th key={i} className="px-3 py-2 font-medium">
                                  {h}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border/60">
                            {fileMeta.dataPreview.rows.map((row, rIdx) => (
                              <tr key={rIdx} className="hover:bg-muted/20">
                                {row.map((cell, cIdx) => (
                                  <td key={cIdx} className="px-3 py-1.5 truncate max-w-[180px]">
                                    {cell}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {fileMeta.previewText && !fileMeta.dataPreview && (
                    <div className="relative rounded-xl border border-border bg-muted/20 overflow-hidden">
                      <div className="flex items-center justify-between px-3 py-2 bg-muted/40 border-b border-border text-xs text-muted-foreground">
                        <span className="font-mono text-[11px]">{fileMeta.language || 'Text'} Preview</span>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={handleCopyText}
                          className="h-6 px-2 text-xs gap-1"
                        >
                          {copied ? <Check size={11} className="text-emerald-500" /> : <Copy size={11} />}
                          <span>{copied ? 'Copied!' : 'Copy Text'}</span>
                        </Button>
                      </div>
                      <pre className="p-3 text-xs font-mono overflow-x-auto max-h-[340px] text-foreground leading-relaxed whitespace-pre-wrap">
                        {fileMeta.previewText}
                      </pre>
                    </div>
                  )}

                  {!fileMeta.previewText && fileMeta.category !== 'image' && (
                    <div className="p-8 text-center bg-muted/20 rounded-xl border border-border">
                      <File className="mx-auto text-muted-foreground mb-2" size={32} />
                      <p className="text-sm font-medium text-foreground">Binary or Document File</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        This file format ({fileMeta.extension.toUpperCase()}) is uploaded and analyzed directly by HSBot backend RAG service.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'metadata' && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-3.5 rounded-xl border border-border bg-card">
                    <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                      <Database size={13} className="text-brand" />
                      <span>File Size</span>
                    </div>
                    <p className="text-lg font-bold text-foreground">{formatBytes(fileMeta.size)}</p>
                    <p className="text-[11px] text-muted-foreground">{fileMeta.size.toLocaleString()} raw bytes</p>
                  </div>

                  <div className="p-3.5 rounded-xl border border-border bg-card">
                    <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                      <Hash size={13} className="text-brand" />
                      <span>Estimated LLM Tokens</span>
                    </div>
                    <p className="text-lg font-bold text-foreground">
                      {fileMeta.estimatedTokens ? fileMeta.estimatedTokens.toLocaleString() : 'N/A'}
                    </p>
                    <p className="text-[11px] text-muted-foreground">Tokens required for model inference</p>
                  </div>

                  <div className="p-3.5 rounded-xl border border-border bg-card">
                    <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                      <AlignLeft size={13} className="text-brand" />
                      <span>Line & Word Count</span>
                    </div>
                    <p className="text-lg font-bold text-foreground">
                      {fileMeta.lineCount ? `${fileMeta.lineCount} lines` : 'N/A'}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      {fileMeta.wordCount ? `${fileMeta.wordCount.toLocaleString()} words` : 'Non-text content'}
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl border border-border bg-card">
                    <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                      <FileCode size={13} className="text-brand" />
                      <span>MIME Type & Engine Routing</span>
                    </div>
                    <p className="text-sm font-semibold text-foreground truncate">{fileMeta.type || 'application/octet-stream'}</p>
                    <p className="text-[11px] text-muted-foreground">Engine: RAG Vector + NV-Embed v1</p>
                  </div>
                </div>
              )}

              {activeTab === 'actions' && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
                    <Sparkles size={14} className="text-brand" />
                    <span>One-Click AI Analysis Recipes</span>
                  </div>
                  <div className="grid grid-cols-1 gap-2">
                    {fileMeta.suggestedPrompts.map((prompt, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSelectPrompt(prompt)}
                        className="flex items-center justify-between p-3 rounded-xl border border-border bg-card hover:bg-muted text-left transition-all group"
                      >
                        <span className="text-xs text-foreground group-hover:text-primary transition-colors pr-3">
                          {prompt}
                        </span>
                        <div className="w-7 h-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0 group-hover:bg-primary group-hover:text-primary-foreground transition-all">
                          <Send size={12} />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Footer with Prompt Quick Launcher */}
            <div className="px-5 py-3 border-t border-border bg-muted/20 flex items-center justify-between gap-3">
              <span className="text-xs text-muted-foreground truncate">
                Ready for AI reasoning with SambaNova DeepSeek-V3.2 & NVIDIA models
              </span>
              <Button
                size="sm"
                onClick={() => handleSelectPrompt(`Please analyze ${fileMeta.name} and provide a structured summary.`)}
                className="gap-1.5 text-xs font-semibold h-8 rounded-lg"
              >
                <Sparkles size={12} />
                <span>Analyze File</span>
              </Button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
