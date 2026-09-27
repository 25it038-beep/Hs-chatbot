import React, { useEffect, useState } from 'react'
import { VideoJobResponse } from '@/lib/videoApi'
import { Loader2, XCircle, AlertCircle, Clock, Film } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface VideoJobCardProps {
  job: VideoJobResponse
  onCancel?: (jobId: string) => void
}

export function VideoJobCard({ job, onCancel }: VideoJobCardProps) {
  const [elapsed, setElapsed] = useState(job.elapsed_seconds || 0)

  useEffect(() => {
    if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
      setElapsed(job.elapsed_seconds)
      return
    }

    const start = job.started_at || job.created_at
    const timer = setInterval(() => {
      const sec = Math.max(0, Math.floor(Date.now() / 1000 - start))
      setElapsed(sec)
    }, 1000)

    return () => clearInterval(timer)
  }, [job.status, job.started_at, job.created_at, job.elapsed_seconds])

  const isFailed = job.status === 'failed'
  const isCancelled = job.status === 'cancelled'

  return (
    <div className="relative overflow-hidden rounded-2xl border border-primary/30 bg-gradient-to-br from-primary/5 via-background to-muted/30 p-5 shadow-lg">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10 text-primary border border-primary/20">
            {!isFailed && !isCancelled ? (
              <>
                <Loader2 size={20} className="animate-spin text-primary" />
                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-primary animate-ping" />
              </>
            ) : isFailed ? (
              <AlertCircle size={20} className="text-destructive" />
            ) : (
              <XCircle size={20} className="text-muted-foreground" />
            )}
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm capitalize text-foreground">
                {isFailed ? 'Generation Failed' : isCancelled ? 'Generation Cancelled' : 'Synthesizing Video'}
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded-md font-mono bg-primary/10 text-primary border border-primary/20">
                {job.model}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">{job.progress_stage}</p>
          </div>
        </div>

        {/* Real elapsed timer */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-background/80 border border-border text-xs font-mono font-medium text-foreground">
            <Clock size={12} className="text-primary" />
            <span>{elapsed}s</span>
          </div>

          {['queued', 'submitting', 'generating', 'processing'].includes(job.status) && onCancel && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onCancel(job.id)}
              className="h-7 text-xs rounded-lg text-muted-foreground hover:text-destructive border-border hover:border-destructive/40"
            >
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Prompt preview */}
      <div className="mt-3 text-xs text-muted-foreground line-clamp-1 italic bg-background/40 px-3 py-1.5 rounded-lg border border-border/40">
        "{job.prompt}"
      </div>

      {isFailed && job.error_message && (
        <div className="mt-2 text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-2.5">
          {job.error_message}
        </div>
      )}
    </div>
  )
}
