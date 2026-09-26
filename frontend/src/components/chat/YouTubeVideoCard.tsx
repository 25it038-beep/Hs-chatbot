import React from 'react'
import { Play, ExternalLink, Clock, Radio } from 'lucide-react'
import type { YouTubeVideoItem } from '@/types'

interface YouTubeVideoCardProps {
  video: YouTubeVideoItem
  index?: number
  onPlay: (video: YouTubeVideoItem) => void
}

export const YouTubeVideoCard: React.FC<YouTubeVideoCardProps> = ({
  video,
  index,
  onPlay,
}) => {
  return (
    <div className="group relative flex flex-col rounded-xl border border-border/70 bg-card/60 hover:bg-card/90 hover:border-border transition-all duration-200 shadow-sm hover:shadow-md overflow-hidden">
      {/* Thumbnail area */}
      <div
        className="relative aspect-video w-full bg-muted cursor-pointer overflow-hidden"
        onClick={() => onPlay(video)}
        role="button"
        tabIndex={0}
        aria-label={`Play ${video.title}`}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onPlay(video)
          }
        }}
      >
        <img
          src={video.thumbnail_url}
          alt={video.title}
          className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
          onError={(e) => {
            // Fallback thumbnail if HQ not available
            const target = e.currentTarget
            if (!target.src.includes('mqdefault')) {
              target.src = `https://img.youtube.com/vi/${video.video_id}/mqdefault.jpg`
            }
          }}
        />

        {/* Index badge */}
        {typeof index === 'number' && (
          <div className="absolute top-2 left-2 px-1.5 py-0.5 rounded bg-black/70 backdrop-blur-sm text-[10px] font-bold text-white tracking-wider">
            #{index + 1}
          </div>
        )}

        {/* Play Button Overlay */}
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/40 transition-colors">
          <div className="flex items-center justify-center w-11 h-11 rounded-full bg-red-600/90 text-white shadow-lg group-hover:scale-110 group-hover:bg-red-600 transition-all">
            <Play size={18} fill="currentColor" className="ml-0.5" />
          </div>
        </div>

        {/* Duration badge */}
        {video.duration && (
          <div className="absolute bottom-2 right-2 flex items-center gap-1 px-1.5 py-0.5 rounded bg-black/80 text-[11px] font-medium text-white shadow">
            <Clock size={10} />
            <span>{video.duration}</span>
          </div>
        )}
      </div>

      {/* Details area */}
      <div className="flex flex-col flex-1 p-3 gap-2">
        <h4
          className="text-xs sm:text-sm font-semibold text-foreground line-clamp-2 leading-snug cursor-pointer group-hover:text-red-500 transition-colors"
          onClick={() => onPlay(video)}
          title={video.title}
        >
          {video.title}
        </h4>

        <div className="flex items-center justify-between text-[11px] text-muted-foreground mt-auto pt-1">
          <div className="flex items-center gap-1.5 min-w-0 pr-2">
            <Radio size={11} className="text-red-500 shrink-0" />
            <span className="truncate font-medium text-foreground/80">{video.channel_title}</span>
          </div>
          {video.published_at && (
            <span className="shrink-0 text-[10px] text-muted-foreground/80">
              {video.published_at}
            </span>
          )}
        </div>

        {/* Action bar */}
        <div className="flex items-center gap-1.5 pt-2 border-t border-border/40">
          <button
            onClick={() => onPlay(video)}
            className="flex-1 inline-flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg bg-red-600/10 text-red-600 dark:text-red-400 hover:bg-red-600 hover:text-white text-xs font-medium transition-all"
          >
            <Play size={12} fill="currentColor" />
            <span>Play</span>
          </button>
          <a
            href={video.watch_url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-lg border border-border/60 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            title="Open directly on YouTube"
            aria-label="Open on YouTube"
          >
            <ExternalLink size={13} />
          </a>
        </div>
      </div>
    </div>
  )
}
