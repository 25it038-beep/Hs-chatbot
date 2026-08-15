import { api } from './api'
import { getBaseUrl, getAuthHeader } from './api'

export interface VoiceConfig {
  language: string
  voice: string
  sampleRate: number
  model: string
  wakeWord: string
  wakeWordEnabled: boolean
  autoSpeak: boolean
  interruptEnabled: boolean
  silenceTimeout: number
  minSpeechDuration: number
  maxRecordingDuration: number
}

export interface VoiceState {
  status: 'idle' | 'listening' | 'speaking' | 'processing' | 'ai_speaking' | 'error'
  transcript: string
  isRecording: boolean
  audioLevel: number
  error: string | null
}

export const DEFAULT_VOICE_CONFIG: VoiceConfig = {
  language: 'en-US',
  voice: 'en-US-Female-1',
  sampleRate: 24000,
  model: 'nvidia/riva-tts-multilingual',
  wakeWord: 'Hey HS',
  wakeWordEnabled: false,
  autoSpeak: true,
  interruptEnabled: true,
  silenceTimeout: 1500,
  minSpeechDuration: 500,
  maxRecordingDuration: 30000,
}

export async function transcribeAudio(
  audioBlob: Blob,
  language: string = 'en-US'
): Promise<string> {
  const formData = new FormData()
  formData.append('file', audioBlob, 'audio.wav')
  formData.append('language', language)
  
  const response = await fetch(`${getBaseUrl()}/api/nvidia/speech/transcribe`, {
    method: 'POST',
    body: formData,
    headers: getAuthHeader(),
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Transcription failed')
  }
  
  const data = await response.json()
  return data.text
}

export async function synthesizeSpeech(
  text: string,
  config: Partial<VoiceConfig> = {}
): Promise<Blob> {
  const response = await fetch(`${getBaseUrl()}/api/nvidia/speech/synthesize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
    body: JSON.stringify({
      text,
      voice: config.voice || DEFAULT_VOICE_CONFIG.voice,
      model: config.model || DEFAULT_VOICE_CONFIG.model,
      language: config.language || DEFAULT_VOICE_CONFIG.language,
      sample_rate: config.sampleRate || DEFAULT_VOICE_CONFIG.sampleRate,
    }),
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Speech synthesis failed')
  }
  
  return response.blob()
}

export function getVoiceWebSocketUrl(): string {
  const baseUrl = getBaseUrl().replace('http://', 'ws://').replace('https://', 'wss://')
  return `${baseUrl}/api/nvidia/speech/ws`
}

export const VOICE_STATES = {
  IDLE: 'idle',
  LISTENING: 'listening',
  SPEAKING: 'speaking',
  PROCESSING: 'processing',
  AI_SPEAKING: 'ai_speaking',
  ERROR: 'error',
} as const

export type VoiceStatus = typeof VOICE_STATES[keyof typeof VOICE_STATES]