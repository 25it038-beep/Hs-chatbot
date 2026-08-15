import React, { useEffect, useState } from 'react'
import { Pin, Minimize, Minus, X, LayoutGrid, Maximize2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { isTauri, hideWindow, minimizeWindow, toggleAlwaysOnTop, setWindowSize, COMPACT_SIZE, EXPANDED_SIZE } from '@/lib/tauri'

interface TitleBarProps {
  compact: boolean
  onToggleCompact: (compact: boolean) => void
}

/** Frameless window chrome for the desktop overlay: drag region, pin,
 * compact/expand, minimize and hide (close = hide, the app keeps running). */
export function TitleBar({ compact, onToggleCompact }: TitleBarProps) {
  const [pinned, setPinned] = useState(true)

  useEffect(() => {
    toggleAlwaysOnTop(pinned)
  }, [pinned])

  const handleToggleCompact = () => {
    const next = !compact
    onToggleCompact(next)
    setWindowSize(next ? COMPACT_SIZE : EXPANDED_SIZE)
  }

  if (!isTauri) return null

  return (
    <div
      data-tauri-drag-region
      className="flex items-center gap-1 h-9 px-2 border-b border-border bg-background/80 backdrop-blur select-none"
    >
      <div className="flex items-center gap-1.5 mr-1">
        <img src="/logo.jpg" alt="" className="w-5 h-5 rounded-md object-cover border border-border" />
        <span className="text-[11px] font-semibold text-foreground tracking-wide">HSBot</span>
      </div>

      <div className="flex-1" data-tauri-drag-region />

      <div className="flex items-center gap-0.5" data-tauri-drag-region>
        <button
          onClick={() => setPinned(p => !p)}
          className={cn(
            'p-1.5 rounded-md text-muted-foreground/60 hover:text-foreground hover:bg-muted transition-all',
            pinned && 'text-brand',
          )}
          title={pinned ? 'Always on top (on)' : 'Always on top (off)'}
          aria-label="Toggle always on top"
        >
          <Pin size={13} className={pinned ? 'fill-current' : ''} />
        </button>
        <button
          onClick={handleToggleCompact}
          className="p-1.5 rounded-md text-muted-foreground/60 hover:text-foreground hover:bg-muted transition-all"
          title={compact ? 'Expand window' : 'Compact widget mode'}
          aria-label="Toggle compact mode"
        >
          {compact ? <Maximize2 size={13} /> : <LayoutGrid size={13} />}
        </button>
        <button
          onClick={() => minimizeWindow()}
          className="p-1.5 rounded-md text-muted-foreground/60 hover:text-foreground hover:bg-muted transition-all"
          title="Minimize"
          aria-label="Minimize"
        >
          <Minus size={13} />
        </button>
        <button
          onClick={() => hideWindow()}
          className="p-1.5 rounded-md text-muted-foreground/60 hover:text-foreground hover:bg-red-500/10 hover:text-red-400 transition-all"
          title="Hide (keep running — Ctrl+Space to bring back)"
          aria-label="Hide window"
        >
          <X size={13} />
        </button>
      </div>
    </div>
  )
}
