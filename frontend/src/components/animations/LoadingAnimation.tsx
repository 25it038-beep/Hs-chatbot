import React from 'react'
import { motion } from 'framer-motion'
import { useReducedMotion } from '@/hooks/useReducedMotion'

export function LoadingAnimation({ className = '' }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="relative w-5 h-5">
        <div className="absolute inset-0 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
      </div>
      <div className="flex gap-1">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </div>
    </div>
  )
}

export function AIThinking({
  className = '',
  onStop,
}: {
  className?: string
  onStop?: () => void
}) {
  const reducedMotion = useReducedMotion()

  const logo = (
    <div className="relative" aria-hidden="true">
      <motion.div
        className="w-[18px] h-[18px] rounded-full bg-linear-to-br from-brand to-ambient-1 shadow-soft"
        animate={reducedMotion ? undefined : { scale: [1, 1.15, 1], rotate: [0, 10, 0] }}
        transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute -inset-1 rounded-full border-2 border-brand/25 border-t-brand"
        animate={reducedMotion ? undefined : { rotate: 360 }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
      />
      <motion.div
        className="absolute -top-1 -right-1 w-1.5 h-1.5 rounded-full bg-ambient-3"
        animate={reducedMotion ? undefined : { y: [0, -4, 0], opacity: [1, 0.4, 1] }}
        transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
      />
    </div>
  )

  const content = (
    <div className={`flex items-center gap-3 ${className}`}>
      <button
        type="button"
        onClick={onStop}
        disabled={!onStop}
        title={onStop ? 'Stop response' : undefined}
        aria-label={onStop ? 'Stop AI response' : undefined}
        className="relative grid place-items-center rounded-full p-0.5 transition-transform active:scale-90 disabled:cursor-default"
      >
        {logo}
      </button>
      <div className="flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="w-2 h-2 rounded-full bg-primary/60"
            animate={reducedMotion ? undefined : { y: [0, -6, 0] }}
            transition={{
              duration: 0.6,
              repeat: Infinity,
              delay: i * 0.15,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>
    </div>
  )

  if (reducedMotion) {
    return content
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      {content}
    </motion.div>
  )
}

export function Shimmer({ className = '' }: { className?: string }) {
  return (
    <div className={`skeleton animate-shimmer ${className}`} />
  )
}

export function SkeletonBlock({ lines = 3, className = '' }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton animate-shimmer h-4"
          style={{ width: `${70 + Math.random() * 30}%` }}
        />
      ))}
    </div>
  )
}
