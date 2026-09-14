import React from 'react'
import { useAutomation, type PendingAction } from '@/stores/automation'
import { Button } from '@/components/ui/button'
import { Loader2, AlertTriangle, ShieldAlert, ShieldCheck } from 'lucide-react'
import { cn } from '@/lib/utils'

const RISK_STYLES: Record<string, string> = {
  low: 'text-emerald-200 border-emerald-500/40 bg-emerald-500/10',
  medium: 'text-amber-200 border-amber-500/40 bg-amber-500/10',
  high: 'text-orange-200 border-orange-500/40 bg-orange-500/10',
  critical: 'text-red-200 border-red-500/40 bg-red-500/10',
}

export function ConfirmationCard({ action }: { action: PendingAction }) {
  const { confirm, busy } = useAutomation()
  const [choosing, setChoosing] = React.useState<string | null>(null)
  const risk = action.risk ?? 'medium'
  const critical = risk === 'critical' || risk === 'high'

  const handleConfirm = (choice?: string) => {
    setChoosing(choice ?? '__yes__')
    void confirm(action.action_id, true, choice)
  }

  return (
    <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3.5 animate-fade-in">
      <div className="flex items-start gap-2.5">
        {critical ? (
          <ShieldAlert size={16} className="text-red-300 mt-0.5 flex-shrink-0" />
        ) : (
          <AlertTriangle size={16} className="text-amber-300 mt-0.5 flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <p className="text-xs font-semibold text-amber-100">Confirm action</p>
            <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-medium border', RISK_STYLES[risk] ?? RISK_STYLES.medium)}>
              {risk} risk
            </span>
          </div>
          <p className="text-[13px] text-foreground/90 leading-snug">{action.prompt}</p>

          {action.options && action.options.length > 0 ? (
            <div className="mt-3 grid gap-1.5">
              {action.options.map((opt) => (
                <Button
                  key={opt}
                  variant="outline"
                  size="sm"
                  className="w-full justify-start text-xs h-8"
                  onClick={() => handleConfirm(opt)}
                  disabled={busy && choosing !== opt}
                >
                  {busy && choosing === opt && <Loader2 size={12} className="animate-spin" />}
                  {opt}
                </Button>
              ))}
            </div>
          ) : (
            <div className="mt-3 flex gap-2">
              <Button
                size="sm"
                className="flex-1 h-8 text-xs"
                onClick={() => handleConfirm()}
                disabled={busy}
              >
                {busy && choosing === '__yes__' ? <Loader2 size={12} className="animate-spin" /> : <ShieldCheck size={12} />}
                Yes, do it
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="flex-1 h-8 text-xs text-muted-foreground"
                onClick={() => void confirm(action.action_id, false)}
                disabled={busy}
              >
                Cancel
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}