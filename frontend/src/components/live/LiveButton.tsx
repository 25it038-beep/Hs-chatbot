/**
 * HSBot Live Voice System - Live Button
 * 
 * Sleek button for toggling Live Voice mode.
 */

import React from 'react'
import { Radio } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LiveButtonProps {
  onClick: () => void
  isActive?: boolean
  disabled?: boolean
  className?: string
}

export const LiveButton: React.FC<LiveButtonProps> = ({
  onClick,
  isActive = false,
  disabled = false,
  className,
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'relative group flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all duration-200',
        isActive
          ? 'bg-emerald-500 text-white shadow-[0_0_12px_rgba(16,185,129,0.35)] active:scale-95'
          : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 active:scale-95 border border-emerald-500/20',
        'disabled:opacity-40 disabled:pointer-events-none',
        className
      )}
      title="Start NVIDIA Live Voice conversation"
      aria-label="Start NVIDIA Live Voice conversation"
    >
      <Radio
        size={14}
        className={cn(
          'transition-transform',
          isActive ? 'animate-pulse text-white' : 'text-emerald-500 group-hover:scale-110'
        )}
      />
      <span className="font-semibold tracking-wide">Live</span>
      {isActive && (
        <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
        </span>
      )}
    </button>
  )
}
