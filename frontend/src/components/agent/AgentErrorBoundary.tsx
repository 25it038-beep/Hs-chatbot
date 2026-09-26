import React, { Component, ErrorInfo, ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { AlertTriangle, RotateCcw, MessageSquare, ChevronDown, ChevronRight, Bot } from 'lucide-react'
import { useSettings } from '@/stores/settings'

interface Props {
  children: ReactNode
  panelName?: string
  fallbackTitle?: string
  onReset?: () => void
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
  showDetails: boolean
}

export class AgentErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    showDetails: false
  }

  public static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`[AgentErrorBoundary] Uncaught error in ${this.props.panelName || 'Agent Panel'}:`, error, errorInfo)
    this.setState({ errorInfo })
  }

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false
    })
    if (this.props.onReset) {
      this.props.onReset()
    }
  }

  private handleReturnToChat = () => {
    try {
      useSettings.getState().setAppMode('chat')
    } catch {
      window.location.hash = ''
    }
  }

  public render() {
    if (this.state.hasError) {
      const panelName = this.props.panelName || 'Agent Component'
      const title = this.props.fallbackTitle || `${panelName} encountered an unexpected error`

      return (
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center bg-card/40 border border-destructive/20 rounded-2xl m-4 shadow-sm">
          <div className="w-12 h-12 rounded-2xl bg-destructive/10 text-destructive flex items-center justify-center mb-3">
            <AlertTriangle size={24} />
          </div>

          <h3 className="text-sm font-bold text-foreground mb-1">
            {title}
          </h3>

          <p className="text-xs text-muted-foreground max-w-md mb-4 leading-relaxed">
            A component rendering error was safely intercepted to prevent an application crash.
            You can refresh this panel or return to Chat mode.
          </p>

          <div className="flex items-center gap-2 flex-wrap justify-center mb-4">
            <Button
              size="sm"
              variant="default"
              onClick={this.handleReset}
              className="h-8 text-xs gap-1.5 rounded-lg"
            >
              <RotateCcw size={13} />
              <span>Retry / Recover Panel</span>
            </Button>

            <Button
              size="sm"
              variant="outline"
              onClick={this.handleReturnToChat}
              className="h-8 text-xs gap-1.5 rounded-lg border-border"
            >
              <MessageSquare size={13} />
              <span>Switch to Chat</span>
            </Button>
          </div>

          {/* Expandable Technical Debug Details */}
          <div className="w-full max-w-lg text-left">
            <button
              onClick={() => this.setState((prev) => ({ showDetails: !prev.showDetails }))}
              className="flex items-center gap-1 text-[11px] font-mono text-muted-foreground hover:text-foreground mx-auto"
            >
              {this.state.showDetails ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              <span>{this.state.showDetails ? 'Hide error details' : 'Show technical error details'}</span>
            </button>

            {this.state.showDetails && (
              <div className="mt-2 p-3 rounded-xl bg-black/80 text-destructive text-[11px] font-mono overflow-auto max-h-48 border border-destructive/30 text-left select-text whitespace-pre-wrap">
                <div className="font-bold text-red-400 mb-1">
                  {this.state.error?.name}: {this.state.error?.message}
                </div>
                {this.state.error?.stack && (
                  <div className="text-muted-foreground text-[10px] leading-tight">
                    {this.state.error.stack}
                  </div>
                )}
                {this.state.errorInfo?.componentStack && (
                  <div className="text-muted-foreground/70 text-[9px] mt-2 pt-2 border-t border-border/20 leading-tight">
                    Component Stack:
                    {this.state.errorInfo.componentStack}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
