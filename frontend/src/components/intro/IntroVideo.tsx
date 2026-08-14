import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Volume2, VolumeX, SkipForward, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface IntroVideoProps {
  onComplete: () => void
}

const SEEN_KEY = 'hsbot-intro-seen'

export function hasSeenIntro(): boolean {
  try {
    return sessionStorage.getItem(SEEN_KEY) === '1'
  } catch {
    return false
  }
}

export function IntroVideo({ onComplete }: IntroVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [soundBlocked, setSoundBlocked] = useState(false)
  const [done, setDone] = useState(false)

  const tryPlayWithSound = () => {
    const v = videoRef.current
    if (!v) return
    v.muted = false
    v.volume = 1
    v.play().catch(() => {
      // Browser blocked autoplay with sound — fall back to muted autoplay
      v.muted = true
      setSoundBlocked(true)
      v.play().catch(() => {})
    })
  }

  useEffect(() => {
    try {
      sessionStorage.setItem(SEEN_KEY, '1')
    } catch {
      /* ignore */
    }

    const v = videoRef.current
    if (!v) return
    v.muted = true
    const p = v.play()
    if (p) {
      p.then(tryPlayWithSound).catch(() => {
        v.muted = true
        setSoundBlocked(true)
        v.play().catch(() => {})
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleUnlockSound = () => {
    const v = videoRef.current
    if (!v) return
    setSoundBlocked(false)
    v.muted = false
    v.volume = 1
    v.play().catch(() => setSoundBlocked(true))
  }

  const handleSkip = () => {
    setDone(true)
    setTimeout(onComplete, 400)
  }

  return (
    <AnimatePresence>
      {!done && (
        <motion.div
          className="fixed inset-0 z-[60] bg-black"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.02 }}
          transition={{ duration: 0.4 }}
        >
          <video
            ref={videoRef}
            src="/intro.mp4"
            className="w-full h-full object-contain"
            playsInline
            autoPlay
            muted
            onEnded={onComplete}
            onClick={soundBlocked ? handleUnlockSound : undefined}
            aria-label="HSBot introduction video"
          />
          <div className="absolute top-0 inset-x-0 p-4 sm:p-5 flex items-center justify-between pointer-events-none">
            <span className="flex items-center gap-2 text-white/90 text-sm font-semibold tracking-tight">
              <Sparkles size={14} className="text-white/70" />
              HSBot
            </span>
            {soundBlocked && (
              <button
                onClick={handleUnlockSound}
                className="pointer-events-auto flex items-center gap-1.5 text-[11px] text-white/80 bg-white/10 hover:bg-white/20 border border-white/20 px-3 py-1.5 rounded-full backdrop-blur-sm transition-colors"
              >
                <VolumeX size={12} />
                Tap for sound
              </button>
            )}
          </div>
          <div className="absolute bottom-0 inset-x-0 p-4 sm:p-6 flex items-center justify-between">
            <span className="text-[11px] text-white/40 tracking-wide">
              {soundBlocked ? <VolumeX size={13} className="inline mr-1" /> : <Volume2 size={13} className="inline mr-1" />}
              {soundBlocked ? 'Sound blocked by browser — tap anywhere to enable' : 'Playing with sound'}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSkip}
              className="text-white/80 hover:text-white hover:bg-white/10 border border-white/15 rounded-full px-4 h-8 text-xs"
              aria-label="Skip introduction video"
            >
              Skip intro
              <SkipForward size={13} className="ml-1.5" />
            </Button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}