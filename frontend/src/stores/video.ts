/**
 * Zustand store for AI Video Generation studio
 */

import { create } from 'zustand'
import {
  videoApi,
  VideoModelCapability,
  VideoJobResponse,
  VideoHealthResponse,
} from '@/lib/videoApi'

interface ReferenceImageState {
  id: string
  name: string
  previewUrl: string
}

interface VideoState {
  models: VideoModelCapability[]
  activeModel: string
  mode: 'text_to_video' | 'image_to_video'
  prompt: string
  negativePrompt: string
  aspectRatio: string
  resolution: string
  duration: number
  fps: number
  seed: number | undefined
  referenceImage: ReferenceImageState | null
  activeJob: VideoJobResponse | null
  history: VideoJobResponse[]
  isEnhancing: boolean
  isSubmitting: boolean
  isUploadingRef: boolean
  health: VideoHealthResponse | null
  selectedVideo: VideoJobResponse | null
  error: string | null

  // Setters
  setActiveModel: (model: string) => void
  setMode: (mode: 'text_to_video' | 'image_to_video') => void
  setPrompt: (prompt: string) => void
  setNegativePrompt: (negativePrompt: string) => void
  setAspectRatio: (aspectRatio: string) => void
  setResolution: (resolution: string) => void
  setDuration: (duration: number) => void
  setFps: (fps: number) => void
  setSeed: (seed: number | undefined) => void
  setSelectedVideo: (video: VideoJobResponse | null) => void
  clearError: () => void

  // Async Actions
  loadInitialData: () => Promise<void>
  enhanceCurrentPrompt: () => Promise<void>
  uploadReferenceFile: (file: File) => Promise<void>
  clearReferenceImage: () => void
  startGeneration: () => Promise<void>
  cancelJob: (jobId: string) => Promise<void>
  deleteVideo: (jobId: string) => Promise<void>
  pollJob: (jobId: string) => Promise<void>
}

let pollTimer: any = null

