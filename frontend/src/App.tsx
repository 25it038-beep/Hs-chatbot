import React, { useEffect } from 'react'
import { useAuth } from '@/stores/auth'
import { useChat } from '@/stores/chat'
import { AnimatedBackground } from '@/components/animations/AnimatedBackground'
import { AuthPage } from '@/pages/AuthPage'
import { ChatPage } from '@/pages/ChatPage'
import { SettingsPage } from '@/pages/SettingsPage'

export default function App() {
  const { user, initialized, loadUser } = useAuth()
  const { loadChats, loadFolders, loadModels } = useChat()

  useEffect(() => { loadUser() }, [loadUser])

  useEffect(() => {
    if (user) { loadChats(); loadFolders(); loadModels() }
  }, [user, loadChats, loadFolders, loadModels])

  return (
    <AnimatedBackground>
      {!initialized ? (
        <div className="min-h-screen flex items-center justify-center relative z-10">
          <div className="flex flex-col items-center gap-4">
            <div className="relative w-10 h-10">
              <div className="absolute inset-0 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
            </div>
            <p className="text-sm text-muted-foreground animate-pulse">Loading HSBot...</p>
          </div>
        </div>
      ) : !user ? (
        <AuthPage />
      ) : (
        <React.Fragment>
          <ChatPage />
          <SettingsPage />
        </React.Fragment>
      )}
    </AnimatedBackground>
  )
}
