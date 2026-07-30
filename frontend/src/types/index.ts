export interface User {
  id: string
  email: string
  username: string
  display_name?: string
  avatar_url?: string
  bio?: string
  is_active: boolean
  preferences?: string
  created_at: string
}

export interface Chat {
  id: string
  title?: string
  model: string
  provider: string
  system_prompt?: string
  temperature: number
  max_tokens: number
  is_pinned: boolean
  is_archived: boolean
  token_count: number
  folder_id?: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface ChatFolder {
  id: string
  name: string
  icon?: string
  color?: string
  sort_order: number
  created_at: string
}

export interface Message {
  id: string
  chat_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  model?: string
  provider?: string
  reasoning?: string
  metadata?: Record<string, unknown>
  token_count: number
  input_tokens: number
  output_tokens: number
  latency_ms?: number
  parent_id?: string
  created_at: string
}

export interface StreamChunk {
  type: 'content' | 'reasoning' | 'tool_call' | 'error' | 'done'
  content: string
  reasoning?: string
  model?: string
  provider?: string
  input_tokens?: number
  output_tokens?: number
  done: boolean
}

export interface ModelInfo {
  id: string
  name: string
  provider: string
  capabilities: string[]
}

export interface ProviderInfo {
  id: string
  name: string
  icon: string
  requires_key: boolean
}

export interface FileInfo {
  id: string
  filename: string
  size: number
  content_type: string
  text_preview: string
  chunk_count: number
  analysis?: string
}

export interface ImageGenResponse {
  image_b64: string
  model: string
  provider: string
  seed: number
  latency_ms: number
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export interface ChatRequest {
  message: string
  chat_id?: string
  model?: string
  provider?: string
  system_prompt?: string
  temperature?: number
  max_tokens?: number
  stream?: boolean
  files?: string[]
  tools?: Record<string, unknown>[]
}
