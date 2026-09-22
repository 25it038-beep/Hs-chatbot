import React, { useState } from 'react'
import { Sparkles, ArrowRight, HelpCircle, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ClarificationQuiz } from '@/types'
import { useChatStore } from '@/stores/chat'

interface ClarificationQuizProps {
  quiz: ClarificationQuiz
  messageId: string
  className?: string
}

export function ClarificationQuizComponent({ quiz, messageId, className }: ClarificationQuizProps) {
  const [selectedOption, setSelectedOption] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { currentChat, sendMessage } = useChatStore()

  if (!quiz || !quiz.options || quiz.options.length === 0) {
    return null
  }

  const handleSelectOption = async (option: string) => {
    if (selectedOption || isSubmitting) return
    setSelectedOption(option)
    setIsSubmitting(true)
    try {
      await sendMessage(option, currentChat?.id)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div
      className={cn(
        'my-3 p-3.5 sm:p-4 rounded-xl border border-primary/20 bg-primary/[0.03] backdrop-blur-sm shadow-soft transition-all duration-200',
        className
      )}
    >
      {/* Quiz Header */}
      <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-primary uppercase tracking-wider">
        <div className="flex items-center justify-center w-5 h-5 rounded-full bg-primary/10 text-primary">
          <HelpCircle size={13} />
        </div>
        <span>Quick Clarification</span>
        {quiz.context && (
          <span className="ml-auto lowercase font-normal px-2 py-0.5 rounded-md bg-primary/10 text-primary text-[11px]">
            {quiz.context}
          </span>
        )}
      </div>

      <p className="text-sm font-medium text-foreground mb-3 leading-snug">
        {quiz.question}
      </p>

      {/* Option Pills */}
      <div className="flex flex-wrap gap-2">
        {quiz.options.map((option, idx) => {
          const isSelected = selectedOption === option
          return (
            <button
              key={`${quiz.id || messageId}-opt-${idx}`}
              onClick={() => handleSelectOption(option)}
              disabled={!!selectedOption || isSubmitting}
              className={cn(
                'group flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-[13px] font-medium border transition-all duration-150',
                isSelected
                  ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                  : 'bg-background hover:bg-muted/80 text-foreground/90 hover:text-foreground border-border/80 hover:border-primary/40 active:scale-[0.98]',
                selectedOption && !isSelected && 'opacity-50 cursor-not-allowed hover:bg-background hover:border-border/80'
              )}
            >
              {isSelected ? (
                <CheckCircle2 size={13} className="text-primary-foreground animate-in zoom-in-50" />
              ) : (
                <span className="w-1.5 h-1.5 rounded-full bg-primary/40 group-hover:bg-primary transition-colors" />
              )}
              <span>{option}</span>
              {!selectedOption && (
                <ArrowRight size={11} className="text-muted-foreground/40 group-hover:text-primary transition-colors ml-0.5" />
              )}
            </button>
          )
        })}
      </div>

      {quiz.allow_custom && !selectedOption && (
        <p className="mt-2.5 text-[11px] text-muted-foreground/70 italic">
          Tip: You can also type your custom preference directly into the chat input.
        </p>
      )}
    </div>
  )
}
