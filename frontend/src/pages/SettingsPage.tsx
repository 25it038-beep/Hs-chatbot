import React from 'react'
import { useTheme } from 'next-themes'
import { useSettings } from '@/stores/settings'
import { useAuth } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { X, Sun, Moon, Monitor, LogOut, Trash2, Bot, Sparkles } from 'lucide-react'
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
            className="relative ml-auto w-full sm:max-w-md h-full glass-panel-strong shadow-2xl border-l border-glass-border flex flex-col pt-safe pb-safe"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          >
            <div className="flex items-center justify-between p-4 border-b border-border/50 flex-shrink-0">
              <h2 className="font-semibold text-sm tracking-tight">Settings</h2>
              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-xl text-muted-foreground/60 hover:text-foreground" onClick={() => setSettingsOpen(false)}>
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
                        <img src="/logo.jpg" alt="HSBot" className="w-full h-full object-cover" />
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
                      return (
                        <button
                          key={t.id}
                          onClick={() => setTheme(t.id)}
                          className={`flex-1 flex flex-col items-center gap-2 p-3.5 rounded-xl border transition-all duration-200 ${
                            theme === t.id
                              ? 'border-ring/50 bg-muted/50 shadow-sm'
                              : 'border-border/40 hover:border-ring/30 bg-muted/10'
                          }`}
                        >
                          <Icon size={18} className={theme === t.id ? 'text-foreground' : 'text-muted-foreground/60'} />
                          <span className="text-xs font-medium">{t.label}</span>
                        </button>
                      )
                    })}
                  </div>
                </section>

                <Separator className="opacity-30" />

                <section className="space-y-2">
                  <h3 className="text-xs font-medium text-muted-foreground/70 uppercase tracking-wider mb-3 ml-1">Actions</h3>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full justify-start gap-2.5 rounded-xl text-destructive/80 hover:text-destructive hover:bg-destructive/10 h-9"
                  >
                    <Trash2 size={14} />
                    Clear all conversations
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
                    <Sparkles size={10} />
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
