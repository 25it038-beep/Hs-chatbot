import React, { useRef, useState } from 'react'
import { VideoJobResponse, videoApi } from '@/lib/videoApi'
import { Play, Pause, Volume2, VolumeX, Maximize2, Download, Film, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface VideoPlayerProps {
  video: VideoJobResponse
  onClose?: () => void
}

export function VideoPlayer({ video }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(video.duration_seconds || 0)

  const streamUrl = videoApi.getStreamUrl(video.id)
  const downloadUrl = videoApi.getDownloadUrl(video.id)

  const togglePlay = () => {
    if (!videoRef.current) return
    if (isPlaying) {
      videoRef.current.pause()
      setIsPlaying(false)
    } else {
      videoRef.current.play()
      setIsPlaying(true)
    }
  }

  const toggleMute = () => {
    if (!videoRef.current) return
    videoRef.current.muted = !isMuted
    setIsMuted(!isMuted)
  }

  const toggleFullscreen = () => {
    if (!videoRef.current) return
    if (document.fullscreenElement) {
      document.exitFullscreen()
    } else {
      videoRef.current.requestFullscreen()
    }
  }

  const handleTimeUpdate = () => {
    if (!videoRef.current) return
    setCurrentTime(videoRef.current.currentTime)
  }

  const handleLoadedMetadata = () => {
    if (!videoRef.current) return
    setDuration(videoRef.current.duration || video.duration_seconds || 0)
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value)
    if (videoRef.current) {
      videoRef.current.currentTime = val
      setCurrentTime(val)
    }
  }

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = Math.floor(secs % 60)
    return `${m}:${s < 10 ? '0' : ''}${s}`
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return ''
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(1)} MB`
  }

  return (
    <div className="flex flex-col bg-background/95 rounded-2xl border border-border shadow-xl overflow-hidden">
      {/* Video Viewport */}
      <div className="relative aspect-video bg-black/90 flex items-center justify-center group overflow-hidden">
        <video
          ref={videoRef}
          src={streamUrl}
          className="w-full h-full object-contain"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
          playsInline
        />

        {/* Big Center Play Overlay */}
        {!isPlaying && (
          <button
            onClick={togglePlay}
            className="absolute inset-0 m-auto w-16 h-16 rounded-full bg-primary/90 text-primary-foreground flex items-center justify-center shadow-2xl hover:scale-110 active:scale-95 transition-all"
            aria-label="Play video"
          >
            <Play size={28} className="ml-1 fill-current" />
          </button>
        )}

        {/* Hover Controls Bar */}
        <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-3 flex flex-col gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          {/* Progress Slider */}
          <input
            type="range"
            min={0}
            max={duration || 1}
            step={0.1}
            value={currentTime}
            onChange={handleSeek}
            className="w-full h-1.5 bg-white/30 rounded-lg appearance-none cursor-pointer accent-primary"
          />

          <div className="flex items-center justify-between text-white text-xs">
            <div className="flex items-center gap-3">
              <button onClick={togglePlay} className="hover:text-primary transition-colors">
                {isPlaying ? <Pause size={16} /> : <Play size={16} className="fill-current" />}
              </button>
              <button onClick={toggleMute} className="hover:text-primary transition-colors">
                {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
              </button>
              <span>
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button onClick={toggleFullscreen} className="hover:text-primary transition-colors">
                <Maximize2 size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Info & Download Bar */}
      <div className="p-4 flex flex-col gap-3 bg-muted/20">
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-col gap-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-primary/10 text-primary border border-primary/20">
                <Film size={11} />
                {video.model}
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-muted font-medium text-muted-foreground border border-border">
                {video.width}×{video.height}
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-muted font-medium text-muted-foreground border border-border">
                {video.duration_seconds}s
              </span>
              {video.file_size && (
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-muted font-medium text-muted-foreground border border-border">
                  {formatFileSize(video.file_size)}
                </span>
              )}
            </div>
            <p className="text-sm font-medium line-clamp-2 text-foreground/90 mt-1">
              "{video.prompt}"
            </p>
          </div>

          <a
            href={downloadUrl}
            download={`${video.id}.mp4`}
            className="flex-shrink-0"
          >
            <Button size="sm" className="gap-1.5 rounded-xl shadow-xs">
              <Download size={14} />
              <span>Download MP4</span>
            </Button>
          </a>
        </div>
      </div>
    </div>
  )
}
