import { useSettings } from '@/stores/settings'
import { useTheme } from 'next-themes'
import { UserButton, useUser } from '@clerk/clerk-react'
import { Button } from '@/components/ui/button'
import {
  Sun, Moon, Settings, Sparkles, PanelLeft
} from 'lucide-react'

const HAS_CLERK = Boolean(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY)

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
  const { sidebarOpen, toggleSidebar, toggleSettings } = useSettings()
  const { theme, setTheme } = useTheme()

  return (
    <header className="flex items-center justify-between px-3 md:px-4 h-12 border-b border-border/50 bg-background/30 backdrop-blur-md relative z-10">
      <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
        {!sidebarOpen && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 rounded-xl text-muted-foreground/70 hover:text-foreground flex-shrink-0"
            onClick={toggleSidebar}
            title="Open sidebar"
          >
            <PanelLeft size={16} />
          </Button>
        )}
        <span className="flex items-center gap-2 px-1.5 sm:px-2 py-1 text-sm font-medium flex-shrink-0">
          <img src="/logo.jpg" alt="HSBot" className="w-5 h-5 rounded object-cover" />
          <span className="tracking-tight font-semibold text-sm">HSBot</span>
        </span>
        <span className="hidden xs:inline-flex items-center gap-1 text-[10px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 dark:bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 flex-shrink-0">
          <Sparkles size={9} />
          <span className="truncate">Auto-Router</span>
        </span>
      </div>

      <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
        {HAS_CLERK && <ClerkUserAvatar />}
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
