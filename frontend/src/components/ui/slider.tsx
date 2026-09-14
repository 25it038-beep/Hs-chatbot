import * as React from 'react'
import { cn } from '@/lib/utils'

interface SliderProps {
  value?: number[]
  onValueChange?: (value: number[]) => void
  min?: number
  max?: number
  step?: number
  className?: string
}

export function Slider({ value = [0], onValueChange, min = 0, max = 100, step = 1, className }: SliderProps) {
  return (
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value[0]}
      onChange={(e) => onValueChange?.([Number(e.target.value)])}
      className={cn('h-2 w-full cursor-pointer accent-primary', className)}
    />
  )
}
