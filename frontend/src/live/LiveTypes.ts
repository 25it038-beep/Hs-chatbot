/**
 * HSBot Live Voice System - Isolated Type Definitions
 * 
 * Strict NVIDIA-only live voice conversation types.
 */

export type LiveState =
  | 'IDLE'
  | 'CONNECTING'
  | 'LISTENING'
  | 'PROCESSING'
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
}

export interface LiveAudioLevel {
  input: number  // 0.0 to 1.0
  output: number // 0.0 to 1.0
}

// Client -> Server messages
export type ClientLiveMessage =
  | { type: 'config'; config: Partial<LiveConfig> }
  | { type: 'audio'; data: string; sampleRate: number } // base64 PCM 16kHz
  | { type: 'user_speech'; text: string }
  | { type: 'commit_turn' }
  | { type: 'interrupt' }
  | { type: 'ping'; timestamp: number }

// Server -> Client messages
export type ServerLiveMessage =
  | { type: 'status'; state: LiveState; message?: string }
  | { type: 'transcript'; role: 'user' | 'assistant'; text: string; isFinal: boolean }
  | { type: 'llm_chunk'; text: string }
  | { type: 'audio_chunk'; audio: string; sampleRate: number; index: number } // base64 PCM
  | { type: 'error'; code: string; message: string }
  | { type: 'pong'; timestamp: number }

export interface LiveError {
  code: string
  message: string
  recoverable: boolean
}
