export interface ProductItem {
  id: string
  name: string
  brand: string
  tagline: string
  description: string
  actionLabel: string
  actionUrl?: string
  isExternal?: boolean
  badge?: string
  isCurrent?: boolean
  icon: 'studio' | 'bot' | 'desktop' | 'core'
}

export const HS_PRODUCTS: ProductItem[] = [
  {
    id: 'hs-ai-studio',
    name: 'HS AI Studio',
    brand: 'HS AI Solutions',
    tagline: 'Flagship Creative & Workflow Studio',
    description: 'AI platform by HS AI Solutions.',
    actionLabel: 'Explore HS AI Studio',
    actionUrl: 'https://hs-ai-studio-4i7i.vercel.app/',
    isExternal: true,
    badge: 'Featured Ecosystem',
    icon: 'studio',
  },
  {
    id: 'hs-bot',
    name: 'HS Bot',
    brand: 'HS AI Solutions',
    tagline: 'Autonomous Conversational Assistant',
    description: 'Intelligent AI assistant featuring multi-model auto-routing, coding intelligence, and document synthesis.',
    actionLabel: 'Current Assistant',
    isCurrent: true,
    badge: 'Active Application',
    icon: 'bot',
  },
  {
    id: 'electorn',
    name: 'Electorn',
    brand: 'HS AI Solutions',
    tagline: 'High-Performance Desktop Client',
    description: 'Native Windows desktop companion with global hotkey invocation (Ctrl+Space), local acceleration, and deep automation.',
    actionLabel: 'Download Windows App',
    actionUrl: '/downloads/HSBot_1.0.0_x64-setup.exe',
    isExternal: false,
    badge: 'Desktop App',
    icon: 'desktop',
  },
  {
    id: 'hs-ai-core',
    name: 'HS AI Core',
    brand: 'HS AI Solutions',
    tagline: 'Resilient Multi-Provider Engine',
    description: 'Unified intelligence routing architecture optimizing low-latency inference across NVIDIA, SambaNova, and hybrid endpoints.',
    actionLabel: 'Engine Architecture',
    badge: 'Foundational Infrastructure',
    icon: 'core',
  },
]
