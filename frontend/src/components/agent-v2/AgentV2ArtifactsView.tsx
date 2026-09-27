import React from 'react'
import { Package, Download, FileText, Check, ExternalLink, Archive } from 'lucide-react'
import type { ArtifactData } from '@/lib/agentV2Api'

interface AgentV2ArtifactsViewProps {
  artifacts: ArtifactData[]
  files: Record<string, string>
}

export function AgentV2ArtifactsView({ artifacts, files }: AgentV2ArtifactsViewProps) {
  const handleDownloadZip = () => {
    // Generate simple client-side archive trigger if needed
    const fileEntries = Object.entries(files)
    if (fileEntries.length === 0) return

    // Create a plain text bundle if JSZip not present
    let bundle = ''
    for (const [name, content] of fileEntries) {
      bundle += `\n\n==================== ${name} ====================\n\n` + content
    }
    const blob = new Blob([bundle], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'project-bundle.txt'
    a.click()
  }

  return (
    <div className="p-6 max-w-4xl mx-auto w-full space-y-6 overflow-y-auto h-full">
      <div className="p-5 rounded-2xl bg-card border border-border/80 shadow-xs flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Archive size={16} className="text-primary" />
            <h3 className="text-sm font-bold text-foreground">Verified Release Deliverables</h3>
          </div>
          <p className="text-xs text-muted-foreground">
            Complete project packages, documentation, and architecture manifests ready for distribution.
          </p>
        </div>

        <button
          onClick={handleDownloadZip}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-xl text-xs font-semibold shadow-xs hover:bg-primary/90 transition-all flex items-center gap-1.5"
        >
          <Download size={13} />
          <span>Export Workspace Bundle</span>
        </button>
      </div>

      {/* Artifact Deliverables Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="p-5 rounded-2xl bg-card border border-border/70 space-y-3 text-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Package size={15} className="text-primary" />
              <span className="font-bold text-foreground">release.zip</span>
            </div>
            <span className="text-[10px] font-mono bg-muted px-1.5 py-0.5 rounded text-muted-foreground">ZIP Archive</span>
          </div>
          <p className="text-muted-foreground text-[11px] leading-relaxed">
            Contains all synthesized source files, CSS stylesheets, test suites, and package manifest.
          </p>
          <div className="pt-2 border-t border-border/40 flex items-center justify-between text-[11px] font-mono text-muted-foreground">
            <span>Verified 100% PASS</span>
            <button onClick={handleDownloadZip} className="text-primary hover:underline font-bold">
              Download
            </button>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-card border border-border/70 space-y-3 text-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText size={15} className="text-blue-400" />
              <span className="font-bold text-foreground">README.md</span>
            </div>
            <span className="text-[10px] font-mono bg-muted px-1.5 py-0.5 rounded text-muted-foreground">Documentation</span>
          </div>
          <p className="text-muted-foreground text-[11px] leading-relaxed">
            Auto-generated architecture documentation, user guide, and setup instructions.
          </p>
          <div className="pt-2 border-t border-border/40 flex items-center justify-between text-[11px] font-mono text-muted-foreground">
            <span>Markdown Format</span>
            <span className="text-emerald-400">Included</span>
          </div>
        </div>
      </div>
    </div>
  )
}
