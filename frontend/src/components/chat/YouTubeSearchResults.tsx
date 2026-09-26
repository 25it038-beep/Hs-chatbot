import React, { useState } from 'react'
import { Play, Tv, Sparkles } from 'lucide-react'
import type { YouTubeSearchResult, YouTubeVideoItem } from '@/types'
import { YouTubeVideoCard } from './YouTubeVideoCard'
import { YouTubePlayerModal } from './YouTubePlayerModal'

interface YouTubeSearchResultsProps {
  results: YouTubeSearchResult | YouTubeVideoItem[]
  query?: string
}

export const YouTubeSearchResults: React.FC<YouTubeSearchResultsProps> = ({
  results,
  query,
}) => {
  const [activeVideo, setActiveVideo] = useState<YouTubeVideoItem | null>(null)
  const [isPlayerOpen, setIsPlayerOpen] = useState(false)

  // Normalize results whether passed as YouTubeSearchResult object or array of videos
  const videoList: YouTubeVideoItem[] = Array.isArray(results)
    ? results
    : results?.results || []

  const searchQuery = query || (!Array.isArray(results) ? results?.query : '')

  const handlePlayVideo = (video: YouTubeVideoItem) => {
    setActiveVideo(video)
    setIsPlayerOpen(true)
  }

  const handleClosePlayer = () => {
    setIsPlayerOpen(false)
    setActiveVideo(null)
  }

  if (!videoList || videoList.length === 0) {
    return null
  }

  return (
    <div className="my-3 flex flex-col gap-2.5 rounded-2xl border border-red-500/20 bg-gradient-to-b from-red-500/[0.04] to-transparent p-3 sm:p-4">
      {/* Search Header */}
      <div className="flex items-center justify-between gap-2 pb-1 border-b border-border/50">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex items-center justify-center w-6 h-6 rounded-lg bg-red-600 text-white shadow-sm shrink-0">
            <Tv size={13} />
          </div>
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-xs sm:text-sm font-semibold text-foreground tracking-tight">
              YouTube Videos
            </span>
            {searchQuery && (
              <span className="text-xs text-muted-foreground truncate hidden xs:inline">
                for <span className="text-foreground font-medium italic">"{searchQuery}"</span>
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
            <Sparkles size={10} />
            <span>{videoList.length} {videoList.length === 1 ? 'video' : 'videos'}</span>
          </span>
        </div>
      </div>

      {/* Video Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        {videoList.map((video, idx) => (
          <YouTubeVideoCard
            key={video.video_id || idx}
            video={video}
            index={idx}
            onPlay={handlePlayVideo}
          />
        ))}
      </div>

      {/* Interactive Modal Player */}
      <YouTubePlayerModal
        video={activeVideo}
        isOpen={isPlayerOpen}
        onClose={handleClosePlayer}
      />
    </div>
  )
}
