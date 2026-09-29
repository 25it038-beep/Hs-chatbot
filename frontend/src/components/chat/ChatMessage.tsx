import React from 'react'
import { cn } from '@/lib/utils'
import { MarkdownRenderer } from './MarkdownRenderer'
import { Copy, Check, Download, Pencil, Undo2, Volume2, VolumeX, Loader2, ChevronDown } from 'lucide-react'
import type { Message, Attachment } from '@/types'
import { MessageEntrance } from '@/components/animations/ChatAnimations'
import { FileAttachmentCard } from './FileAttachmentCard'
import { useVoiceStore } from '@/lib/speech'
import { extractWebProject } from '@/lib/webProject'
import { WebProjectCard } from './WebProjectCard'
import { WebSearchResults } from './WebSearchResults'
import { ClarificationQuizComponent } from './ClarificationQuiz'
import { SatisfactionCheckComponent } from './SatisfactionCheck'
import { YouTubeSearchResults } from './YouTubeSearchResults'
import {
  downloadAiResponsesAsFile,
  EXPORT_FILE_FORMATS,
  getActiveChatAiResponses,
} from '@/lib/documentGenerator'
import { useChatStore } from '@/stores/chat'


interface ChatMessageProps {
  message: Message
  isStreaming?: boolean
  index?: number
  onEdit?: (message: Message) => void
  onUnsend?: (message: Message) => void
  showImages?: boolean
}

function GeneratedImage({ content }: { content: string }) {
  const src = content.match(/src="([^"]+)"/)?.[1] || ''
  if (!src) return null
  const handleDownload = () => {
    const a = document.createElement('a')
    a.href = src
    a.download = 'hsbot-generated-image.png'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
  return (
    <div className="relative group/img rounded-xl overflow-hidden border border-border shadow-elevated bg-background my-1">
      <img
        src={src}
        alt="Generated image"
        className="max-w-full"
        style={{ maxHeight: '512px' }}
        loading="lazy"
      />
      <button
        onClick={handleDownload}
        title="Download image"
        aria-label="Download generated image"
        className="absolute bottom-2 right-2 p-2 rounded-lg bg-background/90 border border-border shadow-soft text-muted-foreground hover:text-foreground opacity-100 sm:opacity-0 sm:group-hover/img:opacity-100 transition-all"
      >
        <Download size={13} />
      </button>
    </div>
  )
}

