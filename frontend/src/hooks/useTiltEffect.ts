import { useRef, useCallback } from 'react'
import { useReducedMotion } from './useReducedMotion'

interface TiltOptions {
  scale?: number
  max?: number
  speed?: number
  glare?: boolean
}

export function useTiltEffect<T extends HTMLElement>({
  scale = 1.02,
  max = 12,
  speed = 400,
  glare = false,
}: TiltOptions = {}) {
  const ref = useRef<T>(null)
  const reduced = useReducedMotion()
  const state = useRef({ rect: { l: 0, t: 0, w: 0, h: 0 }, timeout: 0 as unknown as ReturnType<typeof setTimeout> })

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (reduced || !ref.current) return
    const el = ref.current
    const r = el.getBoundingClientRect()
    state.current.rect = { l: r.left, t: r.top, w: r.width, h: r.height }
    const x = e.clientX - r.left
    const y = e.clientY - r.top
    const xRot = ((y - r.height / 2) / r.height) * max
    const yRot = ((x - r.width / 2) / r.width) * -max
    el.style.transform = `perspective(800px) rotateX(${xRot}deg) rotateY(${yRot}deg) scale3d(${scale},${scale},${scale})`
  }, [reduced, max, scale])

  const handleMouseLeave = useCallback(() => {
    if (!ref.current) return
    const el = ref.current
    clearTimeout(state.current.timeout)
    el.style.transition = `transform ${speed}ms ease`
    el.style.transform = 'perspective(800px) rotateX(0deg) rotateY(0deg) scale3d(1,1,1)'
    state.current.timeout = setTimeout(() => { el.style.transition = '' }, speed)
  }, [speed])

  return { ref, handleMouseMove, handleMouseLeave }
}
