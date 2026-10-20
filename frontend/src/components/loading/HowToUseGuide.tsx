import React, { useState } from 'react'
import {
  MessageSquare,
  Code,
  FileText,
  Mic,
  Sparkles,
  Command,
  BookOpen,
  CheckCircle,
} from 'lucide-react'
import { HOW_TO_USE_GUIDES, type FeatureGuide } from '@/config/howToUse'

const ICON_MAP = {
  message: MessageSquare,
  code: Code,
  file: FileText,
  voice: Mic,
  router: Sparkles,
  command: Command,
}

export function HowToUseGuide() {
  const [selectedId, setSelectedId] = useState<string>(HOW_TO_USE_GUIDES[0].id)
  const activeGuide = HOW_TO_USE_GUIDES.find((g) => g.id === selectedId) || HOW_TO_USE_GUIDES[0]
  const ActiveIcon = ICON_MAP[activeGuide.icon] || Sparkles

  return (
    <div className="w-full space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="p-1.5 rounded-lg bg-brand/10 text-brand">
            <BookOpen size={14} />
          </span>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-foreground">
            Getting Started with HS Bot
          </h2>
        </div>
        <span className="text-[10px] text-muted-foreground/60 hidden sm:inline">
          Feature Guide
        </span>
      </div>

      {/* Feature Navigation Pills (Scrollable on small screens) */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar touch-pan-x">
        {HOW_TO_USE_GUIDES.map((guide) => {
          const Icon = ICON_MAP[guide.icon] || Sparkles
          const isSelected = guide.id === selectedId

          return (
            <button
              key={guide.id}
              onClick={() => setSelectedId(guide.id)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all duration-200 border flex-shrink-0 ${
                isSelected
                  ? 'bg-brand/15 text-brand border-brand/40 shadow-xs'
                  : 'bg-card/40 text-muted-foreground hover:text-foreground border-border/50 hover:bg-card/80'
              }`}
            >
              <Icon size={12} />
              <span>{guide.title.split(' ')[0]}</span>
            </button>
          )
        })}
      </div>

      {/* Active Feature Detail Card */}
      <div className="rounded-xl border border-border/80 bg-card/60 backdrop-blur-xl p-3.5 sm:p-4 shadow-xs transition-all">
        <div className="flex items-center gap-2 mb-2">
          <div className="p-1.5 rounded-lg bg-brand/15 text-brand">
            <ActiveIcon size={14} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold text-foreground">
                {activeGuide.title}
              </h3>
              <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground border border-border/60 uppercase">
                {activeGuide.badge}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-snug">
              {activeGuide.summary}
            </p>
          </div>
        </div>

        {/* Steps List */}
        <div className="space-y-1.5 pt-2 border-t border-border/40 mt-2">
          {activeGuide.steps.map((step, idx) => (
            <div key={idx} className="flex items-start gap-2 text-xs text-muted-foreground/90">
              <span className="flex-shrink-0 w-4 h-4 rounded-full bg-brand/10 text-brand text-[10px] font-bold flex items-center justify-center mt-0.5">
                {idx + 1}
              </span>
              <span className="leading-relaxed">{step}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
