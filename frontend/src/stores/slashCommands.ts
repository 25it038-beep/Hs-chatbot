import { create } from 'zustand'

interface SlashCommandsState {
  recentlyUsed: string[] // Array of command IDs
  pinnedCommands: string[] // Array of command IDs
  addRecentlyUsed: (id: string) => void
  togglePin: (id: string) => void
  isPinned: (id: string) => boolean
}

const RECENT_KEY = 'hsbot_slash_recent'
const PINNED_KEY = 'hsbot_slash_pinned'

const getInitialRecent = (): string[] => {
  try {
    const data = localStorage.getItem(RECENT_KEY)
    return data ? JSON.parse(data) : ['chat', 'code', 'image', 'settings']
  } catch {
    return ['chat', 'code', 'image', 'settings']
  }
}

const getInitialPinned = (): string[] => {
  try {
    const data = localStorage.getItem(PINNED_KEY)
    return data ? JSON.parse(data) : ['chat', 'code']
  } catch {
    return ['chat', 'code']
  }
}

export const useSlashCommandsStore = create<SlashCommandsState>((set, get) => ({
  recentlyUsed: getInitialRecent(),
  pinnedCommands: getInitialPinned(),

  addRecentlyUsed: (id: string) => {
    const current = get().recentlyUsed
    const updated = [id, ...current.filter(item => item !== id)].slice(0, 10)
    try {
      localStorage.setItem(RECENT_KEY, JSON.stringify(updated))
    } catch {}
    set({ recentlyUsed: updated })
  },

  togglePin: (id: string) => {
    const current = get().pinnedCommands
    const exists = current.includes(id)
    const updated = exists ? current.filter(item => item !== id) : [...current, id]
    try {
      localStorage.setItem(PINNED_KEY, JSON.stringify(updated))
    } catch {}
    set({ pinnedCommands: updated })
  },

  isPinned: (id: string) => {
    return get().pinnedCommands.includes(id)
  },
}))
