import React, { useRef, useEffect } from 'react'
import { useChat } from '@/stores/chat'
import { useAuth } from '@/stores/auth'
import { ChatMessage } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  MessageSquare, ArrowDown, Code, Brain, FileText,
  Globe, Paperclip, Slash, Wand2,
} from 'lucide-react'
import { api } from '@/lib/api'
import type { FileInfo, Message } from '@/types'
import { isImageRequest } from '@/stores/chat'
import { AIThinking } from '@/components/animations/LoadingAnimation'

const SUGGESTIONS = [
  {
    icon: Code,
    label: 'Write code',
    prompt: 'Write a Python function to sort a list of dictionaries by a key',
  },
  {
    icon: MessageSquare,
    label: 'Explain code',
    prompt: 'Explain how React hooks work with examples',
  },
  {
    icon: Brain,
    label: 'Research',
    prompt: 'Research and summarize the key differences between REST and GraphQL',
  },
  {
    icon: FileText,
    label: 'Analyze',
    prompt: 'How do I analyze a CSV file with pandas?',
  },
]

const CAPABILITIES = [
  { icon: Globe, label: 'Live web search' },
  { icon: Wand2, label: 'Image generation' },
  { icon: Paperclip, label: 'Document analysis' },
  { icon: Slash, label: 'Slash commands' },
]

const PHASE_ICONS: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  searching: Globe,
  writing: FileText,
  thinking: Brain,
  browser_action: Globe,
}

const PHASE_LABELS: Record<string, string> = {
  searching: 'Searching the web...',
  writing: 'Writing...',
  thinking: 'Thinking...',
  browser_action: 'Controlling the browser...',
}

function StreamingIndicator({ phase, onStop }: { phase?: string; onStop?: () => void }) {
  const Icon = phase ? PHASE_ICONS[phase] || Brain : Brain
  return (
    <div className="flex items-center gap-2.5 py-3 px-1 animate-fade-in" role="status" aria-live="polite">
      <AIThinking onStop={onStop} />
      <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
        {phase === 'searching' && <Icon size={13} className="text-brand animate-pulse" />}
        {PHASE_LABELS[phase || 'thinking'] || 'Thinking...'}
      </span>
    </div>
  )
}

