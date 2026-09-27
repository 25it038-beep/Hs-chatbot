/**
 * Video Generation API Client
 */

import { getAuthHeader, getBaseUrl, ensureFreshToken } from '@/lib/api'

export interface VideoModelCapability {
  model_id: string
  name: string
  provider: string
  modes: string[]
  resolutions: string[]
  aspect_ratios: string[]
  durations: number[]
  default_fps: number
  description: string
  status: string
}

export type VideoJobStatus =
  | 'queued'
  | 'submitting'
  | 'generating'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled'

export interface VideoJobResponse {
  id: string
  user_id: string
  model: string
  mode: 'text_to_video' | 'image_to_video'
  prompt: string
  negative_prompt?: string
  status: VideoJobStatus
  progress_stage: string
  created_at: number
  started_at?: number
  completed_at?: number
  elapsed_seconds: number
  video_url?: string
  stream_url?: string
  download_url?: string
  duration_seconds?: number
  width?: number
  height?: number
  file_size?: number
  error_message?: string
  parameters?: Record<string, any>
}

export interface VideoGenerationRequest {
  prompt: string
  negative_prompt?: string
  model: string
  mode: 'text_to_video' | 'image_to_video'
  aspect_ratio: string
  duration_seconds: number
  resolution: string
  fps: number
  seed?: number
  reference_image_id?: string
  motion_strength?: number
}

export interface EnhancePromptResponse {
  original_prompt: string
  enhanced_prompt: string
  camera_movement?: string
  lighting?: string
  style?: string
}

export interface VideoHealthResponse {
  status: string
  active_models: number
  running_jobs: number
  providers: Record<string, any>
}

async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  await ensureFreshToken()
  const baseUrl = getBaseUrl()
  const headers = {
    ...getAuthHeader(),
    ...(options.headers as Record<string, string>),
  }

  const res = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers,
  })

  if (res.status === 401) {
    const freshToken = await ensureFreshToken(true)
    if (freshToken) {
      return fetch(`${baseUrl}${path}`, {
        ...options,
        headers: {
          ...headers,
          Authorization: `Bearer ${freshToken}`,
        },
      })
    }
  }

  return res
}

export const videoApi = {
  async getHealth(): Promise<VideoHealthResponse> {
    const res = await authFetch('/api/video/health')
    if (!res.ok) throw new Error('Failed to fetch video health status')
    return res.json()
  },

  async listModels(): Promise<VideoModelCapability[]> {
    const res = await authFetch('/api/video/models')
    if (!res.ok) throw new Error('Failed to load video models')
    return res.json()
  },

  async enhancePrompt(prompt: string, style = 'cinematic'): Promise<EnhancePromptResponse> {
    const res = await authFetch('/api/video/enhance-prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, style }),
    })
    if (!res.ok) throw new Error('Failed to enhance prompt')
    return res.json()
  },

  async uploadReferenceImage(file: File): Promise<{ reference_image_id: string; filename: string }> {
    const formData = new FormData()
    formData.append('file', file)

    const res = await authFetch('/api/video/upload-reference', {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
      throw new Error(err.detail || 'Failed to upload reference image')
    }
    return res.json()
  },

  async generate(req: VideoGenerationRequest): Promise<VideoJobResponse> {
    const res = await authFetch('/api/video/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Generation request failed' }))
      throw new Error(err.detail || 'Failed to start video generation')
    }
    return res.json()
  },

  async getJob(jobId: string): Promise<VideoJobResponse> {
    const res = await authFetch(`/api/video/jobs/${jobId}`)
    if (!res.ok) throw new Error('Failed to fetch job status')
    return res.json()
  },

  async cancelJob(jobId: string): Promise<void> {
    const res = await authFetch(`/api/video/jobs/${jobId}/cancel`, {
      method: 'POST',
    })
    if (!res.ok) throw new Error('Failed to cancel job')
  },

  async listJobs(): Promise<VideoJobResponse[]> {
    const res = await authFetch('/api/video/jobs')
    if (!res.ok) throw new Error('Failed to list video history')
    return res.json()
  },

  async deleteJob(jobId: string): Promise<void> {
    const res = await authFetch(`/api/video/jobs/${jobId}`, {
      method: 'DELETE',
    })
    if (!res.ok) throw new Error('Failed to delete video')
  },

  getStreamUrl(jobId: string): string {
    const baseUrl = getBaseUrl()
    const token = localStorage.getItem('access_token')
    const query = token ? `?token=${encodeURIComponent(token)}` : ''
    return `${baseUrl}/api/video/${jobId}/stream${query}`
  },

  getDownloadUrl(jobId: string): string {
    const baseUrl = getBaseUrl()
    const token = localStorage.getItem('access_token')
    const query = token ? `?token=${encodeURIComponent(token)}` : ''
    return `${baseUrl}/api/video/${jobId}/download${query}`
  },
}
