export type ConnectionState =
  | 'INITIALIZING'
  | 'CONNECTING'
  | 'WAKING_UP'
  | 'VERIFYING_READINESS'
  | 'CONNECTED'
  | 'RECONNECTING'
  | 'CONNECTION_ERROR'

export interface ReadinessResponse {
  status: 'ready' | 'degraded' | 'initializing' | 'ok'
  ready?: boolean
  database?: string
  ai_ready?: boolean
  version?: string
  commit?: string
  timestamp?: number
  detail?: any
}

export interface ConnectionInfo {
  state: ConnectionState
  isReady: boolean
  backendUrl: string
  elapsedSeconds: number
  attemptCount: number
  nextRetrySeconds: number
  lastError: string | null
  diagnostics: {
    online: boolean
    statusCode?: number
    responseTimeMs?: number
    serverInfo?: ReadinessResponse | null
  }
}
