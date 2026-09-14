import React from 'react'
import { useSettings } from '@/stores/settings'
import { useAutomation } from '@/stores/automation'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ConfirmationCard } from '@/components/automation/ConfirmationCard'
import { CommandConsole } from '@/components/automation/CommandConsole'
import { StatusBar } from '@/components/automation/StatusBar'
import { HistoryList } from '@/components/automation/HistoryList'
import { X, Zap, ShieldCheck, History } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export function AutomationPage() {
  const { automationOpen, setAutomationOpen } = useSettings()
  const { pending, connect, disconnect, refreshStatus, loadHistory } = useAutomation()

  React.useEffect(() => {
    if (automationOpen) {
      connect()
      void refreshStatus()
      void loadHistory()
    } else {
      disconnect()
    }
  }, [automationOpen, connect, disconnect, refreshStatus, loadHistory])

  return (
    <AnimatePresence>
      {automationOpen && (
        <div className="fixed inset-0 z-50 flex">
          <motion.div
            className="absolute inset-0 bg-background/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setAutomationOpen(false)}
          />
          <motion.div
            className="relative ml-auto w-full sm:max-w-md h-full glass-panel-strong border-l border-glass-border flex flex-col pt-safe pb-safe"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            role="dialog"
            aria-label="OS Automation"
          >
            <div className="flex items-center justify-between p-4 border-b border-border/50 flex-shrink-0">
              <div className="flex items-center gap-2">
                <Zap size={15} className="text-brand" />
                <h2 className="font-semibold text-sm tracking-tight">OS Automation</h2>
              </div>
              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-xl text-muted-foreground/60 hover:text-foreground" onClick={() => setAutomationOpen(false)} aria-label="Close automation">
                <X size={15} />
              </Button>
            </div>

            <ScrollArea className="flex-1 min-h-0">
              <div className="p-4 space-y-5">
                <section>
                  <h3 className="text-xs font-medium text-muted-foreground/70 uppercase tracking-wider mb-2.5 ml-1">Command</h3>
                  <CommandConsole />
                </section>

                <AnimatePresence>
                  {pending && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.18 }}
                    >
                      <ConfirmationCard action={pending} />
                    </motion.div>
                  )}
                </AnimatePresence>

                <Separator className="opacity-30" />

                <section>
                  <h3 className="text-xs font-medium text-muted-foreground/70 uppercase tracking-wider mb-2.5 ml-1 flex items-center gap-1.5">
                    <ShieldCheck size={11} className="text-brand" /> Status
                  </h3>
                  <StatusBar />
                </section>

                <Separator className="opacity-30" />

                <section>
                  <h3 className="text-xs font-medium text-muted-foreground/70 uppercase tracking-wider mb-2.5 ml-1 flex items-center gap-1.5">
                    <History size={11} className="text-brand" /> Recent actions
                  </h3>
                  <HistoryList />
                </section>

                <div className="rounded-xl border border-border/40 bg-muted/15 p-3">
                  <p className="text-[11px] leading-relaxed text-muted-foreground/70">
                    Safety: risky actions (delete, move, restart, shutdown, terminal) always ask for confirmation first. Voice-verified commands skip prompts for medium-risk actions. Automation never runs on the cloud backend.
                  </p>
                </div>
              </div>
            </ScrollArea>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}