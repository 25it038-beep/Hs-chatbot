import React from 'react'
import { VideoJobResponse, videoApi } from '@/lib/videoApi'
import { Play, Download, Trash2, Copy, Film, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface VideoHistoryProps {
  videos: VideoJobResponse[]
  onSelect: (video: VideoJobResponse) => void
  onUsePrompt: (prompt: string) => void
  onDelete: (id: string) => void
  selectedId?: string
}

export function VideoHistory({
  videos,
  onSelect,
  onUsePrompt,
  onDelete,
  selectedId,
}: VideoHistoryProps) {
  if (videos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center border border-dashed border-border/60 rounded-2xl bg-muted/10">
        <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-3">
          <Film size={24} />
        </div>
        <p className="text-sm font-semibold text-foreground">No Generated Videos Yet</p>
        <p className="text-xs text-muted-foreground mt-1 max-w-xs">
          Compose a cinematic prompt on the left and start generating your first AI video.
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[520px] overflow-y-auto pr-1">
      {videos.map((v) => {
        const isSelected = selectedId === v.id
        const isCompleted = v.status === 'completed'
        const streamUrl = isCompleted ? videoApi.getStreamUrl(v.id) : undefined

        return (
          <div
            key={v.id}
            onClick={() => isCompleted && onSelect(v)}
            className={`group relative flex flex-col justify-between rounded-xl border p-3 transition-all cursor-pointer ${
              isSelected
                ? 'border-primary bg-primary/5 shadow-md'
                : 'border-border bg-card/60 hover:border-primary/40 hover:bg-muted/30'
            }`}
          >
            {/* Video preview / thumbnail */}
            {isCompleted ? (
              <div className="relative aspect-video rounded-lg bg-black/80 overflow-hidden mb-2.5 flex items-center justify-center">
                <video
                  src={streamUrl}
                  preload="metadata"
                  className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                />
                <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-transparent transition-colors">
                  <div className="w-8 h-8 rounded-full bg-primary/90 text-primary-foreground flex items-center justify-center shadow-md transform group-hover:scale-110 transition-transform">
                    <Play size={14} className="ml-0.5 fill-current" />
                  </div>
                </div>
                <span className="absolute bottom-1.5 right-1.5 px-1.5 py-0.5 rounded text-[10px] font-mono bg-black/70 text-white">
                  {v.duration_seconds}s
                </span>
              </div>
            ) : (
              <div className="relative aspect-video rounded-lg bg-muted/40 border border-border/50 mb-2.5 flex flex-col items-center justify-center text-xs text-muted-foreground">
                <span className="capitalize font-semibold text-foreground/80">{v.status}</span>
                <span className="text-[10px] mt-0.5">{v.model}</span>
              </div>
            )}

            {/* Prompt snippet */}
            <p className="text-xs font-medium text-foreground line-clamp-2 leading-relaxed">
              "{v.prompt}"
            </p>

            {/* Metadata & Actions */}
            <div className="flex items-center justify-between mt-3 pt-2 border-t border-border/40 text-[11px] text-muted-foreground">
              <span className="font-mono text-[10px] truncate max-w-[120px]">{v.model}</span>

              <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    onUsePrompt(v.prompt)
                  }}
                  title="Use Prompt"
                  className="p-1 hover:text-primary transition-colors"
                >
                  <Copy size={13} />
                </button>
                {isCompleted && (
                  <a
                    href={videoApi.getDownloadUrl(v.id)}
                    download={`${v.id}.mp4`}
                    onClick={(e) => e.stopPropagation()}
                    title="Download"
                    className="p-1 hover:text-primary transition-colors"
                  >
                    <Download size={13} />
                  </a>
                )}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    onDelete(v.id)
                  }}
                  title="Delete"
                  className="p-1 hover:text-destructive transition-colors"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
