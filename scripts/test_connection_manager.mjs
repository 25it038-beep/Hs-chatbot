import { test, describe, beforeEach, afterEach } from 'node:test'
import assert from 'node:assert/strict'

// Create an isolated, controllable test harness for ConnectionManager logic
function createTestConnectionManager({ mockFetch, initialOnline = true }) {
  let isOnline = initialOnline
  let state = 'INITIALIZING'
  let isReady = false
  let elapsedSeconds = 0
  let attemptCount = 0
  let nextRetrySeconds = 0
  let lastError = null
  let serverInfo = null
  let consecutiveFailures = 0
  let hasBeenConnectedOnce = false
  let inFlight = false
  let currentIntervalMs = 2500
  const INITIAL_INTERVAL_MS = 2500
  const MAX_INTERVAL_MS = 10000
  const BACKOFF_MULTIPLIER = 1.4
  const CONSECUTIVE_FAILURES_FOR_ERROR = 4

  const stateHistory = [state]
  const listeners = new Set()

  function getInfo() {
    return {
      state,
      isReady,
      elapsedSeconds,
      attemptCount,
      nextRetrySeconds,
      lastError,
      diagnostics: { online: isOnline, serverInfo },
    }
  }

  function notify() {
    stateHistory.push(state)
    listeners.forEach((l) => l(getInfo()))
  }

  function setState(newState) {
    if (state !== newState) {
      state = newState
      notify()
    }
  }

  async function checkConnectionImmediate() {
    if (inFlight) return
    inFlight = true
    attemptCount++

    if (!isOnline) {
      lastError = 'Browser is currently offline'
      setState(hasBeenConnectedOnce ? 'RECONNECTING' : 'CONNECTION_ERROR')
      inFlight = false
      return
    }

    if (state !== 'WAKING_UP' && state !== 'RECONNECTING') {
      setState(hasBeenConnectedOnce ? 'RECONNECTING' : 'CONNECTING')
    }

    try {
      const data = await mockFetch()
      lastError = null
      serverInfo = data

      if (data.ready === false || data.status === 'initializing') {
        setState('VERIFYING_READINESS')
        consecutiveFailures = 0
        currentIntervalMs = INITIAL_INTERVAL_MS
        inFlight = false
        return
      }

      setState('VERIFYING_READINESS')
      isReady = true
      hasBeenConnectedOnce = true
      consecutiveFailures = 0
      currentIntervalMs = INITIAL_INTERVAL_MS
      setState('CONNECTED')
      inFlight = false
      return
    } catch (err) {
      const errorMsg = err.message || 'Failed to connect'
      lastError = errorMsg
      consecutiveFailures++

      const isGatewayWake =
        errorMsg.includes('502') ||
        errorMsg.includes('503') ||
        errorMsg.includes('504') ||
        errorMsg.includes('waking') ||
        errorMsg.includes('timed out')

      if (hasBeenConnectedOnce) {
        setState('RECONNECTING')
      } else if (isGatewayWake || consecutiveFailures < CONSECUTIVE_FAILURES_FOR_ERROR) {
        setState('WAKING_UP')
      } else {
        setState('CONNECTION_ERROR')
      }

      // Backoff calculation
      currentIntervalMs = Math.min(
        Math.round(currentIntervalMs * BACKOFF_MULTIPLIER),
        MAX_INTERVAL_MS
      )
      inFlight = false
    }
  }

  function reportBackendFailure(error) {
    const msg = error?.message || ''
    if (msg.includes('401') || msg.includes('403')) return
    isReady = false
    lastError = msg || 'Lost connection'
    setState('RECONNECTING')
  }

  async function retryNow() {
    currentIntervalMs = INITIAL_INTERVAL_MS
    consecutiveFailures = 0
    await checkConnectionImmediate()
  }

  function setOnline(online) {
    isOnline = online
    if (!online) {
      lastError = 'Network connection offline'
      setState(hasBeenConnectedOnce ? 'RECONNECTING' : 'CONNECTION_ERROR')
    }
  }

  return {
    getInfo,
    getState: () => state,
    getStateHistory: () => stateHistory,
    getCurrentInterval: () => currentIntervalMs,
    getConsecutiveFailures: () => consecutiveFailures,
    checkConnectionImmediate,
    reportBackendFailure,
    retryNow,
    setOnline,
    subscribe: (fn) => {
      listeners.add(fn)
      return () => listeners.delete(fn)
    },
  }
}

