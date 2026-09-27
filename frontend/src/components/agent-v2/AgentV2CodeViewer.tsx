import React, { useState, useEffect } from 'react'
import { Copy, Check, Save, Code2, Cpu, UserCheck } from 'lucide-react'

interface AgentV2CodeViewerProps {
  filePath: string
  content: string
  onSave?: (path: string, newContent: string) => void
  assignedEmployee?: string
  assignedModel?: string
}

export function AgentV2CodeViewer({
  filePath,
  content,
  onSave,
  assignedEmployee = 'Frontend Engineer',
  assignedModel = 'codestral'
}: AgentV2CodeViewerProps) {
  const [code, setCode] = useState(content)
  const [copied, setCopied] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setCode(content)
  }, [content])

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSave = () => {
    onSave?.(filePath, code)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const lines = code.split('\n')

  return (
    <div className="flex flex-col h-full bg-card/20 select-text overflow-hidden">
      {/* Top File Attribution Header */}
      <div className="h-10 px-4 border-b border-border bg-muted/40 flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-2 truncate">
          <Code2 size={14} className="text-primary" />
          <span className="font-bold text-foreground truncate">{filePath}</span>
          <span className="text-muted-foreground/60 hidden sm:inline">·</span>
          <span className="text-[11px] text-muted-foreground hidden sm:flex items-center gap-1">
            <UserCheck size={11} />
            <span>{assignedEmployee}</span>
          </span>
          <span className="text-muted-foreground/60 hidden sm:inline">·</span>
          <span className="text-[11px] text-muted-foreground hidden sm:flex items-center gap-1">
            <Cpu size={11} />
            <span>{assignedModel}</span>
          </span>
        </div>

        <div className="flex items-center gap-2">
          {onSave && code !== content && (
            <button
              onClick={handleSave}
              className="px-2.5 py-1 bg-primary text-primary-foreground text-[10px] font-bold rounded flex items-center gap-1 shadow-2xs"
            >
              <Save size={11} />
              <span>{saved ? 'Saved' : 'Save'}</span>
            </button>
          )}

          <button
            onClick={handleCopy}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted transition-colors"
            title="Copy code"
          >
            {copied ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
          </button>
        </div>
      </div>

      {/* Code with Line Numbers */}
      <div className="flex-1 flex overflow-hidden font-mono text-xs bg-slate-950 text-slate-100">
        {/* Line Numbers gutter */}
        <div className="py-3 px-3 select-none text-right text-slate-600 bg-slate-950/80 border-r border-slate-900 font-mono text-[11px] overflow-hidden">
          {lines.map((_, i) => (
            <div key={i} className="leading-5 h-5 tabular-nums">
              {i + 1}
            </div>
          ))}
        </div>

        {/* Code Content */}
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          spellCheck={false}
          className="flex-1 p-3 bg-transparent text-slate-100 resize-none focus:outline-hidden leading-5 font-mono text-[11px] whitespace-pre overflow-auto"
        />
      </div>
    </div>
  )
}
