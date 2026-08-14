import React from 'react'
import { cn } from '@/lib/utils'
import { MarkdownRenderer } from './MarkdownRenderer'
import { Copy, Check, Download, Pencil, Undo2 } from 'lucide-react'
import type { Message } from '@/types'
import { MessageEntrance } from '@/components/animations/ChatAnimations'

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
  const isUser = message.role === 'user'
  const isGeneratedImage = !isUser && message.content.startsWith('<img ')

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <MessageEntrance index={index}>
      <div className={cn('group py-4 sm:py-5 min-w-0', isUser ? 'flex justify-end' : '')}>
        {isUser ? (
          <div className="max-w-[85%] sm:max-w-[75%]">
            <div className="inline-block rounded-xl bg-accent px-3.5 py-2.5 text-[13px] sm:text-sm leading-relaxed whitespace-pre-wrap break-words text-foreground">
              {message.content}
            </div>
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
            <MarkdownRenderer content={message.content} allowImages={showImages} />
            {isStreaming && (
              <span className="inline-flex gap-1 ml-0.5 align-baseline" aria-label="AI is typing">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </span>
            )}
            {!isStreaming && message.content && (
              <div className="flex items-center gap-0.5 mt-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 focus-within:opacity-100 transition-all duration-200">
                <button
                  onClick={handleCopy}
                  className="p-1.5 rounded-md text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-all"
                  title={copied ? 'Copied' : 'Copy response'}
                  aria-label="Copy response"
                >
                  {copied ? <Check size={12} className="text-brand" /> : <Copy size={12} />}
                </button>
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