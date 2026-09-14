import * as React from 'react'
import { cn } from '@/lib/utils'

interface ToggleProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'onChange'> {
  pressed?: boolean
  onPressedChange?: (pressed: boolean) => void
}

export function Toggle({ pressed = false, onPressedChange, className, ...props }: ToggleProps) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      className={cn(
        'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors',
        pressed ? 'bg-primary' : 'bg-input',
        className
      )}
      onClick={() => onPressedChange?.(!pressed)}
      {...props}
    >
      <span
        className={cn(
          'pointer-events-none block h-5 w-5 rounded-full bg-white shadow transition-transform',
          pressed ? 'translate-x-5' : 'translate-x-0'
        )}
      />
    </button>
  )
}
