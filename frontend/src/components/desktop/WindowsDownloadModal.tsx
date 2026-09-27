import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Monitor, Download, X, Sparkles, CheckCircle2,
  Layers, ExternalLink, ShieldCheck, Copy, Check, AlertCircle, Loader2
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { downloadWindowsInstaller, formatBytes, getFullDownloadUrl, DownloadProgress } from '@/lib/downloader'

interface WindowsDownloadModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function WindowsDownloadModal({ open, onOpenChange }: WindowsDownloadModalProps) {
  const [progress, setProgress] = useState<DownloadProgress | null>(null)
  const [copied, setCopied] = useState(false)

  const handleDownload = async () => {
    setProgress({
      loaded: 0,
      total: 4252272,
      percent: 5,
      status: 'downloading',
    })

    const ok = await downloadWindowsInstaller({
      filename: 'HSBot_1.0.0_x64-setup.exe',
      onProgress: (p) => setProgress(p),
    })

    if (!ok) {
      setProgress((prev) => ({
        loaded: prev?.loaded || 0,
        total: 4252272,
        percent: 0,
        status: 'blocked',
        errorMessage: 'Automatic download blocked by browser iframe. Please use direct download or copy link below.',
      }))
    }
  }

  const handleCopyLink = () => {
    const fullUrl = getFullDownloadUrl('/downloads/HSBot_1.0.0_x64-setup.exe')
    navigator.clipboard.writeText(fullUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  const handleOpenDirect = () => {
    const fullUrl = getFullDownloadUrl('/downloads/HSBot_1.0.0_x64-setup.exe')
    window.open(fullUrl, '_blank', 'noopener,noreferrer')
  }

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            className="absolute inset-0 bg-background/70 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => onOpenChange(false)}
          />

          <motion.div
            className="relative w-full max-w-lg rounded-2xl border border-border bg-card shadow-2xl p-6 overflow-hidden z-10"
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            role="dialog"
            aria-label="Download HSBot for Windows"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-4 mb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center border border-primary/20 shadow-soft">
                  <Monitor size={24} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold tracking-tight text-foreground">HSBot for Windows</h3>
                    <span className="text-[10px] font-semibold bg-primary/15 text-primary border border-primary/30 px-2 py-0.5 rounded-full">
                      v1.0.0 Official
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Standalone desktop overlay with AI chat, browser automation & hotkeys
                  </p>
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

            {/* Feature Highlights */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 my-4">
              <div className="p-3 rounded-xl bg-muted/40 border border-border/50 text-left">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground mb-1">
                  <Sparkles size={13} className="text-brand" />
                  <span>Global Hotkey</span>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Press <kbd className="px-1.5 py-0.5 rounded bg-background border border-border font-mono text-[10px] text-foreground font-medium">Ctrl+Space</kbd> anywhere on PC to summon instantly.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-muted/40 border border-border/50 text-left">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground mb-1">
                  <Layers size={13} className="text-brand" />
                  <span>Floating Overlay</span>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Frameless, compact & always stays pinned while coding or browsing.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-muted/40 border border-border/50 text-left">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground mb-1">
                  <ShieldCheck size={13} className="text-brand" />
                  <span>Browser Control</span>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Multi-tab agent with local browser profile support.
                </p>
              </div>
            </div>

            {/* Download Action Section */}
            <div className="p-4 rounded-xl bg-primary/5 border border-primary/20 text-center my-4 space-y-3">
              <Button
                onClick={handleDownload}
                size="lg"
                disabled={progress?.status === 'downloading'}
                className="w-full gap-2 text-sm font-semibold rounded-xl bg-primary text-primary-foreground hover:opacity-95 shadow-md h-11"
              >
                {progress?.status === 'downloading' ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Fetching Installer ({progress.percent}%)</span>
                  </>
                ) : (
                  <>
                    <Download size={16} />
                    <span>Download Windows Installer (.exe • 4.1 MB)</span>
                  </>
                )}
              </Button>

              {/* Real-time Progress Bar */}
              {progress?.status === 'downloading' && (
                <div className="space-y-1.5 text-left pt-1">
                  <div className="flex justify-between text-[11px] text-muted-foreground font-mono">
                    <span>{formatBytes(progress.loaded)} of {formatBytes(progress.total)}</span>
                    <span>{progress.percent}%</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-150 rounded-full"
                      style={{ width: `${Math.max(5, progress.percent)}%` }}
                    />
                  </div>
                </div>
              )}

              {progress?.status === 'completed' && (
                <div className="flex items-center justify-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 font-medium py-1">
                  <CheckCircle2 size={15} />
                  <span>Download completed! Run <strong className="font-mono">HSBot_1.0.0_x64-setup.exe</strong> to install.</span>
                </div>
              )}

              {progress?.status === 'blocked' && (
                <div className="space-y-2 text-left p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-700 dark:text-amber-300">
                  <div className="flex items-center gap-1.5 font-semibold">
                    <AlertCircle size={14} className="text-amber-500 flex-shrink-0" />
                    <span>Browser iframe restriction detected</span>
                  </div>
                  <p>In-page automated download was prevented by the preview sandbox. Click below to open directly in a new tab or copy link:</p>
                  <div className="flex gap-2 pt-1">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleOpenDirect}
                      className="text-xs h-7 gap-1"
                    >
                      <ExternalLink size={12} />
                      <span>Open in New Tab</span>
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleCopyLink}
                      className="text-xs h-7 gap-1"
                    >
                      {copied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                      <span>{copied ? 'Copied URL!' : 'Copy Direct Link'}</span>
                    </Button>
                  </div>
                </div>
              )}

              {(!progress || progress.status === 'idle') && (
                <p className="text-[11px] text-muted-foreground">
                  Compatible with Windows 10 & 11 (64-bit). Verified safe standalone NSIS installer.
                </p>
              )}
            </div>

            {/* Direct fallback links bar */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border/50 text-[11px] text-muted-foreground">
              <button
                onClick={handleCopyLink}
                className="flex items-center gap-1 hover:text-foreground transition-colors font-medium"
              >
                {copied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                <span>{copied ? 'Copied setup URL to clipboard!' : 'Copy direct installer URL'}</span>
              </button>

              <button
                onClick={handleOpenDirect}
                className="flex items-center gap-1 text-primary hover:underline font-medium"
              >
                <span>Direct Download Link</span>
                <ExternalLink size={11} />
              </button>
            </div>

            {/* Steps */}
            <div className="border-t border-border pt-3 mt-3 space-y-1.5 text-left">
              <h4 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Quick Setup:</h4>
              <ol className="text-xs text-muted-foreground space-y-1 pl-4 list-decimal">
                <li>Run <code className="text-[11px] font-mono bg-muted px-1.5 py-0.5 rounded text-foreground">HSBot_1.0.0_x64-setup.exe</code>.</li>
                <li>Launch HSBot from your Start Menu or Desktop shortcut.</li>
                <li>Press <kbd className="px-1.5 py-0.5 rounded bg-muted border border-border font-mono text-[10px] text-foreground font-semibold">Ctrl + Space</kbd> anywhere on your PC to toggle the assistant.</li>
              </ol>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
