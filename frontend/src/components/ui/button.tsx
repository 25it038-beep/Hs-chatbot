import React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cn } from '@/lib/utils'

const variantStyles = {
  default: 'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 active:scale-[0.97] transition-all',
  destructive: 'bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90 active:scale-[0.97] transition-all',
  outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground active:scale-[0.97] transition-all',
  secondary: 'bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80 active:scale-[0.97] transition-all',
  ghost: 'hover:bg-accent hover:text-accent-foreground active:scale-[0.97] transition-all',
  link: 'text-primary underline-offset-4 hover:underline',
}

const sizeStyles = {
  default: 'h-10 px-4 py-2',
  sm: 'h-9 rounded-lg px-3',
  lg: 'h-11 rounded-lg px-8',
  icon: 'h-10 w-10',
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variantStyles
  size?: keyof typeof sizeStyles
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return (
      <Comp
        className={cn(
          'inline-flex items-center justify-center whitespace-nowrap rounded-xl text-sm font-medium transition-all duration-150',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'

export { Button, variantStyles }
