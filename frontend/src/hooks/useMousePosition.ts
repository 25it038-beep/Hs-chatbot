import { useState, useEffect } from 'react'

interface MousePosition {
  x: number
  y: number
  vx: number
  vy: number
}

export function useMousePosition() {
  const [pos, setPos] = useState<MousePosition>({ x: 0, y: 0, vx: 0, vy: 0 })
  const [prev, setPrev] = useState({ x: 0, y: 0 })

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      setPos(p => {
        const vx = e.clientX - p.x
        const vy = e.clientY - p.y
        return { x: e.clientX, y: e.clientY, vx, vy }
      })
      setPrev({ x: e.clientX, y: e.clientY })
    }
    window.addEventListener('mousemove', handler)
    return () => window.removeEventListener('mousemove', handler)
  }, [])

  return pos
}