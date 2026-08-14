import React, { useEffect, useRef, useState } from 'react'
import { useChat } from '@/stores/chat'
import { useAmbient } from '@/stores/ambient'
import { getActiveFestival } from '@/lib/festival'

type AmbientState = 'idle' | 'typing' | 'thinking' | 'streaming' | 'complete'

interface ReactiveAmbientBackgroundProps {
  children?: React.ReactNode
}

export function ReactiveAmbientBackground({ children }: ReactiveAmbientBackgroundProps) {
  const { streaming, streamingPhase, generatingImage, currentChat } = useChat()
  const { userTyping, festivalEnabled } = useAmbient()
  const [completePulse, setCompletePulse] = useState(false)
  const wasActiveRef = useRef(false)
  const phase = currentChat ? streamingPhase[currentChat.id] : undefined

  const active = streaming || generatingImage
  const state: AmbientState = active
    ? phase === 'thinking'
      ? 'thinking'
      : 'streaming'
    : userTyping
      ? 'typing'
      : completePulse
        ? 'complete'
        : 'idle'

  useEffect(() => {
    if (active) {
      wasActiveRef.current = true
      return
    }
    if (wasActiveRef.current) {
      wasActiveRef.current = false
      setCompletePulse(true)
      const timer = setTimeout(() => setCompletePulse(false), 2600)
      return () => clearTimeout(timer)
    }
  }, [active])

  useEffect(() => {
    document.documentElement.setAttribute('data-ai-state', state)
  }, [state])

  useEffect(() => {
    const festival = festivalEnabled ? getActiveFestival(new Date()) : { id: 'normal' as const, label: 'Normal' }
    document.documentElement.setAttribute('data-festival', festival.id)
  }, [festivalEnabled])

  return (
    <div className="relative min-h-screen bg-background">
      <div className="ambient-bg" aria-hidden="true">
        <div className="ambient-wash" />
      </div>
      <div className="relative z-10">{children}</div>
    </div>
  )
}