describe('ConnectionManager Scenarios', () => {
  test('Scenario A: Backend is already ready -> Transitions to CONNECTED immediately', async () => {
    const cm = createTestConnectionManager({
      mockFetch: async () => ({ status: 'ready', ready: true, database: 'connected' }),
    })

    assert.equal(cm.getState(), 'INITIALIZING')
    await cm.checkConnectionImmediate()

    assert.equal(cm.getState(), 'CONNECTED')
    assert.equal(cm.getInfo().isReady, true)
    assert.deepEqual(cm.getStateHistory(), [
      'INITIALIZING',
      'CONNECTING',
      'VERIFYING_READINESS',
      'CONNECTED',
    ])
  })

  test('Scenario B: Backend takes time (502 / cold start) -> WAKING_UP -> CONNECTED', async () => {
    let callCount = 0
    const cm = createTestConnectionManager({
      mockFetch: async () => {
        callCount++
        if (callCount < 3) {
          throw new Error('502 Bad Gateway - Render instance starting')
        }
        return { status: 'ready', ready: true, database: 'connected' }
      },
    })

    // Attempt 1: 502 error
    await cm.checkConnectionImmediate()
    assert.equal(cm.getState(), 'WAKING_UP')
    assert.equal(cm.getInfo().isReady, false)

    // Attempt 2: 502 error
    await cm.checkConnectionImmediate()
    assert.equal(cm.getState(), 'WAKING_UP')

    // Attempt 3: server wakes up
    await cm.checkConnectionImmediate()
    assert.equal(cm.getState(), 'CONNECTED')
    assert.equal(cm.getInfo().isReady, true)
    assert.equal(cm.getInfo().attemptCount, 3)
  })

  test('Scenario C: Prolonged backend outage -> CONNECTION_ERROR and RetryNow reset', async () => {
    const cm = createTestConnectionManager({
      mockFetch: async () => {
        throw new Error('Connection refused')
      },
    })

    for (let i = 0; i < 4; i++) {
      await cm.checkConnectionImmediate()
    }
    assert.equal(cm.getState(), 'CONNECTION_ERROR')
    assert.ok(cm.getCurrentInterval() > 2500)

    // Manual retry
    let retried = false
    const cmRetry = createTestConnectionManager({
      mockFetch: async () => {
        retried = true
        return { status: 'ready', ready: true }
      },
    })
    // Simulate initial failure
    cmRetry.setOnline(false)
    assert.equal(cmRetry.getState(), 'CONNECTION_ERROR')
    cmRetry.setOnline(true)
    await cmRetry.retryNow()
    assert.equal(cmRetry.getCurrentInterval(), 2500)
    assert.equal(retried, true)
  })

  test('Scenario D: Offline status detection -> immediate state change without network probe', async () => {
    let fetchCalled = false
    const cm = createTestConnectionManager({
      mockFetch: async () => {
        fetchCalled = true
        return { status: 'ready' }
      },
      initialOnline: false,
    })

    await cm.checkConnectionImmediate()
    assert.equal(fetchCalled, false)
    assert.equal(cm.getState(), 'CONNECTION_ERROR')
    assert.equal(cm.getInfo().diagnostics.online, false)
  })

  test('Scenario E: Backend disconnects during active session -> RECONNECTING -> RECOVERY', async () => {
    let shouldFail = false
    const cm = createTestConnectionManager({
      mockFetch: async () => {
        if (shouldFail) throw new Error('504 Gateway Timeout')
        return { status: 'ready', ready: true }
      },
    })

    // Step 1: Initial successful connection
    await cm.checkConnectionImmediate()
    assert.equal(cm.getState(), 'CONNECTED')

    // Step 2: Connection drop reported during chat
    cm.reportBackendFailure(new Error('Network request failed'))
    assert.equal(cm.getState(), 'RECONNECTING')
    assert.equal(cm.getInfo().isReady, false)

    // Step 3: Server recovers
    await cm.checkConnectionImmediate()
    assert.equal(cm.getState(), 'CONNECTED')
    assert.equal(cm.getInfo().isReady, true)
  })

  test('Scenario F: Auth 401 error is NOT treated as a backend outage', async () => {
    const cm = createTestConnectionManager({
      mockFetch: async () => ({ status: 'ready', ready: true }),
    })
    await cm.checkConnectionImmediate()
    assert.equal(cm.getState(), 'CONNECTED')

    // 401 error during chat should not trigger RECONNECTING
    cm.reportBackendFailure(new Error('HTTP 401: Unauthorized'))
    assert.equal(cm.getState(), 'CONNECTED')
  })

  test('Scenario G: Exponential backoff increases retry interval up to maximum cap', async () => {
    const cm = createTestConnectionManager({
      mockFetch: async () => {
        throw new Error('Timeout')
      },
    })

    const intervals = []
    for (let i = 0; i < 8; i++) {
      await cm.checkConnectionImmediate()
      intervals.push(cm.getCurrentInterval())
    }

    // Verify progression is monotonic and bounded by 10000ms
    assert.ok(intervals[1] > intervals[0])
    assert.ok(intervals[intervals.length - 1] <= 10000)
    assert.equal(intervals[intervals.length - 1], 10000)
  })
})
