/**
 * Type definitions for HSBot Isolated Live Voice Subsystem.
 * Supports Nemotron VoiceChat (primary S2S) and Cascaded NVIDIA Live (Riva + LLM + FastPitch).
 */

export type LiveState =
  | 'IDLE'
  | 'CONNECTING'
  | 'CONNECTED'
  | 'LISTENING'
  | 'PROCESSING'
  | 'SPEAKING'
  | 'INTERRUPTED'
  | 'ERROR'
  | 'DISCONNECTED'

export type LiveEngine = 'nemotron_voicechat' | 'cascaded'

export interface LiveTurnTranscript {
  id: string
  role: 'user' | 'assistant'
  text: string
  isFinal: boolean
  timestamp: number
  engine?: LiveEngine
}

export interface LiveDiagnosticsData {
  engine: LiveEngine
  connectionState: LiveState
  wsLatencyMs: number
  micActive: boolean
  micSampleRate: number
  micInputLevel: number
  audioOutputActive: boolean
  audioBufferQueueLength: number
  asrLatencyMs: number
  llmFirstTokenLatencyMs: number
  ttsFirstAudioLatencyMs: number
  totalTurnLatencyMs: number
  packetCount: number
  lastErrorCode?: string
  lastErrorMessage?: string
  lastErrorDetails?: any
}

export interface LiveServerMessage {
  type:
    | 'connection'
    | 'status'
    | 'transcript'
    | 'llm_chunk'
    | 'audio_chunk'
    | 'timing'
    | 'diagnostics'
    | 'engine_switched'
    | 'error'
  state?: LiveState
  role?: 'user' | 'assistant'
  text?: string
  isFinal?: boolean
  audio?: string
  sampleRate?: number
  index?: number
  metric?: string
  value?: number
  code?: string
  message?: string
  details?: any
  engine?: LiveEngine
  data?: any
  timestamp?: number
}

export interface LiveVoiceConfig {
  voice?: string
  sampleRate?: number
  vadSensitivity?: number
  autoListen?: boolean
  engine?: LiveEngine
}
