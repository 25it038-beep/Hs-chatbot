import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMotionConfig, fadeVariants, scaleVariants, slideUpVariants, blurVariants } from './MotionConfig'

type TransitionType = 'fade' | 'scale' | 'slideUp' | 'blur'

interface PageTransitionProps {
  children: React.ReactNode
  type?: TransitionType
  duration?: number
  className?: string
  delay?: number
}

const variants: Record<TransitionType, { hidden: any; visible: any; exit: any }> = {
  fade: fadeVariants,
  scale: scaleVariants,
  slideUp: slideUpVariants,
  blur: blurVariants,
}

export function PageTransition({
  children,
  type = 'fade',
  duration = 0.35,
  className = '',
  delay = 0,
}: PageTransitionProps) {
  const { reducedMotion } = useMotionConfig()
  const v = variants[type]

  if (reducedMotion) {
    return <>{children}</>
  }

  return (
    <motion.div
      className={className}
      variants={v}
      initial="hidden"
      animate="visible"
      exit="exit"
      transition={{ duration, delay, ease: [0.25, 0.1, 0.25, 1] }}
    >
      {children}
    </motion.div>
  )
}

export function AnimatedPresence({
  children,
  mode = 'wait' as 'wait' | 'sync' | 'popLayout',
}: {
  children: React.ReactNode
  mode?: 'wait' | 'sync' | 'popLayout'
}) {
  return (
    <AnimatePresence mode={mode}>
      {children}
    </AnimatePresence>
  )
}

export function StaggerChildren({
  children,
  staggerDelay = 0.05,
  className = '',
}: {
  children: React.ReactNode
  staggerDelay?: number
  className?: string
}) {
  const { reducedMotion } = useMotionConfig()
  if (reducedMotion) return <>{children}</>

  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="visible"
      variants={{
        hidden: { opacity: 1 },
        visible: { transition: { staggerChildren: staggerDelay, delayChildren: 0.05 } },
      }}
    >
      {React.Children.map(children, (child) => (
        <motion.div
          variants={{
            hidden: { opacity: 0, y: 15 },
            visible: { opacity: 1, y: 0 },
          }}
        >
          {child}
        </motion.div>
      ))}
    </motion.div>
  )
}
