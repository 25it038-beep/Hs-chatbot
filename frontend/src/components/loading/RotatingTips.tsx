import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  Sparkles,
  Code,
  Layers,
  HelpCircle,
  FileText,
  MessageSquare,
  AlertTriangle,
  ListOrdered,
  Mic,
  Terminal,
  ShieldCheck,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Pause,
  Play,
  Lightbulb,
} from 'lucide-react'
import { AI_TIPS, type AiTip } from '@/config/tips'
import { Button } from '@/components/ui/button'

const ICON_MAP = {
  Sparkles,
  Code,
  Layers,
  HelpCircle,
  FileText,
  MessageSquare,
  AlertTriangle,
  ListOrdered,
  Mic,
  Terminal,
  ShieldCheck,
  CheckCircle2,
}

const ROTATION_INTERVAL_MS = 6000

export function RotatingTips() {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isPaused, setIsPaused] = useState(false)
  const [isHovered, setIsHovered] = useState(false)
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)
  const timerRef = useRef<any>(null)

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
      setPrefersReducedMotion(mediaQuery.matches)
      const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches)
      mediaQuery.addEventListener('change', handler)
      return () => mediaQuery.removeEventListener('change', handler)
    }
  }, [])

  const handleNext = useCallback(() => {
    setCurrentIndex((prev) => (prev + 1) % AI_TIPS.length)
  }, [])

  const handlePrev = useCallback(() => {
    setCurrentIndex((prev) => (prev - 1 + AI_TIPS.length) % AI_TIPS.length)
  }, [])

  // Auto-rotation effect
  useEffect(() => {
    if (isPaused || isHovered) {
      if (timerRef.current) clearInterval(timerRef.current)
      return
    }

    timerRef.current = setInterval(() => {
      handleNext()
    }, ROTATION_INTERVAL_MS)

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isPaused, isHovered, handleNext])

  const currentTip: AiTip = AI_TIPS[currentIndex]
  const IconComponent = ICON_MAP[currentTip.iconName] || Sparkles

  return (
    <div
      className="w-full rounded-2xl border border-border/80 bg-card/60 backdrop-blur-xl p-4 sm:p-5 shadow-sm relative overflow-hidden transition-all duration-300"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onTouchStart={() => setIsHovered(true)}
      onTouchEnd={() => setTimeout(() => setIsHovered(false), 2000)}
    >
      {/* Background Accent Gradient */}
      <div className="absolute top-0 right-0 w-44 h-44 bg-brand/5 rounded-full blur-3xl pointer-events-none" />

      {/* Top Header */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="p-1.5 rounded-lg bg-brand/10 text-brand">
            <Lightbulb size={14} />
          </span>
          <span className="text-xs font-semibold text-foreground uppercase tracking-wider">
            AI Pro Tips ({currentIndex + 1} of {AI_TIPS.length})
          </span>
        </div>

        <div className="flex items-center gap-1">
          {/* Pause / Resume Button */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 rounded-lg text-muted-foreground/70 hover:text-foreground"
            onClick={() => setIsPaused((prev) => !prev)}
            aria-label={isPaused ? 'Resume tip rotation' : 'Pause tip rotation'}
            title={isPaused ? 'Resume rotation' : 'Pause rotation'}
          >
            {isPaused ? <Play size={12} /> : <Pause size={12} />}
          </Button>

          {/* Navigation Controls */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 rounded-lg text-muted-foreground/70 hover:text-foreground"
            onClick={handlePrev}
            aria-label="Previous AI tip"
          >
            <ChevronLeft size={14} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 rounded-lg text-muted-foreground/70 hover:text-foreground"
            onClick={handleNext}
            aria-label="Next AI tip"
          >
            <ChevronRight size={14} />
          </Button>
        </div>
      </div>

      {/* Tip Content Card */}
      <div
        className={`min-h-[100px] sm:min-h-[110px] flex flex-col justify-center transition-all ${
          prefersReducedMotion ? '' : 'duration-300 animate-fade-in'
        }`}
        key={currentTip.id}
      >
        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-brand/10 text-brand text-[10px] font-semibold">
            <IconComponent size={11} />
            {currentTip.tag}
          </span>
          <span className="text-xs font-semibold text-foreground line-clamp-1">
            {currentTip.title}
          </span>
        </div>

        <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
          {currentTip.content}
        </p>
      </div>

      {/* Pagination Dot Indicators */}
      <div className="flex items-center justify-between pt-3 mt-2 border-t border-border/40">
        <div className="flex items-center gap-1">
          {AI_TIPS.map((tip, idx) => (
            <button
              key={tip.id}
              onClick={() => setCurrentIndex(idx)}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                idx === currentIndex
                  ? 'w-5 bg-brand'
                  : 'w-1.5 bg-muted-foreground/25 hover:bg-muted-foreground/50'
              }`}
              aria-label={`Go to tip ${idx + 1}: ${tip.title}`}
            />
          ))}
        </div>

        <span className="text-[10px] text-muted-foreground/60 select-none">
          {isPaused ? 'Paused' : isHovered ? 'Hovered' : 'Auto-rotating'}
        </span>
      </div>
    </div>
  )
}
