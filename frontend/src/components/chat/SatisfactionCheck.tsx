import React, { useState } from 'react'
import { Check, ThumbsUp, MessageSquarePlus, RotateCcw, ShieldCheck, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { VerificationResult } from '@/types'
import { useChatStore } from '@/stores/chat'

interface SatisfactionCheckProps {
  verification?: VerificationResult
  messageId: string
  className?: string
}

export function SatisfactionCheckComponent({ verification, messageId, className }: SatisfactionCheckProps) {
  const [feedbackState, setFeedbackState] = useState<'idle' | 'satisfied' | 'adjusting'>('idle')
  const [showDetails, setShowDetails] = useState(false)
  const { currentChat, sendMessage } = useChatStore()

  const handleSatisfied = () => {
    setFeedbackState('satisfied')
  }

  const handleNeedMoreDetail = async () => {
    setFeedbackState('satisfied')
    await sendMessage('Could you please expand and provide more in-depth details on this?', currentChat?.id)
  }

  const handleAdjustmentOption = async (option: string) => {
    setFeedbackState('satisfied')
    await sendMessage(option, currentChat?.id)
  }

  if (feedbackState === 'satisfied') {
    return (
      <div className={cn('mt-2 flex items-center gap-2 text-xs text-muted-foreground/80 px-1 py-0.5', className)}>
        <Check size={12} className="text-emerald-500" />
        <span>Thank you for your feedback!</span>
        {verification?.sources_verified && (
          <span className="ml-auto inline-flex items-center gap-1 text-[11px] text-muted-foreground/60">
            <ShieldCheck size={11} className="text-primary/70" />
            Verified sources
          </span>
        )}
      </div>
    )
  }

  return (
    <div className={cn('mt-3 pt-2.5 border-t border-border/40 text-xs', className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-muted-foreground/80 font-medium">
          <span>Did this answer meet your needs?</span>
          {verification?.answer_verified && (
            <button
              onClick={() => setShowDetails(prev => !prev)}
              className="inline-flex items-center gap-0.5 ml-1 text-[11px] font-normal text-muted-foreground/60 hover:text-foreground transition-colors"
              title="View verification details"
            >
              <ShieldCheck size={11} className="text-primary/70" />
              <span>Verified</span>
              <ChevronDown size={10} className={cn('transition-transform', showDetails && 'rotate-180')} />
            </button>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleSatisfied}
            className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-muted/50 hover:bg-muted text-foreground/80 hover:text-foreground font-medium transition-colors border border-border/60 hover:border-border"
          >
            <ThumbsUp size={11} className="text-emerald-500" />
            <span>Yes, that&apos;s it</span>
          </button>

          <button
            onClick={handleNeedMoreDetail}
            className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-muted/50 hover:bg-muted text-foreground/80 hover:text-foreground font-medium transition-colors border border-border/60 hover:border-border"
          >
            <MessageSquarePlus size={11} className="text-sky-500" />
            <span>Need more detail</span>
          </button>

          <button
            onClick={() => setFeedbackState(feedbackState === 'adjusting' ? 'idle' : 'adjusting')}
            className={cn(
              'flex items-center gap-1 px-2.5 py-1 rounded-md font-medium transition-colors border',
              feedbackState === 'adjusting'
                ? 'bg-primary/10 text-primary border-primary/30'
                : 'bg-muted/50 hover:bg-muted text-foreground/80 hover:text-foreground border-border/60 hover:border-border'
            )}
          >
            <RotateCcw size={11} className="text-amber-500" />
            <span>Not what I meant</span>
          </button>
        </div>
      </div>

      {/* Verification details drawer */}
      {showDetails && verification && (
        <div className="mt-2 p-2 rounded-lg bg-muted/30 border border-border/50 text-[11px] text-muted-foreground space-y-1">
          <div className="flex items-center justify-between">
            <span>Grounding & Requirements:</span>
            <span className="text-emerald-500 font-medium">Complete</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Sources & Citations:</span>
            <span className="text-emerald-500 font-medium">Verified</span>
          </div>
          {verification.verification_notes && (
            <p className="text-[10px] text-muted-foreground/70 italic pt-0.5">
              {verification.verification_notes}
            </p>
          )}
        </div>
      )}

      {/* Adjustment Quick Pills */}
      {feedbackState === 'adjusting' && (
        <div className="mt-2.5 pt-2 border-t border-border/30 flex flex-wrap gap-1.5 animate-in fade-in-50 duration-150">
          <span className="text-[11px] text-muted-foreground/70 self-center mr-1">Quick fix:</span>
          {[
            'Simpler explanation',
            'Focus on practical examples',
            'More concise summary',
            'Compare with alternatives instead',
          ].map(opt => (
            <button
              key={opt}
              onClick={() => handleAdjustmentOption(opt)}
              className="px-2 py-0.5 rounded-full text-[11px] bg-background hover:bg-muted text-foreground border border-border/80 hover:border-primary/40 transition-colors"
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
