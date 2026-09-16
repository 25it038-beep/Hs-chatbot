/**
 * HSBot Live Voice System - Live Transcript View
 * 
 * Renders user and assistant speech turns with auto-scrolling
 * and distinct visual styling for speech bubbles.
 */

import React, { useEffect, useRef } from 'react'
import { LiveTranscriptItem } from '@/live/LiveTypes'
import { User, Bot } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LiveTranscriptProps {
  items: LiveTranscriptItem[]
  className?: string
}

export const LiveTranscript: React.FC<LiveTranscriptProps> = ({ items, className }) => {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [items])

  if (items.length === 0) {
    return (
      <div className={cn('flex flex-col items-center justify-center p-8 text-center text-muted-foreground text-xs', className)}>
        <p>Speak naturally into your microphone.</p>
        <p className="mt-1 text-[11px] opacity-70">NVIDIA ASR will transcribe your speech and NVIDIA TTS will respond in real time.</p>
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col gap-3 overflow-y-auto px-4 py-2 max-h-64', className)}>
      {items.map((item) => {
        const isUser = item.role === 'user'
        return (
          <div
            key={item.id}
            className={cn(
              'flex items-start gap-2.5 max-w-[85%]',
              isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'
            )}
          >
            <div
              className={cn(
                'w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs',
                isUser ? 'bg-primary text-primary-foreground' : 'bg-muted border border-border text-foreground'
              )}
            >
              {isUser ? <User size={12} /> : <Bot size={12} />}
            </div>

            <div
              className={cn(
                'px-3.5 py-2 rounded-2xl text-xs leading-relaxed transition-all',
                isUser
                  ? 'bg-primary text-primary-foreground rounded-tr-sm'
                  : 'bg-muted/70 text-foreground border border-border/40 rounded-tl-sm'
              )}
            >
              <p>{item.text}</p>
              {!item.isFinal && (
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-current ml-1 animate-pulse" />
              )}
            </div>
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}
