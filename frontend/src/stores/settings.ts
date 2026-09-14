import { create } from 'zustand'

interface SettingsState {
  sidebarOpen: boolean
  settingsOpen: boolean
  automationOpen: boolean
  browserAutomationPriority: boolean
  toggleSidebar: () => void
  toggleSettings: () => void
  setSidebarOpen: (open: boolean) => void
  setSettingsOpen: (open: boolean) => void
  setAutomationOpen: (open: boolean) => void
  setBrowserAutomationPriority: (priority: boolean) => void
}

export const useSettings = create<SettingsState>((set) => ({
  sidebarOpen: true,
  settingsOpen: false,
  automationOpen: false,
  browserAutomationPriority: false,
  toggleSidebar: () => set(state => ({ sidebarOpen: !state.sidebarOpen })),
  toggleSettings: () => set(state => ({ settingsOpen: !state.settingsOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setSettingsOpen: (open) => set({ settingsOpen: open }),
  setAutomationOpen: (open) => set({ automationOpen: open }),
  setBrowserAutomationPriority: (priority) => set({ browserAutomationPriority: priority }),
}))
