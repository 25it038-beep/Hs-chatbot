import { useSettings } from '@/stores/settings'
import { useTheme } from 'next-themes'
import { UserButton, useUser } from '@clerk/clerk-react'
import { Button } from '@/components/ui/button'
import {
  Sun, Moon, Monitor, Settings, Sparkles, PanelLeft
} from 'lucide-react'

const HAS_CLERK = Boolean(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY)

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
  const { sidebarOpen, toggleSidebar, toggleSettings } = useSettings()
  const { theme, setTheme } = useTheme()
  const current = THEME_META[(theme as ThemeOption) in THEME_META ? (theme as ThemeOption) : 'system']
  const ThemeIcon = current.icon

  return (
    <header className="flex items-center justify-between px-3 md:px-5 h-12 border-b border-border bg-background relative z-10">
      <div className="flex items-center gap-1.5 min-w-0">
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
        <span className="hidden xs:inline-flex items-center gap-1 text-[10px] font-medium text-muted-foreground/70 bg-muted/60 px-2 py-0.5 rounded-full border border-border">
          <Sparkles size={9} />
          <span className="truncate">Auto-Router</span>
        </span>
      </div>

      <div className="flex items-center gap-1 flex-shrink-0">
        {HAS_CLERK && <ClerkUserAvatar />}
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
  )
}