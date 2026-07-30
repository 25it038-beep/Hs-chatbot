import React from 'react'
import { motion } from 'framer-motion'
import { useReducedMotion } from '@/hooks/useReducedMotion'

interface TextRevealProps {
  children: string
  className?: string
  delay?: number
  duration?: number
  once?: boolean
}

export function TextReveal({ children, className = '', delay = 0, duration = 0.03, once = true }: TextRevealProps) {
  const reducedMotion = useReducedMotion()

  if (reducedMotion) {
    return <span className={className}>{children}</span>
  }

  const words = children.split(' ')

  return (
    <span className={className}>
      {words.map((word, i) => (
        <span key={i} className="inline-block overflow-hidden" style={{ verticalAlign: 'bottom' }}>
          <motion.span
            className="inline-block"
            initial={{ y: '100%', opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            viewport={{ once }}
            transition={{
              duration: 0.4,
              delay: delay + i * duration,
              ease: [0.25, 0.1, 0.25, 1],
            }}
          >
            {word}{i < words.length - 1 ? '\u00A0' : ''}
          </motion.span>
        </span>
      ))}
    </span>
  )
}

export function CharReveal({ children, className = '', delay = 0 }: { children: string; className?: string; delay?: number }) {
  const reducedMotion = useReducedMotion()

  if (reducedMotion) return <span className={className}>{children}</span>

  return (
    <span className={className}>
      {children.split('').map((char, i) => (
        <motion.span
          key={i}
          className="inline-block"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: delay + i * 0.02, duration: 0.2, ease: 'easeOut' }}
        >
          {char === ' ' ? '\u00A0' : char}
        </motion.span>
      ))}
    </span>
  )
}
