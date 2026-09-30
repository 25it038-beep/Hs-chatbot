import React, { useEffect, useRef, useState } from 'react'
import { useChat } from '@/stores/chat'
import { useAmbient } from '@/stores/ambient'
import { getActiveFestival } from '@/lib/festival'
import { useWallpaperStore, WALLPAPERS } from '@/stores/wallpaper'

type AmbientState = 'idle' | 'typing' | 'thinking' | 'streaming' | 'complete'

interface ReactiveAmbientBackgroundProps {
  children?: React.ReactNode
}

export function ReactiveAmbientBackground({ children }: ReactiveAmbientBackgroundProps) {
  const { streaming, streamingPhase, generatingImage, currentChat } = useChat()
  const { userTyping, festivalEnabled } = useAmbient()
  const {
    currentWallpaperId,
    autoCycle,
    cycleIntervalSeconds,
    opacity,
    blur,
    nextWallpaper,
  } = useWallpaperStore()

  const [completePulse, setCompletePulse] = useState(false)
  const wasActiveRef = useRef(false)
  const phase = currentChat ? streamingPhase[currentChat.id] : undefined

  const active = streaming || generatingImage
  const state: AmbientState = active
    ? phase === 'thinking'
      ? 'thinking'
      : 'streaming'
    : userTyping
      ? 'typing'
      : completePulse
        ? 'complete'
        : 'idle'

  // AI state pulse animation
  useEffect(() => {
    if (active) {
      wasActiveRef.current = true
      return
    }
    if (wasActiveRef.current) {
      wasActiveRef.current = false
      setCompletePulse(true)
      const timer = setTimeout(() => setCompletePulse(false), 2600)
      return () => clearTimeout(timer)
    }
  }, [active])

  useEffect(() => {
    document.documentElement.setAttribute('data-ai-state', state)
  }, [state])

  useEffect(() => {
    const festival = festivalEnabled ? getActiveFestival(new Date()) : { id: 'normal' as const, label: 'Normal' }
    document.documentElement.setAttribute('data-festival', festival.id)
  }, [festivalEnabled])

  // Auto-cycle wallpaper timer (defaults to every 30 seconds)
  useEffect(() => {
    if (!autoCycle) return
    const intervalMs = Math.max(5000, cycleIntervalSeconds * 1000)
    const timer = setInterval(() => {
      nextWallpaper()
    }, intervalMs)
    return () => clearInterval(timer)
  }, [autoCycle, cycleIntervalSeconds, nextWallpaper])

  // Dual-layer smooth crossfade when switching wallpapers
  const currentItem = WALLPAPERS.find(w => w.id === currentWallpaperId)
  const isImageWallpaper = currentWallpaperId !== 'none' && !!currentItem?.fullUrl

  const [layerA, setLayerA] = useState<string | null>(isImageWallpaper ? currentItem!.fullUrl : null)
  const [layerB, setLayerB] = useState<string | null>(null)
  const [showLayerA, setShowLayerA] = useState(true)

  useEffect(() => {
    const nextUrl = isImageWallpaper && currentItem ? currentItem.fullUrl : null

    if (showLayerA) {
      if (layerA === nextUrl) return
      setLayerB(nextUrl)
      setShowLayerA(false)
    } else {
      if (layerB === nextUrl) return
      setLayerA(nextUrl)
      setShowLayerA(true)
    }
  }, [currentWallpaperId, isImageWallpaper, currentItem])

  return (
    <div className="relative min-h-screen bg-background transition-colors duration-500">
      <div className="ambient-bg" aria-hidden="true">
        {/* Base Ambient Wash (Festival / AI reactive gradient) */}
        <div className="ambient-wash" />

        {/* Dual-Layer Crossfade Image Background Layer A */}
        {layerA && (
          <div
            className={`absolute inset-0 bg-cover bg-center pointer-events-none transition-opacity duration-1000 ease-in-out ${
              showLayerA ? 'opacity-100' : 'opacity-0'
            }`}
            style={{
              backgroundImage: `url(${layerA})`,
              filter: blur > 0 ? `blur(${blur}px)` : undefined,
              transform: 'scale(1.02)', // prevent edge blur leakage
            }}
          />
        )}

        {/* Dual-Layer Crossfade Image Background Layer B */}
        {layerB && (
          <div
            className={`absolute inset-0 bg-cover bg-center pointer-events-none transition-opacity duration-1000 ease-in-out ${
              !showLayerA ? 'opacity-100' : 'opacity-0'
            }`}
            style={{
              backgroundImage: `url(${layerB})`,
              filter: blur > 0 ? `blur(${blur}px)` : undefined,
              transform: 'scale(1.02)',
            }}
          />
        )}

        {/* Contrast Scrim / Theme Protector: Ensures 100% typography contrast in Light & Dark */}
        {(layerA || layerB) && (
          <div
            className="absolute inset-0 pointer-events-none transition-all duration-700"
            style={{
              backgroundColor: 'var(--color-background)',
              opacity: Math.max(0.08, 1 - opacity),
            }}
          />
        )}
      </div>

      <div className="relative z-10">{children}</div>
    </div>
  )
}