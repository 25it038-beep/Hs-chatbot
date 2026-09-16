/**
 * HSBot Live Voice System - Isolated Error Boundary
 * 
 * Guarantees that any unexpected runtime error inside Live Voice
 * is isolated and never crashes the main chat application.
 */

import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  onReset?: () => void
}

interface State {
  hasError: boolean
  error: Error | null
}

export class LiveErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[LiveErrorBoundary] Caught error:', error, errorInfo)
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null })
    this.props.onReset?.()
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 rounded-2xl bg-destructive/10 border border-destructive/20 text-foreground flex flex-col items-center justify-center gap-4 text-center max-w-md mx-auto my-8">
          <div className="w-12 h-12 rounded-full bg-destructive/20 flex items-center justify-center text-destructive">
            <AlertCircle size={24} />
          </div>
          <div>
            <h3 className="text-base font-semibold">Live Voice Subsystem Error</h3>
            <p className="text-xs text-muted-foreground mt-1">
              {this.state.error?.message || 'An unexpected error occurred in the live voice module.'}
            </p>
          </div>
          <button
            type="button"
            onClick={this.handleReset}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium bg-foreground text-background hover:opacity-90 transition-all active:scale-95"
          >
            <RefreshCw size={14} />
            Reset Live Voice
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
