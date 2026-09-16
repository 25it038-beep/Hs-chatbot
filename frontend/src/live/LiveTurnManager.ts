/**
 * HSBot Live Voice System - Deterministic Live Turn Manager
 * 
 * Enforces strict transitions between conversational states:
 * IDLE -> CONNECTING -> LISTENING -> PROCESSING -> SPEAKING -> IDLE
 * Handles barge-in / interruptions and circuit-breaking.
 */

import { LiveState } from './LiveTypes'
import { LiveLogger } from './LiveLogger'

export interface TurnManagerCallbacks {
  onStateChange: (state: LiveState) => void
  onInterrupt: () => void
  onError: (error: string) => void
}

export class LiveTurnManager {
  private currentState: LiveState = 'IDLE'
  private consecutiveErrors = 0
  private readonly maxErrors = 3
  private callbacks: TurnManagerCallbacks

  constructor(callbacks: TurnManagerCallbacks) {
    this.callbacks = callbacks
  }

  getState(): LiveState {
    return this.currentState
  }

  transitionTo(newState: LiveState, reason?: string) {
    if (this.currentState === newState) return

    // Validate transitions
    const valid = this.isValidTransition(this.currentState, newState)
    if (!valid) {
      LiveLogger.warn(`Invalid state transition attempted: ${this.currentState} -> ${newState}`)
      return
    }

    LiveLogger.info(`State: ${this.currentState} -> ${newState}${reason ? ` (${reason})` : ''}`)
    this.currentState = newState

    if (newState !== 'ERROR') {
      this.consecutiveErrors = 0
    }

    this.callbacks.onStateChange(newState)
  }

  private isValidTransition(from: LiveState, to: LiveState): boolean {
    if (to === 'ERROR' || to === 'IDLE') return true

    switch (from) {
      case 'IDLE':
        return to === 'CONNECTING'
      case 'CONNECTING':
        return to === 'LISTENING'
      case 'LISTENING':
        return to === 'PROCESSING' || to === 'INTERRUPTED'
      case 'PROCESSING':
        return to === 'SPEAKING' || to === 'LISTENING' || to === 'INTERRUPTED'
      case 'SPEAKING':
        return to === 'INTERRUPTED' || to === 'LISTENING' || to === 'PROCESSING'
      case 'INTERRUPTED':
        return to === 'LISTENING' || to === 'PROCESSING'
      case 'ERROR':
        return to === 'CONNECTING'
      default:
        return true
    }
  }

  /**
   * Called when user speech is detected while AI is SPEAKING or PROCESSING
   */
  handleBargeIn() {
    if (this.currentState === 'SPEAKING' || this.currentState === 'PROCESSING') {
      LiveLogger.info('Barge-in detected: User interrupted AI playback')
      this.transitionTo('INTERRUPTED', 'User speech detected')
      this.callbacks.onInterrupt()
      // Immediately transition back to LISTENING to capture user utterance
      setTimeout(() => {
        if (this.currentState === 'INTERRUPTED') {
          this.transitionTo('LISTENING', 'Ready for user input')
        }
      }, 50)
    }
  }

  handleError(errorMessage: string) {
    this.consecutiveErrors++
    LiveLogger.error(`TurnManager encountered error (${this.consecutiveErrors}/${this.maxErrors}): ${errorMessage}`)

    if (this.consecutiveErrors >= this.maxErrors) {
      this.transitionTo('ERROR', `Circuit breaker tripped: ${errorMessage}`)
      this.callbacks.onError(errorMessage)
    } else {
      // Graceful fallback to LISTENING on minor transient error
      this.transitionTo('LISTENING', 'Recovered from transient error')
    }
  }

  reset() {
    this.currentState = 'IDLE'
    this.consecutiveErrors = 0
    this.callbacks.onStateChange('IDLE')
  }
}
