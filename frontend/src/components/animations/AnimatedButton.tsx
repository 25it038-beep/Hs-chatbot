import React, { useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { useReducedMotion } from '@/hooks/useReducedMotion'
import { useMotionConfig } from './MotionConfig'

interface AnimatedButtonProps {
  children: React.ReactNode
  className?: string
  magnetic?: boolean
  ripple?: boolean
  glow?: boolean
  onClick?: (e: React.MouseEvent) => void
  as?: 'button' | 'div'
}

export function AnimatedButton({
  children,
  className = '',
  magnetic = true,
  ripple = true,
  glow = false,
  onClick,
  as = 'button',
}: AnimatedButtonProps) {
  const ref = useRef<HTMLDivElement>(null)
  const reducedMotion = useReducedMotion()
  const [ripples, setRipples] = useState<Array<{ x: number; y: number; id: number }>>([])

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!magnetic || reducedMotion || !ref.current) return
    const rect = ref.current.getBoundingClientRect()
    const x = (e.clientX - rect.left - rect.width / 2) * 0.3
    const y = (e.clientY - rect.top - rect.height / 2) * 0.3
    ref.current.style.transform = `translate(${x}px, ${y}px)`
  }

  const handleMouseLeave = () => {
    if (!ref.current) return
    ref.current.style.transform = 'translate(0px, 0px)'
  }

  const handleClick = (e: React.MouseEvent) => {
    if (ripple && !reducedMotion && ref.current) {
      const rect = ref.current.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top
      const id = Date.now()
      setRipples((prev) => [...prev, { x, y, id }])
      setTimeout(() => setRipples((prev) => prev.filter((r) => r.id !== id)), 600)
    }
    onClick?.(e)
  }

  const Comp = as as any

  return (
    <Comp className={`relative inline-block ${className}`} onClick={handleClick}>
      <div
        ref={ref}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className="relative transition-transform duration-200 ease-out"
      >
        {children}
        {ripple && !reducedMotion && ripples.map((r) => (
          <span
            key={r.id}
            className="absolute pointer-events-none rounded-full bg-white/20 animate-ripple"
            style={{ left: r.x, top: r.y, width: 10, height: 10, transform: 'translate(-50%, -50%)' }}
          />
        ))}
      </div>
      {glow && !reducedMotion && (
        <motion.div
          className="absolute inset-0 rounded-[inherit] opacity-0 group-hover:opacity-100"
          style={{
            background: 'radial-gradient(circle at 50% 50%, rgba(59,130,246,0.15), transparent 70%)',
            filter: 'blur(10px)',
            zIndex: -1,
          }}
          animate={{ opacity: [0, 0.5, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}
    </Comp>
  )
}

export function MagneticButton({
  children,
  className = '',
  strength = 0.3,
}: {
  children: React.ReactNode
  className?: string
  strength?: number
}) {
  const ref = useRef<HTMLDivElement>(null)
  const reducedMotion = useReducedMotion()

  const handleMouseMove = (e: React.MouseEvent) => {
    if (reducedMotion || !ref.current) return
    const rect = ref.current.getBoundingClientRect()
    const x = (e.clientX - rect.left - rect.width / 2) * strength
    const y = (e.clientY - rect.top - rect.height / 2) * strength
    ref.current.style.transform = `translate(${x}px, ${y}px)`
  }

  const handleMouseLeave = () => {
    if (!ref.current) return
    ref.current.style.transform = 'translate(0px, 0px)'
  }

  return (
    <div
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={`inline-block transition-transform duration-200 ease-out ${className}`}
    >
      {children}
    </div>
  )
}