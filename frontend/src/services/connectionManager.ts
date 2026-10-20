import { api, getBaseUrl } from '@/lib/api'
import type { ConnectionInfo, ConnectionState, ReadinessResponse } from '@/types/connection'

type ConnectionListener = (info: ConnectionInfo) => void

const INITIAL_INTERVAL_MS = 2500
const MAX_INTERVAL_MS = 10000
const BACKOFF_MULTIPLIER = 1.4
const REQUEST_TIMEOUT_MS = 4500
const WAKING_UP_THRESHOLD_MS = 3800
const CONSECUTIVE_FAILURES_FOR_ERROR = 6 // ~20-25 seconds before showing CONNECTION_ERROR

class ConnectionManager {
  private state: ConnectionState = 'INITIALIZING'
  private isReady = false
  private elapsedSeconds = 0
  private attemptCount = 0
  private nextRetrySeconds = 0
  private lastError: string | null = null
  private serverInfo: ReadinessResponse | null = null
  private lastResponseTimeMs = 0
  private consecutiveFailures = 0
  private hasBeenConnectedOnce = false

  private listeners = new Set<ConnectionListener>()
  private pollingTimer: any = null
  private elapsedTimer: any = null
  private countdownTimer: any = null
  private abortController: AbortController | null = null
  private inFlight = false
  private currentIntervalMs = INITIAL_INTERVAL_MS
  private startTime = Date.now()

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', this.handleOnline)
      window.addEventListener('offline', this.handleOffline)
    }
  }

  public init() {
    if (this.state === 'CONNECTED' && this.isReady) {
      return
    }
    this.startElapsedTimer()
    this.checkConnectionImmediate()
  }

  public subscribe(listener: ConnectionListener): () => void {
    this.listeners.add(listener)
    listener(this.getInfo())
    return () => {
      this.listeners.delete(listener)
    }
  }

  public getInfo(): ConnectionInfo {
    return {
      state: this.state,
      isReady: this.isReady,
      backendUrl: getBaseUrl().replace(/\/api$/, ''),
      elapsedSeconds: this.elapsedSeconds,
      attemptCount: this.attemptCount,
      nextRetrySeconds: this.nextRetrySeconds,
      lastError: this.lastError,
      diagnostics: {
        online: typeof navigator !== 'undefined' ? navigator.onLine : true,
        responseTimeMs: this.lastResponseTimeMs,
        serverInfo: this.serverInfo,
      },
    }
  }

  private notify() {
    const info = this.getInfo()
    this.listeners.forEach((listener) => {
      try {
        listener(info)
      } catch (err) {
        console.error('[ConnectionManager] Listener error:', err)
      }
    })
  }

  private setState(newState: ConnectionState) {
    if (this.state !== newState) {
      this.state = newState
      this.notify()
    }
  }

  private startElapsedTimer() {
    if (this.elapsedTimer) return
    this.startTime = Date.now() - (this.elapsedSeconds * 1000)
    this.elapsedTimer = setInterval(() => {
      this.elapsedSeconds = Math.max(0, Math.floor((Date.now() - this.startTime) / 1000))
      this.notify()
    }, 1000)
  }

  private stopElapsedTimer() {
    if (this.elapsedTimer) {
      clearInterval(this.elapsedTimer)
      this.elapsedTimer = null
    }
  }

  private startCountdownTimer(totalMs: number) {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer)
      this.countdownTimer = null
    }
    const targetTime = Date.now() + totalMs
    const updateCountdown = () => {
      const remaining = Math.max(0, Math.ceil((targetTime - Date.now()) / 1000))
      this.nextRetrySeconds = remaining
      this.notify()
      if (remaining <= 0 && this.countdownTimer) {
        clearInterval(this.countdownTimer)
        this.countdownTimer = null
      }
    }
    updateCountdown()
    this.countdownTimer = setInterval(updateCountdown, 500)
  }

  public async retryNow() {
    this.clearTimers()
    this.currentIntervalMs = INITIAL_INTERVAL_MS
    this.consecutiveFailures = 0
    await this.checkConnectionImmediate()
  }

  public checkConnectionImmediate = async () => {
    if (this.inFlight) return
    this.clearTimers()
    await this.executeCheck()
  }

  private async executeCheck() {
    if (this.inFlight) return
    this.inFlight = true
    this.attemptCount++

    // If offline, flag immediately
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      this.lastError = 'Browser is currently offline'
      this.setState(this.hasBeenConnectedOnce ? 'RECONNECTING' : 'CONNECTION_ERROR')
      this.inFlight = false
      this.scheduleNextPoll()
      return
    }

    if (this.state !== 'WAKING_UP' && this.state !== 'RECONNECTING') {
      this.setState(this.hasBeenConnectedOnce ? 'RECONNECTING' : 'CONNECTING')
    }

    this.abortController = new AbortController()
    const checkStartTime = Date.now()

    // Detect server sleeping / waking up if check takes longer than WAKING_UP_THRESHOLD_MS
    const wakingUpTimer = setTimeout(() => {
      if (this.inFlight && this.state !== 'CONNECTED') {
        this.setState('WAKING_UP')
      }
    }, WAKING_UP_THRESHOLD_MS)

    // Request timeout controller
    const timeoutTimer = setTimeout(() => {
      if (this.abortController) {
        this.abortController.abort()
      }
    }, REQUEST_TIMEOUT_MS)

    try {
      // Primary check: readiness endpoint (verifies server + DB + AI services)
      const data = await api.ready(this.abortController.signal)
      clearTimeout(wakingUpTimer)
      clearTimeout(timeoutTimer)

      this.lastResponseTimeMs = Date.now() - checkStartTime
      this.serverInfo = data as ReadinessResponse
      this.lastError = null

      if (data.ready === false || data.status === 'initializing') {
        // Backend HTTP is responding, but dependencies are still initializing
        this.setState('VERIFYING_READINESS')
        this.consecutiveFailures = 0
        this.currentIntervalMs = INITIAL_INTERVAL_MS
        this.inFlight = false
        this.scheduleNextPoll(1500) // check again in 1.5s
        return
      }

      // Backend is fully ready!
      this.setState('VERIFYING_READINESS')
      // Short micro-delay to let UI show verification pulse
      await new Promise((r) => setTimeout(r, 400))

      this.isReady = true
      this.hasBeenConnectedOnce = true
      this.consecutiveFailures = 0
      this.currentIntervalMs = INITIAL_INTERVAL_MS
      this.setState('CONNECTED')

      // Stop polling on success
      this.stopElapsedTimer()
      this.clearTimers()
      this.inFlight = false
      return
    } catch (err: any) {
      clearTimeout(wakingUpTimer)
      clearTimeout(timeoutTimer)
      this.lastResponseTimeMs = Date.now() - checkStartTime

      const isAbort = err?.name === 'AbortError'
      const errorMsg = isAbort ? 'Connection attempt timed out' : (err?.message || 'Failed to connect')
      this.lastError = errorMsg
      this.consecutiveFailures++

      // Categorize state:
      // 502/503/504 or timeouts are strong evidence of a sleeping Render instance waking up
      const isGatewayWake =
        isAbort ||
        errorMsg.includes('502') ||
        errorMsg.includes('503') ||
        errorMsg.includes('504') ||
        errorMsg.includes('waking') ||
        errorMsg.includes('timed out')

      if (this.hasBeenConnectedOnce) {
        this.setState('RECONNECTING')
      } else if (isGatewayWake || this.consecutiveFailures < CONSECUTIVE_FAILURES_FOR_ERROR) {
        this.setState('WAKING_UP')
      } else {
        this.setState('CONNECTION_ERROR')
      }

      this.inFlight = false
      this.scheduleNextPoll()
    }
  }

  private scheduleNextPoll(customDelayMs?: number) {
    if (this.isReady && this.state === 'CONNECTED') {
      return // Stop polling when connected
    }

    // Exponential backoff
    const delay = customDelayMs ?? this.currentIntervalMs
    this.currentIntervalMs = Math.min(
      Math.round(this.currentIntervalMs * BACKOFF_MULTIPLIER),
      MAX_INTERVAL_MS
    )

    this.startCountdownTimer(delay)

    this.pollingTimer = setTimeout(() => {
      this.executeCheck()
    }, delay)
  }

  public reportBackendFailure(error: any) {
    // Called when a chat request in the app fails due to network/server drop
    const msg = error?.message || ''
    // Ignore explicit client 401/403/400 errors
    if (msg.includes('401') || msg.includes('403') || msg.includes('400')) {
      return
    }
    console.warn('[ConnectionManager] Detected backend failure during active session:', error)
    this.isReady = false
    this.lastError = msg || 'Lost connection to backend server'
    this.setState('RECONNECTING')
    this.startElapsedTimer()
    this.checkConnectionImmediate()
  }

  private handleOnline = () => {
    console.log('[ConnectionManager] Browser back online. Resuming checks.')
    this.currentIntervalMs = INITIAL_INTERVAL_MS
    this.checkConnectionImmediate()
  }

  private handleOffline = () => {
    console.log('[ConnectionManager] Browser went offline.')
    this.lastError = 'Network connection offline'
    this.setState(this.hasBeenConnectedOnce ? 'RECONNECTING' : 'CONNECTION_ERROR')
  }

  private clearTimers() {
    if (this.pollingTimer) {
      clearTimeout(this.pollingTimer)
      this.pollingTimer = null
    }
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer)
      this.countdownTimer = null
    }
    if (this.abortController) {
      this.abortController.abort()
      this.abortController = null
    }
  }

  public destroy() {
    this.clearTimers()
    this.stopElapsedTimer()
    this.listeners.clear()
    if (typeof window !== 'undefined') {
      window.removeEventListener('online', this.handleOnline)
      window.removeEventListener('offline', this.handleOffline)
    }
  }
}

export const connectionManager = new ConnectionManager()
