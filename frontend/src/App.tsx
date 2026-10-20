import React, { useEffect, useState, useRef } from 'react'
import { useUser, useAuth as useClerkAuth } from '@clerk/clerk-react'
import { useAuth } from '@/stores/auth'
import { useChat } from '@/stores/chat'
import { api, setTokens } from '@/lib/api'
import { AnimatedBackground } from '@/components/animations/AnimatedBackground'
import { AuthPage } from '@/pages/AuthPage'
import { ChatPage } from '@/pages/ChatPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { LoadingExperience } from '@/components/loading'
import { useConnection } from '@/hooks/useConnection'
import { isTauri, listenForHotkeyFocus } from '@/lib/tauri'
import { HAS_CLERK, CLERK_PUBLISHABLE_KEY } from '@/lib/clerkConfig'

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

function ClerkAppInner() {
  const { isLoaded: isUserLoaded, isSignedIn: isUserSignedIn, user: clerkUser } = useUser()
  const { isLoaded: isAuthLoaded, isSignedIn: isAuthSignedIn, getToken } = useClerkAuth()
  const { loadChats, loadFolders, loadModels } = useChat()
  const { user: customUser } = useAuth()

  const isLoaded = isUserLoaded && isAuthLoaded
  const isSignedIn = !!(isUserSignedIn || isAuthSignedIn)

  useEffect(() => {
    if (isSignedIn) {
      // Clean up any remaining sign-in/up hash from Clerk immediately
      if (window.location.hash.includes('sign-') || window.location.hash.includes('__clerk')) {
        window.location.hash = ''
        window.history.replaceState(null, '', window.location.pathname || '/')
        window.dispatchEvent(new HashChangeEvent('hashchange'))
      }

      if (clerkUser) {
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
      }

      // Sync Clerk session token with local storage & API client
      const syncToken = async () => {
        try {
          const token = await getToken()
          if (token) setTokens(token, '')
        } catch {}
      }

      syncToken().finally(() => {
        loadChats()
        loadFolders()
        loadModels()
      })

      // Clerk session tokens expire every ~60s; keep local token continuously fresh
      const refreshInterval = setInterval(syncToken, 35 * 1000)
      return () => clearInterval(refreshInterval)
    }
  }, [isSignedIn, clerkUser, getToken, loadChats, loadFolders, loadModels])

  const isAuthenticated = isSignedIn || !!customUser

  if (!isLoaded && !customUser) return <LoadingExperience />
  if (!isAuthenticated) return <AuthPage />

  return (
    <>
      <ChatPage />
      <SettingsPage />
    </>
  )
}

export default function App() {
  const connection = useConnection()
  const { user: customUser, initialized, loadUser } = useAuth()
  const { loadChats, loadFolders, loadModels } = useChat()
  const [hasEverBeenReady, setHasEverBeenReady] = useState(false)
  const initializedUserRef = useRef(false)
  const loadedChatsRef = useRef(false)

  useKeepAlive() // keep Render backend awake

  // Once backend confirms readiness at least once, unlock the application view
  useEffect(() => {
    if (connection.isReady) {
      setHasEverBeenReady(true)
    }
  }, [connection.isReady])

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

  // When readiness is confirmed, verify user session
  useEffect(() => {
    if (!HAS_CLERK && connection.isReady && !initializedUserRef.current) {
      initializedUserRef.current = true
      loadUser()
    }
  }, [connection.isReady, loadUser])

  // When user is confirmed and ready, load chat data once
  useEffect(() => {
    if (!HAS_CLERK && customUser && connection.isReady && !loadedChatsRef.current) {
      loadedChatsRef.current = true
      loadChats()
      loadFolders()
      loadModels()
    }
  }, [customUser, connection.isReady, loadChats, loadFolders, loadModels])

  // While backend is still performing its initial boot/connection check,
  // show the premium full-screen loading experience immediately.
  if (!hasEverBeenReady && !connection.isReady) {
    return <LoadingExperience />
  }

  return (
    <AnimatedBackground>
      {BYPASS_AUTH ? (
        <>
          <ChatPage />
          <SettingsPage />
        </>
      ) : HAS_CLERK && CLERK_PUBLISHABLE_KEY ? (
        <ClerkAppInner />
      ) : !initialized ? (
        <LoadingExperience />
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
