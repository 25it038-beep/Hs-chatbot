import React, { useState, useEffect } from 'react'
import { WebProject, downloadProjectZip, buildCombinedHtmlPreview } from '@/lib/webProject'
import { agentApi } from '@/lib/agentApi'
import { useSettings } from '@/stores/settings'
import {
  FolderArchive,
  Gamepad2,
  Download,
  Eye,
  Bot,
  FileCode,
  Check,
  Maximize2,
  Minimize2,
  RotateCw,
  Smartphone,
  Tablet,
  Monitor,
  X,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
} from 'lucide-react'

interface WebProjectCardProps {
  project: WebProject
  messageId?: string
}

export function WebProjectCard({ project, messageId }: WebProjectCardProps) {
  const [downloading, setDownloading] = useState(false)
  const [downloaded, setDownloaded] = useState(false)
  const [openingAgent, setOpeningAgent] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewDevice, setPreviewDevice] = useState<'desktop' | 'tablet' | 'mobile'>('desktop')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [iframeKey, setIframeKey] = useState(0)
  const [runtimeErrors, setRuntimeErrors] = useState<string[]>([])

  const { setAppMode } = useSettings()

  useEffect(() => {
    const handleMsg = (event: MessageEvent) => {
      if (event.data && event.data.type === 'hsbot_preview_status' && event.data.error) {
        setRuntimeErrors(prev => Array.from(new Set([...prev, String(event.data.error)])))
      }
    }
    window.addEventListener('message', handleMsg)
    return () => window.removeEventListener('message', handleMsg)
  }, [])

  const handleDownload = async () => {
    try {
      setDownloading(true)
      const zipName = project.isGame ? `${project.gameGenre || 'game'}-project.zip` : 'website-project.zip'
      await downloadProjectZip(project, zipName)
      setDownloaded(true)
      setTimeout(() => setDownloaded(false), 3000)
    } catch (err) {
      console.error('Failed to download project zip:', err)
    } finally {
      setDownloading(false)
    }
  }

  const handleOpenInAgent = async () => {
    try {
      setOpeningAgent(true)
      // Push each file into the agent workspace
      for (const file of project.files) {
        await agentApi.writeFile(file.path, file.content)
      }
      // Switch mode to agent workbench
      setAppMode('agent')
    } catch (err) {
      console.error('Failed to export to agent workspace:', err)
    } finally {
      setOpeningAgent(false)
    }
  }

  const combinedHtml = buildCombinedHtmlPreview(project)

  return (
    <>
      <div className={`my-4 rounded-xl border backdrop-blur-sm p-4 shadow-md transition-all ${
        project.isGame
          ? 'border-emerald-500/40 bg-card/85 hover:border-emerald-500/60 shadow-emerald-500/5'
          : 'border-primary/30 bg-card/70 hover:border-primary/50'
      }`}>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-border/40 pb-3">
          <div className="flex items-center gap-2.5">
            <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${
              project.isGame ? 'bg-emerald-500/10 text-emerald-400' : 'bg-primary/10 text-primary'
            }`}>
              {project.isGame ? <Gamepad2 size={20} /> : <FolderArchive size={20} />}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-sm text-foreground">
                  {project.isGame
                    ? `Playable ${project.gameGenre ? project.gameGenre.toUpperCase() + ' ' : ''}Game Package`
                    : 'Complete Web Project Package'}
                </span>
                <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-500 border border-emerald-500/20">
                  {project.isGame ? 'Ready to Play' : 'Ready to Run'}
                </span>
                {project.isGame && (
                  <span className="rounded-full bg-cyan-500/10 px-2 py-0.5 text-[10px] font-medium text-cyan-400 border border-cyan-500/20 flex items-center gap-1">
                    <ShieldCheck size={11} />
                    Verified (Polished)
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {project.isGame
                  ? 'Procedural vector graphics, 60 FPS loop, responsive controls & Web Audio synthesized'
                  : 'All source files generated — HTML5, CSS, JavaScript & configuration bundled'}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            <button
              onClick={() => {
                setRuntimeErrors([])
                setPreviewOpen(true)
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-secondary/80 hover:bg-secondary text-foreground transition-all border border-border/50"
              title={project.isGame ? 'Play Game in Live Preview' : 'Interactive Live Preview'}
            >
              {project.isGame ? <Gamepad2 size={13} className="text-emerald-400" /> : <Eye size={13} />}
              <span>{project.isGame ? 'Play Game' : 'Live Preview'}</span>
            </button>

            <button
              onClick={handleDownload}
              disabled={downloading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-sm"
              title="Download full project as ZIP"
            >
              {downloaded ? <Check size={13} className="text-white" /> : <Download size={13} />}
              <span>{downloading ? 'Packaging...' : downloaded ? 'Downloaded!' : 'Download ZIP'}</span>
            </button>

            <button
              onClick={handleOpenInAgent}
              disabled={openingAgent}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 border border-indigo-500/30 transition-all"
              title="Open all project files in Autonomous Agent Workbench"
            >
              <Bot size={13} />
              <span>{openingAgent ? 'Loading Agent...' : 'Agent Mode'}</span>
            </button>
          </div>
        </div>

        {/* Project Files List */}
        <div className="mt-3">
          <div className="text-[11px] font-medium text-muted-foreground mb-1.5 flex items-center justify-between">
            <span>Project Workspace ({project.files.length} files):</span>
            {project.isGame && (
              <span className="text-[10px] text-emerald-400/90 font-mono">
                HTML5 Canvas • Delta Time • Web Audio • FSM
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {project.files.map(f => (
              <span
                key={f.path}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-muted/60 text-[11px] font-mono text-muted-foreground border border-border/40 hover:text-foreground transition-colors"
                title={`${f.path} (${f.content.length} chars)`}
              >
                <FileCode size={11} className="text-primary/70" />
                {f.path}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Interactive Responsive Live Preview Modal */}
      {previewOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-2 sm:p-4 backdrop-blur-md animate-in fade-in duration-200">
          <div className={`flex flex-col w-full bg-slate-950 border border-slate-800 shadow-2xl overflow-hidden transition-all duration-300 ${
            isFullscreen ? 'fixed inset-0 h-full max-w-none rounded-none' : 'h-[92vh] max-w-5xl rounded-2xl'
          }`}>
            {/* Modal Header */}
            <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900 border-b border-slate-800 text-slate-200">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-red-500/80" />
                  <span className="w-3 h-3 rounded-full bg-amber-500/80" />
                  <span className="w-3 h-3 rounded-full bg-emerald-500/80" />
                </div>
                <div className="flex items-center gap-2">
                  {project.isGame && <Gamepad2 size={15} className="text-emerald-400" />}
                  <span className="text-xs font-semibold text-slate-200">{project.title}</span>
                </div>
              </div>

              {/* Viewport Device Controls & Error Monitor */}
              <div className="flex items-center gap-2">
                {/* Game Error Monitor */}
                <div className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono border bg-slate-950 border-slate-800">
                  {runtimeErrors.length === 0 ? (
                    <span className="flex items-center gap-1 text-emerald-400">
                      <Check size={11} /> 0 Errors
                    </span>
                  ) : (
                    <span
                      className="flex items-center gap-1 text-rose-400 cursor-pointer"
                      title={runtimeErrors.join('\n')}
                    >
                      <AlertCircle size={11} /> {runtimeErrors.length} Error{runtimeErrors.length > 1 ? 's' : ''}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-1 bg-slate-950 px-2 py-1 rounded-lg border border-slate-800">
                  <button
                    onClick={() => setPreviewDevice('desktop')}
                    className={`p-1.5 rounded transition-all ${previewDevice === 'desktop' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                    title="Desktop View (100%)"
                  >
                    <Monitor size={14} />
                  </button>
                  <button
                    onClick={() => setPreviewDevice('tablet')}
                    className={`p-1.5 rounded transition-all ${previewDevice === 'tablet' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                    title="Tablet View (768px)"
                  >
                    <Tablet size={14} />
                  </button>
                  <button
                    onClick={() => setPreviewDevice('mobile')}
                    className={`p-1.5 rounded transition-all ${previewDevice === 'mobile' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                    title="Mobile View (375px)"
                  >
                    <Smartphone size={14} />
                  </button>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setRuntimeErrors([])
                    setIframeKey(k => k + 1)
                  }}
                  className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition-colors flex items-center gap-1 text-xs"
                  title="Restart Game / Reload Preview"
                >
                  <RotateCw size={14} />
                  <span className="hidden sm:inline">Restart</span>
                </button>

                <button
                  onClick={() => setIsFullscreen(f => !f)}
                  className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition-colors"
                  title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
                >
                  {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                </button>

                <button
                  onClick={handleDownload}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
                  title="Download Project ZIP"
                >
                  <Download size={12} />
                  <span>Download ZIP</span>
                </button>

                <button
                  onClick={() => {
                    setIsFullscreen(false)
                    setPreviewOpen(false)
                  }}
                  className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition-colors ml-1"
                  title="Close Preview"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Sandbox Iframe Container */}
            <div className="flex-1 bg-slate-900/50 flex items-center justify-center p-2 overflow-auto">
              <div
                className="h-full bg-white transition-all duration-300 rounded-lg shadow-xl overflow-hidden flex flex-col"
                style={{
                  width:
                    previewDevice === 'desktop'
                      ? '100%'
                      : previewDevice === 'tablet'
                      ? '768px'
                      : '375px',
                  maxWidth: '100%',
                }}
              >
                <iframe
                  key={iframeKey}
                  title="Site Preview"
                  srcDoc={combinedHtml}
                  className="w-full h-full border-0 flex-1 bg-white"
                  sandbox="allow-scripts allow-modals allow-forms allow-same-origin"
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
