import React, { useEffect } from 'react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { ChatContainer } from '@/components/chat/ChatContainer'
import { useSettings } from '@/stores/settings'

export function ChatPage() {
  const { setSidebarOpen } = useSettings()

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
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <div className="flex items-center justify-center gap-2 px-4 py-2 border-b border-amber-500/30 bg-amber-500/10 text-amber-300 text-sm text-center">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
          </span>
          <span>
            We are facing some issues right now and our team is actively working to fix them. Stay tuned!
          </span>
        </div>
        <main className="flex-1 flex flex-col min-h-0">
          <ChatContainer />
        </main>
        <footer className="flex items-center justify-center px-4 py-1.5 border-t border-border/50 bg-background/30 backdrop-blur-md relative z-10">
          <a
            href="https://hs-ai-studio.onrender.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-muted-foreground/70 hover:text-foreground transition-colors"
          >
            © {new Date().getFullYear()} HSBot — All rights reserved to HS AI Solution
          </a>
        </footer>
      </div>
    </div>
  )
}
