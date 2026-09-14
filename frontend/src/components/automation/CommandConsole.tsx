import React from 'react'
import { useAutomation, eventKey } from '@/stores/automation'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { Send, Loader2, Square, Bot, Zap, FolderOpen, Monitor, Globe, Cpu, TerminalSquare, FileText, MousePointer, Keyboard, Settings, Mic, MicOff, AudioLines } from 'lucide-react'

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  application: <Bot size={12} />,
  file: <FileText size={12} />,
  folder: <FolderOpen size={12} />,
  keyboard: <Keyboard size={12} />,
  mouse: <MousePointer size={12} />,
  window: <Monitor size={12} />,
  system: <Settings size={12} />,
  browser: <Globe size={12} />,
  process: <Cpu size={12} />,
  terminal: <TerminalSquare size={12} />,
}

function lineFor(event: { type: string; message?: string; intent?: string; target?: string | null; success?: boolean; error?: string | null; prompt?: string; steps?: string[]; confirmed?: boolean; category?: string }): { text: string; tone: string } {
  switch (event.type) {
    case 'chain_start':
      return { text: `▶ Chain: ${(event.steps ?? []).join(' → ')}`, tone: 'text-foreground/80' }
    case 'step':
      return { text: `· ${event.message ?? 'step'}`, tone: event.success ? 'text-muted-foreground' : 'text-red-300' }
    case 'action_start':
      return { text: `⚙ ${event.intent ?? 'action'} ${event.target ? `→ ${event.target}` : ''}`, tone: 'text-sky-300' }
    case 'action_done':
      return {
        text: event.success
          ? `✓ ${event.message ?? 'done'}`
          : `✗ ${event.message ?? 'failed'}${event.error ? ` (${event.error})` : ''}`,
        tone: event.success ? 'text-emerald-300' : 'text-red-300',
      }
    case 'confirmation_required':
      return { text: `? ${event.prompt ?? 'Confirmation required'}`, tone: 'text-amber-300' }
    case 'confirmed':
      return { text: event.confirmed ? '✓ Confirmed' : '✗ Declined', tone: event.confirmed ? 'text-emerald-300' : 'text-muted-foreground' }
    case 'cancelled':
      return { text: '⏹ Cancelled', tone: 'text-orange-300' }
    case 'chain_done':
      return { text: '✓ Chain complete', tone: 'text-emerald-300' }
    case 'chain_failed':
      return { text: `✗ ${event.message ?? 'Chain failed'}`, tone: 'text-red-300' }
    case 'tab_event':
      return { text: `🔀 ${event.message ?? 'Tab'}: ${event.target ?? ''}`, tone: 'text-muted-foreground' }
    case 'browser_status':
      return { text: `🌐 ${event.message ?? ''}`, tone: 'text-sky-300' }
    case 'voice_wake':
      return { text: `🎙 ${event.message ?? 'Wake word heard'}`, tone: 'text-amber-300' }
    case 'voice_command':
      return { text: `🎙 ${event.message ?? ''}`, tone: 'text-sky-300' }
    case 'voice_chat':
      return { text: `💬 ${event.message ?? ''}`, tone: 'text-muted-foreground' }
    case 'voice_result':
      return { text: `🎙 ${event.message ?? ''}`, tone: event.success ? 'text-emerald-300' : 'text-red-300' }
    case 'voice_error':
      return { text: `🎙 Error: ${event.message ?? ''}`, tone: 'text-red-300' }
    default:
      return { text: `${event.type}: ${event.message ?? event.prompt ?? ''}`, tone: 'text-muted-foreground' }
  }
}

