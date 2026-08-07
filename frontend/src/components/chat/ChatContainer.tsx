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
  const { messages, currentChat, streaming, streamingContent, streamingPhase, sendMessage, addAssistantMessage, cancelStream, createChat, generatingImage } = useChat()
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

  const currentPhase = currentChat ? streamingPhase[currentChat.id] : undefined
  const handleSend = async (content: string) => {
    if (!currentChat) {
      await createChat()
    }
    await sendMessage(content)
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
        <div className="flex-1 flex items-center justify-center px-3 sm:px-4 py-4 overflow-y-auto">
          <div className="text-center max-w-lg mx-auto animate-fade-in-up my-auto">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl overflow-hidden mx-auto mb-4 sm:mb-6 shadow-sm border border-primary/10">
              <img src="/logo.jpg" alt="HSBot" className="w-full h-full object-cover" />
            </div>
            <h1 className="text-xl sm:text-2xl font-semibold tracking-tight mb-2">How can I help you?</h1>
            <p className="text-xs sm:text-sm text-muted-foreground/70 mb-2 max-w-xs sm:max-w-sm mx-auto">
              I'm your AI assistant. Ask me anything — I can help with coding, analysis, research, and more.
            </p>
            <p className="text-[11px] text-muted-foreground/50 mb-6 max-w-xs mx-auto">
              Note: the first response may be a little slower while the model warms up.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3 max-w-md mx-auto">
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
                    className={`text-left p-3 sm:p-3.5 rounded-xl border bg-gradient-to-br ${item.color} transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 active:translate-y-0`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Icon size={14} className="text-primary" />
                      <span className="font-medium text-xs sm:text-sm">{item.label}</span>
                    </div>
                    <p className="text-xs text-muted-foreground/60 line-clamp-1">{item.prompt}</p>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
        <ChatInput onSend={handleSend} onSendWithFile={handleSendWithFile} onStop={cancelStream} streaming={streaming} />
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
            <div className="flex items-center gap-3 py-4 px-4 animate-fade-in">
              <AIThinking />
              <span className="text-sm text-muted-foreground animate-pulse">
                {currentPhase === 'writing' ? 'Writing...' : 'Thinking...'}
              </span>
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

      <ChatInput onSend={handleSend} onSendWithFile={handleSendWithFile} onStop={cancelStream} streaming={streaming} />
    </div>
  )
}