export const useVideoStore = create<VideoState>((set, get) => ({
  models: [],
  activeModel: 'wan-ai/wan2.2',
  mode: 'text_to_video',
  prompt: '',
  negativePrompt: '',
  aspectRatio: '16:9',
  resolution: '720p',
  duration: 5,
  fps: 24,
  seed: undefined,
  referenceImage: null,
  activeJob: null,
  history: [],
  isEnhancing: false,
  isSubmitting: false,
  isUploadingRef: false,
  health: null,
  selectedVideo: null,
  error: null,

  setActiveModel: (activeModel) => set({ activeModel }),
  setMode: (mode) => set({ mode }),
  setPrompt: (prompt) => set({ prompt }),
  setNegativePrompt: (negativePrompt) => set({ negativePrompt }),
  setAspectRatio: (aspectRatio) => set({ aspectRatio }),
  setResolution: (resolution) => set({ resolution }),
  setDuration: (duration) => set({ duration }),
  setFps: (fps) => set({ fps }),
  setSeed: (seed) => set({ seed }),
  setSelectedVideo: (selectedVideo) => set({ selectedVideo }),
  clearError: () => set({ error: null }),

  loadInitialData: async () => {
    try {
      const [models, history, health] = await Promise.all([
        videoApi.listModels().catch(() => []),
        videoApi.listJobs().catch(() => []),
        videoApi.getHealth().catch(() => null),
      ])
      set({
        models,
        history,
        health,
        activeModel: models[0]?.model_id || 'wan-ai/wan2.2',
      })

      // Check if there is an in-flight job in history
      const running = history.find(j => ['queued', 'submitting', 'generating', 'processing'].includes(j.status))
      if (running) {
        set({ activeJob: running })
        get().pollJob(running.id)
      }
    } catch (err: any) {
      set({ error: err.message })
    }
  },

  enhanceCurrentPrompt: async () => {
    const { prompt } = get()
    if (!prompt.trim()) return
    set({ isEnhancing: true, error: null })
    try {
      const res = await videoApi.enhancePrompt(prompt, 'cinematic')
      set({ prompt: res.enhanced_prompt })
    } catch (err: any) {
      set({ error: `Prompt enhancement failed: ${err.message}` })
    } finally {
      set({ isEnhancing: false })
    }
  },

  uploadReferenceFile: async (file: File) => {
    set({ isUploadingRef: true, error: null })
    try {
      const previewUrl = URL.createObjectURL(file)
      const res = await videoApi.uploadReferenceImage(file)
      set({
        referenceImage: {
          id: res.reference_image_id,
          name: res.filename,
          previewUrl,
        },
        mode: 'image_to_video',
      })
    } catch (err: any) {
      set({ error: `Reference image upload failed: ${err.message}` })
    } finally {
      set({ isUploadingRef: false })
    }
  },

  clearReferenceImage: () => {
    const { referenceImage } = get()
    if (referenceImage?.previewUrl) {
      URL.revokeObjectURL(referenceImage.previewUrl)
    }
    set({ referenceImage: null, mode: 'text_to_video' })
  },

  startGeneration: async () => {
    const {
      prompt,
      negativePrompt,
      activeModel,
      mode,
      aspectRatio,
      resolution,
      duration,
      fps,
      seed,
      referenceImage,
    } = get()

    if (!prompt.trim()) {
      set({ error: 'Please enter a prompt to generate a video' })
      return
    }

    if (mode === 'image_to_video' && !referenceImage) {
      set({ error: 'Please upload a reference starting image for Image-to-Video mode' })
      return
    }

    set({ isSubmitting: true, error: null })

    try {
      const job = await videoApi.generate({
        prompt: prompt.trim(),
        negative_prompt: negativePrompt.trim() || undefined,
        model: activeModel,
        mode,
        aspect_ratio: aspectRatio,
        resolution,
        duration_seconds: duration,
        fps,
        seed,
        reference_image_id: referenceImage?.id,
      })

      set({
        activeJob: job,
        history: [job, ...get().history.filter(j => j.id !== job.id)],
      })

      get().pollJob(job.id)
    } catch (err: any) {
      set({ error: err.message })
    } finally {
      set({ isSubmitting: false })
    }
  },

  cancelJob: async (jobId: string) => {
    try {
      await videoApi.cancelJob(jobId)
      if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
      }
      const updatedJob = await videoApi.getJob(jobId).catch(() => null)
      if (updatedJob) {
        set(state => ({
          activeJob: state.activeJob?.id === jobId ? updatedJob : state.activeJob,
          history: state.history.map(j => (j.id === jobId ? updatedJob : j)),
        }))
      }
    } catch (err: any) {
      set({ error: `Cancellation failed: ${err.message}` })
    }
  },

  deleteVideo: async (jobId: string) => {
    try {
      await videoApi.deleteJob(jobId)
      set(state => ({
        history: state.history.filter(j => j.id !== jobId),
        selectedVideo: state.selectedVideo?.id === jobId ? null : state.selectedVideo,
        activeJob: state.activeJob?.id === jobId ? null : state.activeJob,
      }))
    } catch (err: any) {
      set({ error: `Delete failed: ${err.message}` })
    }
  },

  pollJob: async (jobId: string) => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }

    pollTimer = setInterval(async () => {
      try {
        const job = await videoApi.getJob(jobId)
        set(state => ({
          activeJob: state.activeJob?.id === jobId ? job : state.activeJob,
          history: state.history.map(j => (j.id === jobId ? job : j)),
        }))

        if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
          clearInterval(pollTimer)
          pollTimer = null
          if (job.status === 'completed') {
            set({ selectedVideo: job })
          }
        }
      } catch (err) {
        clearInterval(pollTimer)
        pollTimer = null
      }
    }, 2000)
  },
}))
