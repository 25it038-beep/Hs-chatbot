import React, { useState } from 'react'
import { ExternalLink, Globe, Calendar, ShieldCheck } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { WebSourceItem } from '@/types'

interface WebResultCardProps {
  source: WebSourceItem
  index?: number
  isHighlighted?: boolean
}

export function WebResultCard({ source, index, isHighlighted }: WebResultCardProps) {
  const [faviconError, setFaviconError] = useState(false)

  const domain = source.domain || (() => {
    try {
      return new URL(source.url).hostname.replace(/^www\./, '')
    } catch {
      return 'web'
    }
  })()

  const sourceId = source.source_id || (index !== undefined ? index + 1 : undefined)
  const isOfficial = source.source_type === 'official' || source.source_type === 'government'

  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      id={sourceId ? `source-card-${sourceId}` : undefined}
      className={cn(
        'group relative flex flex-col justify-between p-3 rounded-xl border transition-all duration-200 text-left',
        'bg-card/70 hover:bg-accent/40 hover:shadow-md hover:-translate-y-0.5',
        'w-64 min-w-[16rem] max-w-[16rem] shrink-0 select-none overflow-hidden',
        isHighlighted
          ? 'border-primary ring-2 ring-primary/20 bg-primary/5'
          : 'border-border/60 hover:border-primary/40'
      )}
      title={source.title}
    >
      <div>
        {/* Top Header: Favicon + Domain + Source ID Badge */}
        <div className="flex items-center justify-between gap-1.5 mb-2">
          <div className="flex items-center gap-1.5 min-w-0">
            {!faviconError && source.favicon_url ? (
              <img
                src={source.favicon_url}
                alt=""
                className="w-4 h-4 rounded-sm shrink-0 object-contain"
                onError={() => setFaviconError(true)}
                loading="lazy"
              />
            ) : (
              <Globe className="w-4 h-4 text-muted-foreground/70 shrink-0" />
            )}
            <span className="text-[11px] font-medium text-muted-foreground truncate" title={domain}>
              {domain}
            </span>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            {isOfficial && (
              <span
                className="inline-flex items-center gap-0.5 text-[9px] font-semibold px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                title="Official / Government Source"
              >
                <ShieldCheck size={10} />
                Gov
              </span>
            )}
            {sourceId && (
              <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-muted text-[10px] font-bold text-muted-foreground group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                {sourceId}
              </span>
            )}
          </div>
        </div>

        {/* Title */}
        <h4 className="text-[13px] font-semibold leading-snug line-clamp-2 text-foreground group-hover:text-primary transition-colors mb-1.5">
          {source.title || domain}
        </h4>

        {/* Snippet */}
        {source.snippet && (
          <p className="text-[11px] leading-relaxed text-muted-foreground/80 line-clamp-2 mb-2">
            {source.snippet}
          </p>
        )}
      </div>

      {/* Footer: Date & Link Indicator */}
      <div className="flex items-center justify-between text-[10px] text-muted-foreground/60 pt-2 border-t border-border/30 mt-auto">
        <div className="flex items-center gap-1">
          {source.published_date && (
            <span className="inline-flex items-center gap-1 truncate max-w-[120px]">
              <Calendar size={10} />
              {source.published_date}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 text-muted-foreground group-hover:text-primary transition-colors">
          <span className="text-[10px] font-medium opacity-0 group-hover:opacity-100 transition-opacity">Open</span>
          <ExternalLink size={11} className="shrink-0" />
        </div>
      </div>
    </a>
  )
}
