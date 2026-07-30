import React, { createContext, useContext, useMemo } from 'react'
import { useReducedMotion } from '@/hooks/useReducedMotion'

export type SpringConfig = {
  type: 'spring'
  stiffness: number
  damping: number
  mass: number
}

export type MotionConfigValue = {
  reducedMotion: boolean
  spring: SpringConfig
  springGentle: SpringConfig
  springSnappy: SpringConfig
  springBouncy: SpringConfig
  stagger: { staggerChildren: number; delayChildren: number }
  viewport: { once: boolean; amount: number; margin: string }
}

const defaultConfig: MotionConfigValue = {
  reducedMotion: false,
  spring: { type: 'spring', stiffness: 300, damping: 30, mass: 1 },
  springGentle: { type: 'spring', stiffness: 200, damping: 25, mass: 1.2 },
  springSnappy: { type: 'spring', stiffness: 400, damping: 25, mass: 0.8 },
  springBouncy: { type: 'spring', stiffness: 350, damping: 15, mass: 1 },
  stagger: { staggerChildren: 0.05, delayChildren: 0.1 },
  viewport: { once: true, amount: 0.2, margin: '-50px' },
}

const MotionConfigCtx = createContext<MotionConfigValue>(defaultConfig)

export function MotionConfigProvider({ children }: { children: React.ReactNode }) {
  const prefersReduced = useReducedMotion()

  const value = useMemo(() => ({
    ...defaultConfig,
    reducedMotion: prefersReduced,
  }), [prefersReduced])

  return (
    <MotionConfigCtx.Provider value={value}>
      {children}
    </MotionConfigCtx.Provider>
  )
}

export function useMotionConfig() {
  return useContext(MotionConfigCtx)
}

export const fadeVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
}

export const slideUpVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
}

export const slideDownVariants = {
  hidden: { opacity: 0, y: -20 },
  visible: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 10 },
}

export const slideLeftVariants = {
  hidden: { opacity: 0, x: 20 },
  visible: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -10 },
}

export const slideRightVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 10 },
}

export const scaleVariants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.95 },
}

export const blurVariants = {
  hidden: { opacity: 0, filter: 'blur(8px)' },
  visible: { opacity: 1, filter: 'blur(0px)' },
  exit: { opacity: 0, filter: 'blur(8px)' },
}

export const staggerVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: (i: number = 0) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.05, ...defaultConfig.springGentle },
  }),
}