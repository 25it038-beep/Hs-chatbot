import React, { useEffect, useState } from 'react'
import { X, ExternalLink, Play, AlertCircle } from 'lucide-react'
import type { YouTubeVideoItem } from '@/types'

interface YouTubePlayerModalProps {
  video: YouTubeVideoItem | null
  isOpen: boolean
  onClose: () => void
}

export const YouTubePlayerModal: React.FC<YouTubePlayerModalProps> = ({
  video,
  isOpen,
  onClose,
}) => {
  const [embedError, setEmbedError] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
      setEmbedError(false)
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, onClose])

  if (!isOpen || !video) return null

  const embedSrc = `https://www.youtube.com/embed/${video.video_id}?autoplay=1&rel=0&modestbranding=1`

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="yt-player-title"
    >
      <div
        className="relative w-full max-w-4xl bg-card border border-border/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/60 bg-muted/40">
          <div className="flex items-center gap-2 min-w-0 pr-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-md bg-red-600 text-white shrink-0">
              <Play size={12} fill="currentColor" />
            </span>
            <div className="min-w-0">
              <h3 id="yt-player-title" className="text-sm font-semibold truncate text-foreground">
                {video.title}
              </h3>
              <p className="text-xs text-muted-foreground truncate">
                {video.channel_title} {video.published_at ? `• ${video.published_at}` : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <a
              href={video.watch_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
              title="Open video on YouTube"
            >
              <span>Open on YouTube</span>
              <ExternalLink size={12} />
            </a>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              aria-label="Close video player"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Video Iframe Viewport */}
        <div className="relative w-full bg-black aspect-video flex items-center justify-center">
          {embedError ? (
            <div className="flex flex-col items-center justify-center p-6 text-center text-white space-y-3">
              <AlertCircle size={36} className="text-red-500" />
              <div className="max-w-md">
                <p className="font-semibold text-sm">Playback on other websites disabled</p>
                <p className="text-xs text-zinc-400 mt-1">
                  The video owner has restricted embedding. You can still watch it directly on YouTube.
                </p>
              </div>
              <a
                href={video.watch_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-xl bg-red-600 text-white hover:bg-red-700 transition-colors shadow-lg"
              >
                <span>Watch on YouTube</span>
                <ExternalLink size={13} />
              </a>
            </div>
          ) : (
            <iframe
              src={embedSrc}
              title={video.title}
              className="w-full h-full border-0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
              onError={() => setEmbedError(true)}
            />
          )}
        </div>

        {/* Footer info bar */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-muted/20 border-t border-border/40 text-xs text-muted-foreground">
          <span className="truncate">
            HSBot Interactive YouTube Player
          </span>
          {video.duration && (
            <span className="font-mono bg-muted/80 px-2 py-0.5 rounded text-[11px]">
              Duration: {video.duration}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
