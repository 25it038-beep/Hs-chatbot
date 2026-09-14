import * as React from 'react'
import { cn } from '@/lib/utils'

const AlertDialog = ({ children, open }: { children: React.ReactNode; open?: boolean }) => <>{children}</>
const AlertDialogAction = ({ children, className, onClick }: { children: React.ReactNode; className?: string; onClick?: () => void }) => <button className={cn(className)} onClick={onClick}>{children}</button>
const AlertDialogCancel = ({ children, className, onClick }: { children: React.ReactNode; className?: string; onClick?: () => void }) => <button className={cn(className)} onClick={onClick}>{children}</button>
const AlertDialogContent = ({ children, className }: { children: React.ReactNode; className?: string }) => <div className={cn('rounded-xl border bg-background p-6', className)}>{children}</div>
const AlertDialogDescription = ({ children, className }: { children: React.ReactNode; className?: string }) => <p className={cn('text-sm text-muted-foreground', className)}>{children}</p>
const AlertDialogHeader = ({ children, className }: { children: React.ReactNode; className?: string }) => <div className={cn('mb-4', className)}>{children}</div>
const AlertDialogTitle = ({ children, className }: { children: React.ReactNode; className?: string }) => <h3 className={cn('text-lg font-semibold', className)}>{children}</h3>

export { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogHeader, AlertDialogTitle }
