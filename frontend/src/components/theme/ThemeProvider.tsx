import React, { createContext, useContext, useEffect, useState, useMemo, useCallback } from 'react'

type Theme = 'light' | 'dark' | 'system' | string

interface UseThemeProps {
  theme: string
  setTheme: (theme: string) => void
  resolvedTheme: 'light' | 'dark'
  themes: string[]
  systemTheme?: 'light' | 'dark'
  forcedTheme?: string
}

interface ThemeProviderProps {
  children: React.ReactNode
  defaultTheme?: string
  storageKey?: string
  attribute?: string
  enableSystem?: boolean
  forcedTheme?: string
  themes?: string[]
  disableTransitionOnChange?: boolean
}

const ThemeContext = createContext<UseThemeProps>({
  theme: 'system',
  setTheme: () => {},
  resolvedTheme: 'light',
  themes: ['light', 'dark', 'system'],
  systemTheme: 'light',
})

function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'theme',
  attribute = 'class',
  enableSystem = true,
  forcedTheme,
  themes = ['light', 'dark', 'system'],
}: ThemeProviderProps) {
  const [theme, setInternalTheme] = useState<string>(() => {
    if (forcedTheme) return forcedTheme
    if (typeof window === 'undefined') return defaultTheme
    try {
      return localStorage.getItem(storageKey) || defaultTheme
    } catch {
      return defaultTheme
    }
  })

  const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>(() => getSystemTheme())

  // Listen for system theme changes
  useEffect(() => {
    if (!enableSystem || typeof window === 'undefined') return
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const handleChange = (e: MediaQueryListEvent) => {
      setSystemTheme(e.matches ? 'dark' : 'light')
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [enableSystem])

  const resolvedTheme: 'light' | 'dark' = useMemo(() => {
    if (forcedTheme) return forcedTheme === 'dark' ? 'dark' : 'light'
    if (theme === 'system' && enableSystem) return systemTheme
    return theme === 'dark' ? 'dark' : 'light'
  }, [forcedTheme, theme, enableSystem, systemTheme])

  // Apply to DOM without rendering any script tag
  useEffect(() => {
    if (typeof document === 'undefined') return
    const root = document.documentElement

    if (attribute === 'class') {
      root.classList.remove('light', 'dark')
      root.classList.add(resolvedTheme)
    } else {
      root.setAttribute(attribute, resolvedTheme)
    }

    root.style.colorScheme = resolvedTheme
  }, [attribute, resolvedTheme])

  const setTheme = useCallback(
    (newTheme: string) => {
      if (forcedTheme) return
      setInternalTheme(newTheme)
      try {
        localStorage.setItem(storageKey, newTheme)
      } catch {
        // ignore storage write errors
      }
    },
    [forcedTheme, storageKey]
  )

  const value = useMemo(
    () => ({
      theme: forcedTheme || theme,
      setTheme,
      resolvedTheme,
      themes,
      systemTheme: enableSystem ? systemTheme : undefined,
      forcedTheme,
    }),
    [forcedTheme, theme, setTheme, resolvedTheme, themes, enableSystem, systemTheme]
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): UseThemeProps {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
