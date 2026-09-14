import { create } from 'zustand'
import { getAuthHeader } from '@/lib/api'
import { getLocalBackendUrl } from '@/lib/backendDetector'
import { useChat } from '@/stores/chat'

const LOCAL_ONLY_MESSAGE = 'Automation runs on your computer — start the local backend (localhost:8000).'

/** Resolve the local backend; never falls back to Render (automation is local-only). */
async function resolveLocalBase(): Promise<string> {
  const local = await getLocalBackendUrl()
  if (!local) throw new Error('LOCAL_UNAVAILABLE')
  return `${local}/api`
}

export interface AutomationEvent {
  type: string
  action_id?: string
  request_id?: string
  intent?: string
  target?: string | null
  explanation?: string
  prompt?: string
  risk?: string
  options?: string[]
  message?: string
  success?: boolean
  result?: unknown
  error?: string | null
  step_index?: number
  total?: number
  steps?: string[]
  confirmed?: boolean
  timestamp?: string
}

export interface PendingAction {
  action_id: string
  prompt: string
  risk: string
  options?: string[]
}

export interface LogEntry {
  timestamp: string
  action_id: string
  intent: string
  category: string
  target: string | null
  risk_level: string
  execution_time_ms?: number
  success: boolean
  error?: string | null
  explanation?: string
}

export interface EngineStatus {
  automation_available: boolean
  platform: string
  engine: { active_processes: number; max_workers: number; pending_confirmations: number }
  voice_listener: { state: string; microphone_enabled: boolean; continuous_mode: boolean }
  examples: string[]
}

interface AutomationState {
  open: boolean
  connecting: boolean
  connected: boolean
  busy: boolean
  executing: string | null
  events: AutomationEvent[]
  pending: PendingAction | null
  history: LogEntry[]
  status: EngineStatus | null
  lastError: string | null
  voiceEnabled: boolean
  voiceStarting: boolean
  voiceWsConnected: boolean
  voiceListenerState: string
  connect: () => void
  disconnect: () => void
  execute: (command: string) => Promise<void>
  confirm: (actionId: string, confirmed: boolean, choice?: string) => Promise<void>
  cancel: () => Promise<void>
  refreshStatus: () => Promise<void>
  loadHistory: () => Promise<void>
  enableVoice: () => Promise<void>
  disableVoice: () => Promise<void>
  reset: () => void
}

let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectAttempts = 0
let voiceWs: WebSocket | null = null

function eventKey(e: AutomationEvent): string {
  return `${e.type}-${e.action_id ?? e.request_id ?? ''}-${e.step_index ?? ''}-${e.timestamp ?? Date.now()}`
}

