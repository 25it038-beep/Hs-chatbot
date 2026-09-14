import * as React from 'react'
import { cn } from '@/lib/utils'

const Dialog = ({ open, onOpenChange, children }: { open?: boolean; onOpenChange?: (open: boolean) => void; children: React.ReactNode }) => (
  <div>{children}</div>
)

const DialogTrigger = ({ asChild, children }: { asChild?: boolean; children: React.ReactNode }) => <>{children}</>

const DialogContent = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={cn('rounded-xl border bg-background p-6 shadow-lg', className)}>{children}</div>
)

const DialogHeader = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={cn('mb-4', className)}>{children}</div>
)

const DialogTitle = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <h3 className={cn('text-lg font-semibold', className)}>{children}</h3>
)

const DialogDescription = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <p className={cn('text-sm text-muted-foreground', className)}>{children}</p>
)

export { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription }
