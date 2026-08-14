import React, { useEffect, useState } from 'react'
import { useUser } from '@clerk/clerk-react'
import { useAuth } from '@/stores/auth'
import { useChat } from '@/stores/chat'
import { api } from '@/lib/api'
import { AnimatedBackground } from '@/components/animations/AnimatedBackground'
import { IntroVideo, hasSeenIntro } from '@/components/intro/IntroVideo'
import { AuthPage } from '@/pages/AuthPage'
import { ChatPage } from '@/pages/ChatPage'
import { SettingsPage } from '@/pages/SettingsPage'

// Keep Render backend warm — ping every 4 minutes so it never cold-starts
function useKeepAlive() {
  useEffect(() => {
    const ping = () => api.health().catch(() => {})
    ping() // immediate ping on mount
    const id = setInterval(ping, 4 * 60 * 1000)
    return () => clearInterval(id)
  }, [])
}

const HAS_CLERK = Boolean(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY)
const BYPASS_AUTH = import.meta.env.VITE_BYPASS_AUTH === 'true'

function LoadingScreen() {
  return (
    <div className="min-h-screen flex items-center justify-center relative z-10">
      <div className="flex flex-col items-center gap-4">
        <div className="w-11 h-11 rounded-xl overflow-hidden border border-border shadow-soft">
          <img src="/logo.jpg" alt="HSBot" className="w-full h-full object-cover" />
        </div>
        <div className="flex items-center gap-2">
          <div className="relative w-4 h-4">
            <div className="absolute inset-0 rounded-full border-2 border-border border-t-foreground animate-spin" />
          </div>
          <p className="text-sm text-muted-foreground">Loading HSBot...</p>
        </div>
      </div>
    </div>
  )
}

function IntroGate({ children }: { children: React.ReactNode }) {
  const [introDone, setIntroDone] = useState(() => hasSeenIntro())
  if (introDone) return <>{children}</>
  return <IntroVideo onComplete={() => setIntroDone(true)} />
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
    <IntroGate>
      <ChatPage />
      <SettingsPage />
    </IntroGate>
  )
}

export default function App() {
  const { user: customUser, initialized, loadUser } = useAuth()
  const { loadChats, loadFolders, loadModels } = useChat()

  useKeepAlive() // keep Render backend awake

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
        <IntroGate>
          <ChatPage />
          <SettingsPage />
        </IntroGate>
      ) : HAS_CLERK ? (
        <ClerkAppInner />
      ) : !initialized ? (
        <LoadingScreen />
      ) : !customUser ? (
        <AuthPage />
      ) : (
        <IntroGate>
          <ChatPage />
          <SettingsPage />
        </IntroGate>
      )}
    </AnimatedBackground>
  )
}