export const useAutomation = create<AutomationState>((set, get) => ({
  open: false,
  connecting: false,
  connected: false,
  busy: false,
  executing: null,
  events: [],
  pending: null,
  history: [],
  status: null,
  lastError: null,
  voiceEnabled: false,
  voiceStarting: false,
  voiceWsConnected: false,
  voiceListenerState: 'stopped',

  connect: () => {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
    set({ connecting: true, lastError: null })
    void (async () => {
      try {
        const base = await resolveLocalBase()
        const token = localStorage.getItem('access_token') ?? 'hsbot_default_access_token'
        const scheme = base.startsWith('https') ? 'wss' : 'ws'
        const url = `${scheme}://${base.replace(/^https?:\/\//, '').replace(/\/api$/, '')}/api/automation/ws?token=${encodeURIComponent(token)}`
        const socket = new WebSocket(url)
        ws = socket

        socket.onopen = () => {
          reconnectAttempts = 0
          set({ connected: true, connecting: false })
          void get().refreshStatus()
          void get().loadHistory()
        }

        socket.onmessage = (msg) => {
          try {
            const event = JSON.parse(msg.data) as AutomationEvent
            if (event.type === 'connected') return
            const events = [...get().events, { ...event, timestamp: new Date().toISOString() }]
            set({ events: events.slice(-200) })
            if (event.type === 'confirmation_required' && event.action_id) {
              set({
                pending: {
                  action_id: event.action_id,
                  prompt: event.prompt ?? event.explanation ?? 'Confirm this action?',
                  risk: event.risk ?? 'medium',
                  options: event.options,
                },
              })
            }
            if (event.type === 'confirmed') {
              if (!event.confirmed) set({ pending: null })
            }
            if (event.type === 'chain_done' || event.type === 'chain_failed' || event.type === 'cancelled') {
              set({ busy: false, executing: null })
              if (event.type !== 'chain_done') void get().loadHistory()
            }
            if (event.type === 'action_done' || event.type === 'action_start') {
              set({ executing: event.type === 'action_start' ? (event.intent ?? null) : null })
            }
          } catch {
            /* ignore malformed frames */
          }
        }

        socket.onerror = () => {
          set({ connected: false, connecting: false, lastError: 'Could not connect to the automation stream.' })
        }

        socket.onclose = () => {
          set({ connected: false, connecting: false })
          if (reconnectAttempts < 5) {
            reconnectAttempts += 1
            reconnectTimer = setTimeout(() => get().connect(), 3000 * reconnectAttempts)
          }
        }
      } catch {
        set({ connecting: false, lastError: LOCAL_ONLY_MESSAGE })
      }
    })()
  },

  disconnect: () => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = null
    if (ws) {
      ws.onclose = null
      ws.close()
      ws = null
    }
    set({ connected: false, connecting: false })
  },

  execute: async (command: string) => {
    const trimmed = command.trim()
    if (!trimmed || get().busy) return
    set({ busy: true, lastError: null, executing: 'detecting' })
    try {
      const base = await resolveLocalBase()
      const res = await fetch(`${base}/automation/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify({ command: trimmed }),
      })
      if (res.status === 503) {
        const body = await res.json().catch(() => null)
        set({ busy: false, executing: null, lastError: body?.detail ?? 'Automation is only available on the local backend.' })
        return
      }
      if (!res.ok) {
        set({ busy: false, executing: null, lastError: `Command failed (${res.status}).` })
        return
      }
      const data = await res.json()
      if (data.requires_confirmation && data.action_id) {
        set({
          pending: {
            action_id: data.action_id,
            prompt: data.confirmation_prompt ?? data.message,
            risk: 'medium',
            options: data.options ?? undefined,
          },
          busy: false,
          executing: null,
        })
        return
      }
      if (data.success === false) {
        set({ busy: false, executing: null, lastError: data.message })
        if (data.action_id) void get().loadHistory()
        return
      }
      setTimeout(() => {
        set({ busy: false, executing: null })
        void get().loadHistory()
      }, 350)
    } catch {
      set({ busy: false, executing: null, lastError: LOCAL_ONLY_MESSAGE })
    }
  },

  confirm: async (actionId: string, confirmed: boolean, choice?: string) => {
    try {
      const base = await resolveLocalBase()
      const res = await fetch(`${base}/automation/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify({ action_id: actionId, confirmed, choice: choice ?? null }),
      })
      if (!res.ok) {
        set({ lastError: `Confirmation failed (${res.status}).` })
        return
      }
      const data = await res.json()
      set({ pending: null, busy: false, executing: null })
      if (data.success === false) set({ lastError: data.message })
      void get().loadHistory()
    } catch {
      set({ lastError: LOCAL_ONLY_MESSAGE })
    }
  },

  cancel: async () => {
    try {
      const base = await resolveLocalBase()
      await fetch(`${base}/automation/cancel`, {
        method: 'POST',
        headers: { ...getAuthHeader() },
      })
      set({ busy: false, executing: null })
    } catch {
      set({ lastError: LOCAL_ONLY_MESSAGE })
    }
  },

  refreshStatus: async () => {
    try {
      const base = await resolveLocalBase()
      const res = await fetch(`${base}/automation/status`, { headers: { ...getAuthHeader() } })
      if (res.ok) {
        const data = await res.json()
        set({ status: data, lastError: data.automation_available ? null : 'Automation is unavailable here — connect to the local backend.' })
      } else if (res.status === 503) {
        set({ lastError: 'Automation is disabled on the cloud backend. Connect to your local backend (localhost:8000).' })
      }
    } catch {
      set({ lastError: 'Local backend is not reachable.' })
    }
  },

  loadHistory: async () => {
    try {
      const base = await resolveLocalBase()
      const res = await fetch(`${base}/automation/log?limit=50`, { headers: { ...getAuthHeader() } })
      if (res.ok) {
        const data = await res.json()
        set({ history: (data.entries ?? []).slice(-30).reverse() })
      }
    } catch {
      /* silent — history is best-effort */
    }
  },

  enableVoice: async () => {
    if (get().voiceStarting || voiceWs) return
    set({ voiceStarting: true, lastError: null })
    try {
      const base = await resolveLocalBase()
      const startRes = await fetch(`${base}/voice/listener/start`, { method: 'POST', headers: { ...getAuthHeader() } })
      if (!startRes.ok && startRes.status !== 503) {
        set({ voiceStarting: false, lastError: `Could not start the voice listener (${startRes.status}).` })
        return
      }
      const token = localStorage.getItem('access_token') ?? 'hsbot_default_access_token'
      const scheme = base.startsWith('https') ? 'wss' : 'ws'
      const url = `${scheme}://${base.replace(/^https?:\/\//, '').replace(/\/api$/, '')}/api/voice/ws?token=${encodeURIComponent(token)}`
      const socket = new WebSocket(url)
      voiceWs = socket

      socket.onopen = () => set({ voiceWsConnected: true, voiceEnabled: true, voiceStarting: false })
      socket.onmessage = (msg) => {
        try {
          const ev = JSON.parse(msg.data)
          const events = get().events
          let entry: AutomationEvent | null = null
          switch (ev.type) {
            case 'connected':
              set({ voiceListenerState: ev.state ?? 'idle' })
              return
            case 'state_change':
              set({ voiceListenerState: ev.new_state ?? 'idle' })
              return
            case 'wake_word':
              entry = { type: 'voice_wake', message: `Wake word heard — say your command`, timestamp: ev.timestamp }
              break
            case 'command':
              entry = { type: 'voice_command', message: `Heard: ${ev.command_text ?? ''}`, timestamp: ev.timestamp }
              break
            case 'chat_intent': {
              const text = (ev.command_text ?? '').trim()
              entry = { type: 'voice_chat', message: `"${text}" isn't an automation command — sent to chat`, timestamp: ev.timestamp }
              if (text) {
                const chat = useChat.getState()
                if (!chat.streaming) void chat.sendMessage(text)
              }
              break
            }
            case 'execution_result':
              entry = {
                type: 'voice_result',
                message: `${ev.success ? '✓' : '✗'} ${ev.message ?? ''}${ev.requires_confirmation ? ' (needs confirmation)' : ''}`,
                success: ev.success,
                timestamp: ev.timestamp,
              }
              break
            case 'error':
              entry = { type: 'voice_error', message: ev.error ?? 'Voice listener error', timestamp: ev.timestamp }
              break
          }
          if (entry) set({ events: [...events, entry].slice(-200) })
        } catch {
          /* ignore malformed frames */
        }
      }
      socket.onerror = () => {
        set({ voiceWsConnected: false, voiceEnabled: false, voiceStarting: false, lastError: 'Voice stream failed to connect.' })
        voiceWs = null
      }
      socket.onclose = () => {
        set({ voiceWsConnected: false })
        voiceWs = null
      }
    } catch {
      set({ voiceStarting: false, lastError: LOCAL_ONLY_MESSAGE })
    }
  },

  disableVoice: async () => {
    // NOTE: never stop the backend listener — it is always-listening by design.
    // This only disconnects the event stream in this panel.
    if (voiceWs) {
      voiceWs.onclose = null
      voiceWs.close()
      voiceWs = null
    }
    set({ voiceEnabled: false, voiceWsConnected: false, voiceStarting: false, voiceListenerState: 'stopped' })
  },

  reset: () => {
    get().disconnect()
    set({ events: [], pending: null, history: [], status: null, lastError: null, busy: false, executing: null })
  },
}))

export { eventKey }