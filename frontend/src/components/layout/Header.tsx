import React, { useState } from 'react'
import { useSettings } from '@/stores/settings'
import { useTheme } from '@/components/theme/ThemeProvider'
import { UserButton, useUser } from '@clerk/clerk-react'
import { Button } from '@/components/ui/button'
import {
  Sun, Moon, Monitor, Settings, Sparkles, PanelLeft, Download, Radio, MessageSquare, Bot, Video, ChevronDown, Loader2
} from 'lucide-react'
import { isTauri } from '@/lib/tauri'
import { useChat } from '@/stores/chat'
import { WindowsDownloadModal } from '@/components/desktop/WindowsDownloadModal'
import { HAS_CLERK, CLERK_PUBLISHABLE_KEY } from '@/lib/clerkConfig'
import {
  downloadAiResponsesAsFile,
  EXPORT_FILE_FORMATS,
  getActiveChatAiResponses,
} from '@/lib/documentGenerator'

const THEME_CYCLE = ['light', 'dark', 'system'] as const
type ThemeOption = (typeof THEME_CYCLE)[number]

const THEME_META: Record<ThemeOption, { icon: typeof Sun; label: string; next: ThemeOption }> = {
  light: { icon: Sun, label: 'Light mode', next: 'dark' },
  dark: { icon: Moon, label: 'Dark mode', next: 'system' },
  system: { icon: Monitor, label: 'System theme', next: 'light' },
}

function ClerkUserAvatar() {
  const { isSignedIn } = useUser()
  if (!isSignedIn) return null
  return (
    <div className="flex items-center">
      <UserButton afterSignOutUrl="/" />
    </div>
  )
}

