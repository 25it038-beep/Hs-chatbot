import React, { useRef, useEffect } from 'react'
import { useReducedMotion } from '@/hooks/useReducedMotion'

const MAX_PARTICLES = 3000
const SPAWN_RATE = 6
const IDLE_SPAWN_RATE = 1.2
const TRAIL_ALPHA_DARK = 0.06
const TRAIL_ALPHA_LIGHT = 0.025

interface Particle {
  x: number; y: number
  vx: number; vy: number
  size: number
  alpha: number
  life: number
  maxLife: number
  hue: number
  sat: number
  light: number
  alive: boolean
}

let pool: Particle[] = []
for (let i = 0; i < MAX_PARTICLES; i++) {
  pool.push({ x: 0, y: 0, vx: 0, vy: 0, size: 0, alpha: 0, life: 0, maxLife: 0, hue: 0, sat: 0, light: 0, alive: false })
}

let activeCount = 0

function acquire(): Particle | null {
  for (let i = 0; i < pool.length; i++) {
    if (!pool[i].alive) {
      pool[i].alive = true
      activeCount++
      return pool[i]
    }
  }
  return null
}

function release(p: Particle) {
  p.alive = false
  activeCount--
}

function getCSSBg(): string {
  if (typeof document === 'undefined') return '#020204'
  const val = getComputedStyle(document.documentElement).getPropertyValue('--color-background').trim()
  if (!val) return document.documentElement.classList.contains('dark') ? '#020204' : '#f2f3f7'
  const match = val.match(/hsl\(([\d.]+)\s+([\d.]+)%\s+([\d.]+)%/)
  if (!match) return '#020204'
  const l = parseFloat(match[3]) / 100
  const g = Math.round(l * 255)
  return `rgb(${g},${g},${g})`
}

export function FluidBackground({ children }: { children?: React.ReactNode }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const reducedMotion = useReducedMotion()

  useEffect(() => {
    if (reducedMotion) return

    const container = containerRef.current
    if (!container) return

    const canvas = document.createElement('canvas')
    canvas.style.position = 'fixed'
    canvas.style.inset = '0'
    canvas.style.width = '100%'
    canvas.style.height = '100%'
    canvas.style.pointerEvents = 'none'
    canvas.style.zIndex = '0'
    canvas.style.display = 'block'
    container.prepend(canvas)

    const ctx = canvas.getContext('2d', { alpha: false })!
    let w = 0, h = 0
    let mouseX = -1000, mouseY = -1000
    let mouseActive = false
    let mouseTimer = 0
    let running = true
    let bgColor = getCSSBg()
    let isDark = document.documentElement.classList.contains('dark')
    let hueOffset = 0
    let time = 0

    function resetCanvas() {
      ctx.globalCompositeOperation = 'source-over'
      ctx.globalAlpha = 1
      ctx.fillStyle = bgColor
      ctx.fillRect(0, 0, w, h)
    }

    const resize = () => {
      w = window.innerWidth
      h = window.innerHeight
      const dpr = Math.min(window.devicePixelRatio, 2)
      canvas.width = w * dpr
      canvas.height = h * dpr
      canvas.style.width = w + 'px'
      canvas.style.height = h + 'px'
      ctx.scale(dpr, dpr)
      resetCanvas()
    }
    resize()
    window.addEventListener('resize', resize)

    const handleMouse = (e: MouseEvent) => {
      mouseX = e.clientX
      mouseY = e.clientY
      mouseActive = true
      mouseTimer = 0
    }
    const handleMouseLeave = () => {
      mouseActive = false
    }
    window.addEventListener('mousemove', handleMouse)
    window.addEventListener('mouseleave', handleMouseLeave)

    const observer = new MutationObserver(() => {
      isDark = document.documentElement.classList.contains('dark')
      bgColor = getCSSBg()
      resetCanvas()
      for (const p of pool) { p.alive = false }
      activeCount = 0
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })

    let spawnAccum = 0

    const animate = () => {
      if (!running) return
      mouseTimer++
      time += 0.016

      const intensity = mouseActive && mouseTimer < 60 ? Math.min(1, 1 - (mouseTimer / 60)) : Math.max(0.15, 1 - mouseTimer / 120)

      if (isDark) {
        ctx.globalCompositeOperation = 'source-over'
        ctx.fillStyle = bgColor
        ctx.globalAlpha = TRAIL_ALPHA_DARK * (0.5 + 0.5 * intensity)
        ctx.fillRect(0, 0, w, h)
      }

      if (isDark) {
        hueOffset = (hueOffset + 0.15) % 360

        const spawnRate = mouseActive && mouseTimer < 30 ? SPAWN_RATE * intensity : IDLE_SPAWN_RATE
        spawnAccum += spawnRate
        const toSpawn = Math.min(Math.floor(spawnAccum), MAX_PARTICLES - activeCount)
        spawnAccum -= toSpawn

        for (let i = 0; i < toSpawn; i++) {
          const p = acquire()
          if (!p) break
          const angle = Math.random() * Math.PI * 2
          const dist = Math.random() * 60 + 10
          p.x = mouseActive ? mouseX + Math.cos(angle) * dist : Math.random() * w
          p.y = mouseActive ? mouseY + Math.sin(angle) * dist : Math.random() * h
          p.vx = (Math.random() - 0.5) * 0.8
          p.vy = (Math.random() - 0.5) * 0.8
          p.size = Math.random() * 5 + 1.5
          p.maxLife = 120 + Math.random() * 250
          p.alpha = 0.4 + Math.random() * 0.5
          const hueShift = Math.random() * 180 - 90
          p.hue = (hueOffset + hueShift + 360) % 360
          p.sat = 80 + Math.random() * 20
          p.light = 55 + Math.random() * 30
          p.life = p.maxLife
        }

        ctx.globalCompositeOperation = 'lighter'

        for (let i = 0; i < pool.length; i++) {
          const p = pool[i]
          if (!p.alive) continue

          p.life--
          if (p.life <= 0) { release(p); continue }

          const lifeRatio = p.life / p.maxLife
          const fadeIn = Math.min(1, (p.maxLife - p.life) / 15)
          const alpha = p.alpha * fadeIn * lifeRatio * (0.5 + 0.5 * intensity)

          p.x += p.vx + (Math.random() - 0.5) * 0.25
          p.y += p.vy + (Math.random() - 0.5) * 0.25

          if (p.x < -50 || p.x > w + 50 || p.y < -50 || p.y > h + 50) {
            release(p); continue
          }

          const radius = p.size * (0.3 + 0.7 * lifeRatio)
          const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, radius * 3)
          gradient.addColorStop(0, `hsla(${p.hue}, ${p.sat}%, ${p.light + 20}%, ${alpha})`)
          gradient.addColorStop(0.3, `hsla(${p.hue}, ${p.sat}%, ${p.light}%, ${alpha * 0.5})`)
          gradient.addColorStop(0.6, `hsla(${p.hue + 20}, ${p.sat}%, ${p.light - 10}%, ${alpha * 0.15})`)
          gradient.addColorStop(1, `hsla(${p.hue + 40}, ${p.sat}%, ${p.light - 20}%, 0)`)
          ctx.fillStyle = gradient
          ctx.beginPath()
          ctx.arc(p.x, p.y, radius * 3, 0, Math.PI * 2)
          ctx.fill()
        }

        if (mouseActive && mouseTimer < 30) {
          const glowHue = (hueOffset + 180) % 360
          const glow = ctx.createRadialGradient(mouseX, mouseY, 0, mouseX, mouseY, 80 + 40 * intensity)
          glow.addColorStop(0, `hsla(${glowHue}, 80%, 70%, ${0.08 * intensity})`)
          glow.addColorStop(0.5, `hsla(${glowHue + 30}, 70%, 50%, ${0.03 * intensity})`)
          glow.addColorStop(1, `hsla(0, 0%, 0%, 0)`)
          ctx.globalCompositeOperation = 'lighter'
          ctx.fillStyle = glow
          ctx.fillRect(mouseX - 120, mouseY - 120, 240, 240)
        }
      } else {
        ctx.globalCompositeOperation = 'source-over'
        ctx.fillStyle = bgColor
        ctx.globalAlpha = TRAIL_ALPHA_LIGHT * (0.3 + 0.7 * intensity)
        ctx.fillRect(0, 0, w, h)

        hueOffset = (hueOffset + 0.06) % 360

        const spawnRate = (mouseActive && mouseTimer < 30 ? SPAWN_RATE * intensity * 0.7 : IDLE_SPAWN_RATE * 0.6)
        spawnAccum += spawnRate
        const toSpawn = Math.min(Math.floor(spawnAccum), 200 - activeCount)
        spawnAccum -= toSpawn

        for (let i = 0; i < toSpawn; i++) {
          const p = acquire()
          if (!p) break
          const angle = Math.random() * Math.PI * 2
          const dist = Math.random() * 80 + 15
          p.x = mouseActive ? mouseX + Math.cos(angle) * dist : Math.random() * w
          p.y = mouseActive ? mouseY + Math.sin(angle) * dist : Math.random() * h
          const waveX = Math.sin(time * 0.3 + p.x * 0.005) * 0.15
          const waveY = Math.cos(time * 0.25 + p.y * 0.005) * 0.15
          p.vx = (Math.random() - 0.5) * 0.35 + waveX
          p.vy = (Math.random() - 0.5) * 0.35 + waveY - 0.08
          p.size = Math.random() * 3.5 + 1.2
          p.maxLife = 180 + Math.random() * 250
          p.alpha = 0.3 + Math.random() * 0.4
          const hueShift = Math.random() * 70 - 35
          p.hue = ((hueOffset * 0.4 + 230) + hueShift + 360) % 360
          p.sat = 30 + Math.random() * 30
          p.light = 58 + Math.random() * 18
          p.life = p.maxLife
        }

        ctx.globalCompositeOperation = 'source-over'

        for (let i = 0; i < pool.length; i++) {
          const p = pool[i]
          if (!p.alive) continue

          p.life--
          if (p.life <= 0) { release(p); continue }

          const lifeRatio = p.life / p.maxLife
          const fadeIn = Math.min(1, (p.maxLife - p.life) / 20)
          const alpha = p.alpha * fadeIn * lifeRatio * (0.4 + 0.6 * intensity)

          const waveX = Math.sin(time * 0.4 + p.x * 0.004) * 0.08
          const waveY = Math.cos(time * 0.35 + p.y * 0.004) * 0.08
          p.x += p.vx + waveX + (Math.random() - 0.5) * 0.06
          p.y += p.vy + waveY + (Math.random() - 0.5) * 0.06

          if (p.x < -50 || p.x > w + 50 || p.y < -50 || p.y > h + 50) {
            release(p); continue
          }

          const radius = p.size * (0.4 + 0.6 * lifeRatio)
          const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, radius * 5)
          gradient.addColorStop(0, `hsla(${p.hue}, ${p.sat}%, ${p.light + 15}%, ${alpha * 0.8})`)
          gradient.addColorStop(0.3, `hsla(${p.hue + 10}, ${p.sat}%, ${p.light}%, ${alpha * 0.35})`)
          gradient.addColorStop(0.6, `hsla(${p.hue + 25}, ${p.sat - 5}%, ${p.light - 5}%, ${alpha * 0.12})`)
          gradient.addColorStop(1, `hsla(${p.hue + 40}, ${p.sat - 10}%, ${p.light - 10}%, 0)`)
          ctx.fillStyle = gradient
          ctx.beginPath()
          ctx.arc(p.x, p.y, radius * 5, 0, Math.PI * 2)
          ctx.fill()
        }

        if (mouseActive && mouseTimer < 30) {
          const glowHue = (hueOffset * 0.5 + 270) % 360
          const glow = ctx.createRadialGradient(mouseX, mouseY, 0, mouseX, mouseY, 200 + 60 * intensity)
          glow.addColorStop(0, `hsla(${glowHue}, 35%, 75%, ${0.04 * intensity})`)
          glow.addColorStop(0.4, `hsla(${glowHue + 15}, 30%, 68%, ${0.02 * intensity})`)
          glow.addColorStop(1, `hsla(0, 0%, 100%, 0)`)
          ctx.globalCompositeOperation = 'source-over'
          ctx.fillStyle = glow
          ctx.fillRect(mouseX - 260, mouseY - 260, 520, 520)
        }
      }

      animRef.current = requestAnimationFrame(animate)
    }

    const animRef = { current: requestAnimationFrame(animate) }

    const visHandler = () => {
      if (document.hidden) { running = false; cancelAnimationFrame(animRef.current) }
      else { running = true; animRef.current = requestAnimationFrame(animate) }
    }
    document.addEventListener('visibilitychange', visHandler)

    return () => {
      running = false
      cancelAnimationFrame(animRef.current)
      window.removeEventListener('mousemove', handleMouse)
      window.removeEventListener('mouseleave', handleMouseLeave)
      window.removeEventListener('resize', resize)
      document.removeEventListener('visibilitychange', visHandler)
      observer.disconnect()
      canvas.remove()
      for (const p of pool) p.alive = false
      activeCount = 0
    }
  }, [reducedMotion])

  if (reducedMotion) return <>{children}</>

  return (
    <div ref={containerRef} className="relative min-h-screen">
      <div className="relative z-10">{children}</div>
    </div>
  )
}