export function ChatMessage({ message, isStreaming, index = 0, onEdit, onUnsend, showImages = true }: ChatMessageProps) {
  const [copied, setCopied] = React.useState(false)
  const [downloadMenuOpen, setDownloadMenuOpen] = React.useState(false)
  const [downloadingFormat, setDownloadingFormat] = React.useState<string | null>(null)
  const [exportScope, setExportScope] = React.useState<'single' | 'all'>('all')
  const [customFormat, setCustomFormat] = React.useState('')

  const isUser = message.role === 'user'
  const isGeneratedImage = !isUser && message.content.startsWith('<img ')
  const { isSpeaking, speakingMessageId, speakText, stopSpeaking, synthesisSupported } = useVoiceStore()
  const isThisSpeaking = isSpeaking && speakingMessageId === message.id

  const webProject = React.useMemo(() => {
    if (isUser || isStreaming || !message.content) return null
    return extractWebProject(message.content)
  }, [isUser, isStreaming, message.content])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSpeakToggle = () => {
    if (isThisSpeaking) {
      stopSpeaking()
    } else {
      speakText(message.content, message.id)
    }
  }

  const handleDownloadAsFormat = async (fmt: string) => {
    const cleanFmt = fmt.trim().toLowerCase().replace(/^\.+/, '')
    if (!cleanFmt || downloadingFormat) return
    setDownloadingFormat(cleanFmt)
    try {
      const currentChat = useChatStore.getState().currentChat
      const allChatResponses = getActiveChatAiResponses()
      const responsesToExport =
        exportScope === 'all' && allChatResponses.length > 0
          ? allChatResponses
          : [message.content]

      await downloadAiResponsesAsFile({
        responses: responsesToExport,
        format: cleanFmt,
        title: currentChat?.title || undefined,
        chatId: currentChat?.id,
      })
      setDownloadMenuOpen(false)
    } catch (err) {
      console.error('Failed to download AI responses:', err)
    } finally {
      setDownloadingFormat(null)
    }
  }

  return (
    <MessageEntrance index={index}>
      <div className={cn('group py-4 sm:py-5 min-w-0', isUser ? 'flex justify-end' : '')}>
        {isUser ? (
          <div className="max-w-[85%] sm:max-w-[75%] flex flex-col items-end">
            {(() => {
              const userAtts: Attachment[] =
                message.attachments ||
                (message.metadata?.attachments as Attachment[]) ||
                ((message as any).extra_data?.attachments as Attachment[]) ||
                []
              if (!userAtts || userAtts.length === 0) return null
              return (
                <div className="flex flex-wrap justify-end gap-2 mb-1.5 w-full">
                  {userAtts.map((att) => (
                    <FileAttachmentCard key={att.id || att.fileId || att.name} attachment={att} />
                  ))}
                </div>
              )
            })()}
            {message.content && (
              <div className="inline-block rounded-xl bg-accent px-3.5 py-2.5 text-[13px] sm:text-sm leading-relaxed whitespace-pre-wrap break-words text-foreground">
                {message.content}
              </div>
            )}
            {onEdit && onUnsend && (
              <div className="flex items-center gap-0.5 mt-1.5 justify-end opacity-100 sm:opacity-0 sm:group-hover:opacity-100 focus-within:opacity-100 transition-all duration-200">
                <button
                  onClick={() => onEdit(message)}
                  className="p-1.5 rounded-md text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-all"
                  title="Edit message"
                  aria-label="Edit message"
                >
                  <Pencil size={12} />
                </button>
                <button
                  onClick={() => onUnsend(message)}
                  className="p-1.5 rounded-md text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-all"
                  title="Unsend message"
                  aria-label="Unsend message"
                >
                  <Undo2 size={12} />
                </button>
              </div>
            )}
          </div>
        ) : isGeneratedImage ? (
          <GeneratedImage content={message.content} />
        ) : (
          <div className="min-w-0">
            {(() => {
              const sources = message.sources || ((message as any).extra_data?.sources as any[])
              if (!sources || sources.length === 0) return null
              return <WebSearchResults sources={sources} />
            })()}
            <MarkdownRenderer content={message.content} allowImages={showImages} />
            {(() => {
              const ytResults =
                message.youtube_results ||
                ((message as any).extra_data?.youtube_results as any)
              if (!ytResults) return null
              return <YouTubeSearchResults results={ytResults} />
            })()}
            {webProject && (
              <WebProjectCard project={webProject} messageId={message.id} />
            )}
            {(() => {
              const atts: Attachment[] =
                message.attachments ||
                (message.metadata?.attachments as Attachment[]) ||
                ((message as any).extra_data?.attachments as Attachment[]) ||
                []
              if (!atts || atts.length === 0) return null
              return (
                <div className="flex flex-col gap-2 my-2">
                  {atts.map(att => (
                    <FileAttachmentCard key={att.id || att.name} attachment={att} />
                  ))}
                </div>
              )
            })()}

            {(() => {
              const quiz = message.quiz || ((message as any).extra_data?.quiz as any)
              if (!quiz) return null
              return <ClarificationQuizComponent quiz={quiz} messageId={message.id} />
            })()}

            {(() => {
              if (isStreaming) return null
              const isSatisfaction = message.satisfaction_check || (message as any).extra_data?.satisfaction_check
              const verification = message.verification || (message as any).extra_data?.verification
              if (!isSatisfaction && !verification?.satisfaction_check) return null
              return <SatisfactionCheckComponent verification={verification} messageId={message.id} />
            })()}

            {isStreaming && (
              <span className="inline-flex gap-1 ml-0.5 align-baseline" aria-label="AI is typing">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </span>
            )}

            {!isStreaming && message.content && (
              <div className="relative flex items-center gap-0.5 mt-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 focus-within:opacity-100 transition-all duration-200">
                <button
                  onClick={handleCopy}
                  className="p-1.5 rounded-md text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-all"
                  title={copied ? 'Copied' : 'Copy response'}
                  aria-label="Copy response"
                >
                  {copied ? <Check size={12} className="text-brand" /> : <Copy size={12} />}
                </button>

                {/* Download AI Response(s) as any file format */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setDownloadMenuOpen(v => !v)}
                    className={cn(
                      'px-2 py-1 rounded-md text-xs transition-all flex items-center gap-1',
                      downloadMenuOpen
                        ? 'text-primary bg-primary/10'
                        : 'text-muted-foreground/60 hover:text-foreground hover:bg-muted'
                    )}
                    title="Download AI responses as any file format"
                    aria-label="Download AI responses as any file format"
                  >
                    {downloadingFormat ? (
                      <Loader2 size={12} className="animate-spin text-primary" />
                    ) : (
                      <Download size={12} />
                    )}
                    <span className="text-[11px] font-medium">Download</span>
                    <ChevronDown size={10} />
                  </button>

                  {downloadMenuOpen && (
                    <div className="absolute left-0 bottom-full mb-1.5 z-50 w-72 rounded-xl border border-border bg-popover text-popover-foreground shadow-xl p-2.5 space-y-2">
                      <div className="flex items-center justify-between gap-1 pb-1.5 border-b border-border">
                        <span className="text-[11px] font-semibold text-foreground">
                          Download AI Responses
                        </span>
                        <div className="flex items-center rounded-md bg-muted p-0.5 text-[10px]">
                          <button
                            type="button"
                            onClick={() => setExportScope('all')}
                            className={cn(
                              'px-1.5 py-0.5 rounded font-medium transition-colors',
                              exportScope === 'all'
                                ? 'bg-background text-foreground shadow-xs'
                                : 'text-muted-foreground hover:text-foreground'
                            )}
                          >
                            All in Chat
                          </button>
                          <button
                            type="button"
                            onClick={() => setExportScope('single')}
                            className={cn(
                              'px-1.5 py-0.5 rounded font-medium transition-colors',
                              exportScope === 'single'
                                ? 'bg-background text-foreground shadow-xs'
                                : 'text-muted-foreground hover:text-foreground'
                            )}
                          >
                            This Reply
                          </button>
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-1 max-h-44 overflow-y-auto pr-0.5">
                        {EXPORT_FILE_FORMATS.map(f => (
                          <button
                            key={f.ext}
                            type="button"
                            disabled={!!downloadingFormat}
                            onClick={() => handleDownloadAsFormat(f.ext)}
                            className="px-2 py-1 rounded-md text-[11px] font-medium text-left hover:bg-muted border border-transparent hover:border-border transition-colors flex items-center justify-between"
                            title={f.description}
                          >
                            <span>.{f.ext.toUpperCase()}</span>
                            {downloadingFormat === f.ext && (
                              <Loader2 size={10} className="animate-spin text-primary" />
                            )}
                          </button>
                        ))}
                      </div>

                      <form
                        onSubmit={e => {
                          e.preventDefault()
                          if (customFormat.trim()) {
                            handleDownloadAsFormat(customFormat.trim())
                            setCustomFormat('')
                          }
                        }}
                        className="flex items-center gap-1 pt-1.5 border-t border-border"
                      >
                        <input
                          type="text"
                          value={customFormat}
                          onChange={e => setCustomFormat(e.target.value)}
                          placeholder="Any format (e.g. docx, log, ini, yaml)"
                          className="flex-1 min-w-0 px-2 py-1 text-[11px] rounded bg-muted/60 border border-border text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        />
                        <button
                          type="submit"
                          disabled={!customFormat.trim() || !!downloadingFormat}
                          className="px-2.5 py-1 rounded bg-primary text-primary-foreground text-[11px] font-medium hover:opacity-90 disabled:opacity-50"
                        >
                          Save
                        </button>
                      </form>
                    </div>
                  )}
                </div>

                {synthesisSupported && (
                  <button
                    onClick={handleSpeakToggle}
                    className={cn(
                      'p-1.5 rounded-md transition-all flex items-center gap-1',
                      isThisSpeaking
                        ? 'text-primary bg-primary/10 hover:bg-primary/20'
                        : 'text-muted-foreground/50 hover:text-foreground hover:bg-muted'
                    )}
                    title={isThisSpeaking ? 'Stop speaking' : 'Read aloud'}
                    aria-label={isThisSpeaking ? 'Stop speaking' : 'Read aloud'}
                  >
                    {isThisSpeaking ? (
                      <>
                        <VolumeX size={12} className="text-primary animate-pulse" />
                        <span className="text-[10px] font-medium text-primary hidden xs:inline">Stop</span>
                      </>
                    ) : (
                      <Volume2 size={12} />
                    )}
                  </button>
                )}
                {message.latency_ms ? (
                  <span className="ml-1 text-[10px] text-muted-foreground/40 font-mono" title="Response time">
                    {(message.latency_ms / 1000).toFixed(1)}s
                  </span>
                ) : null}
              </div>
            )}
          </div>
        )}
      </div>
    </MessageEntrance>
  )
}