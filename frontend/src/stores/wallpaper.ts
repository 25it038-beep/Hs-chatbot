import { create } from 'zustand'

export interface WallpaperItem {
  id: string
  title: string
  subtitle: string
  color: string
  previewUrl: string
  fullUrl: string
}

export const WALLPAPERS: WallpaperItem[] = [
  {
    id: 'none',
    title: 'Ambient Glow',
    subtitle: 'Reactive RGB Aura (Default)',
    color: '#6366f1',
    previewUrl: '',
    fullUrl: '',
  },
  {
    id: 'pink-lotus',
    title: 'Pink Petal Macro',
    subtitle: 'Delicate floral curves',
    color: '#f472b6',
    previewUrl: '/wallpapers/pink-lotus-thumb.jpg',
    fullUrl: '/wallpapers/pink-lotus.jpg',
  },
  {
    id: 'emerald-dew',
    title: 'Emerald Dewdrops',
    subtitle: 'Morning forest drops',
    color: '#10b981',
    previewUrl: '/wallpapers/emerald-dew-thumb.jpg',
    fullUrl: '/wallpapers/emerald-dew.jpg',
  },
  {
    id: 'violet-bloom',
    title: 'Violet Petals',
    subtitle: 'Deep indigo & iris',
    color: '#8b5cf6',
    previewUrl: '/wallpapers/violet-bloom-thumb.jpg',
    fullUrl: '/wallpapers/violet-bloom.jpg',
  },
  {
    id: 'golden-sunburst',
    title: 'Golden Sunburst',
    subtitle: 'Amber floral rays',
    color: '#f59e0b',
    previewUrl: '/wallpapers/golden-sunburst-thumb.jpg',
    fullUrl: '/wallpapers/golden-sunburst.jpg',
  },
  {
    id: 'azure-dandelion',
    title: 'Azure Dandelion Drop',
    subtitle: 'Crystal blue spheres',
    color: '#0ea5e9',
    previewUrl: '/wallpapers/azure-dandelion-thumb.jpg',
    fullUrl: '/wallpapers/azure-dandelion.jpg',
  },
  {
    id: 'creamy-rose',
    title: 'Creamy White Rose',
    subtitle: 'Ethereal ivory swirl',
    color: '#e2e8f0',
    previewUrl: '/wallpapers/creamy-rose-thumb.jpg',
    fullUrl: '/wallpapers/creamy-rose.jpg',
  },
  {
    id: 'crimson-leaf',
    title: 'Crimson Velvet Leaf',
    subtitle: 'Ruby botanical veins',
    color: '#ef4444',
    previewUrl: '/wallpapers/crimson-leaf-thumb.jpg',
    fullUrl: '/wallpapers/crimson-leaf.jpg',
  },
  {
    id: 'spring-droplet',
    title: 'Spring Green Blade',
    subtitle: 'Lush hanging droplet',
    color: '#22c55e',
    previewUrl: '/wallpapers/spring-droplet-thumb.jpg',
    fullUrl: '/wallpapers/spring-droplet.jpg',
  },
  {
    id: 'magenta-dew',
    title: 'Magenta Orchid Drops',
    subtitle: 'Shimmering dew spheres',
    color: '#ec4899',
    previewUrl: '/wallpapers/magenta-dew-thumb.jpg',
    fullUrl: '/wallpapers/magenta-dew.jpg',
  },
  {
    id: 'teal-cascade',
    title: 'Teal Silk Cascade',
    subtitle: 'Cool ocean cyan curves',
    color: '#06b6d4',
    previewUrl: '/wallpapers/teal-cascade-thumb.jpg',
    fullUrl: '/wallpapers/teal-cascade.jpg',
  },
  {
    id: 'warm-stamen',
    title: 'Golden Flora Glow',
    subtitle: 'Pastel sunset stamen',
    color: '#fbbf24',
    previewUrl: '/wallpapers/warm-stamen-thumb.jpg',
    fullUrl: '/wallpapers/warm-stamen.jpg',
  },
  {
    id: 'midnight-dew',
    title: 'Midnight Indigo Bloom',
    subtitle: 'Luminescent night drops',
    color: '#6366f1',
    previewUrl: '/wallpapers/midnight-dew-thumb.jpg',
    fullUrl: '/wallpapers/midnight-dew.jpg',
  },
  {
    id: 'macro-collage',
    title: 'Macro Flora Collage',
    subtitle: 'All 12 floral horizons',
    color: '#a855f7',
    previewUrl: '/wallpapers/macro-collage.jpg',
    fullUrl: '/wallpapers/macro-collage.jpg',
  },
]

