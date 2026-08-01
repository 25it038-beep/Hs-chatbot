import { create } from 'zustand'
import type { User } from '@/types'
import { api, setTokens, clearTokens } from '@/lib/api'

interface AuthState {
  user: User | null
  loading: boolean
  initialized: boolean
  login: (username: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: false,
  initialized: false,

  login: async (username, password) => {
    set({ loading: true })
    try {
      const data = await api.login(username, password)
      setTokens(data.access_token, data.refresh_token)
      set({ user: data.user, loading: false, initialized: true })
    } catch (error) {
      set({ loading: false })
      throw error
    }
  },

  register: async (email, username, password) => {
    set({ loading: true })
    try {
      const data = await api.register(email, username, password)
      setTokens(data.access_token, data.refresh_token)
      set({ user: data.user, loading: false, initialized: true })
    } catch (error) {
      set({ loading: false })
      throw error
    }
  },

  logout: () => {
    clearTokens()
    set({ user: null, initialized: true })
  },

  loadUser: async () => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      set({ user: null, initialized: true })
      return
    }
    try {
      const user = await api.getMe()
      set({ user, initialized: true })
    } catch {
      clearTokens()
      set({ user: null, initialized: true })
    }
  },
}))
