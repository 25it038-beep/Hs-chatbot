import React, { useState, useEffect, useRef } from 'react'
import {
  RotateCcw,
  ExternalLink,
  Smartphone,
  Tablet,
  Monitor,
  Terminal,
  AlertTriangle,
  Maximize2
} from 'lucide-react'

interface AgentV2PreviewProps {
  files: Record<string, string>
  onOpenFullscreen?: () => void
}

export function AgentV2Preview({ files, onOpenFullscreen }: AgentV2PreviewProps) {
  const [device, setDevice] = useState<'desktop' | 'tablet' | 'mobile'>('desktop')
  const [previewHtml, setPreviewHtml] = useState<string>('')
  const [consoleLogs, setConsoleLogs] = useState<{ type: string; message: string }[]>([])
  const [showConsole, setShowConsole] = useState(false)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  const buildCompiledHtml = () => {
    const rawHtml = files['index.html']
    if (!rawHtml) {
      setPreviewHtml('')
      return
    }

    let compiled = rawHtml
    const cssContent = files['styles.css'] || ''
    const jsContent = files['script.js'] || ''

    // Inject styles
    if (cssContent) {
      if (compiled.includes('</head>')) {
        compiled = compiled.replace('</head>', `<style>\n${cssContent}\n</style>\n</head>`)
      } else {
        compiled = `<style>\n${cssContent}\n</style>\n` + compiled
      }
    }

    // Inject script with resilient load listener & console capture
    const scriptShim = `
<script>
(function() {
  // Capture console logs for preview inspector
  const _log = console.log;
  const _err = console.error;
  window.addEventListener('error', function(e) {
    window.parent.postMessage({ type: 'preview_log', level: 'error', message: e.message }, '*');
  });

  // Ensure DOMContentLoaded always triggers even in srcdoc
  const origAdd = document.addEventListener.bind(document);
  document.addEventListener = function(type, listener, options) {
    if (type === 'DOMContentLoaded' && (document.readyState === 'interactive' || document.readyState === 'complete')) {
      setTimeout(function() {
        try { listener({ type: 'DOMContentLoaded', target: document }); } catch(err) { console.error('Script Error:', err); }
      }, 0);
    } else {
      origAdd(type, listener, options);
    }
  };
})();
${jsContent}
</script>`

    if (compiled.includes('</body>')) {
      compiled = compiled.replace('</body>', `${scriptShim}\n</body>`)
    } else {
      compiled = compiled + `\n${scriptShim}`
    }

    setPreviewHtml(compiled)
  }

  useEffect(() => {
    buildCompiledHtml()
  }, [files])

  useEffect(() => {
    const handleMsg = (e: MessageEvent) => {
      if (e.data && e.data.type === 'preview_log') {
        setConsoleLogs((prev) => [...prev.slice(-30), { type: e.data.level, message: e.data.message }])
      }
    }
    window.addEventListener('message', handleMsg)
    return () => window.removeEventListener('message', handleMsg)
  }, [])

  const handleOpenNewTab = () => {
    if (!previewHtml) return
    const blob = new Blob([previewHtml], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
  }

  const getDeviceWidth = () => {
    switch (device) {
      case 'mobile':
        return 'w-[375px]'
      case 'tablet':
        return 'w-[768px]'
      default:
        return 'w-full'
    }
  }

  return (
    <div className="flex flex-col h-full bg-slate-950/60 overflow-hidden select-none">
      {/* Top Preview Control Bar */}
      <div className="h-10 px-4 border-b border-border bg-card/60 flex items-center justify-between text-xs">
        {/* Device Switcher */}
        <div className="flex items-center gap-1 bg-muted/60 p-0.5 rounded-lg border border-border/60">
          <button
            onClick={() => setDevice('desktop')}
            className={`p-1 rounded ${device === 'desktop' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            title="Desktop 1440px"
          >
            <Monitor size={13} />
          </button>
          <button
            onClick={() => setDevice('tablet')}
            className={`p-1 rounded ${device === 'tablet' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            title="Tablet 768px"
          >
            <Tablet size={13} />
          </button>
          <button
            onClick={() => setDevice('mobile')}
            className={`p-1 rounded ${device === 'mobile' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            title="Mobile 375px"
          >
            <Smartphone size={13} />
          </button>
        </div>

        {/* Right Tools */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowConsole(!showConsole)}
            className={`px-2 py-1 rounded text-[11px] font-mono flex items-center gap-1 transition-colors ${
              consoleLogs.length > 0 ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' : 'text-muted-foreground hover:bg-muted'
            }`}
          >
            <Terminal size={11} />
            <span>Console ({consoleLogs.length})</span>
          </button>

          <button
            onClick={buildCompiledHtml}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted transition-colors"
            title="Reload Preview"
          >
            <RotateCcw size={13} />
          </button>

          <button
            onClick={handleOpenNewTab}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted transition-colors"
            title="Open in new window"
          >
            <ExternalLink size={13} />
          </button>

          {onOpenFullscreen && (
            <button
              onClick={onOpenFullscreen}
              className="p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted transition-colors"
              title="Fullscreen"
            >
              <Maximize2 size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Main Preview Container */}
      <div className="flex-1 overflow-auto flex items-center justify-center p-4 bg-slate-950/80">
        {previewHtml ? (
          <div
            className={`h-full bg-white rounded-xl shadow-2xl overflow-hidden border border-border/50 transition-all duration-200 flex flex-col ${getDeviceWidth()}`}
          >
            <iframe
              ref={iframeRef}
              srcDoc={previewHtml}
              title="Live App Preview"
              sandbox="allow-scripts allow-modals allow-same-origin allow-forms"
              className="w-full h-full border-0 bg-white"
            />
          </div>
        ) : (
          <div className="text-center text-muted-foreground p-8">
            <Monitor size={32} className="mx-auto opacity-20 mb-3" />
            <p className="text-xs font-semibold">Live Sandbox Viewport Ready</p>
            <p className="text-[11px] text-muted-foreground/60 mt-1">
              Synthesized application will mount here automatically upon code generation.
            </p>
          </div>
        )}
      </div>

      {/* Optional Console Drawer */}
      {showConsole && (
        <div className="h-32 border-t border-border bg-slate-950 p-3 overflow-y-auto font-mono text-[11px] text-slate-300">
          <div className="flex items-center justify-between text-slate-500 mb-2 pb-1 border-b border-slate-900 text-[10px]">
            <span>SANDBOX RUNTIME CONSOLE</span>
            <button onClick={() => setConsoleLogs([])} className="hover:text-slate-300">
              Clear
            </button>
          </div>
          {consoleLogs.length > 0 ? (
            consoleLogs.map((log, i) => (
              <div key={i} className="flex items-start gap-2 py-0.5">
                <span className={log.type === 'error' ? 'text-rose-400 font-bold' : 'text-slate-400'}>
                  [{log.type.toUpperCase()}]
                </span>
                <span className="text-slate-200">{log.message}</span>
              </div>
            ))
          ) : (
            <p className="text-slate-600">No runtime errors logged.</p>
          )}
        </div>
      )}
    </div>
  )
}
