import React, { useEffect, useState } from 'react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { ChatContainer } from '@/components/chat/ChatContainer'
import { AgentPage } from '@/pages/AgentPage'
import { AgentV2Shell } from '@/components/agent-v2/AgentV2Shell'
import { AgentErrorBoundary } from '@/components/agent/AgentErrorBoundary'
import { TitleBar } from '@/components/desktop/TitleBar'
import { BrowserTabs } from '@/components/desktop/BrowserTabs'
import { useSettings } from '@/stores/settings'
import { isTauri } from '@/lib/tauri'
import { Download } from 'lucide-react'

export function ChatPage() {
  const { setSidebarOpen, appMode } = useSettings()
  const [compact, setCompact] = useState(false)
  const [agentVersion, setAgentVersion] = useState<'v2' | 'classic'>('v2')

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setSidebarOpen(false)
      }
    }
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [setSidebarOpen])

  return (
    <div className="flex h-screen overflow-hidden relative z-10">
      {!compact && <Sidebar />}
      <div className="flex-1 flex flex-col min-w-0">
        {isTauri && <TitleBar compact={compact} onToggleCompact={setCompact} />}
        {isTauri && <BrowserTabs />}
        <Header />
        <main className="flex-1 flex flex-col min-h-0">
          {appMode === 'agent' ? (
            <AgentErrorBoundary panelName="Autonomous AI Product Company Workbench">
              {agentVersion === 'v2' ? (
                <AgentV2Shell onToggleClassic={() => setAgentVersion('classic')} />
              ) : (
                <div className="flex-1 flex flex-col h-full overflow-hidden">
                  <div className="h-8 px-4 bg-muted/60 border-b border-border flex items-center justify-between text-xs font-mono">
                    <span className="text-muted-foreground">Classic Agent Mode</span>
                    <button
                      onClick={() => setAgentVersion('v2')}
                      className="text-primary hover:underline font-bold"
                    >
                      Switch to Agent V2 (AI Company)
                    </button>
                  </div>
                  <AgentPage />
                </div>
              )}
            </AgentErrorBoundary>
          ) : (
            <ChatContainer />
          )}
        </main>
        {!compact && (
          <footer className="flex items-center justify-between px-4 py-2 border-t border-border bg-background relative z-10 text-[11px] text-muted-foreground/50">
            <a
              href="https://hs-ai-studio.onrender.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              © {new Date().getFullYear()} HSBot — HS AI Solution
            </a>
            {!isTauri && (
              <a
                href="/downloads/HSBot_1.0.0_x64-setup.exe"
                download="HSBot_1.0.0_x64-setup.exe"
                className="flex items-center gap-1.5 text-primary hover:underline font-medium transition-colors"
                title="Download HSBot Windows Setup (.exe)"
              >
                <Download size={11} />
                <span>Download Windows App (.exe)</span>
              </a>
            )}
          </footer>
        )}
      </div>
    </div>
  )
}
