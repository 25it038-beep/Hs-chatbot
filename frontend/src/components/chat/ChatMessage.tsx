import React from 'react'
import { cn } from '@/lib/utils'
import { MarkdownRenderer } from './MarkdownRenderer'
import { Bot, User, Copy, Check, ThumbsUp, ThumbsDown } from 'lucide-react'
import type { Message } from '@/types'
import { MessageEntrance } from '@/components/animations/ChatAnimations'

interface ChatMessageProps {
  message: Message
  isStreaming?: boolean
  index?: number
}

export function ChatMessage({ message, isStreaming, index = 0 }: ChatMessageProps) {
  const [copied, setCopied] = React.useState(false)
  const isUser = message.role === 'user'

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <MessageEntrance index={index}>
      <div className={cn('flex gap-2.5 sm:gap-3 md:gap-4 py-3 sm:py-4 md:py-6 group min-w-0', isUser ? 'flex-row-reverse' : '')}>
        <div className={cn(
          'flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 rounded-xl flex items-center justify-center shadow-sm relative overflow-hidden glass-reflection',
          isUser
            ? 'bg-gradient-to-br from-primary to-primary/80 text-primary-foreground'
            : 'bg-gradient-to-br from-primary/10 to-primary/5 text-primary border border-primary/10'
        )}>
          {isUser ? <User size={14} /> : <Bot size={14} />}
        </div>

        <div className={cn('flex flex-col min-w-0 max-w-[92%] sm:max-w-[85%] md:max-w-[75%]', isUser ? 'items-end' : 'items-start')}>
          <div className={cn(
            'rounded-2xl px-3.5 sm:px-4 py-2.5 sm:py-3 transition-all duration-200 min-w-0 overflow-hidden',
            isUser
              ? 'bg-gradient-to-br from-primary to-primary/90 text-primary-foreground shadow-sm'
              : 'bg-muted/30 backdrop-blur-sm border border-border/30 hover:border-border/50 shadow-soft'
          )}>
            {isUser ? (
              <p className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap break-words">{message.content}</p>
            ) : message.content.startsWith('<img ') ? (
              <div className="min-w-0">
                <img
                  src={message.content.match(/src="([^"]+)"/)?.[1] || ''}
                  alt="Generated image"
                  className="max-w-full rounded-xl my-1 shadow-elevated hover:shadow-glass-xl transition-shadow duration-300"
                  style={{ maxHeight: '512px' }}
                  loading="lazy"
                />
              </div>
            ) : (
              <div className="min-w-0">
                <MarkdownRenderer content={message.content} />
                {isStreaming && (
                  <span className="inline-flex gap-1 ml-0.5">
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                  </span>
                )}
              </div>
            )}
          </div>

          {!isUser && !isStreaming && message.content && (
            <div className="flex items-center gap-0.5 mt-1 px-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-all duration-200">
              <button
                onClick={handleCopy}
                className="p-1.5 rounded-lg text-muted-foreground/60 sm:text-muted-foreground/50 hover:text-foreground hover:bg-muted/60 transition-all"
                title="Copy response"
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
              </button>
              <button
                className="p-1.5 rounded-lg text-muted-foreground/60 sm:text-muted-foreground/50 hover:text-foreground hover:bg-muted/60 transition-all"
                title="Good response"
              >
                <ThumbsUp size={12} />
              </button>
              <button
                className="p-1.5 rounded-lg text-muted-foreground/60 sm:text-muted-foreground/50 hover:text-foreground hover:bg-muted/60 transition-all"
                title="Bad response"
              >
                <ThumbsDown size={12} />
              </button>
              {message.latency_ms && (
                <span className="ml-2 text-[10px] text-muted-foreground/40 font-mono">
                  {(message.latency_ms / 1000).toFixed(1)}s
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </MessageEntrance>
  )
}
