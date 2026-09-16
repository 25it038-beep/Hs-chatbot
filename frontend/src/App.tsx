import React, { useEffect, useState } from 'react'
import { useUser, useAuth as useClerkAuth } from '@clerk/clerk-react'
import { useAuth } from '@/stores/auth'
import { useChat } from '@/stores/chat'
import { api, setTokens } from '@/lib/api'
import { AnimatedBackground } from '@/components/animations/AnimatedBackground'
import { IntroVideo, hasSeenIntro } from '@/components/intro/IntroVideo'
import { AuthPage } from '@/pages/AuthPage'
import { ChatPage } from '@/pages/ChatPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { isTauri, listenForHotkeyFocus } from '@/lib/tauri'
import { HAS_CLERK } from '@/lib/clerkConfig'

// Keep Render backend warm — ping every 4 minutes so it never cold-starts
function useKeepAlive() {
  useEffect(() => {
    const ping = () => api.health().catch(() => {})
    ping() // immediate ping on mount
    const id = setInterval(ping, 4 * 60 * 1000)
    return () => clearInterval(id)
  }, [])
}

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
  return <>{children}</>
}

function ClerkAppInner() {
  const { isLoaded, isSignedIn, user: clerkUser } = useUser()
  const { getToken } = useClerkAuth()
  const { loadChats, loadFolders, loadModels } = useChat()
  const { user: customUser } = useAuth()

  useEffect(() => {
    if (isSignedIn && clerkUser) {
      // Clean up any remaining sign-in/up hash from Clerk
      if (window.location.hash.includes('sign-')) {
        window.location.hash = ''
        window.history.replaceState(null, '', window.location.pathname)
      }

      // Sync Clerk user profile into our auth store so Sidebar and Settings show the user
      useAuth.setState({
        user: {
          id: clerkUser.id,
          username:
            clerkUser.username ||
            clerkUser.firstName ||
            clerkUser.primaryEmailAddress?.emailAddress?.split('@')[0] ||
            'User',
          email: clerkUser.primaryEmailAddress?.emailAddress || '',
          display_name: clerkUser.fullName || clerkUser.firstName || undefined,
          is_active: true,
          created_at: clerkUser.createdAt ? new Date(clerkUser.createdAt).toISOString() : new Date().toISOString(),
        },
        initialized: true,
      })

      // Sync Clerk session token with local storage & API client
      getToken()
        .then((token) => {
          if (token) setTokens(token, '')
          loadChats()
          loadFolders()
          loadModels()
        })
        .catch(() => {
          loadChats()
          loadFolders()
          loadModels()
        })
    }
  }, [isSignedIn, clerkUser, getToken, loadChats, loadFolders, loadModels])

  const isAuthenticated = isSignedIn || !!customUser

  if (!isLoaded && !customUser) return <LoadingScreen />
  if (!isAuthenticated) return <AuthPage />

  return (
    <>
      <ChatPage />
      <SettingsPage />
    </>
  )
}

export default function App() {
  const { user: customUser, initialized, loadUser } = useAuth()
  const { loadChats, loadFolders, loadModels } = useChat()

  useKeepAlive() // keep Render backend awake

  // Desktop overlay: global hotkey (Rust registers Ctrl+Space) → focus the
  // command input the moment the window appears.
  useEffect(() => {
    if (!isTauri) return
    return listenForHotkeyFocus(() => {
      const el = document.getElementById('hs-command-input') as HTMLTextAreaElement | null
      if (el) {
        el.focus()
        el.scrollIntoView?.()
      }
    })
  }, [])

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
        <>
          <ChatPage />
          <SettingsPage />
        </>
      ) : HAS_CLERK ? (
        <ClerkAppInner />
      ) : !initialized ? (
        <LoadingScreen />
      ) : !customUser ? (
        <AuthPage />
      ) : (
        <>
          <ChatPage />
          <SettingsPage />
        </>
      )}
    </AnimatedBackground>
  )
}
