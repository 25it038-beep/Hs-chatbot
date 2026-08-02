import React, { useEffect } from 'react'
import { useUser } from '@clerk/clerk-react'
import { useAuth } from '@/stores/auth'
import { useChat } from '@/stores/chat'
import { AnimatedBackground } from '@/components/animations/AnimatedBackground'
import { AuthPage } from '@/pages/AuthPage'
import { ChatPage } from '@/pages/ChatPage'
import { SettingsPage } from '@/pages/SettingsPage'

const HAS_CLERK = Boolean(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY)
const BYPASS_AUTH = import.meta.env.VITE_BYPASS_AUTH === 'true'

function LoadingScreen() {
  return (
    <div className="min-h-screen flex items-center justify-center relative z-10">
      <div className="flex flex-col items-center gap-4">
        <div className="relative w-10 h-10">
          <div className="absolute inset-0 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
        </div>
        <p className="text-sm text-muted-foreground animate-pulse">Loading HSBot...</p>
      </div>
    </div>
  )
}

function ClerkAppInner() {
  const { isLoaded, isSignedIn } = useUser()
  const { loadChats, loadFolders, loadModels } = useChat()

  useEffect(() => {
    if (isSignedIn) {
      loadChats()
      loadFolders()
      loadModels()
    }
  }, [isSignedIn, loadChats, loadFolders, loadModels])

  if (!isLoaded) return <LoadingScreen />
  if (!isSignedIn) return <AuthPage />

  return (
    <React.Fragment>
      <ChatPage />
      <SettingsPage />
    </React.Fragment>
  )
}

export default function App() {
  const { user: customUser, initialized, loadUser } = useAuth()
  const { loadChats, loadFolders, loadModels } = useChat()

  useEffect(() => {
    if (!HAS_CLERK) loadUser()
  }, [loadUser])

  useEffect(() => {
    if (!HAS_CLERK && customUser) {
      loadChats()
      loadFolders()
      loadModels()
    }
  }, [customUser, loadChats, loadFolders, loadModels])

  return (
    <AnimatedBackground>
      {BYPASS_AUTH ? (
        <React.Fragment>
          <ChatPage />
          <SettingsPage />
        </React.Fragment>
      ) : HAS_CLERK ? (
        <ClerkAppInner />
      ) : !initialized ? (
        <LoadingScreen />
      ) : !customUser ? (
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
