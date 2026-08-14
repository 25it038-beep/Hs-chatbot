import type { User, Chat, ChatFolder, Message, ModelInfo, ProviderInfo, FileInfo, TokenResponse, StreamChunk, ImageGenResponse } from '@/types'

function getBaseUrl(): string {
  const envUrl = (import.meta.env.VITE_API_URL as string)?.trim()
  if (!envUrl) return '/api'
  const cleanUrl = envUrl.replace(/\/+$/, '')
  if (cleanUrl.endsWith('/api')) return cleanUrl
  return `${cleanUrl}/api`
}

const BASE_URL = getBaseUrl()

let accessToken: string | null = localStorage.getItem('access_token')
let refreshToken: string | null = localStorage.getItem('refresh_token')

export function setTokens(access: string, refresh: string) {
  accessToken = access
  refreshToken = refresh
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
}

export function clearTokens() {
  accessToken = null
  refreshToken = null
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

async function refreshAccessToken(): Promise<boolean> {
  if (!refreshToken) return false
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!res.ok) return false
    const data: TokenResponse = await res.json()
    setTokens(data.access_token, data.refresh_token)
    return true
  } catch {
    return false
  }
}

function getAuthHeader(): Record<string, string> {
  const token = accessToken || localStorage.getItem('access_token') || 'hsbot_default_access_token'
  return { Authorization: `Bearer ${token}` }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
    ...(options.headers as Record<string, string>),
  }
  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  } catch {
    throw new Error('Unable to connect to server. Please verify backend is running.')
  }

  if (res.status === 401 && refreshToken && path !== '/auth/login' && path !== '/auth/register') {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      headers['Authorization'] = `Bearer ${accessToken}`
      try {
        res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
      } catch {
        throw new Error('Unable to connect to server. Please verify backend is running.')
      }
    }
  }

  if (!res.ok) {
    let errorMessage = `Request failed with status ${res.status}`
    try {
      const err = await res.json()
      if (typeof err.detail === 'string' && err.detail.trim()) {
        errorMessage = err.detail
      } else if (Array.isArray(err.detail) && err.detail.length > 0) {
        errorMessage = err.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ')
      } else if (err.detail && typeof err.detail === 'object') {
        errorMessage = JSON.stringify(err.detail)
      } else if (err.message) {
        errorMessage = err.message
      } else if (res.statusText) {
        errorMessage = `HTTP ${res.status}: ${res.statusText}`
      }
    } catch {
      errorMessage = res.statusText ? `HTTP ${res.status}: ${res.statusText}` : `Request failed with status ${res.status}`
    }
    throw new Error(errorMessage)
  }
  return res.json()
}