export function ChatContainer() {
  const { messages, currentChat, streaming, streamingContent, streamingPhase, sendMessage, addAssistantMessage, cancelStream, createChat, generatingImage, unsendMessages, editAndResend } = useChat()
  const { user } = useAuth()
  const scrollRef = useRef<HTMLDivElement>(null)
  const [showScrollBtn, setShowScrollBtn] = React.useState(false)
  const [isAtBottom, setIsAtBottom] = React.useState(true)
  const [editingMessage, setEditingMessage] = React.useState<Message | null>(null)

  useEffect(() => {
    setEditingMessage(null)
  }, [currentChat?.id])

  const scrollToBottom = (smooth = true) => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto',
      })
    }
  }

  useEffect(() => {
    if (isAtBottom) scrollToBottom()
  }, [messages, streamingContent, isAtBottom])

  const handleScroll = () => {
    if (!scrollRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current
    const atBottom = scrollHeight - scrollTop - clientHeight < 80
    setIsAtBottom(atBottom)
    setShowScrollBtn(!atBottom)
  }

  const currentPhase = currentChat ? streamingPhase[currentChat.id] : undefined
  const handleSend = async (content: string) => {
    if (!currentChat) {
      await createChat()
    }
    await sendMessage(content)
  }

  const handleEdit = (msg: Message) => {
    setEditingMessage(msg)
  }

  const handleUnsend = (msg: Message) => {
    if (editingMessage?.id === msg.id) setEditingMessage(null)
    unsendMessages(msg.id)
  }

  const handleEditSubmit = async (messageId: string, content: string) => {
    setEditingMessage(null)
    await editAndResend(messageId, content)
  }

  const handleCancelEdit = () => {
    setEditingMessage(null)
  }

  const handleSendWithFile = async (file: File, prompt: string) => {
    if (!currentChat) {
      await createChat()
    }
    let filename = file.name
    try {
      const uploadRes = await api.uploadFile(file) as FileInfo
      filename = uploadRes.filename || file.name
    } catch {
      // upload failed — fall back to raw filename; chat will report if file is missing
    }

    if (file.type.startsWith('image/')) {
      await sendMessage(`[Image: ${filename}]${prompt ? ` ${prompt}` : ''}`)
      return
    }

    if (!prompt) {
      await addAssistantMessage(
        `I've received **${filename}**. To analyze it, tell me what you'd like to know — e.g. "Summarize this PDF", "Extract the key points", or "What is this about?"`,
      )
      return
    }

    await sendMessage(`[File: ${filename}] ${prompt}`)
  }

  if (messages.length === 0) {
    return (
      <div className="flex flex-col flex-1 min-h-0">
        <div className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 py-8 overflow-y-auto">
          <div className="w-full max-w-xl mx-auto animate-fade-in-up text-center my-auto">
            <div className="w-12 h-12 rounded-xl overflow-hidden border border-border shadow-soft mx-auto mb-5">
              <img src="/logo.jpg" alt="HSBot" className="w-full h-full object-cover" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-balance mb-2">
              {user?.display_name || user?.username
                ? `Hello, ${user.display_name || user.username}! How can I help you today?`
                : 'What can I help you with?'}
            </h1>
            <p className="text-sm text-muted-foreground mb-7 text-pretty">
              Ask questions, write code, research topics, or analyze documents.
            </p>

            <ChatInput
              onSend={handleSend}
              onSendWithFile={handleSendWithFile}
              onStop={cancelStream}
              streaming={streaming}
              variant="hero"
              editing={editingMessage ? { id: editingMessage.id, content: editingMessage.content } : null}
              onEditSubmit={handleEditSubmit}
              onCancelEdit={handleCancelEdit}
            />

            <div className="flex items-center justify-center gap-2 flex-wrap mt-4">
              {SUGGESTIONS.map((item) => {
                const Icon = item.icon
                return (
                  <button
                    key={item.label}
                    onClick={() => handleSend(item.prompt)}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full border border-border bg-card text-xs text-muted-foreground hover:text-foreground hover:border-foreground/30 hover:bg-muted transition-all duration-150 active:scale-[0.98]"
                  >
                    <Icon size={12} />
                    {item.label}
                  </button>
                )
              })}
            </div>

            <div className="flex items-center justify-center gap-2 flex-wrap mt-6">
              {CAPABILITIES.map((cap) => {
                const Icon = cap.icon
                return (
                  <span
                    key={cap.label}
                    className="flex items-center gap-1.5 text-[11px] text-muted-foreground/60"
                  >
                    <Icon size={11} />
                    {cap.label}
                  </span>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    )
  }

  let allowImages = false
  for (let k = messages.length - 1; k >= 0; k--) {
    if (messages[k].role === 'user') {
      allowImages = isImageRequest(messages[k].content)
      break
    }
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 relative">
      <ScrollArea ref={scrollRef} className="flex-1 min-h-0 px-3 md:px-6" onScroll={handleScroll}>
        <div className="max-w-3xl mx-auto py-4 pb-36">
          {messages.map((msg, i) => {
            let allowImages = false
            for (let k = i - 1; k >= 0; k--) {
              if (messages[k].role === 'user') {
                allowImages = isImageRequest(messages[k].content)
                break
              }
            }
            return (
              <ChatMessage
                key={msg.id}
                message={msg}
                index={i}
                onEdit={handleEdit}
                onUnsend={handleUnsend}
                showImages={allowImages}
              />
            )
          })}
          {streaming && streamingContent && (
            <ChatMessage
              message={{
                id: 'streaming',
                chat_id: currentChat?.id || '',
                role: 'assistant',
                content: streamingContent,
                token_count: 0,
                input_tokens: 0,
                output_tokens: 0,
                created_at: new Date().toISOString(),
              }}
              isStreaming
              showImages={allowImages}
            />
          )}
          {streaming && !streamingContent && !generatingImage && (
            <div className="px-1">
              <StreamingIndicator phase={currentPhase} onStop={() => cancelStream()} />
            </div>
          )}
          {generatingImage && (
            <div className="flex items-center gap-2.5 py-4 px-1 animate-fade-in" role="status" aria-live="polite">
              <div className="relative w-4 h-4">
                <div className="absolute inset-0 rounded-full border-2 border-border border-t-foreground animate-spin" />
              </div>
              <span className="text-sm text-muted-foreground">Generating image...</span>
            </div>
          )}
          <div className="h-2" />
        </div>
      </ScrollArea>

      {showScrollBtn && (
        <button
          onClick={() => scrollToBottom(true)}
          className="absolute bottom-32 left-1/2 -translate-x-1/2 z-10 h-9 w-9 rounded-full bg-card border border-border shadow-elevated flex items-center justify-center hover:bg-muted transition-all animate-fade-in"
          title="Scroll to bottom"
          aria-label="Scroll to bottom"
        >
          <ArrowDown size={14} />
        </button>
      )}

      <ChatInput
        onSend={handleSend}
        onSendWithFile={handleSendWithFile}
        onStop={cancelStream}
        streaming={streaming}
        editing={editingMessage ? { id: editingMessage.id, content: editingMessage.content } : null}
        onEditSubmit={handleEditSubmit}
        onCancelEdit={handleCancelEdit}
      />
    </div>
  )
}