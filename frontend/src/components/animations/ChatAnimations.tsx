import React, { useMemo } from 'react'
import { motion } from 'framer-motion'
import { useReducedMotion } from '@/hooks/useReducedMotion'

interface StreamingTextProps {
  content: string
  speed?: number
  className?: string
}

export function StreamingText({ content, speed = 20, className = '' }: StreamingTextProps) {
  const reducedMotion = useReducedMotion()
  const [displayed, setDisplayed] = React.useState(reducedMotion ? content : '')
  const indexRef = React.useRef(0)

  React.useEffect(() => {
    if (reducedMotion) {
      setDisplayed(content)
      return
    }

    indexRef.current = 0
    setDisplayed('')

    const interval = setInterval(() => {
      if (indexRef.current < content.length) {
        setDisplayed(content.slice(0, indexRef.current + 1))
        indexRef.current++
      } else {
        clearInterval(interval)
      }
    }, speed)

    return () => clearInterval(interval)
  }, [content, speed, reducedMotion])

  return (
    <span className={className}>
      {displayed}
      {!reducedMotion && displayed.length < content.length && (
        <span className="streaming-cursor" />
      )}
    </span>
  )
}

interface MessageEntranceProps {
  children: React.ReactNode
  index?: number
  className?: string
}

export function MessageEntrance({ children, index = 0, className = '' }: MessageEntranceProps) {
  const reducedMotion = useReducedMotion()

  const variants = useMemo(() => ({
    hidden: { opacity: 0, y: 12, scale: reducedMotion ? 1 : 0.98 },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        delay: index * 0.05,
        duration: 0.3,
        ease: [0.25, 0.1, 0.25, 1],
      },
    },
  }), [index, reducedMotion])

  if (reducedMotion) {
    return <div className={className}>{children}</div>
  }

  return (
    <motion.div
      className={className}
      variants={variants}
      initial="hidden"
      animate="visible"
      layout
    >
      {children}
    </motion.div>
  )
}
