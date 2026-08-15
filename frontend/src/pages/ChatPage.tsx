import React, { useEffect, useState } from 'react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { ChatContainer } from '@/components/chat/ChatContainer'
import { TitleBar } from '@/components/desktop/TitleBar'
import { BrowserTabs } from '@/components/desktop/BrowserTabs'
import { useSettings } from '@/stores/settings'
import { isTauri } from '@/lib/tauri'

export function ChatPage() {
  const { setSidebarOpen } = useSettings()
  const [compact, setCompact] = useState(false)

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setSidebarOpen(false)
      }
    }
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [setSidebarOpen])

  return (
    <div className="flex h-screen overflow-hidden relative z-10">
      {!compact && <Sidebar />}
      <div className="flex-1 flex flex-col min-w-0">
        {isTauri && <TitleBar compact={compact} onToggleCompact={setCompact} />}
        {isTauri && <BrowserTabs />}
        <Header />
        <main className="flex-1 flex flex-col min-h-0">
          <ChatContainer />
        </main>
        {!compact && (
          <footer className="flex items-center justify-center px-4 py-2 border-t border-border bg-background relative z-10">
            <a
              href="https://hs-ai-studio.onrender.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[11px] text-muted-foreground/50 hover:text-foreground transition-colors"
            >
              © {new Date().getFullYear()} HSBot — HS AI Solution
            </a>
          </footer>
        )}
      </div>
    </div>
  )
}
