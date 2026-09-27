import React, { useState } from 'react'
import { Sparkles, StopCircle, ArrowUp, Cpu, FileCheck2, Lightbulb } from 'lucide-react'
import type { ModelProfile } from '@/lib/agentV2Api'

interface AgentV2ConversationBarProps {
  prompt: string
  setPrompt: (p: string) => void
  onSubmit: (customPrompt?: string) => void
  onInspectRequirements: () => void
  onStop: () => void
  isRunning: boolean
  models: ModelProfile[]
  selectedModel: string
  setSelectedModel: (m: string) => void
}

export function AgentV2ConversationBar({
  prompt,
  setPrompt,
  onSubmit,
  onInspectRequirements,
  onStop,
  isRunning,
  models,
  selectedModel,
  setSelectedModel
}: AgentV2ConversationBarProps) {
  const presets = [
    { label: 'Underwater Archaeological Expedition', text: 'Build a completely unique application for managing a fictional underwater archaeological expedition with artifact scanning and sonar mapping' },
    { label: 'Highway Traffic Racer', text: 'Build a fast 2D canvas highway car racing game with nitro boost, traffic lanes, high scores and sound effects' },
    { label: 'Restaurant Reservation Portal', text: 'Build a modern restaurant reservation and table booking portal with party size picker, menu view, and confirmation triage' },
    { label: 'Climate Science Simulator', text: 'Build a scientific climate simulation dashboard modeling atmospheric carbon concentrations, temperature anomalies, and projection models' }
  ]

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isRunning && prompt.trim()) {
      onSubmit()
    }
  }

  return (
    <div className="border-t border-border bg-card/80 backdrop-blur-md p-3 select-none flex-shrink-0 z-20 space-y-2">
      {/* Input bar */}
      <div className="flex items-center gap-2 max-w-5xl mx-auto">
        {/* Model Selector */}
        <div className="relative flex-shrink-0">
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            disabled={isRunning}
            className="h-10 text-xs font-mono font-semibold px-3 py-1.5 rounded-xl bg-background border border-border text-foreground focus:outline-hidden focus:ring-1 focus:ring-primary cursor-pointer disabled:opacity-50"
            title="Select NVIDIA AI Model for code synthesis"
          >
            {models.map((m) => (
              <option key={m.model_id} value={m.model_id}>
                {m.display_name}
              </option>
            ))}
          </select>
        </div>

        {/* Text Prompt Input */}
        <div className="flex-1 relative flex items-center">
          <input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isRunning}
            placeholder="Describe your product idea to direct the AI Company (e.g. 'Build an archaeology research workspace')..."
            className="w-full h-10 px-3.5 text-xs bg-background rounded-xl border border-border focus:outline-hidden focus:ring-1 focus:ring-primary text-foreground disabled:opacity-50"
          />
        </div>

        {/* Action Controls */}
        {isRunning ? (
          <button
            onClick={onStop}
            className="h-10 px-4 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-xs transition-colors"
          >
            <StopCircle size={14} />
            <span>Stop</span>
          </button>
        ) : (
          <div className="flex items-center gap-1.5">
            <button
              onClick={onInspectRequirements}
              disabled={!prompt.trim()}
              className="h-10 px-3 rounded-xl border border-primary/30 text-primary hover:bg-primary/5 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
              title="Analyze requirements sufficiency before launching"
            >
              <FileCheck2 size={13} />
              <span className="hidden sm:inline">Inspect Requirements</span>
            </button>

            <button
              onClick={() => onSubmit()}
              disabled={!prompt.trim()}
              className="h-10 px-4 rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground font-semibold text-xs flex items-center gap-1.5 shadow-xs transition-all disabled:opacity-50"
            >
              <Sparkles size={13} />
              <span>Launch Company</span>
            </button>
          </div>
        )}
      </div>

      {/* Domain Preset Chips */}
      <div className="flex items-center gap-1.5 max-w-5xl mx-auto overflow-x-auto text-[11px] pt-0.5">
        <span className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1 flex-shrink-0">
          <Lightbulb size={11} className="text-primary" />
          <span>Ideas:</span>
        </span>
        {presets.map((p, i) => (
          <button
            key={i}
            onClick={() => {
              setPrompt(p.text)
            }}
            className="px-2.5 py-0.5 rounded-lg border border-border/60 hover:border-border text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors whitespace-nowrap text-[11px]"
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  )
}
