import React, { useRef, useEffect } from 'react'
import { useChat } from '@/stores/chat'
import { useAuth } from '@/stores/auth'
import { ChatMessage } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Bot, Sparkles, MessageSquare, ArrowDown, Code, Brain, FileText } from 'lucide-react'
import { api } from '@/lib/api'
import type { FileInfo } from '@/types'
import { AIThinking } from '@/components/animations/LoadingAnimation'

export function ChatContainer() {
  const { messages, currentChat, streaming, streamingContent, sendMessage, cancelStream, createChat, generatingImage } = useChat()
  const { user } = useAuth()
  const scrollRef = useRef<HTMLDivElement>(null)
  const [showScrollBtn, setShowScrollBtn] = React.useState(false)
  const [isAtBottom, setIsAtBottom] = React.useState(true)

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

  const handleSend = async (content: string) => {
    if (!currentChat) {
      await createChat()
    }
    await sendMessage(content)
  }

  const handleUploadFile = async (file: File) => {
    if (!currentChat) {
      await createChat()
    }
    let filename = file.name
    let analysis: string | undefined
    try {
      const uploadRes = await api.uploadFile(file) as FileInfo
      filename = uploadRes.filename || file.name
      analysis = uploadRes.analysis
    } catch {
    }
    if (file.type.startsWith('image/')) {
      try {
        const visionRes: any = await api.nvidiaVision(file, 'Describe this image in detail.')
        const description = visionRes.content || visionRes.text || ''
        await sendMessage(`[Image: ${filename}] ${description}`.trim())
      } catch {
        await sendMessage(`[Image: ${filename}]`)
      }
    } else {
      if (analysis) {
        await sendMessage(`[File: ${filename}]\n\n**Analysis Report:**\n${analysis}\n\nI've analyzed the file above. What would you like to know about it?`)
      } else {
        await sendMessage(`[File: ${filename}]`)
      }
    }
  }

  if (messages.length === 0) {
    return (
      <div className="flex flex-col flex-1 min-h-0">
        <div className="flex-1 flex items-center justify-center px-4">
          <div className="text-center max-w-lg mx-auto animate-fade-in-up">
            <div className="w-16 h-16 rounded-2xl overflow-hidden mx-auto mb-6 shadow-sm border border-primary/10">
              <img src="/logo.jpg" alt="HSBot" className="w-full h-full object-cover" />
            </div>
            <h1 className="text-2xl font-semibold tracking-tight mb-2">How can I help you?</h1>
            <p className="text-sm text-muted-foreground/70 mb-8 max-w-sm mx-auto">
              I'm your AI assistant. Ask me anything — I can help with coding, analysis, research, and more.
            </p>
            <div className="grid grid-cols-2 gap-3 max-w-md mx-auto">
              {[
                { icon: Code, label: 'Write code', prompt: 'Write a Python function to sort a list of dictionaries by a key', color: 'from-blue-500/10 to-blue-500/5 border-blue-500/20 hover:border-blue-500/40' },
                { icon: MessageSquare, label: 'Explain code', prompt: 'Explain how React hooks work with examples', color: 'from-emerald-500/10 to-emerald-500/5 border-emerald-500/20 hover:border-emerald-500/40' },
                { icon: Brain, label: 'Research', prompt: 'Research and summarize the key differences between REST and GraphQL', color: 'from-purple-500/10 to-purple-500/5 border-purple-500/20 hover:border-purple-500/40' },
                { icon: FileText, label: 'Analyze', prompt: 'How do I analyze a CSV file with pandas?', color: 'from-amber-500/10 to-amber-500/5 border-amber-500/20 hover:border-amber-500/40' },
              ].map((item) => {
                const Icon = item.icon
                return (
                  <button
                    key={item.label}
                    onClick={() => handleSend(item.prompt)}
                    className={`text-left p-3.5 rounded-xl border bg-gradient-to-br ${item.color} transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 active:translate-y-0`}
                  >
                    <div className="flex items-center gap-2 mb-1.5">
                      <Icon size={14} className="text-primary" />
                      <span className="font-medium text-sm">{item.label}</span>
                    </div>
                    <p className="text-xs text-muted-foreground/60 line-clamp-1">{item.prompt}</p>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
        <ChatInput onSend={handleSend} onStop={cancelStream} onUploadFile={handleUploadFile} streaming={streaming} />
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 relative">
      <ScrollArea ref={scrollRef} className="flex-1 min-h-0 px-3 md:px-4" onScroll={handleScroll}>
        <div className="max-w-4xl mx-auto py-2 pb-32">
          {messages.map((msg, i) => (
            <ChatMessage key={msg.id} message={msg} index={i} />
          ))}
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
            />
          )}
          {streaming && !streamingContent && !generatingImage && (
            <div className="flex items-center gap-3 py-4 px-4">
              <AIThinking />
            </div>
          )}
          {generatingImage && (
            <div className="flex items-center gap-3 py-4 px-4 animate-fade-in">
              <div className="relative w-5 h-5">
                <div className="absolute inset-0 rounded-full border-2 border-purple-500/20 border-t-purple-500 animate-spin" />
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
          className="absolute bottom-28 left-1/2 -translate-x-1/2 z-10 h-8 w-8 rounded-full glass-panel shadow-md flex items-center justify-center hover:bg-muted/80 transition-all animate-fade-in"
          title="Scroll to bottom"
        >
          <ArrowDown size={14} />
        </button>
      )}

      <ChatInput onSend={handleSend} onStop={cancelStream} onUploadFile={handleUploadFile} streaming={streaming} />
    </div>
  )
}
