import React from 'react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { ChatContainer } from '@/components/chat/ChatContainer'
import { useSettings } from '@/stores/settings'

export function ChatPage() {
  const { sidebarOpen } = useSettings()

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
