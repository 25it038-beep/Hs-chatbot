import React, { useState } from 'react'
import { Folder, FileCode, Plus, Search, FileText, FileSpreadsheet, Image } from 'lucide-react'

interface AgentV2FileExplorerProps {
  files: Record<string, string>
  selectedFilePath?: string
  onSelectFile: (path: string) => void
  onNewFile?: (path: string) => void
}

export function AgentV2FileExplorer({
  files,
  selectedFilePath,
  onSelectFile,
  onNewFile
}: AgentV2FileExplorerProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [newFileInputOpen, setNewFileInputOpen] = useState(false)
  const [newFileName, setNewFileName] = useState('')

  const fileKeys = Object.keys(files)
  const filteredFiles = fileKeys.filter((f) => f.toLowerCase().includes(searchQuery.toLowerCase()))

  const handleCreate = () => {
    if (!newFileName.trim()) return
    onNewFile?.(newFileName.trim())
    setNewFileName('')
    setNewFileInputOpen(false)
  }

  const getFileIcon = (path: string) => {
    if (path.endsWith('.html')) return <FileCode size={13} className="text-orange-400" />
    if (path.endsWith('.css')) return <FileCode size={13} className="text-cyan-400" />
    if (path.endsWith('.js') || path.endsWith('.ts')) return <FileCode size={13} className="text-amber-400" />
    if (path.endsWith('.json')) return <FileText size={13} className="text-yellow-400" />
    if (path.endsWith('.md')) return <FileText size={13} className="text-blue-400" />
    return <FileText size={13} className="text-slate-400" />
  }

  return (
    <div className="flex flex-col h-full bg-card/40 border-r border-border w-64 flex-shrink-0 select-none">
      {/* Header */}
      <div className="p-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-muted-foreground">
          <Folder size={14} className="text-primary" />
          <span>Workspace</span>
        </div>
        <button
          onClick={() => setNewFileInputOpen(!newFileInputOpen)}
          className="p-1 text-muted-foreground hover:text-foreground rounded hover:bg-muted transition-colors"
          title="New file"
        >
          <Plus size={14} />
        </button>
      </div>

      {/* Search Bar */}
      <div className="p-2 border-b border-border/60">
        <div className="relative flex items-center">
          <Search size={12} className="absolute left-2.5 text-muted-foreground" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search files..."
            className="w-full text-[11px] pl-7 pr-2 py-1 rounded-lg bg-background border border-border/70 focus:outline-hidden focus:ring-1 focus:ring-primary text-foreground"
          />
        </div>
      </div>

      {/* New file inline prompt */}
      {newFileInputOpen && (
        <div className="p-2 border-b border-border/60 bg-muted/30 flex items-center gap-1.5 animate-in fade-in duration-100">
          <input
            value={newFileName}
            onChange={(e) => setNewFileName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            placeholder="filename.ext"
            className="flex-1 text-[11px] px-2 py-1 rounded bg-background border border-border focus:outline-hidden text-foreground"
            autoFocus
          />
          <button
            onClick={handleCreate}
            className="px-2 py-1 bg-primary text-primary-foreground text-[10px] font-bold rounded"
          >
            Add
          </button>
        </div>
      )}

      {/* File List */}
      <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {filteredFiles.length > 0 ? (
          filteredFiles.map((path) => {
            const isSelected = selectedFilePath === path

            return (
              <button
                key={path}
                onClick={() => onSelectFile(path)}
                className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-mono transition-colors flex items-center justify-between group ${
                  isSelected
                    ? 'bg-primary/10 text-primary font-bold shadow-2xs'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  {getFileIcon(path)}
                  <span className="truncate">{path}</span>
                </div>
                <span className="text-[10px] text-emerald-500 font-bold opacity-0 group-hover:opacity-100 transition-opacity">
                  +
                </span>
              </button>
            )
          })
        ) : (
          <div className="p-4 text-center text-[11px] text-muted-foreground/60">
            No files in workspace yet.
          </div>
        )}
      </div>
    </div>
  )
}
