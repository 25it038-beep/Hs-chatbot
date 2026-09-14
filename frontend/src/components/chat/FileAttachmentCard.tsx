import React, { useState } from 'react'
import { Download, Check, Loader2, FileText, FileSpreadsheet, Presentation } from 'lucide-react'
import type { Attachment } from '@/types'
import { api } from '@/lib/api'

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
      label: 'PDF',
      color: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
      icon: FileText,
      iconColor: 'text-rose-500',
    }
  }
  if (ext === 'docx' || ext === 'doc' || mimeType.includes('word')) {
    return {
      label: 'Word',
      color: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
      icon: FileText,
      iconColor: 'text-blue-500',
    }
  }
  if (ext === 'pptx' || ext === 'ppt' || mimeType.includes('presentation')) {
    return {
      label: 'PowerPoint',
      color: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
      icon: Presentation,
      iconColor: 'text-amber-500',
    }
  }
  if (ext === 'xlsx' || ext === 'xls' || mimeType.includes('spreadsheet') || mimeType.includes('excel')) {
    return {
      label: 'Excel',
      color: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
      icon: FileSpreadsheet,
      iconColor: 'text-emerald-500',
    }
  }
  if (ext === 'csv') {
    return {
      label: 'CSV',
      color: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20',
      icon: FileSpreadsheet,
      iconColor: 'text-indigo-500',
    }
  }
  return {
    label: ext.toUpperCase() || 'FILE',
    color: 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20',
    icon: FileText,
    iconColor: 'text-slate-500',
  }
}

export function FileAttachmentCard({ attachment }: FileAttachmentCardProps) {
  const [downloading, setDownloading] = useState(false)
  const [downloaded, setDownloaded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fmt = getFormatDetails(attachment.name, attachment.type)
  const Icon = fmt.icon

  const handleDownload = async (e: React.MouseEvent) => {
    e.preventDefault()
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
      // Fallback direct navigation
      const token = localStorage.getItem('access_token')
      const q = token ? `?token=${encodeURIComponent(token)}` : ''
      window.open(`/api/files/${attachment.id}/download${q}`, '_blank')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 my-2.5 rounded-xl border border-border bg-card/80 shadow-soft max-w-lg transition-all hover:border-border/80">
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <div className={`p-2.5 rounded-lg border flex items-center justify-center shrink-0 ${fmt.color}`}>
          <Icon size={20} className={fmt.iconColor} />
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
            {error && <span className="text-destructive">• {error}</span>}
          </div>
        </div>
      </div>

      <button
        onClick={handleDownload}
        disabled={downloading}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all shrink-0 w-full sm:w-auto justify-center ${
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
  )
}