// Only image-based wallpapers for cycling (skip 'none')
export const CYCLEABLE_WALLPAPERS = WALLPAPERS.filter(w => w.id !== 'none')

interface WallpaperState {
  currentWallpaperId: string
  autoCycle: boolean
  cycleIntervalSeconds: number
  opacity: number
  blur: number
  isPickerOpen: boolean

  setWallpaper: (id: string) => void
  setAutoCycle: (enabled: boolean) => void
  setCycleIntervalSeconds: (seconds: number) => void
  setOpacity: (opacity: number) => void
  setBlur: (blur: number) => void
  setPickerOpen: (open: boolean) => void
  nextWallpaper: () => void
  prevWallpaper: () => void
}

function getStoredString(key: string, def: string): string {
  try {
    return localStorage.getItem(key) || def
  } catch {
    return def
  }
}

function getStoredBool(key: string, def: boolean): boolean {
  try {
    const val = localStorage.getItem(key)
    return val === null ? def : val === 'true'
  } catch {
    return def
  }
}

function getStoredNumber(key: string, def: number): number {
  try {
    const val = localStorage.getItem(key)
    return val === null ? def : Number(val)
  } catch {
    return def
  }
}

export const useWallpaperStore = create<WallpaperState>((set, get) => ({
  currentWallpaperId: getStoredString('hsbot_wallpaper', 'none'),
  autoCycle: getStoredBool('hsbot_wallpaper_autocycle', false),
  cycleIntervalSeconds: getStoredNumber('hsbot_wallpaper_cycle_sec', 30),
  opacity: getStoredNumber('hsbot_wallpaper_opacity', 0.45),
  blur: getStoredNumber('hsbot_wallpaper_blur', 0),
  isPickerOpen: false,

  setWallpaper: (id: string) => {
    localStorage.setItem('hsbot_wallpaper', id)
    set({ currentWallpaperId: id })
  },

  setAutoCycle: (enabled: boolean) => {
    localStorage.setItem('hsbot_wallpaper_autocycle', String(enabled))
    // If enabling auto-cycle and current is 'none', switch to first wallpaper
    if (enabled && get().currentWallpaperId === 'none') {
      const first = CYCLEABLE_WALLPAPERS[0]?.id || 'pink-lotus'
      localStorage.setItem('hsbot_wallpaper', first)
      set({ autoCycle: enabled, currentWallpaperId: first })
      return
    }
    set({ autoCycle: enabled })
  },

  setCycleIntervalSeconds: (seconds: number) => {
    const valid = Math.max(5, seconds)
    localStorage.setItem('hsbot_wallpaper_cycle_sec', String(valid))
    set({ cycleIntervalSeconds: valid })
  },

  setOpacity: (opacity: number) => {
    const clamped = Math.max(0.05, Math.min(1.0, opacity))
    localStorage.setItem('hsbot_wallpaper_opacity', String(clamped))
    set({ opacity: clamped })
  },

  setBlur: (blur: number) => {
    const clamped = Math.max(0, Math.min(20, blur))
    localStorage.setItem('hsbot_wallpaper_blur', String(clamped))
    set({ blur: clamped })
  },

  setPickerOpen: (open: boolean) => set({ isPickerOpen: open }),

  nextWallpaper: () => {
    const { currentWallpaperId } = get()
    const currentIndex = CYCLEABLE_WALLPAPERS.findIndex(w => w.id === currentWallpaperId)
    const nextIndex = currentIndex === -1 ? 0 : (currentIndex + 1) % CYCLEABLE_WALLPAPERS.length
    const next = CYCLEABLE_WALLPAPERS[nextIndex]
    if (next) {
      localStorage.setItem('hsbot_wallpaper', next.id)
      set({ currentWallpaperId: next.id })
    }
  },

  prevWallpaper: () => {
    const { currentWallpaperId } = get()
    const currentIndex = CYCLEABLE_WALLPAPERS.findIndex(w => w.id === currentWallpaperId)
    const prevIndex = currentIndex <= 0 ? CYCLEABLE_WALLPAPERS.length - 1 : currentIndex - 1
    const prev = CYCLEABLE_WALLPAPERS[prevIndex]
    if (prev) {
      localStorage.setItem('hsbot_wallpaper', prev.id)
      set({ currentWallpaperId: prev.id })
    }
  },
}))
