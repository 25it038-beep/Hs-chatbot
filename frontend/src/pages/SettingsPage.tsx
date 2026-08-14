import React from 'react'
import { useTheme } from 'next-themes'
import { useSettings } from '@/stores/settings'
import { useAuth } from '@/stores/auth'
import { useChat } from '@/stores/chat'
import { useAmbient } from '@/stores/ambient'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { X, Sun, Moon, Monitor, LogOut, Trash2, Sparkles, Check, Loader2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const themes = [
  { id: 'light', label: 'Light', icon: Sun },
  { id: 'dark', label: 'Dark', icon: Moon },
  { id: 'system', label: 'System', icon: Monitor },
]

export function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const { settingsOpen, setSettingsOpen } = useSettings()
  const { user, logout } = useAuth()
  const { chats, deleteChat } = useChat()
  const { festivalEnabled, setFestivalEnabled } = useAmbient()
  const [confirmClear, setConfirmClear] = React.useState(false)
  const [clearing, setClearing] = React.useState(false)

  const handleClearAll = async () => {
    if (!confirmClear) {
      setConfirmClear(true)
      setTimeout(() => setConfirmClear(false), 4000)
      return
    }
    setClearing(true)
    for (const chat of chats) {
      await deleteChat(chat.id)
    }
    setClearing(false)
    setConfirmClear(false)
  }

  return (
    <AnimatePresence>
      {settingsOpen && (
        <div className="fixed inset-0 z-50 flex">
          <motion.div
            className="absolute inset-0 bg-background/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSettingsOpen(false)}
          />
          <motion.div
            className="relative ml-auto w-full sm:max-w-md h-full glass-panel-strong border-l border-glass-border flex flex-col pt-safe pb-safe"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            role="dialog"
            aria-label="Settings"
          >
            <div className="flex items-center justify-between p-4 border-b border-border/50 flex-shrink-0">
              <h2 className="font-semibold text-sm tracking-tight">Settings</h2>
              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-xl text-muted-foreground/60 hover:text-foreground" onClick={() => setSettingsOpen(false)} aria-label="Close settings">
                <X size={15} />
              </Button>
            </div>

            <ScrollArea className="flex-1 min-h-0">
              <div className="p-4 space-y-6">
                {user && (
                  <section>
                    <h3 className="text-xs font-medium text-muted-foreground/70 uppercase tracking-wider mb-3 ml-1">Profile</h3>
                    <div className="flex items-center gap-3 p-3.5 rounded-xl bg-muted/30 border border-border/40">
                      <div className="w-10 h-10 rounded-xl overflow-hidden border border-primary/10">
                        <img src="/logo.jpg" alt="Profile" className="w-full h-full object-cover" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{user.display_name || user.username}</p>
                        <p className="text-xs text-muted-foreground/60 truncate">{user.email}</p>
                      </div>
                    </div>
                  </section>
                )}

                <section>
                  <h3 className="text-xs font-medium text-muted-foreground/70 uppercase tracking-wider mb-3 ml-1">Theme</h3>
                  <div className="flex gap-2">
                    {themes.map((t) => {
                      const Icon = t.icon
                      const active = theme === t.id
                      return (
                        <button
                          key={t.id}
                          onClick={() => setTheme(t.id)}
                          aria-pressed={active}
                          className={`flex-1 flex flex-col items-center gap-2 p-3.5 rounded-xl border transition-all duration-200 ${
                            active
                              ? 'border-foreground/20 bg-accent shadow-soft'
                              : 'border-border/60 hover:border-foreground/20 bg-muted/30 hover:bg-muted/60'
                          }`}
                        >
                          <Icon size={18} className={active ? 'text-foreground' : 'text-muted-foreground/60'} />
                          <span className={`text-xs font-medium ${active ? 'text-foreground' : 'text-muted-foreground/70'}`}>
                            {t.label}
                          </span>
                          {active && <Check size={11} className="text-brand" />}
                        </button>
                      )
                    })}
                  </div>
                </section>

                <Separator className="opacity-30" />

                <section>
                  <h3 className="text-xs font-medium text-muted-foreground/70 uppercase tracking-wider mb-3 ml-1">Ambient</h3>
                  <button
                    onClick={() => setFestivalEnabled(!festivalEnabled)}
                    aria-pressed={festivalEnabled}
                    className="w-full flex items-center justify-between gap-3 p-3.5 rounded-xl border border-border/60 bg-muted/30 hover:bg-muted/60 transition-all duration-200"
                  >
                    <span className="flex items-center gap-2.5">
                      <Sparkles size={14} className="text-brand" />
                      <span className="text-sm font-medium">Festival ambient glow</span>
                    </span>
                    <span
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 ${
                        festivalEnabled ? 'bg-brand' : 'bg-muted-foreground/25'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${
                          festivalEnabled ? 'translate-x-[18px]' : 'translate-x-0.5'
                        }`}
                      />
                    </span>
                  </button>
                  <p className="text-xs text-muted-foreground/60 mt-2 ml-1">
                    Auto-apply festival color palettes (Diwali, Pongal, Independence Day, ...) to the ambient glow.
                  </p>
                </section>

                <Separator className="opacity-30" />

                <section className="space-y-2">
                  <h3 className="text-xs font-medium text-muted-foreground/70 uppercase tracking-wider mb-3 ml-1">Actions</h3>
                  <Button
                    variant="ghost"
                    size="sm"
                    className={`w-full justify-start gap-2.5 rounded-xl h-9 transition-all ${
                      confirmClear
                        ? 'bg-destructive/15 text-destructive hover:bg-destructive/25'
                        : 'text-destructive/80 hover:text-destructive hover:bg-destructive/10'
                    }`}
                    onClick={handleClearAll}
                    disabled={clearing || chats.length === 0}
                  >
                    {clearing ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : confirmClear ? (
                      <Check size={14} />
                    ) : (
                      <Trash2 size={14} />
                    )}
                    {clearing
                      ? 'Clearing conversations...'
                      : confirmClear
                        ? `Delete all ${chats.length} conversations?`
                        : 'Clear all conversations'}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full justify-start gap-2.5 rounded-xl text-muted-foreground/70 hover:text-foreground hover:bg-muted/40 h-9"
                    onClick={() => { logout() }}
                  >
                    <LogOut size={14} />
                    Sign out
                  </Button>
                </section>

                <div className="text-center pt-6 pb-4">
                  <div className="flex items-center justify-center gap-1.5 text-xs text-muted-foreground/40 mb-1">
                    <Sparkles size={10} className="text-brand" />
                    <span>HSBot v1.0.0</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground/30">Built with React, FastAPI, and Rust</p>
                </div>
              </div>
            </ScrollArea>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}