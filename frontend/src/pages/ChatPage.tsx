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
        <main className="flex-1 flex flex-col min-h-0">
          <ChatContainer />
        </main>
      </div>
    </div>
  )
}
