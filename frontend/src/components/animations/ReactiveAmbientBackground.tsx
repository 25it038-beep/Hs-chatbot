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
    fit,
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

  const renderWallpaperLayer = (url: string | null, isVisible: boolean) => {
    if (!url) return null
    const combinedFilter = blur > 0 ? `blur(${blur}px)` : undefined

    if (fit === 'contain') {
      return (
        <div
          className={`absolute inset-0 pointer-events-none overflow-hidden transition-opacity duration-1000 ease-in-out ${
            isVisible ? 'opacity-100' : 'opacity-0'
          }`}
        >
          {/* Ambient blurred backdrop fills canvas */}
          <div
            className="absolute inset-0 bg-cover bg-center filter blur-2xl opacity-60 scale-110"
            style={{ backgroundImage: `url(${url})` }}
          />
          {/* Crisp uncropped foreground */}
          <div
            className="absolute inset-0 bg-contain bg-center bg-no-repeat"
            style={{
              backgroundImage: `url(${url})`,
              filter: combinedFilter,
            }}
          />
        </div>
      )
    }

    if (fit === 'stretch') {
      return (
        <div
          className={`absolute inset-0 bg-center bg-no-repeat pointer-events-none transition-opacity duration-1000 ease-in-out ${
            isVisible ? 'opacity-100' : 'opacity-0'
          }`}
          style={{
            backgroundImage: `url(${url})`,
            backgroundSize: '100% 100%',
            filter: combinedFilter,
          }}
        />
      )
    }

    // Default 'cover'
    return (
      <div
        className={`absolute inset-0 bg-cover bg-center pointer-events-none transition-opacity duration-1000 ease-in-out ${
          isVisible ? 'opacity-100' : 'opacity-0'
        }`}
        style={{
          backgroundImage: `url(${url})`,
          filter: combinedFilter,
          transform: 'scale(1.02)', // prevent edge blur leakage
        }}
      />
    )
  }

  return (
    <div className="relative min-h-screen bg-background transition-colors duration-500">
      <div className="ambient-bg" aria-hidden="true">
        {/* Base Ambient Wash (Festival / AI reactive gradient) */}
        <div className="ambient-wash" />

        {/* Dual-Layer Crossfade Image Background Layers */}
        {renderWallpaperLayer(layerA, showLayerA)}
        {renderWallpaperLayer(layerB, !showLayerA)}

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