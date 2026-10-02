import React, { useEffect, useState } from 'react'
import {
  useWallpaperStore,
  WALLPAPERS,
  CYCLEABLE_WALLPAPERS,
  WallpaperItem,
} from '@/stores/wallpaper'
import {
  Sparkles,
  Play,
  Pause,
  SkipForward,
  SkipBack,
  Sliders,
  Check,
  X,
  Clock,
  Eye,
} from 'lucide-react'
import { Button } from '@/components/ui/button'

interface WallpaperPickerModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function WallpaperPickerModal({ open, onOpenChange }: WallpaperPickerModalProps) {
  const {
    currentWallpaperId,
    autoCycle,
    cycleIntervalSeconds,
    opacity,
    blur,
    fit,
    setFit,
    setWallpaper,
    setAutoCycle,
    setCycleIntervalSeconds,
    setOpacity,
    setBlur,
    nextWallpaper,
    prevWallpaper,
  } = useWallpaperStore()

  // Visual countdown timer for auto-cycle
  const [secondsRemaining, setSecondsRemaining] = useState(cycleIntervalSeconds)

  useEffect(() => {
    if (!autoCycle) {
      setSecondsRemaining(cycleIntervalSeconds)
      return
    }

    setSecondsRemaining(cycleIntervalSeconds)
    const interval = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          return cycleIntervalSeconds
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [autoCycle, cycleIntervalSeconds, currentWallpaperId])

  if (!open) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-background/80 backdrop-blur-md animate-fade-in"
      onClick={() => onOpenChange(false)}
    >
      <div
        className="w-full max-w-2xl bg-card border border-border shadow-2xl rounded-2xl overflow-hidden flex flex-col max-h-[90vh] animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-border flex items-center justify-between bg-muted/20">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
              <Sparkles size={16} />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-foreground">Wallpapers & Backgrounds</h2>
              <p className="text-xs text-muted-foreground">
                Macro floral & nature wallpapers • 30-second auto-cycle
              </p>
            </div>
          </div>

          <button
            onClick={() => onOpenChange(false)}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
            title="Close"
          >
            <X size={16} />
          </button>
        </div>

        {/* Quick Toolbar: 30s Auto-Cycle & Navigation */}
        <div className="px-5 py-3 border-b border-border bg-muted/10 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAutoCycle(!autoCycle)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border font-medium transition-all ${
                autoCycle
                  ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 shadow-xs'
                  : 'border-border bg-background hover:bg-muted text-muted-foreground hover:text-foreground'
              }`}
            >
              {autoCycle ? (
                <>
                  <Pause size={13} className="text-emerald-500" />
                  <span>Cycling (Every {cycleIntervalSeconds}s)</span>
                  <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-600 dark:text-emerald-300">
                    {secondsRemaining}s
                  </span>
                </>
              ) : (
                <>
                  <Play size={13} />
                  <span>Start 30s Auto-Cycle</span>
                </>
              )}
            </button>

            {/* Cycle Interval Quick Selector */}
            <div className="flex items-center gap-1 bg-background border border-border rounded-lg p-0.5">
              {[15, 30, 60].map((sec) => (
                <button
                  key={sec}
                  onClick={() => setCycleIntervalSeconds(sec)}
                  className={`px-2 py-1 rounded text-[11px] font-mono transition-all ${
                    cycleIntervalSeconds === sec
                      ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                  title={`Change background every ${sec} seconds`}
                >
                  {sec}s
                </button>
              ))}
            </div>

            {/* Fit Mode Switcher */}
            <div className="flex items-center gap-1 bg-background border border-border rounded-lg p-0.5 ml-1">
              {(
                [
                  { id: 'cover' as const, label: 'Fill' },
                  { id: 'contain' as const, label: 'Fit' },
                  { id: 'stretch' as const, label: 'Stretch' },
                ]
              ).map((mode) => (
                <button
                  key={mode.id}
                  onClick={() => setFit(mode.id)}
                  className={`px-2 py-1 rounded text-[11px] font-medium transition-all ${
                    fit === mode.id
                      ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                  title={
                    mode.id === 'contain'
                      ? 'Fit: Show entire image with ambient blur backdrop'
                      : mode.id === 'cover'
                      ? 'Fill: Crop to fill whole screen'
                      : 'Stretch: Stretch image to screen edges'
                  }
                >
                  {mode.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-1.5 ml-auto">
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={prevWallpaper}
              title="Previous Wallpaper"
            >
              <SkipBack size={12} />
              <span className="hidden sm:inline">Prev</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={nextWallpaper}
              title="Next Wallpaper"
            >
              <span className="hidden sm:inline">Next</span>
              <SkipForward size={12} />
            </Button>
          </div>
        </div>

        {/* Wallpaper Grid */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {WALLPAPERS.map((wp) => {
              const active = currentWallpaperId === wp.id
              const isAmbient = wp.id === 'none'
              const isMesh = wp.type === 'mesh'

              return (
                <button
                  key={wp.id}
                  onClick={() => setWallpaper(wp.id)}
                  className={`group relative flex flex-col rounded-xl overflow-hidden border text-left transition-all duration-200 ${
                    active
                      ? 'border-primary ring-2 ring-primary/40 shadow-lg scale-[1.02]'
                      : 'border-border/70 hover:border-foreground/30 hover:shadow-md'
                  }`}
                >
                  {/* Thumbnail Container */}
                  <div className="relative aspect-[4/3] w-full overflow-hidden bg-muted/40">
                    {isAmbient ? (
                      <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-indigo-500/20 via-purple-500/10 to-amber-500/20">
                        <Sparkles size={24} className="text-primary/70 animate-pulse" />
                      </div>
                    ) : isMesh ? (
                      <div
                        className="w-full h-full flex flex-col items-center justify-center relative p-3 text-center"
                        style={{
                          background:
                            wp.preset === 'neon'
                              ? 'linear-gradient(135deg, #04060a 0%, #7dff4d 40%, #ff2f92 70%, #29e6ff 100%)'
                              : wp.preset === 'mint'
                              ? 'linear-gradient(135deg, #f7f4e8 0%, #dcecd9 35%, #9ccfb2 70%, #5c9c85 100%)'
                              : wp.preset === 'noir'
                              ? 'linear-gradient(135deg, #08090b 0%, #2f3237 35%, #8b9099 70%, #f3f4f6 100%)'
                              : 'linear-gradient(135deg, #180814 0%, #48103e 35%, #95275f 70%, #e07a9c 100%)',
                        }}
                      >
                        <div className="px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-sm border border-white/20 text-[9px] font-mono font-bold text-white tracking-wider uppercase shadow-xs">
                          GPU MESH
                        </div>
                      </div>
                    ) : (
                      <img
                        src={wp.previewUrl}
                        alt={wp.title}
                        className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                        loading="lazy"
                      />
                    )}

                    {active && (
                      <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-primary text-primary-foreground flex items-center justify-center shadow-md">
                        <Check size={12} />
                      </div>
                    )}
                  </div>

                  {/* Label */}
                  <div className="p-2 bg-card">
                    <p className="text-xs font-semibold text-foreground truncate">{wp.title}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{wp.subtitle}</p>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Footer: Intensity & Depth Controls */}
        <div className="px-5 py-3.5 border-t border-border bg-muted/20 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4 flex-1 min-w-[200px]">
            <div className="flex items-center gap-2 flex-1">
              <Eye size={13} className="text-muted-foreground" />
              <span className="text-[11px] font-medium text-foreground whitespace-nowrap">
                Opacity: {Math.round(opacity * 100)}%
              </span>
              <input
                type="range"
                min="0.15"
                max="0.85"
                step="0.05"
                value={opacity}
                onChange={(e) => setOpacity(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
              />
            </div>

            <div className="flex items-center gap-2 flex-1">
              <Sliders size={13} className="text-muted-foreground" />
              <span className="text-[11px] font-medium text-foreground whitespace-nowrap">
                Blur: {blur}px
              </span>
              <input
                type="range"
                min="0"
                max="12"
                step="1"
                value={blur}
                onChange={(e) => setBlur(parseInt(e.target.value, 10))}
                className="w-full h-1.5 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
              />
            </div>
          </div>

          <Button
            size="sm"
            className="h-8 text-xs font-medium px-4 ml-auto"
            onClick={() => onOpenChange(false)}
          >
            Done
          </Button>
        </div>
      </div>
    </div>
  )
}