export function Header() {
  const { sidebarOpen, toggleSidebar, toggleSettings, appMode, setAppMode } = useSettings()
  const { setLiveOpen, messages, currentChat } = useChat()
  const { theme, setTheme } = useTheme()
  const [downloadModalOpen, setDownloadModalOpen] = useState(false)
  const [exportMenuOpen, setExportMenuOpen] = useState(false)
  const [exportingFormat, setExportingFormat] = useState<string | null>(null)
  const [customFormat, setCustomFormat] = useState('')
  const current = THEME_META[(theme as ThemeOption) in THEME_META ? (theme as ThemeOption) : 'system']
  const ThemeIcon = current.icon

  const hasAiResponses = messages.some(m => m.role === 'assistant' && m.content && m.content.trim().length > 0)

  const handleExportChatResponses = async (fmt: string) => {
    const cleanFmt = fmt.trim().toLowerCase().replace(/^\.+/, '')
    if (!cleanFmt || exportingFormat) return
    setExportingFormat(cleanFmt)
    try {
      const responses = getActiveChatAiResponses()
      await downloadAiResponsesAsFile({
        responses,
        format: cleanFmt,
        title: currentChat?.title || 'AI Chat Responses',
        chatId: currentChat?.id,
      })
      setExportMenuOpen(false)
    } catch (err) {
      console.error('Failed to export chat AI responses:', err)
    } finally {
      setExportingFormat(null)
    }
  }

  return (
    <>
      <header className="flex items-center justify-between px-3 md:px-5 h-12 border-b border-border bg-background relative z-10">
        <div className="flex items-center gap-2 min-w-0">
          {!sidebarOpen && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-lg text-muted-foreground/70 hover:text-foreground flex-shrink-0"
              onClick={toggleSidebar}
              aria-label="Open sidebar"
            >
              <PanelLeft size={16} />
            </Button>
          )}
          {!sidebarOpen && (
            <span className="flex items-center gap-2 px-1 text-sm font-medium flex-shrink-0">
              <img src="/logo.jpg" alt="HSBot logo" className="w-5 h-5 rounded object-cover" />
              <span className="tracking-tight font-semibold text-sm">HSBot</span>
            </span>
          )}

          {/* Mode Switcher */}
          <div className="flex items-center bg-muted/60 p-0.5 rounded-lg border border-border">
            <button
              onClick={() => setAppMode('chat')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                appMode === 'chat'
                  ? 'bg-background text-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <MessageSquare size={12} />
              <span>Chat</span>
            </button>
            <button
              onClick={() => setAppMode('agent')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                appMode === 'agent'
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Bot size={12} />
              <span>Agent Mode</span>
              <span className="hidden sm:inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            </button>
            <button
              onClick={() => setAppMode('video')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                appMode === 'video'
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Video size={12} />
              <span>Video Studio</span>
              <span className="hidden sm:inline-block w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
            </button>
          </div>
        </div>

        <div className="flex items-center gap-1.5 flex-shrink-0">
          {appMode === 'chat' && hasAiResponses && (
            <div className="relative">
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1.5 rounded-lg border-border bg-card hover:bg-muted text-foreground text-xs font-medium px-2.5 shadow-xs"
                onClick={() => setExportMenuOpen(v => !v)}
                title="Download all AI responses in this chat as any file format"
              >
                {exportingFormat ? (
                  <Loader2 size={13} className="animate-spin text-primary" />
                ) : (
                  <Download size={13} className="text-primary" />
                )}
                <span className="hidden sm:inline">Download AI Responses</span>
                <ChevronDown size={11} className="opacity-70" />
              </Button>

              {exportMenuOpen && (
                <div className="absolute right-0 top-full mt-1.5 z-50 w-72 rounded-xl border border-border bg-popover text-popover-foreground shadow-xl p-3 space-y-2.5">
                  <div className="flex items-center justify-between border-b border-border pb-1.5">
                    <span className="text-xs font-semibold text-foreground">
                      Download Chat AI Responses
                    </span>
                    <button
                      type="button"
                      onClick={() => setExportMenuOpen(false)}
                      className="text-[11px] text-muted-foreground hover:text-foreground"
                    >
                      Close
                    </button>
                  </div>
                  <div className="grid grid-cols-3 gap-1 max-h-48 overflow-y-auto pr-0.5">
                    {EXPORT_FILE_FORMATS.map(fmt => (
                      <button
                        key={fmt.ext}
                        type="button"
                        disabled={!!exportingFormat}
                        onClick={() => handleExportChatResponses(fmt.ext)}
                        title={fmt.description}
                        className="px-2 py-1.5 rounded-md text-[11px] font-medium text-left border border-border/60 hover:border-primary/40 hover:bg-primary/10 hover:text-primary transition-colors flex items-center justify-between"
                      >
                        <span>.{fmt.ext.toUpperCase()}</span>
                        {exportingFormat === fmt.ext && (
                          <Loader2 size={10} className="animate-spin" />
                        )}
                      </button>
                    ))}
                  </div>
                  <form
                    onSubmit={e => {
                      e.preventDefault()
                      if (customFormat.trim()) {
                        handleExportChatResponses(customFormat)
                      }
                    }}
                    className="flex items-center gap-1.5 pt-1.5 border-t border-border"
                  >
                    <input
                      type="text"
                      value={customFormat}
                      onChange={e => setCustomFormat(e.target.value)}
                      placeholder="Any format (e.g. pdf, docx, csv, sql, yaml)..."
                      className="flex-1 h-7 px-2 rounded-md border border-border bg-background text-[11px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <button
                      type="submit"
                      disabled={!customFormat.trim() || !!exportingFormat}
                      className="h-7 px-2.5 rounded-md bg-primary text-primary-foreground text-[11px] font-semibold disabled:opacity-50 hover:opacity-90 transition-opacity"
                    >
                      Export
                    </button>
                  </form>
                </div>
              )}
            </div>
          )}

          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 rounded-lg border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-semibold px-2.5 shadow-xs transition-all active:scale-95"
            onClick={() => setLiveOpen(true)}
            title="Start Live Voice Conversation"
          >
            <Radio size={13} className="text-emerald-500 animate-pulse" />
            <span>Live Voice</span>
          </Button>

          {!isTauri && (
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 rounded-lg border-primary/30 bg-primary/5 hover:bg-primary/15 text-primary text-xs font-medium px-2.5"
              onClick={() => setDownloadModalOpen(true)}
              title="Download HSBot Desktop Assistant for Windows (.exe)"
            >
              <Monitor size={13} />
              <span className="hidden sm:inline">Windows App</span>
              <Download size={11} className="opacity-70" />
            </Button>
          )}
          {HAS_CLERK && CLERK_PUBLISHABLE_KEY && <ClerkUserAvatar />}
          <Button
            variant="ghost" size="icon" className="h-8 w-8 rounded-lg text-muted-foreground/60 hover:text-foreground"
            onClick={() => setTheme(current.next)}
            title={`${current.label} — switch to ${THEME_META[current.next].label}`}
            aria-label={`Theme: ${current.label}. Click to switch theme`}
          >
            <ThemeIcon size={15} />
          </Button>
          <Button
            variant="ghost" size="icon" className="h-8 w-8 rounded-lg text-muted-foreground/60 hover:text-foreground"
            onClick={toggleSettings}
            title="Settings"
            aria-label="Open settings"
          >
            <Settings size={15} />
          </Button>
        </div>
      </header>

      <WindowsDownloadModal
        open={downloadModalOpen}
        onOpenChange={setDownloadModalOpen}
      />
    </>
  )
}