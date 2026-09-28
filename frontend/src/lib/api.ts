import type { User, Chat, ChatFolder, Message, ModelInfo, ProviderInfo, FileInfo, FileStatusInfo, Attachment, TokenResponse, StreamChunk, ImageGenResponse } from '@/types'

function getBaseUrlInternal(): string {
  const envUrl = (import.meta.env.VITE_API_URL as string)?.trim()
  const isBrowser = typeof window !== 'undefined' && Boolean(window.location?.hostname)
  const isLocalhost = isBrowser && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')

  if (envUrl) {
    const cleanUrl = envUrl.replace(/\/+$/, '')
    // Only accept localhost URL if actually running on localhost
    if (!cleanUrl.includes('localhost') || isLocalhost) {
      return cleanUrl.endsWith('/api') ? cleanUrl : `${cleanUrl}/api`
    }
  }

  if (isBrowser) {
    const hostname = window.location.hostname
    // If on Google Cloud Run or local dev or same-origin deployment, use relative /api
    if (hostname.includes('run.app') || isLocalhost || hostname.endsWith('.local')) {
      return '/api'
    }
    // If deployed on Render static site (e.g. hs-chatbot-3.onrender.com)
    if (hostname.includes('onrender.com')) {
      if (hostname.includes('hs-chatbot-2')) {
        return '/api'
      }
      return 'https://hs-chatbot-2.onrender.com/api'
    }
  }

  return '/api'
}

const BASE_URL = getBaseUrlInternal()

export function getBaseUrl(): string {
  return BASE_URL
}

