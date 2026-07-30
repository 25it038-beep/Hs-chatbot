import React, { useRef, useCallback } from 'react'
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import { useReducedMotion } from '@/hooks/useReducedMotion'
import { useMotionConfig } from './MotionConfig'

interface AnimatedCardProps {
  children: React.ReactNode
  className?: string
  tiltDegree?: number
  glare?: boolean
  scale?: number
  shadow?: boolean
}

export function AnimatedCard({
  children,
  className = '',
  tiltDegree = 8,
  glare = true,
  scale = 1.02,
  shadow = true,
}: AnimatedCardProps) {
  const ref = useRef<HTMLDivElement>(null)
  const reducedMotion = useReducedMotion()
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)

  const rotateX = useSpring(useTransform(y, [-0.5, 0.5], [tiltDegree, -tiltDegree]), { stiffness: 200, damping: 20 })
  const rotateY = useSpring(useTransform(x, [-0.5, 0.5], [-tiltDegree, tiltDegree]), { stiffness: 200, damping: 20 })
  const glareX = useTransform(mouseX, [0, 1], [0, 100])
  const glareY = useTransform(mouseY, [0, 1], [0, 100])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (reducedMotion) return
    const rect = ref.current?.getBoundingClientRect()
    if (!rect) return
    const xVal = (e.clientX - rect.left) / rect.width - 0.5
    const yVal = (e.clientY - rect.top) / rect.height - 0.5
    x.set(xVal)
    y.set(yVal)
    mouseX.set((e.clientX - rect.left) / rect.width)
    mouseY.set((e.clientY - rect.top) / rect.height)
  }, [reducedMotion, x, y, mouseX, mouseY])

  const handleMouseLeave = useCallback(() => {
    x.set(0)
    y.set(0)
  }, [x, y])

  if (reducedMotion) {
    return <div className={className}>{children}</div>
  }

  return (
    <motion.div
      ref={ref}
      className={`relative ${className}`}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        perspective: 1000,
        rotateX,
        rotateY,
        transformStyle: 'preserve-3d',
      }}
      whileHover={{ scale }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
    >
      {children}
      {glare && (
        <motion.div
          className="absolute inset-0 rounded-[inherit] pointer-events-none overflow-hidden"
          style={{ mixBlendMode: 'overlay' }}
        >
          <motion.div
            className="absolute inset-0"
            style={{
              background: 'linear-gradient(135deg, rgba(255,255,255,0.3) 0%, transparent 50%)',
              left: glareX,
              top: glareY,
              width: '200%',
              height: '200%',
              transform: 'translate(-50%, -50%)',
            }}
          />
        </motion.div>
      )}
    </motion.div>
  )
}

export function FloatingCard({
  children,
  className = '',
  floatAmount = 6,
  duration = 4,
}: {
  children: React.ReactNode
  className?: string
  floatAmount?: number
  duration?: number
}) {
  const { reducedMotion } = useMotionConfig()
  if (reducedMotion) return <div className={className}>{children}</div>

  return (
    <motion.div
      className={className}
      animate={{ y: [0, -floatAmount, 0] }}
      transition={{ duration, repeat: Infinity, ease: 'easeInOut' }}
    >
      {children}
    </motion.div>
  )
}