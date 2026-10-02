/**
 * HSBot Live Voice Fibonacci Point-Cloud Globe Visualizer.
 * 
 * Features:
 * - Fibonacci lattice distribution (~1,400 continent points)
 * - 3-term procedural trigonometric land mask
 * - Fixed -0.32 rad X-tilt with Y-spin rotation
 * - Depth-as-color rendering (near = accent color, far = cool white, volume transparency)
 * - Interactive pointer drag with inertia decay back to 0.0035 rad/frame
 * - Real-time Web Audio AnalyserNode reactivity for User Speech & AI Voice output
 * - Multi-state color adaptive theming (IDLE, LISTENING, USER_SPEAKING, PROCESSING, AI_SPEAKING, ERROR)
 */

import React, { useEffect, useRef } from 'react'
import { LiveState } from './LiveVoiceTypes'

export interface LiveGlobeVisualizerProps {
  state: LiveState
  micAnalyser: AnalyserNode | null
  outputAnalyser: AnalyserNode | null
  size?: number
  className?: string
  interactive?: boolean
}

interface Point3D {
  x: number
  y: number
  z: number
}

interface ProjectedPoint {
  sx: number
  sy: number
  dotRadius: number
  alpha: number
  isNear: boolean
  z: number
}

// ─────────────────────────────────────────────────────────────
// PRECOMPUTED FIBONACCI LAND MASK POINTS (Generated Once)
// ─────────────────────────────────────────────────────────────
const TARGET_KEPT = 1400
const OVERSAMPLE = 3.2
const MAX_CANDIDATES = Math.round(TARGET_KEPT * OVERSAMPLE)
const FIBONACCI_LAND_POINTS: Point3D[] = []

for (let i = 0; i < MAX_CANDIDATES && FIBONACCI_LAND_POINTS.length < TARGET_KEPT; i++) {
  // Fibonacci lattice
  const y = 1 - (i / MAX_CANDIDATES) * 2
  const r = Math.sqrt(Math.max(0, 1 - y * y))
  const theta = i * 2.399963
  const x = Math.cos(theta) * r
  const z = Math.sin(theta) * r

  // Spherical coordinates
  const lat = Math.asin(Math.max(-1, Math.min(1, y)))
  const lon = Math.atan2(z, x)

  // 3-term trigonometric land mask
  const s =
    Math.sin(lat * 3.1) * Math.cos(lon * 2.2) +
    Math.sin(lon * 1.3 + 1.1) * Math.cos(lat * 1.7) +
    0.6 * Math.sin((lat + lon) * 4.3)

  if (s > 0.25) {
    FIBONACCI_LAND_POINTS.push({ x, y, z })
  }
}

// State-to-accent RGB mapping
const STATE_ACCENTS: Record<LiveState, [number, number, number]> = {
  IDLE: [56, 189, 248],           // Electric Cyan
  CONNECTING: [168, 85, 247],     // Violet/Purple
  CONNECTED: [56, 189, 248],      // Electric Cyan
  LISTENING: [52, 211, 153],      // Emerald Green (Microphone listening)
  PROCESSING: [168, 85, 247],     // Shifting Purple (Thinking)
  SPEAKING: [96, 165, 250],       // Luminous Azure (AI speaking)
  INTERRUPTED: [251, 146, 60],    // Amber
  ERROR: [248, 113, 113],         // Coral Red
  DISCONNECTED: [148, 163, 184],  // Slate Gray
}

