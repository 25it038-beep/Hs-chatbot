'use client'

import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, VolumeX, Sparkles, Loader2, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { VOICE_STATES } from '@/lib/voice'

interface VoiceOrbProps {
  status: string
  audioLevel: number
  isHandsFree: boolean
  wakeWordDetected: boolean
  wsConnected: boolean
  onToggle: (enabled: boolean) => void
  onInterrupt?: () => void
  className?: string
}

export function VoiceOrb({
  status,
  audioLevel,
  isHandsFree,
  wakeWordDetected,
  wsConnected,
  onToggle,
  onInterrupt,
  className,
}: VoiceOrbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>(0)
  const [pulseScale, setPulseScale] = useState(1)
  const [particles, setParticles] = useState<Array<{ x: number; y: number; vx: number; vy: number; life: number; size: number }>>([])

  // Status configurations
  const statusConfig = {
    [VOICE_STATES.IDLE]: { color: 'hsl(var(--muted-foreground))', label: 'Hands-Free Mode', description: 'Click to activate' },
    [VOICE_STATES.LISTENING]: { color: 'hsl(var(--primary))', label: 'Listening...', description: 'Speak now' },
    [VOICE_STATES.SPEAKING]: { color: 'hsl(var(--primary))', label: 'You\'re speaking...', description: 'Recording your voice' },
    [VOICE_STATES.PROCESSING]: { color: 'hsl(var(--warning))', label: 'Thinking...', description: 'Processing your request' },
    [VOICE_STATES.AI_SPEAKING]: { color: 'hsl(var(--accent))', label: 'HS AI is speaking...', description: 'Playing response' },
    [VOICE_STATES.ERROR]: { color: 'hsl(var(--destructive))', label: 'Error', description: 'Something went wrong' },
  }

  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig[VOICE_STATES.IDLE]

  // Canvas animation for waveform/particles
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const resize = () => {
      const dpr = window.devicePixelRatio || 1
      canvas.width = canvas.offsetWidth * dpr
      canvas.height = canvas.offsetHeight * dpr
      ctx.scale(dpr, dpr)
    }
    resize()
    window.addEventListener('resize', resize)

    let frame = 0
    const animate = () => {
      if (!ctx) return
      
      const width = canvas.offsetWidth
      const height = canvas.offsetHeight
      const centerX = width / 2
      const centerY = height / 2

      ctx.clearRect(0, 0, width, height)

      // Draw background circle
      const baseRadius = Math.min(width, height) / 2 - 20
      
      // Pulsing rings based on audio level
      if (status === VOICE_STATES.LISTENING || status === VOICE_STATES.SPEAKING) {
        const ringCount = 4
        for (let i = 0; i < ringCount; i++) {
          const ringRadius = baseRadius + 10 + (frame * 2 + i * 30) % 60
          const opacity = 0.3 - (i * 0.07) + audioLevel * 0.3
          ctx.beginPath()
          ctx.arc(centerX, centerY, ringRadius, 0, Math.PI * 2)
          ctx.strokeStyle = `hsla(var(--primary), ${opacity})`
          ctx.lineWidth = 2
          ctx.stroke()
        }
      }

      // Main orb
      const orbRadius = baseRadius + audioLevel * 15 + Math.sin(frame * 0.1) * 3
      
      // Orb glow
      const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, orbRadius + 20)
      gradient.addColorStop(0, `${config.color}33`)
      gradient.addColorStop(1, 'transparent')
      ctx.beginPath()
      ctx.arc(centerX, centerY, orbRadius + 20, 0, Math.PI * 2)
      ctx.fillStyle = gradient
      ctx.fill()

      // Orb border
      ctx.beginPath()
      ctx.arc(centerX, centerY, orbRadius, 0, Math.PI * 2)
      ctx.strokeStyle = config.color
      ctx.lineWidth = 3
      ctx.stroke()

      // Inner pulse
      if (status === VOICE_STATES.AI_SPEAKING || status === VOICE_STATES.PROCESSING) {
        const innerRadius = orbRadius * 0.6 + Math.sin(frame * 0.2) * 5
        ctx.beginPath()
        ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2)
        ctx.fillStyle = `${config.color}44`
        ctx.fill()
      }

      // Wake word detection indicator
      if (wakeWordDetected) {
        ctx.beginPath()
        ctx.arc(centerX, centerY - orbRadius - 15, 8, 0, Math.PI * 2)
        ctx.fillStyle = 'hsl(var(--accent))'
        ctx.fill()
        ctx.beginPath()
        ctx.arc(centerX, centerY - orbRadius - 15, 4, 0, Math.PI * 2)
        ctx.fillStyle = 'white'
        ctx.fill()
      }

      // WebSocket status indicator
      if (!wsConnected && isHandsFree) {
        ctx.beginPath()
        ctx.arc(centerX + orbRadius - 10, centerY - orbRadius + 10, 6, 0, Math.PI * 2)
        ctx.fillStyle = 'hsl(var(--destructive))'
        ctx.fill()
      }

      // Waveform bars when speaking
      if (status === VOICE_STATES.SPEAKING || status === VOICE_STATES.LISTENING) {
        const barCount = 32
        const barWidth = (orbRadius * 2) / barCount
        for (let i = 0; i < barCount; i++) {
          const angle = (i / barCount) * Math.PI * 2
          const barHeight = (audioLevel + Math.random() * 0.3) * orbRadius * 0.8
          const x = centerX + Math.cos(angle) * orbRadius
          const y = centerY + Math.sin(angle) * orbRadius
          const endX = centerX + Math.cos(angle) * (orbRadius + barHeight)
          const endY = centerY + Math.sin(angle) * (orbRadius + barHeight)
          
          ctx.beginPath()
          ctx.moveTo(x, y)
          ctx.lineTo(endX, endY)
          ctx.strokeStyle = `${config.color}CC`
          ctx.lineWidth = barWidth * 0.8
          ctx.lineCap = 'round'
          ctx.stroke()
        }
      }

      // Particles for AI speaking
      if (status === VOICE_STATES.AI_SPEAKING) {
        if (Math.random() < 0.3) {
          setParticles(prev => [
            ...prev.slice(-50),
            {
              x: centerX + (Math.random() - 0.5) * orbRadius * 1.5,
              y: centerY + (Math.random() - 0.5) * orbRadius * 1.5,
              vx: (Math.random() - 0.5) * 2,
              vy: (Math.random() - 0.5) * 2 - 1,
              life: 1,
              size: Math.random() * 4 + 2,
            }
          ])
        }
      }

      // Update and draw particles
      setParticles(prev => {
        const updated = prev.map(p => ({
          ...p,
          x: p.x + p.vx,
          y: p.y + p.vy,
          life: p.life - 0.02,
        })).filter(p => p.life > 0)

        updated.forEach(p => {
          ctx.beginPath()
          ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2)
          ctx.fillStyle = `${config.color}${Math.floor(p.life * 255).toString(16).padStart(2, '0')}`
          ctx.fill()
        })

        return updated
      })

      frame++
      animationRef.current = requestAnimationFrame(animate)
    }

    animationRef.current = requestAnimationFrame(animate)

    return () => {
      cancelAnimationFrame(animationRef.current)
      window.removeEventListener('resize', resize)
    }
  }, [status, audioLevel, wakeWordDetected, wsConnected, isHandsFree])

  const handleClick = () => {
    if (status === VOICE_STATES.AI_SPEAKING) {
      onInterrupt?.()
    } else {
      onToggle(!isHandsFree)
    }
  }

  return (
    <div className={cn('relative flex flex-col items-center gap-4', className)} role="region" aria-label="Voice Assistant">
      <div className="relative" onClick={handleClick} style={{ cursor: 'pointer' }}>
        <canvas
          ref={canvasRef}
          width={200}
          height={200}
          className="block"
          aria-hidden="true"
        />
        
        {/* Center icon */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <AnimatePresence mode="wait">
            {status === VOICE_STATES.AI_SPEAKING ? (
              <motion.div
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                exit={{ scale: 0, rotate: 180 }}
                transition={{ duration: 0.3 }}
                className="text-4xl"
              >
                <Sparkles className="text-accent animate-spin" />
              </motion.div>
            ) : status === VOICE_STATES.PROCESSING ? (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
                transition={{ duration: 0.2 }}
                className="text-3xl"
              >
                <Loader2 className="text-primary animate-spin" />
              </motion.div>
            ) : status === VOICE_STATES.ERROR ? (
              <X className="text-3xl text-destructive" />
            ) : (
              <Mic className={cn(
                'text-3xl transition-all duration-300',
                status === VOICE_STATES.LISTENING || status === VOICE_STATES.SPEAKING
                  ? 'text-primary animate-pulse'
                  : 'text-muted-foreground'
              )} />
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Status text */}
      <div className="text-center space-y-1">
        <motion.h3
          key={status}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="text-lg font-medium text-foreground"
        >
          {config.label}
        </motion.h3>
        <motion.p
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -5 }}
          className="text-sm text-muted-foreground"
        >
          {config.description}
        </motion.p>
        
        {/* Connection status */}
        <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <span className={cn('w-2 h-2 rounded-full', wsConnected ? 'bg-green-500' : 'bg-red-500')} />
          <span>{wsConnected ? 'Connected' : isHandsFree ? 'Connecting...' : 'Disconnected'}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => onToggle(!isHandsFree)}
          className={cn(
            'p-3 rounded-full transition-all duration-200',
            isHandsFree
              ? 'bg-primary text-primary-foreground hover:bg-primary/90'
              : 'bg-muted hover:bg-muted/80 text-muted-foreground'
          )}
          aria-label={isHandsFree ? 'Disable Hands-Free Mode' : 'Enable Hands-Free Mode'}
          aria-pressed={isHandsFree}
        >
          {isHandsFree ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
        </button>

        {status === VOICE_STATES.AI_SPEAKING && onInterrupt && (
          <button
            onClick={onInterrupt}
            className="p-3 rounded-full bg-destructive/10 text-destructive hover:bg-destructive/20 transition-all duration-200"
            aria-label="Interrupt AI"
          >
            <VolumeX className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  )
}