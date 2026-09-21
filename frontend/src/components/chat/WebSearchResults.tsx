import React, { useState, useRef } from 'react'
import { Globe, ChevronRight, ChevronLeft, Layers, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { WebSourceItem } from '@/types'
import { WebResultCard } from './WebResultCard'

interface WebSearchResultsProps {
  sources?: WebSourceItem[]
  query?: string
  className?: string
}

export function WebSearchResults({ sources, query, className }: WebSearchResultsProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  if (!sources || sources.length === 0) {
    return null
  }

  // Deduplicate sources by URL
  const uniqueSources = sources.filter(
    (item, index, self) => index === self.findIndex(t => t.url === item.url)
  )

  const handleScroll = (direction: 'left' | 'right') => {
    if (scrollContainerRef.current) {
      const scrollAmount = direction === 'left' ? -280 : 280
      scrollContainerRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' })
    }
  }

  return (
    <div className={cn('mb-4 rounded-xl transition-all', className)}>
      {/* Header Bar */}
      <div className="flex items-center justify-between gap-2 mb-2.5 px-0.5">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-5 h-5 rounded-md bg-primary/10 text-primary">
            <Globe size={13} />
          </div>
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Sources
          </span>
          <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-muted text-muted-foreground">
            {uniqueSources.length}
          </span>
          {query && (
            <span className="text-xs text-muted-foreground/60 truncate max-w-[200px] sm:max-w-xs hidden sm:inline">
              · &quot;{query}&quot;
            </span>
          )}
        </div>

        {uniqueSources.length > 3 && (
          <button
            onClick={() => setIsExpanded(prev => !prev)}
            className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-primary transition-colors py-1 px-2 rounded-lg hover:bg-muted/50"
          >
            <Layers size={12} />
            <span>{isExpanded ? 'Collapse' : `View all (${uniqueSources.length})`}</span>
          </button>
        )}
      </div>

      {/* Content: Carousel or Expanded Grid */}
      {isExpanded ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 pt-1 animate-fade-in">
          {uniqueSources.map((source, idx) => (
            <WebResultCard
              key={`${source.url}-${idx}`}
              source={source}
              index={idx}
            />
          ))}
        </div>
      ) : (
        <div className="relative group/carousel">
          {/* Scroll container */}
          <div
            ref={scrollContainerRef}
            className="flex items-stretch gap-2.5 overflow-x-auto pb-1.5 pt-0.5 scrollbar-thin scrollbar-thumb-muted-foreground/20 scroll-smooth"
            style={{ WebkitOverflowScrolling: 'touch' }}
          >
            {uniqueSources.map((source, idx) => (
              <WebResultCard
                key={`${source.url}-${idx}`}
                source={source}
                index={idx}
              />
            ))}
          </div>

          {/* Navigation scroll buttons for desktop */}
          {uniqueSources.length > 2 && (
            <>
              <button
                onClick={() => handleScroll('left')}
                aria-label="Scroll left"
                className="hidden sm:flex absolute -left-3 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-background/95 border border-border shadow-md items-center justify-center text-muted-foreground hover:text-foreground hover:scale-105 opacity-0 group-hover/carousel:opacity-100 transition-all z-10"
              >
                <ChevronLeft size={14} />
              </button>
              <button
                onClick={() => handleScroll('right')}
                aria-label="Scroll right"
                className="hidden sm:flex absolute -right-3 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-background/95 border border-border shadow-md items-center justify-center text-muted-foreground hover:text-foreground hover:scale-105 opacity-0 group-hover/carousel:opacity-100 transition-all z-10"
              >
                <ChevronRight size={14} />
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}
