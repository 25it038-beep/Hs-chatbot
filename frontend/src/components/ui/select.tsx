import * as React from 'react'
import { cn } from '@/lib/utils'

const Select = ({ value, onValueChange, children }: { value?: string; onValueChange?: (value: string) => void; children: React.ReactNode }) => <>{children}</>

const SelectTrigger = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={cn('flex h-10 w-full items-center rounded-xl border border-input bg-background px-3', className)}>{children}</div>
)

const SelectValue = () => null

const SelectContent = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={cn('mt-1 rounded-xl border bg-background p-1 shadow-md', className)}>{children}</div>
)

const SelectItem = ({ value, children }: { value: string; children: React.ReactNode }) => <div data-value={value}>{children}</div>

export { Select, SelectTrigger, SelectValue, SelectContent, SelectItem }
