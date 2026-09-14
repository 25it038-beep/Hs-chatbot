import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Monitor, Download, X, Sparkles, CheckCircle2,
  Layers, ExternalLink, ShieldCheck
} from 'lucide-react'
import { Button } from '@/components/ui/button'

interface WindowsDownloadModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function WindowsDownloadModal({ open, onOpenChange }: WindowsDownloadModalProps) {
  const [downloadStarted, setDownloadStarted] = useState(false)

  const handleDownload = () => {
    setDownloadStarted(true)
    const link = document.createElement('a')
    link.href = '/downloads/HSBot_1.0.0_x64-setup.exe'
    link.download = 'HSBot_1.0.0_x64-setup.exe'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
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
                      v1.0.0
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Always-on-top desktop overlay with AI & browser automation
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
                  Press <kbd className="px-1.5 py-0.5 rounded bg-background border border-border font-mono text-[10px] text-foreground font-medium">Ctrl+Space</kbd> anywhere to summon.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-muted/40 border border-border/50 text-left">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground mb-1">
                  <Layers size={13} className="text-brand" />
                  <span>Floating Overlay</span>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Frameless, compact & always stays on top while you work.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-muted/40 border border-border/50 text-left">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground mb-1">
                  <ShieldCheck size={13} className="text-brand" />
                  <span>Browser Control</span>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Live multi-tab automation with local persistent profile.
                </p>
              </div>
            </div>

            {/* Download Action Section */}
            <div className="p-4 rounded-xl bg-primary/5 border border-primary/20 text-center my-4 space-y-3">
              <Button
                onClick={handleDownload}
                size="lg"
                className="w-full gap-2 text-sm font-semibold rounded-xl bg-primary text-primary-foreground hover:opacity-95 shadow-md h-11"
              >
                <Download size={16} />
                {downloadStarted ? 'Downloading Installer (4.25 MB)...' : 'Download Windows Setup (.exe)'}
              </Button>

              {downloadStarted ? (
                <div className="flex items-center justify-center gap-1.5 text-xs text-green-500 font-medium">
                  <CheckCircle2 size={13} />
                  <span>Download started! Check your browser's download shelf.</span>
                </div>
              ) : (
                <p className="text-[11px] text-muted-foreground">
                  Compatible with Windows 10 & 11 (64-bit). Standalone NSIS installer.
                </p>
              )}
            </div>

            {/* Steps */}
            <div className="border-t border-border pt-4 mt-2 space-y-2">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Quick Setup:</h4>
              <ol className="text-xs text-muted-foreground space-y-1.5 pl-4 list-decimal">
                <li>Run <code className="text-[11px] font-mono bg-muted px-1.5 py-0.5 rounded text-foreground">HSBot_1.0.0_x64-setup.exe</code> to install.</li>
                <li>Launch HSBot from your Start Menu or Desktop.</li>
                <li>Press <kbd className="px-1.5 py-0.5 rounded bg-muted border border-border font-mono text-[10px] text-foreground font-semibold">Ctrl + Space</kbd> anywhere on your PC to toggle the assistant.</li>
              </ol>
            </div>

            {/* Alternative link */}
            <div className="flex items-center justify-between mt-4 pt-3 border-t border-border/40 text-[11px] text-muted-foreground">
              <span>Direct URL: <a href="/api/download/windows" className="text-primary hover:underline">/api/download/windows</a></span>
              <a
                href="/downloads/HSBot_1.0.0_x64-setup.exe"
                download="HSBot_1.0.0_x64-setup.exe"
                className="flex items-center gap-1 hover:text-foreground transition-colors"
              >
                Direct file link <ExternalLink size={10} />
              </a>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