export function LiveGlobeVisualizer({
  state,
  micAnalyser,
  outputAnalyser,
  size = 330,
  className = '',
  interactive = true,
}: LiveGlobeVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const stateRef = useRef<LiveState>(state)
  const micAnalyserRef = useRef<AnalyserNode | null>(micAnalyser)
  const outputAnalyserRef = useRef<AnalyserNode | null>(outputAnalyser)

  useEffect(() => {
    stateRef.current = state
  }, [state])

  useEffect(() => {
    micAnalyserRef.current = micAnalyser
  }, [micAnalyser])

  useEffect(() => {
    outputAnalyserRef.current = outputAnalyser
  }, [outputAnalyser])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId: number
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const baseRadius = (size * 0.42)

    canvas.width = Math.round(size * dpr)
    canvas.height = Math.round(size * dpr)
    canvas.style.width = `${size}px`
    canvas.style.height = `${size}px`
    ctx.scale(dpr, dpr)

    // Constants per spec
    const TILT_X = -0.32
    const COS_TILT_X = Math.cos(TILT_X)
    const SIN_TILT_X = Math.sin(TILT_X)
    const IDLE_VEL = 0.0035

    // State variables
    let rotY = 0
    let vel = IDLE_VEL
    let isDragging = false
    let lastX = 0

    // Audio reactivity buffers
    const micData = new Uint8Array(64)
    const outData = new Uint8Array(64)
    let smoothedEnergy = 0

    // Reusable projection buffer to prevent GC allocations at 60 FPS
    const projected: ProjectedPoint[] = FIBONACCI_LAND_POINTS.map(() => ({
      sx: 0,
      sy: 0,
      dotRadius: 0,
      alpha: 0,
      isNear: false,
      z: 0,
    }))

    // Pointer handlers
    const onPointerDown = (e: PointerEvent) => {
      if (!interactive) return
      try {
        canvas.setPointerCapture(e.pointerId)
      } catch (_) {}
      isDragging = true
      vel = 0
      lastX = e.clientX
    }

    const onPointerMove = (e: PointerEvent) => {
      if (!isDragging) return
      const dx = e.clientX - lastX
      const deltaRot = dx * 0.006
      rotY += deltaRot
      vel = deltaRot
      lastX = e.clientX
    }

    const onPointerUp = (e: PointerEvent) => {
      if (!isDragging) return
      isDragging = false
      try {
        canvas.releasePointerCapture(e.pointerId)
      } catch (_) {}
    }

    if (interactive) {
      canvas.addEventListener('pointerdown', onPointerDown)
      canvas.addEventListener('pointermove', onPointerMove)
      canvas.addEventListener('pointerup', onPointerUp)
      canvas.addEventListener('pointercancel', onPointerUp)
    }

    // Color transition interpolation
    let currentRGB: [number, number, number] = [...STATE_ACCENTS[stateRef.current]]

    const render = () => {
      animId = requestAnimationFrame(render)

      // Audio analysis
      let rawEnergy = 0
      const currentState = stateRef.current

      if (currentState === 'SPEAKING' && outputAnalyserRef.current) {
        outputAnalyserRef.current.getByteFrequencyData(outData)
        let sum = 0
        for (let i = 0; i < outData.length; i++) sum += outData[i]
        rawEnergy = (sum / (outData.length * 255)) * 2.0
      } else if (micAnalyserRef.current && (currentState === 'LISTENING' || currentState === 'CONNECTED' || currentState === 'IDLE')) {
        micAnalyserRef.current.getByteFrequencyData(micData)
        let sum = 0
        for (let i = 0; i < micData.length; i++) sum += micData[i]
        rawEnergy = (sum / (micData.length * 255)) * 1.8
      }

      // Smooth audio energy lerp
      smoothedEnergy += (rawEnergy - smoothedEnergy) * 0.22

      // Target idle velocity: slightly faster when processing
      const targetIdle = currentState === 'PROCESSING' ? 0.008 : IDLE_VEL

      // Drag inertia decay
      if (!isDragging) {
        vel += (targetIdle - vel) * 0.02
        rotY += vel
      }

      // Smooth color transition
      const targetRGB = STATE_ACCENTS[currentState] || STATE_ACCENTS.IDLE
      currentRGB[0] += (targetRGB[0] - currentRGB[0]) * 0.1
      currentRGB[1] += (targetRGB[1] - currentRGB[1]) * 0.1
      currentRGB[2] += (targetRGB[2] - currentRGB[2]) * 0.1

      // Canvas dimensions
      const cx = size / 2
      const cy = size / 2
      ctx.clearRect(0, 0, size, size)

      // Dynamic reactive radius
      const currentRadius = baseRadius * (1 + smoothedEnergy * 0.1)
      const baseDotRadius = Math.max(1.8, currentRadius * 0.0145)

      const cosY = Math.cos(rotY)
      const sinY = Math.sin(rotY)

      // Project each point
      for (let i = 0; i < FIBONACCI_LAND_POINTS.length; i++) {
        const p = FIBONACCI_LAND_POINTS[i]

        // 1. Spin around Y
        const x1 = p.x * cosY + p.z * sinY
        const y1 = p.y
        const z1 = -p.x * sinY + p.z * cosY

        // 2. Tilt around X by fixed -0.32 rad
        const x2 = x1
        const y2 = y1 * COS_TILT_X - z1 * SIN_TILT_X
        const z2 = y1 * SIN_TILT_X + z1 * COS_TILT_X

        // 3. Depth = (z + 1) / 2
        const depth = (z2 + 1) * 0.5

        // 4. Perspective factor = 0.86 + depth * 0.28
        const perspective = 0.86 + depth * 0.28
        const sx = cx + x2 * currentRadius * perspective
        const sy = cy - y2 * currentRadius * perspective

        // 5. Dot radius = 0.45 + depth * 0.85
        const audioDotBoost = 1 + smoothedEnergy * 0.25 * (depth > 0.5 ? 1 : 0.3)
        const dotRadius = baseDotRadius * (0.45 + depth * 0.85) * audioDotBoost

        // 6. Depth is color, not culling:
        // Near side (z2 >= 0): accent color at 0.18 + depth * 0.72
        // Far side (z2 < 0): cool white at 0.06 + depth * 0.30
        const isNear = z2 >= 0
        const baseAlpha = isNear
          ? Math.max(0.12, Math.min(1.0, 0.18 + depth * 0.72))
          : Math.max(0.04, Math.min(0.4, 0.06 + depth * 0.30))

        const alpha = Math.min(1.0, baseAlpha * (1 + smoothedEnergy * 0.3))

        const item = projected[i]
        item.sx = sx
        item.sy = sy
        item.dotRadius = dotRadius
        item.alpha = alpha
        item.isNear = isNear
        item.z = z2
      }

      // Sort points back-to-front
      projected.sort((a, b) => a.z - b.z)

      // Draw all points
      const r = Math.round(currentRGB[0])
      const g = Math.round(currentRGB[1])
      const b = Math.round(currentRGB[2])

      for (let i = 0; i < projected.length; i++) {
        const pt = projected[i]
        ctx.beginPath()
        ctx.arc(pt.sx, pt.sy, pt.dotRadius, 0, Math.PI * 2)

        if (pt.isNear) {
          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${pt.alpha})`
        } else {
          // Cool white on far hemisphere for transparent volume look
          ctx.fillStyle = `rgba(224, 231, 255, ${pt.alpha})`
        }

        ctx.fill()
      }
    }

    render()

    return () => {
      cancelAnimationFrame(animId)
      if (interactive) {
        canvas.removeEventListener('pointerdown', onPointerDown)
        canvas.removeEventListener('pointermove', onPointerMove)
        canvas.removeEventListener('pointerup', onPointerUp)
        canvas.removeEventListener('pointercancel', onPointerUp)
      }
    }
  }, [size, interactive])

  return (
    <div
      className={`relative flex items-center justify-center select-none ${className}`}
      style={{ width: size, height: size }}
    >
      {/* Ambient background soft glow aura */}
      <div
        className="absolute inset-0 rounded-full pointer-events-none transition-colors duration-700 blur-2xl opacity-40"
        style={{
          background: `radial-gradient(circle, rgba(${STATE_ACCENTS[state].join(',')}, 0.22) 0%, transparent 70%)`,
        }}
      />
      <canvas
        ref={canvasRef}
        className="relative z-10 touch-none cursor-grab active:cursor-grabbing"
      />
    </div>
  )
}