export function CommandConsole() {
  const { events, busy, executing, execute, cancel, status, connected, connecting, lastError, voiceEnabled, voiceStarting, voiceWsConnected, voiceListenerState, enableVoice, disableVoice } = useAutomation()
  const [command, setCommand] = React.useState('')
  const scrollRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [events.length])

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!command.trim() || busy) return
    void execute(command)
    setCommand('')
  }

  const toggleVoice = () => {
    if (voiceEnabled || voiceStarting) {
      void disableVoice()
    } else {
      void enableVoice()
    }
  }

  const examples = status?.examples?.slice(0, 5) ?? [
    'Open Chrome',
    'Check CPU and RAM usage',
    'Create a folder called Projects',
    'Set volume to 60%',
    'Take a screenshot',
  ]

  return (
    <div className="flex flex-col gap-3">
      <form onSubmit={handleSend} className="flex gap-2">
        <input
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          placeholder={busy ? 'Busy...' : 'e.g. open chrome and take a screenshot'}
          aria-label="Automation command"
          disabled={busy}
          className="flex-1 h-10 px-3 rounded-xl bg-muted/50 border border-border/60 text-[13px] outline-none focus:border-brand/60 focus:ring-2 focus:ring-brand/20 placeholder:text-muted-foreground/40 disabled:opacity-60 transition-all"
        />
        {busy ? (
          <Button type="button" size="icon" className="h-10 w-10 rounded-xl" onClick={() => void cancel()} aria-label="Cancel execution" variant="outline">
            <Square size={14} />
          </Button>
        ) : (
          <>
            <Button
              type="button"
              size="icon"
              className={cn('h-10 w-10 rounded-xl', voiceEnabled && 'bg-red-500/20 border-red-500/40 animate-pulse')}
              onClick={toggleVoice}
              aria-label={voiceEnabled ? 'Stop backend voice listener' : 'Use the backend microphone'}
              title={voiceEnabled ? 'Stop listening (backend mic)' : 'Use the backend microphone'}
            >
              {voiceEnabled ? <MicOff size={14} className="text-red-300" /> : <Mic size={14} />}
            </Button>
            <Button type="submit" size="icon" className="h-10 w-10 rounded-xl" disabled={!command.trim()} aria-label="Send command">
              <Send size={14} />
            </Button>
          </>
        )}
      </form>

      {voiceEnabled && (
        <div className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/5 px-3 py-2 text-xs text-red-200 animate-fade-in">
          <AudioLines size={12} className={voiceListenerState === 'listening' || voiceListenerState === 'command_active' ? 'animate-pulse' : ''} />
          <span>
            Backend mic <span className="font-medium capitalize">{voiceListenerState}</span>
            {voiceWsConnected ? '' : ' (stream connecting...)'} — just say
            <span className="font-medium"> "open chrome"</span>
          </span>
        </div>
      )}

      {voiceStarting && (
        <div className="flex items-center gap-2 rounded-xl border border-sky-500/30 bg-sky-500/5 px-3 py-2 text-xs text-sky-200 animate-fade-in">
          <Loader2 size={12} className="animate-spin" />
          Starting the backend voice listener...
        </div>
      )}

      <div className="flex items-center gap-1.5 flex-wrap">
        {examples.map((ex) => (
          <button
            key={ex}
            onClick={() => void execute(ex)}
            disabled={busy}
            className="px-2.5 py-1 rounded-lg border border-border/50 bg-muted/30 text-[11px] text-muted-foreground hover:text-foreground hover:bg-muted/60 disabled:opacity-50 transition-all"
          >
            {ex}
          </button>
        ))}
      </div>

      {lastError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/5 px-3 py-2 text-xs text-red-200 animate-fade-in">
          {lastError}
        </div>
      )}

      {executing && !busy && (
        <div className="flex items-center gap-2 rounded-xl border border-sky-500/30 bg-sky-500/5 px-3 py-2 text-xs text-sky-200 animate-fade-in">
          <Loader2 size={12} className="animate-spin" />
          Running: {executing}
        </div>
      )}

      <div
        ref={scrollRef}
        className="h-52 rounded-xl border border-border/50 bg-background/40 overflow-y-auto no-scrollbar p-3 space-y-1.5"
        aria-label="Automation console"
      >
        {!connected && !connecting && (
          <p className="text-xs text-muted-foreground/60">
            Stream disconnected — events appear while connected to the local backend.
          </p>
        )}
        {events.length === 0 && (
          <p className="text-xs text-muted-foreground/40">
            No events yet. Try a command like "Check CPU and RAM usage".
          </p>
        )}
        {events.map((ev, i) => {
          const line = lineFor(ev)
          return (
            <div key={eventKey(ev) + i} className={cn('flex items-start gap-1.5 text-xs font-mono leading-relaxed', line.tone)}>
              {CATEGORY_ICONS[(ev as { category?: string }).category ?? '']}
              <span className="min-w-0 break-words">{line.text}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}