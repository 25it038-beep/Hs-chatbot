import { create } from 'zustand'

const FESTIVAL_KEY = 'hsbot-festival-enabled'

interface AmbientStore {
  userTyping: boolean
  setUserTyping: (typing: boolean) => void
  festivalEnabled: boolean
  setFestivalEnabled: (enabled: boolean) => void
}

function readFestivalPreference(): boolean {
  try {
    return localStorage.getItem(FESTIVAL_KEY) !== '0'
  } catch {
    return true
  }
}

export const useAmbient = create<AmbientStore>((set) => ({
  userTyping: false,
  setUserTyping: (typing) => set({ userTyping: typing }),
  festivalEnabled: readFestivalPreference(),
  setFestivalEnabled: (enabled) => {
    try {
      localStorage.setItem(FESTIVAL_KEY, enabled ? '1' : '0')
    } catch {
      /* ignore */
    }
    set({ festivalEnabled: enabled })
  },
}))