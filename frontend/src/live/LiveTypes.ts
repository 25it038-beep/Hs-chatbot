/**
 * HSBot Live Voice System - Isolated Type Definitions
 * 
 * Strict NVIDIA-only live voice conversation types.
 */

export type ConnectionState =
  | 'DISCONNECTED'
  | 'CONNECTING'
  | 'CONNECTED'
  | 'RECONNECTING'
  | 'FAILED'

export type TurnState =
  | 'IDLE'
  | 'LISTENING'
  | 'USER_SPEAKING'
  | 'THINKING'
  | 'SPEAKING'
  | 'INTERRUPTED'
  | 'ERROR'

export type LiveState =
  | 'IDLE'
  | 'CONNECTING'
  | 'LISTENING'
  | 'USER_SPEAKING'
  | 'PROCESSING'
  | 'THINKING'
  | 'SPEAKING'
  | 'INTERRUPTED'
  | 'ERROR'
  | 'DISCONNECTED'

export interface LiveConfig {
  sampleRate: number
  language: string
  voice: string
  vadThreshold: number
  silenceDurationMs: number
}

export interface LiveTranscriptItem {
  id: string
  role: 'user' | 'assistant'
  text: string
  isFinal: boolean
  timestamp: number
  turnId?: string
}

export interface LiveAudioLevel {
  input: number  // 0.0 to 1.0
  output: number // 0.0 to 1.0
}

export interface LiveTimingMetrics {
  asr_to_llm_first_token_ms?: number
  llm_first_token_to_tts_first_audio_ms?: number
  total_latency_ms?: number
}

export interface LiveDiagnostics {
  connectionState: ConnectionState
  turnState: TurnState
  micReady: boolean
  micSampleRate: number
  micChannels: number
  micRms: number
  audioFramesCount: number
  audioBytesSent: number
  asrStatus: 'idle' | 'transcribing' | 'success' | 'no_speech' | 'error'
  asrTranscript: string
  llmStatus: 'idle' | 'streaming' | 'complete' | 'error'
  llmTtftMs?: number
  ttsStatus: 'idle' | 'synthesizing' | 'streaming' | 'complete' | 'error'
  ttsBytesReceived: number
  playbackStatus: 'idle' | 'playing' | 'ended'
  totalTurnLatencyMs?: number
}

// Client -> Server messages
export type ClientLiveMessage =
  | { type: 'config'; config: Partial<LiveConfig> }
  | { type: 'audio'; data: string; sampleRate: number; turnId?: string } // base64 PCM 16kHz
  | { type: 'user_speech'; text: string; turnId?: string }
  | { type: 'commit_turn'; turnId?: string }
  | { type: 'interrupt' }
  | { type: 'ping'; timestamp: number }

// Server -> Client messages
export type ServerLiveMessage =
  | { type: 'status'; state: LiveState; message?: string; turnId?: string }
  | { type: 'transcript'; role: 'user' | 'assistant'; text: string; isFinal: boolean; turnId?: string }
  | { type: 'llm_chunk'; text: string; turnId?: string }
  | { type: 'audio_chunk'; audio: string; sampleRate: number; index?: number; turnId?: string } // base64 PCM
  | { type: 'timing'; metric: string; value: number; turnId?: string }
  | { type: 'error'; code: string; message: string }
  | { type: 'pong'; timestamp: number }

export interface LiveError {
  code: string
  message: string
  recoverable: boolean
}