export function getWsBaseUrl(): string {
  const base = getBaseUrl()
  if (base.startsWith('http://') || base.startsWith('https://')) {
    return base.replace(/^http/, 'ws')
  }
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}${base}`
  }
  return 'ws://localhost:8000/api'
}

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

export async function ensureFreshToken(forceRefresh = false): Promise<string | null> {
  // If Clerk is active, ask Clerk SDK for the latest token (with auto-refresh)
  try {
    const clerk = (window as any).Clerk
    if (clerk?.session) {
      const clerkToken = await clerk.session.getToken(forceRefresh ? { skipCache: true } : undefined)
      if (clerkToken) {
        setTokens(clerkToken, '')
        return clerkToken
      }
    }
  } catch (err) {
    console.warn('[AUTH] Error obtaining fresh Clerk token:', err)
  }

  // Fallback to local access token
  const token = accessToken || localStorage.getItem('access_token')
  if (!token || token === 'hsbot_default_access_token' || token === 'hsbot_guest_token') {
    return null
  }
  return token
}

export function getAuthHeader(): Record<string, string> {
  const token = accessToken || localStorage.getItem('access_token')
  if (!token || token === 'hsbot_default_access_token' || token === 'hsbot_guest_token') {
    return {}
  }
  return { Authorization: `Bearer ${token}` }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  await ensureFreshToken()
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

  if (res.status === 401 && path !== '/auth/login' && path !== '/auth/register') {
    let renewed = false
    const clerk = (window as any).Clerk
    if (clerk?.session) {
      const freshToken = await ensureFreshToken(true)
      if (freshToken) {
        headers['Authorization'] = `Bearer ${freshToken}`
        renewed = true
        try {
          res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
        } catch {}
      }
    }
    if (!renewed && refreshToken) {
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

  sendMessageStream: async (data: {
    message: string
    chat_id?: string
    model?: string
    provider?: string
    system_prompt?: string
    temperature?: number
    max_tokens?: number
    files?: string[]
    attachments?: Attachment[]
    location?: string
    timezone?: string
  }, signal?: AbortSignal): Promise<ReadableStreamDefaultReader<Uint8Array>> => {
    await ensureFreshToken()
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    }
    const doFetch = (hdrs: Record<string, string>) =>
      fetch(`${BASE_URL}/chats/messages`, {
        method: 'POST',
        headers: hdrs,
        body: JSON.stringify({ ...data, stream: true }),
        signal,
      })

    let res = await doFetch(headers)
    if (res.status === 401) {
      let renewed = false
      const clerk = (window as any).Clerk
      if (clerk?.session) {
        const freshToken = await ensureFreshToken(true)
        if (freshToken) {
          headers['Authorization'] = `Bearer ${freshToken}`
          renewed = true
          res = await doFetch(headers)
        }
      }
      if (!renewed && refreshToken) {
        const refreshed = await refreshAccessToken()
        if (refreshed) {
          headers['Authorization'] = `Bearer ${accessToken}`
          res = await doFetch(headers)
        }
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
  uploadFile: async (
    file: File,
    options?: { source?: string; analyze?: boolean; signal?: AbortSignal }
  ): Promise<FileInfo> => {
    await ensureFreshToken()
    const formData = new FormData()
    formData.append('file', file, file.name || 'clipboard-file')
    formData.append('analyze', options?.analyze ? 'true' : 'false')
    formData.append('source', options?.source || 'picker')

    let res: Response
    try {
      res = await fetch(`${BASE_URL}/files/upload`, {
        method: 'POST',
        body: formData,
        headers: getAuthHeader(),
        signal: options?.signal,
      })
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') throw err
      throw new Error('Unable to connect to server for file upload.')
    }

    if (res.status === 401 && (window as any).Clerk?.session) {
      const fresh = await ensureFreshToken(true)
      if (fresh) {
        res = await fetch(`${BASE_URL}/files/upload`, {
          method: 'POST',
          body: formData,
          headers: getAuthHeader(),
          signal: options?.signal,
        })
      }
    }

    if (!res.ok) {
      let errorMessage = `Upload failed (${res.status})`
      try {
        const err = await res.json()
        if (typeof err.detail === 'string' && err.detail.trim()) {
          errorMessage = err.detail
        } else if (err.message) {
          errorMessage = err.message
        }
      } catch {}
      throw new Error(errorMessage)
    }

    return res.json() as Promise<FileInfo>
  },

  getFileStatus: (fileId: string, signal?: AbortSignal) =>
    request<FileStatusInfo>(`/files/${fileId}/status`, { signal }),

  deleteUploadedFile: (fileId: string) =>
    request<{ status: string; id: string }>(`/files/${fileId}`, { method: 'DELETE' }),

  downloadUploadedFileBlob: async (fileId: string): Promise<Blob> => {
    await ensureFreshToken()
    let res = await fetch(`${BASE_URL}/files/${fileId}/content`, {
      method: 'GET',
      headers: getAuthHeader(),
    })
    if (res.status === 401 && (window as any).Clerk?.session) {
      const fresh = await ensureFreshToken(true)
      if (fresh) {
        res = await fetch(`${BASE_URL}/files/${fileId}/content`, {
          method: 'GET',
          headers: getAuthHeader(),
        })
      }
    }
    if (!res.ok) {
      throw new Error(`Failed to download file (${res.status})`)
    }
    return res.blob()
  },

  uploadMultiple: async (files: File[], source: 'clipboard' | 'picker' | 'drop' = 'picker') => {
    await ensureFreshToken()
    const formData = new FormData()
    files.forEach(f => formData.append('files', f, f.name || 'clipboard-file'))
    formData.append('analyze', 'false')
    formData.append('source', source)
    let res = await fetch(`${BASE_URL}/files/upload-multiple`, { method: 'POST', body: formData, headers: getAuthHeader() })
    if (res.status === 401 && (window as any).Clerk?.session) {
      const fresh = await ensureFreshToken(true)
      if (fresh) {
        res = await fetch(`${BASE_URL}/files/upload-multiple`, { method: 'POST', body: formData, headers: getAuthHeader() })
      }
    }
    if (!res.ok) {
      let errorMessage = `Upload failed (${res.status})`
      try {
        const err = await res.json()
        if (typeof err.detail === 'string' && err.detail.trim()) {
          errorMessage = err.detail
        }
      } catch {}
      throw new Error(errorMessage)
    }
    return res.json() as Promise<{ files: FileInfo[] }>
  },

  health: () => request<{ status: string }>('/health'),

  get: <T>(path: string) => request<T>(path),

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
    files?: string[]
    attachments?: Attachment[]
    location?: string
    timezone?: string
  }, signal?: AbortSignal): Promise<ReadableStreamDefaultReader<Uint8Array>> => {
    await ensureFreshToken()
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

    // Auto-refresh token on 401
    if (res.status === 401) {
      let renewed = false
      const clerk = (window as any).Clerk
      if (clerk?.session) {
        const freshToken = await ensureFreshToken(true)
        if (freshToken) {
          headers['Authorization'] = `Bearer ${freshToken}`
          renewed = true
          res = await doFetch(headers)
        }
      }
      if (!renewed && refreshToken) {
        const refreshed = await refreshAccessToken()
        if (refreshed) {
          headers['Authorization'] = `Bearer ${accessToken}`
          res = await doFetch(headers)
        }
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

  downloadFile: async (fileId: string, filename = 'download'): Promise<void> => {
    const headers = getAuthHeader()
    const token = localStorage.getItem('access_token')
    const queryParam = token ? `?token=${encodeURIComponent(token)}` : ''
    const res = await fetch(`${BASE_URL}/files/${fileId}/download${queryParam}`, { headers })
    if (!res.ok) {
      throw new Error(`Download failed with status ${res.status}`)
    }
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  },

  getFilePreview: (fileId: string) => {
    return request<import('@/types').DocumentPreviewResponse>(`/files/${fileId}/preview`)
  },
}

