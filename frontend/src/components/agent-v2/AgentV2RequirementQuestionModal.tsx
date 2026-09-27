import React, { useState } from 'react'
import { HelpCircle, Check, ArrowRight, Sparkles } from 'lucide-react'
import type { AdaptiveQuestion } from '@/lib/agentV2Api'

interface AgentV2RequirementQuestionModalProps {
  question: AdaptiveQuestion
  onAnswer: (questionId: string, answer: string) => void
  onDismiss?: () => void
}

export function AgentV2RequirementQuestionModal({
  question,
  onAnswer,
  onDismiss
}: AgentV2RequirementQuestionModalProps) {
  const [selectedOption, setSelectedOption] = useState<string>(
    question.recommended_default || question.options[0] || ''
  )
  const [customAnswer, setCustomAnswer] = useState<string>('')
  const [isCustom, setIsCustom] = useState<boolean>(false)

  const handleConfirm = () => {
    const finalAnswer = isCustom ? customAnswer.trim() : selectedOption
    if (!finalAnswer) return
    onAnswer(question.question_id, finalAnswer)
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 select-none animate-in fade-in duration-150">
      <div className="bg-card border border-border w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-border bg-muted/30 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-bold">
              <HelpCircle size={16} />
            </div>
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-primary">Requirement Decision Needed</h3>
              <p className="text-[11px] text-muted-foreground">The architecture team needs your direction to proceed</p>
            </div>
          </div>
        </div>

        {/* Question Prompt */}
        <div className="p-5 space-y-4">
          <h4 className="text-sm font-semibold text-foreground leading-snug">
            {question.prompt}
          </h4>

          {/* Options */}
          <div className="space-y-2">
            {question.options.map((opt, idx) => {
              const isSelected = !isCustom && selectedOption === opt
              return (
                <button
                  key={idx}
                  onClick={() => {
                    setSelectedOption(opt)
                    setIsCustom(false)
                  }}
                  className={`w-full text-left p-3 rounded-xl border text-xs font-medium transition-all flex items-center justify-between gap-3 ${
                    isSelected
                      ? 'bg-primary/10 border-primary text-foreground shadow-xs'
                      : 'bg-card border-border/70 text-muted-foreground hover:text-foreground hover:bg-muted/40'
                  }`}
                >
                  <span className="leading-snug">{opt}</span>
                  {isSelected && <Check size={14} className="text-primary flex-shrink-0" />}
                </button>
              )
            })}

            {/* Custom option */}
            <div
              onClick={() => setIsCustom(true)}
              className={`p-3 rounded-xl border text-xs transition-all cursor-pointer ${
                isCustom
                  ? 'bg-primary/10 border-primary text-foreground'
                  : 'bg-card border-border/70 text-muted-foreground hover:bg-muted/40'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-xs">+ Provide custom direction</span>
                {isCustom && <Check size={14} className="text-primary" />}
              </div>
              {isCustom && (
                <textarea
                  value={customAnswer}
                  onChange={(e) => setCustomAnswer(e.target.value)}
                  placeholder="Specify custom requirement or rule..."
                  rows={2}
                  className="w-full text-xs p-2 rounded-lg bg-background border border-border focus:outline-hidden focus:ring-1 focus:ring-primary"
                  autoFocus
                />
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border bg-muted/20 flex items-center justify-between gap-2">
          {question.can_skip && onDismiss ? (
            <button
              onClick={onDismiss}
              className="text-xs text-muted-foreground hover:text-foreground font-medium px-3 py-1.5 rounded-lg transition-colors"
            >
              Use Recommendation
            </button>
          ) : (
            <div />
          )}

          <button
            onClick={handleConfirm}
            disabled={isCustom && !customAnswer.trim()}
            className="px-4 py-2 bg-primary text-primary-foreground font-semibold text-xs rounded-xl shadow-xs hover:bg-primary/90 transition-all flex items-center gap-1.5 disabled:opacity-50"
          >
            <span>Confirm & Continue</span>
            <ArrowRight size={13} />
          </button>
        </div>
      </div>
    </div>
  )
}
