import React from 'react'
import { ReactiveAmbientBackground } from './ReactiveAmbientBackground'

interface AnimatedBackgroundProps {
  children?: React.ReactNode
}

export function AnimatedBackground({ children }: AnimatedBackgroundProps) {
  return <ReactiveAmbientBackground>{children}</ReactiveAmbientBackground>
}