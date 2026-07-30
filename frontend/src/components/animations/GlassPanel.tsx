import React from 'react'
import { cn } from '@/lib/utils'

interface GlassPanelProps {
  children: React.ReactNode
  className?: string
  strong?: boolean
  hover?: boolean
  as?: 'div' | 'section' | 'article' | 'aside'
}

export function GlassPanel({ children, className, strong = false, hover = false, as: Comp = 'div' }: GlassPanelProps) {
  return (
    <Comp
      className={cn(
        strong ? 'glass-panel-strong' : 'glass-panel',
        hover && 'glass-panel-hover',
        'rounded-2xl',
        className
      )}
    >
      {children}
    </Comp>
  )
}

export function GlassCard({ children, className, ...props }: GlassPanelProps) {
  return (
    <GlassPanel strong hover className={cn('p-4', className)} {...props}>
      {children}
    </GlassPanel>
  )
}
