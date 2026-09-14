import * as React from 'react'
import { cn } from '@/lib/utils'

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'destructive'
}

export function Alert({ variant = 'default', className, ...props }: AlertProps) {
  return (
    <div
      role="alert"
      className={cn(
        'relative w-full rounded-xl border p-4',
        variant === 'destructive' ? 'border-red-200 bg-red-50 text-red-900' : 'border-blue-200 bg-blue-50 text-blue-950',
        className
      )}
      {...props}
    />
  )
}

export function AlertDescription({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('text-sm opacity-90', className)} {...props} />
}
