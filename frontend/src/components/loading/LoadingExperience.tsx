import React, { useState } from 'react'
import { BackendStatusIndicator } from './BackendStatusIndicator'
import { RotatingTips } from './RotatingTips'
import { ProductShowcase } from './ProductShowcase'
import { HowToUseGuide } from './HowToUseGuide'
import { useConnection } from '@/hooks/useConnection'
import { Sparkles, Layers, BookOpen, Lightbulb } from 'lucide-react'

interface LoadingExperienceProps {
  onReady?: () => void
}

export function LoadingExperience({ onReady }: LoadingExperienceProps) {
  const connection = useConnection()
  const [activeMobileTab, setActiveMobileTab] = useState<'tips' | 'products' | 'guide'>('tips')

  return (
    <div className="min-h-screen w-full bg-background text-foreground flex flex-col justify-between relative overflow-x-hidden selection:bg-brand/30 selection:text-foreground pt-safe pb-safe">
      {/* Cinematic Ambient Atmosphere Glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-[20%] left-1/2 -translate-x-1/2 w-[600px] h-[500px] sm:w-[900px] sm:h-[600px] bg-brand/10 rounded-full blur-[120px] opacity-70" />
        <div className="absolute top-[40%] -left-[10%] w-[350px] h-[350px] bg-cyan-500/5 rounded-full blur-[100px] opacity-50" />
        <div className="absolute bottom-[10%] -right-[10%] w-[400px] h-[400px] bg-amber-500/5 rounded-full blur-[100px] opacity-40" />
      </div>

      {/* Top Ambient Navigation Bar */}
      <header className="w-full border-b border-border/50 bg-background/60 backdrop-blur-md px-4 sm:px-6 py-2.5 sm:py-3 relative z-10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg overflow-hidden border border-border shadow-xs">
            <img src="/logo.jpg" alt="HSBot" className="w-full h-full object-cover" />
          </div>
          <span className="font-bold text-sm tracking-tight text-foreground">HS Bot</span>
          <span className="text-[10px] text-muted-foreground/70 bg-muted/60 px-2 py-0.5 rounded-full border border-border/60 ml-1 hidden xs:inline-block">
            HS AI Solutions
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="relative flex h-2 w-2">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                connection.state === 'CONNECTED'
                  ? 'bg-emerald-400'
                  : connection.state === 'WAKING_UP'
                  ? 'bg-amber-400'
                  : 'bg-brand'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                connection.state === 'CONNECTED'
                  ? 'bg-emerald-500'
                  : connection.state === 'WAKING_UP'
                  ? 'bg-amber-500'
                  : 'bg-brand'
              }`}
            />
          </span>
          <span className="text-[11px] font-medium hidden sm:inline">
            {connection.state.replace('_', ' ')}
          </span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-3 sm:px-6 py-6 sm:py-8 relative z-10 flex flex-col justify-center">
        {/* Responsive Grid: Status & Monitor on Left / Ecosystem on Right (Desktop) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8 items-start">
          {/* Left Column: Backend Connection Status + Rotating AI Tips */}
          <div className="lg:col-span-5 flex flex-col items-center space-y-6">
            <BackendStatusIndicator connection={connection} />

            {/* Desktop: Rotating Tips below status */}
            <div className="w-full hidden lg:block">
              <RotatingTips />
            </div>
          </div>

          {/* Right Column: Mobile Tabs / Desktop Split for Ecosystem & How-To */}
          <div className="lg:col-span-7 flex flex-col space-y-5">
            {/* Mobile Tab Switcher */}
            <div className="flex lg:hidden items-center justify-center p-1 rounded-xl bg-card/60 border border-border/60 backdrop-blur-md mb-2">
              <button
                onClick={() => setActiveMobileTab('tips')}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  activeMobileTab === 'tips'
                    ? 'bg-brand text-brand-foreground shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Lightbulb size={12} />
                <span>AI Tips</span>
              </button>
              <button
                onClick={() => setActiveMobileTab('products')}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  activeMobileTab === 'products'
                    ? 'bg-brand text-brand-foreground shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Layers size={12} />
                <span>Ecosystem</span>
              </button>
              <button
                onClick={() => setActiveMobileTab('guide')}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  activeMobileTab === 'guide'
                    ? 'bg-brand text-brand-foreground shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <BookOpen size={12} />
                <span>Features</span>
              </button>
            </div>

            {/* Mobile Content Display */}
            <div className="block lg:hidden">
              {activeMobileTab === 'tips' && <RotatingTips />}
              {activeMobileTab === 'products' && <ProductShowcase />}
              {activeMobileTab === 'guide' && <HowToUseGuide />}
            </div>

            {/* Desktop Display (Both Ecosystem and How-To visible) */}
            <div className="hidden lg:flex flex-col space-y-6">
              <ProductShowcase />
              <HowToUseGuide />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full border-t border-border/40 bg-background/50 backdrop-blur-md px-4 sm:px-6 py-3 relative z-10 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-muted-foreground/60">
        <div className="flex items-center gap-2">
          <span>© {new Date().getFullYear()} HS AI Solutions</span>
          <span className="hidden sm:inline">•</span>
          <span className="hidden sm:inline">HS Bot Unified Intelligence</span>
        </div>

        <div className="flex items-center gap-3">
          <a
            href="https://hs-ai-studio-4i7i.vercel.app/"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-brand transition-colors text-[11px]"
          >
            HS AI Studio ↗
          </a>
          <span>•</span>
          <a
            href="/downloads/HSBot_1.0.0_x64-setup.exe"
            className="hover:text-foreground transition-colors text-[11px]"
          >
            Windows App (.exe)
          </a>
        </div>
      </footer>
    </div>
  )
}