export const api = {
  // Auth
  login: (username: string, password: string) =>
    request<TokenResponse>('/auth/login', { method: 'POST', body: JSON.stringify({ username, password: password.slice(0, 72) }) }),

  register: (email: string, username: string, password: string) =>
    request<TokenResponse>('/auth/register', { method: 'POST', body: JSON.stringify({ email, username, password: password.slice(0, 72) }) }),

  getMe: () => request<User>('/auth/me'),

  // Chats
  listChats: (folderId?: string) =>
    request<Chat[]>(`/chats${folderId ? `?folder_id=${folderId}` : ''}`),

  getChat: (id: string) => request<Chat>(`/chats/${id}`),

  createChat: (data: Partial<Chat>) =>
    request<Chat>('/chats', { method: 'POST', body: JSON.stringify(data) }),

  updateChat: (id: string, data: Partial<Chat>) =>
    request<Chat>(`/chats/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  deleteChat: (id: string) =>
    request<void>(`/chats/${id}`, { method: 'DELETE' }),

  getMessages: (chatId: string) =>
    request<Message[]>(`/chats/${chatId}/messages`),

  sendMessageStream: (data: {
    message: string
    chat_id?: string
    model?: string
    provider?: string
    system_prompt?: string
    temperature?: number
    max_tokens?: number
  }): Promise<ReadableStreamDefaultReader<Uint8Array>> => {
    const controller = new AbortController()
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    }
    const response = fetch(`${BASE_URL}/chats/messages`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ ...data, stream: true }),
      signal: controller.signal,
    })
    return response.then((res) => {
      if (!res.ok) throw new Error('Stream request failed')
      return res.body!.getReader()
    })
  },

  // Folders
  listFolders: () => request<ChatFolder[]>('/chats/folders'),

  createFolder: (data: { name: string; icon?: string; color?: string }) =>
    request<ChatFolder>('/chats/folders', { method: 'POST', body: JSON.stringify(data) }),

  deleteFolder: (id: string) =>
    request<void>(`/chats/folders/${id}`, { method: 'DELETE' }),

  // Models
  listModels: () => request<ModelInfo[]>('/models'),

  listProviders: () => request<ProviderInfo[]>('/models/providers'),

  // Files
  uploadFile: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const headers = getAuthHeader()
    return fetch(`${BASE_URL}/files/upload`, { method: 'POST', body: formData, headers }).then(r => r.json()) as Promise<FileInfo>
  },

  uploadMultiple: (files: File[]) => {
    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    const headers = getAuthHeader()
    return fetch(`${BASE_URL}/files/upload-multiple`, { method: 'POST', body: formData, headers }).then(r => r.json()) as Promise<{ files: FileInfo[] }>
  },

  health: () => request<{ status: string }>('/health'),

  // NVIDIA
  nvidiaChatStream: async (data: {
    message: string
    chat_id?: string
    model?: string
    system_prompt?: string
    temperature?: number
    max_tokens?: number
    top_p?: number
    stream?: boolean
    json_mode?: boolean
    reasoning?: boolean
    auto_route?: boolean
  }, signal?: AbortSignal): Promise<ReadableStreamDefaultReader<Uint8Array>> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    }
    const doFetch = (hdrs: Record<string, string>) =>
      fetch(`${BASE_URL}/nvidia/chat`, {
        method: 'POST',
        headers: hdrs,
        signal,
        body: JSON.stringify({ ...data, stream: true }),
      })

    let res = await doFetch(headers)

    // Auto-refresh token on 401 (same as request())
    if (res.status === 401 && refreshToken) {
      const refreshed = await refreshAccessToken()
      if (refreshed) {
        headers['Authorization'] = `Bearer ${accessToken}`
        res = await doFetch(headers)
      }
    }

    if (!res.ok) {
      let msg = `Stream failed (${res.status})`
      try {
        const err = await res.json()
        msg = err.detail || err.message || msg
      } catch {}
      throw new Error(msg)
    }
    return res.body!.getReader()
  },

  nvidiaVision: (file: File, prompt: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('prompt', prompt)
    const headers = getAuthHeader()
    return fetch(`${BASE_URL}/nvidia/vision`, { method: 'POST', body: formData, headers }).then(r => r.json())
  },

  nvidiaGenerateImage: (prompt: string, model = 'flux-2-klein', steps = 4) => {
    const formData = new FormData()
    formData.append('prompt', prompt)
    formData.append('model', model)
    formData.append('steps', String(steps))
    formData.append('seed', '0')
    const headers = getAuthHeader()
    return fetch(`${BASE_URL}/nvidia/image/generate`, { method: 'POST', body: formData, headers }).then(r => r.json()) as Promise<ImageGenResponse>
  },

  nvidiaEmbed: (texts: string[], model = 'nv-embed-v1') =>
    request<{ embeddings: number[][]; model: string; dimensions: number }>('/nvidia/embeddings', {
      method: 'POST',
      body: JSON.stringify({ texts, model }),
    }),

  nvidiaRoute: (message: string) =>
    request<{ task: string; model: string; available_fallbacks: string[] }>(`/nvidia/route?message=${encodeURIComponent(message)}`),

  nvidiaUsage: () => request<any>('/nvidia/usage'),

  speechTranscribe: (audioBlob: Blob, language = 'en') => {
    const formData = new FormData()
    formData.append('file', audioBlob, 'recording.wav')
    formData.append('language', language)
    const headers = getAuthHeader()
    return fetch(`${BASE_URL}/nvidia/speech/transcribe`, { method: 'POST', body: formData, headers }).then(r => r.json()) as Promise<{ text: string }>
  },
}
