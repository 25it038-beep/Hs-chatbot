import React from 'react'
import { useReducedMotion } from '@/hooks/useReducedMotion'
import { FluidBackground } from './FluidBackground'

interface AnimatedBackgroundProps {
  children?: React.ReactNode
}

export function AnimatedBackground({ children }: AnimatedBackgroundProps) {
  const reducedMotion = useReducedMotion()

  if (reducedMotion) {
    return (
      <div className="relative min-h-screen bg-background">
        <div className="relative z-10">{children}</div>
      </div>
    )
  }

  return <FluidBackground>{children}</FluidBackground>
}
