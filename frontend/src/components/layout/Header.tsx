import { useSettings } from '@/stores/settings'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import {
  Sun, Moon, Settings, Sparkles, Cpu,
} from 'lucide-react'

export function Header() {
  const { toggleSettings } = useSettings()
  const { theme, setTheme } = useTheme()

  return (
    <header className="flex items-center justify-between px-4 h-12 border-b border-border/50 bg-background/30 backdrop-blur-md relative z-10">
      <div className="flex items-center gap-2">
        <span className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium">
          <img src="/logo.jpg" alt="HSBot" className="w-5 h-5 rounded object-cover" />
          <span className="tracking-tight">HSBot</span>
        </span>
        <span className="flex items-center gap-1 text-[10px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 dark:bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
          <Sparkles size={10} />
          Auto-Router
        </span>
      </div>

      <div className="flex items-center gap-1">
        <Button
          variant="ghost" size="icon" className="h-8 w-8 rounded-xl text-muted-foreground/60 hover:text-foreground"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          title="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </Button>
        <Button
          variant="ghost" size="icon" className="h-8 w-8 rounded-xl text-muted-foreground/60 hover:text-foreground"
          onClick={toggleSettings}
          title="Settings"
        >
          <Settings size={15} />
        </Button>
      </div>
    </header>
  )
}
