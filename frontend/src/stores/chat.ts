import { create } from 'zustand'
import type { Chat, ChatFolder, Message, ModelInfo } from '@/types'
import { api } from '@/lib/api'
import { playCompletionSound } from '@/lib/sound'

interface ChatState {
  chats: Chat[]
  currentChat: Chat | null
  messages: Message[]
  folders: ChatFolder[]
  models: ModelInfo[]
  streaming: boolean
  streamingContent: string
  generatingImage: boolean
  loading: boolean

  chatMessages: Record<string, Message[]>
  chatStreamingContent: Record<string, string>
  streamingChatIds: string[]
  streamingPhase: Record<string, 'thinking' | 'writing'>
  streamingReasoning: Record<string, string>

  loadChats: () => Promise<void>
  loadFolders: () => Promise<void>
  loadModels: () => Promise<void>
  selectChat: (id: string) => Promise<void>
  createChat: () => Promise<Chat>
  deleteChat: (id: string) => Promise<void>
  sendMessage: (content: string, chatId?: string) => Promise<void>
  addAssistantMessage: (content: string, chatId?: string) => Promise<void>
  updateLastAssistantMessage: (content: string, chatId?: string) => Promise<void>
  cancelStream: (chatId?: string) => void
}

export const useChat = create<ChatState>((set, get) => {
  const streamControllers: Record<string, AbortController> = {}

  const syncDisplay = () => {
    const { currentChat, chatMessages, chatStreamingContent, streamingChatIds, generatingImage } = get()
    if (!currentChat) {
      set({ messages: [], streaming: false, streamingContent: '', generatingImage: false })
      return
    }
    set({
      messages: chatMessages[currentChat.id] || [],
      streaming: streamingChatIds.includes(currentChat.id),
      streamingContent: chatStreamingContent[currentChat.id] || '',
      generatingImage: generatingImage,
    })
  }

  return {
    chats: [],
    currentChat: null,
    messages: [],
    folders: [],
    models: [],
    streaming: false,
    streamingContent: '',
    generatingImage: false,
    loading: false,

    chatMessages: {},
    chatStreamingContent: {},
    streamingChatIds: [],
    streamingPhase: {},
    streamingReasoning: {},

    loadChats: async () => {
      try {
        const chats = await api.listChats()
        set({ chats })
      } catch { /* ignore */ }
    },

    loadFolders: async () => {
      try {
        const folders = await api.listFolders()
        set({ folders })
      } catch { /* ignore */ }
    },

    loadModels: async () => {
      try {
        const models = await api.listModels()
        set({ models })
      } catch { /* ignore */ }
    },

    selectChat: async (id: string) => {
      const { chats, chatMessages } = get()
      const chat = chats.find(c => c.id === id) || await api.getChat(id)
      if (!chatMessages[id]) {
        const messages = await api.getMessages(id)
        set(state => ({ chatMessages: { ...state.chatMessages, [id]: messages } }))
      }
      set({ currentChat: chat })
      syncDisplay()
    },

    createChat: async () => {
      const chat = await api.createChat({ model: 'llama-3.1-70b', provider: 'nvidia' })
      set(state => ({
        chats: [chat, ...state.chats],
        currentChat: chat,
        chatMessages: { ...state.chatMessages, [chat.id]: [] },
      }))
      syncDisplay()
      return chat
    },

    deleteChat: async (id: string) => {
      streamControllers[id]?.abort()
      delete streamControllers[id]
      await api.deleteChat(id)
      set(state => {
        const { [id]: _, ...restMessages } = state.chatMessages
        const { [id]: __, ...restStreaming } = state.chatStreamingContent
        const { [id]: ___, ...restPhase } = state.streamingPhase
        const { [id]: ____, ...restReasoning } = state.streamingReasoning
        return {
          chats: state.chats.filter(c => c.id !== id),
          currentChat: state.currentChat?.id === id ? null : state.currentChat,
          chatMessages: restMessages,
          chatStreamingContent: restStreaming,
          streamingChatIds: state.streamingChatIds.filter(sid => sid !== id),
          streamingPhase: restPhase,
          streamingReasoning: restReasoning,
        }
      })
      syncDisplay()
    },

    sendMessage: async (content: string, chatId?: string) => {
      const { currentChat, chatMessages } = get()
      const chat = chatId ? get().chats.find(c => c.id === chatId) : currentChat

      if (!chat) {
        const newChat = await get().createChat()
        await get().sendMessage(content, newChat.id)
        return
      }

      const userMsg: Message = {
        id: crypto.randomUUID(),
        chat_id: chat.id,
        role: 'user',
        content,
        token_count: 0,
        input_tokens: 0,
        output_tokens: 0,
        created_at: new Date().toISOString(),
      }

      const updatedMessages = [...(chatMessages[chat.id] || []), userMsg]

      set(state => ({
        chatMessages: { ...state.chatMessages, [chat.id]: updatedMessages },
        streamingChatIds: [...state.streamingChatIds, chat.id],
        chatStreamingContent: { ...state.chatStreamingContent, [chat.id]: '' },
        streamingPhase: { ...state.streamingPhase, [chat.id]: 'thinking' },
        streamingReasoning: { ...state.streamingReasoning, [chat.id]: '' },
      }))
      if (get().currentChat?.id === chat.id) syncDisplay()

      try {
        const abortController = new AbortController()
        streamControllers[chat.id] = abortController

        const provider = chat.provider || 'nvidia'
        const model = chat.model || 'llama-3.1-70b'

        // Detect image generation requests to enable auto_route only for them
        const IMAGE_KEYWORDS = [
          '/image', '/img', '/draw',
          'generate an image', 'generate a picture', 'generate a photo',
          'create an image', 'create a picture', 'create a photo',
          'draw a', 'draw an', 'draw me',
          'render a', 'render an', 'render me',
          'make an image', 'make a picture', 'make a photo',
          'generate image', 'create image', 'generate art', 'create art',
          'illustrate a', 'illustrate an',
        ]
        const lower = content.toLowerCase()
        const isImageRequest = IMAGE_KEYWORDS.some(k => lower.includes(k))

        const reader = provider === 'nvidia'
          ? await api.nvidiaChatStream({
              message: content,
              chat_id: chat.id,
              model,
              stream: true,
              auto_route: isImageRequest,
            }, abortController.signal)
          : await api.sendMessageStream({
              message: content,
              chat_id: chat.id,
              model,
              provider,
            })

        const decoder = new TextDecoder()
        let fullContent = ''
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim()
              if (data === '[DONE]') continue
              try {
                const chunk = JSON.parse(data)
                if (chunk.type === 'reasoning' && chunk.content) {
                  const reasoning = (get().streamingReasoning[chat.id] || '') + chunk.content
                  set(state => ({
                    streamingReasoning: { ...state.streamingReasoning, [chat.id]: reasoning },
                    streamingPhase: { ...state.streamingPhase, [chat.id]: 'thinking' },
                  }))
                } else if (chunk.type === 'content' && chunk.content) {
                  fullContent += chunk.content
                  set(state => ({
                    chatStreamingContent: { ...state.chatStreamingContent, [chat.id]: fullContent },
                    streamingPhase: { ...state.streamingPhase, [chat.id]: 'writing' },
                  }))
                  if (get().currentChat?.id === chat.id) {
                    set({ streamingContent: fullContent })
                  }
                } else if (chunk.type === 'generating') {
                  fullContent = 'Generating image...'
                  set(state => ({
                    generatingImage: true,
                    chatStreamingContent: { ...state.chatStreamingContent, [chat.id]: fullContent },
                  }))
                  if (get().currentChat?.id === chat.id) {
                    set({ generatingImage: true, streamingContent: fullContent })
                  }
                } else if (chunk.type === 'image') {
                  fullContent = `<img src="data:image/png;base64,${chunk.content}" alt="Generated image" style="max-width:100%;border-radius:8px;" />`
                  set(state => ({
                    generatingImage: false,
                    chatStreamingContent: { ...state.chatStreamingContent, [chat.id]: fullContent },
                  }))
                  if (get().currentChat?.id === chat.id) {
                    set({ generatingImage: false, streamingContent: fullContent })
                  }
                } else if (chunk.type === 'meta') {
                  if (chunk.chat_id && chunk.chat_id !== chat.id) {
                    set(state => ({
                      currentChat: state.currentChat ? { ...state.currentChat, id: chunk.chat_id } : null,
                    }))
                  }
                } else if (chunk.type === 'error') {
                  console.error('Stream error:', chunk.content)
                }
              } catch { /* ignore */ }
            }
          }
        }

        const IMAGE_NOTE = '\n\n**Note:** You can only generate images in this chat from here on. For other requests, please start a new chat.'
        if (fullContent.includes('data:image/png;base64') && !fullContent.includes(IMAGE_NOTE.trim())) {
          fullContent += IMAGE_NOTE
          set(state => ({
            chatStreamingContent: { ...state.chatStreamingContent, [chat.id]: fullContent },
          }))
          if (get().currentChat?.id === chat.id) {
            set({ streamingContent: fullContent })
          }
        }

        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          chat_id: chat.id,
          role: 'assistant',
          content: fullContent,
          token_count: 0,
          input_tokens: 0,
          output_tokens: 0,
          created_at: new Date().toISOString(),
        }

        const finalMessages = [...(get().chatMessages[chat.id] || []), assistantMsg]
        set(state => {
          const { [chat.id]: _, ...rest } = state.chatStreamingContent
          const { [chat.id]: __, ...restPhase } = state.streamingPhase
          const { [chat.id]: ___, ...restReasoning } = state.streamingReasoning
          return {
            chatMessages: { ...state.chatMessages, [chat.id]: finalMessages },
            streamingChatIds: state.streamingChatIds.filter(sid => sid !== chat.id),
            chatStreamingContent: rest,
            streamingPhase: restPhase,
            streamingReasoning: restReasoning,
          }
        })
        if (get().currentChat?.id === chat.id) syncDisplay()

        playCompletionSound()

        await get().loadChats()
      } catch (error) {
        const isAbort = error instanceof DOMException && error.name === 'AbortError'
        if (!isAbort) {
          console.error('Send error:', error)
          // Show error as an assistant message so user sees what happened
          const errMsg: Message = {
            id: crypto.randomUUID(),
            chat_id: chat.id,
            role: 'assistant',
            content: `⚠️ **Something went wrong.** ${error instanceof Error ? error.message : 'Please try again.'}\n\n_If this keeps happening, try refreshing the page._`,
            token_count: 0,
            input_tokens: 0,
            output_tokens: 0,
            created_at: new Date().toISOString(),
          }
          set(state => ({
            chatMessages: { ...state.chatMessages, [chat.id]: [...(state.chatMessages[chat.id] || []), errMsg] },
          }))
        }
        set(state => {
          const { [chat.id]: _, ...restPhase } = state.streamingPhase
          const { [chat.id]: __, ...restReasoning } = state.streamingReasoning
          const { [chat.id]: ___, ...restStreaming } = state.chatStreamingContent
          return {
            streamingChatIds: state.streamingChatIds.filter(sid => sid !== chat.id),
            streamingPhase: restPhase,
            streamingReasoning: restReasoning,
            chatStreamingContent: restStreaming,
          }
        })
        if (get().currentChat?.id === chat.id) syncDisplay()
      } finally {
        delete streamControllers[chat.id]
      }
    },

    addAssistantMessage: async (content: string, chatId?: string) => {
      const chat = chatId ? get().chats.find(c => c.id === chatId) : get().currentChat
      if (!chat) return
      const msg: Message = {
        id: crypto.randomUUID(),
        chat_id: chat.id,
        role: 'assistant',
        content,
        token_count: 0,
        input_tokens: 0,
        output_tokens: 0,
        created_at: new Date().toISOString(),
      }
      set(state => ({
        chatMessages: { ...state.chatMessages, [chat.id]: [...(state.chatMessages[chat.id] || []), msg] },
      }))
      syncDisplay()
    },

    updateLastAssistantMessage: async (content: string, chatId?: string) => {
      const chat = chatId ? get().chats.find(c => c.id === chatId) : get().currentChat
      if (!chat) return
      const msgs = get().chatMessages[chat.id] || []
      if (msgs.length === 0) {
        await get().addAssistantMessage(content, chat.id)
        return
      }
      const lastIdx = msgs.length - 1
      const last = msgs[lastIdx]
      if (last.role !== 'assistant') {
        await get().addAssistantMessage(content, chat.id)
        return
      }
      const updated = msgs.map((m, i) => i === lastIdx ? { ...m, content } : m)
      set(state => ({
        chatMessages: { ...state.chatMessages, [chat.id]: updated },
      }))
      syncDisplay()
    },

    cancelStream: (chatId?: string) => {
      const id = chatId || get().currentChat?.id
      if (id) {
        streamControllers[id]?.abort()
        delete streamControllers[id]
        set(state => {
          const { [id]: _, ...restPhase } = state.streamingPhase
          const { [id]: __, ...restReasoning } = state.streamingReasoning
          return {
            streamingChatIds: state.streamingChatIds.filter(sid => sid !== id),
            streamingPhase: restPhase,
            streamingReasoning: restReasoning,
          }
        })
        syncDisplay()
      }
    },
  }
})
