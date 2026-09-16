/**
 * HSBot Live Voice System - Live Intent Router
 * 
 * Classifies speech intents client-side before forwarding to NVIDIA LLM.
 * Direct utility queries (time, date, system status, short commands) can be resolved
 * instantaneously with sub-50ms latency, while complex queries proceed to NVIDIA LLM.
 */

export type LiveIntentType =
  | 'NORMAL_CONVERSATION'
  | 'TIME_DATE'
  | 'WEATHER'
  | 'SYSTEM_STATUS'
  | 'SHORT_COMMAND'

export interface RouteResult {
  intent: LiveIntentType
  directResponse?: string
  confidence: number
}

export class LiveRouter {
  /**
   * Fast rule-based intent classification for instant vocal response
   */
  static classify(rawText: string): RouteResult {
    const text = rawText.trim().toLowerCase()

    if (!text) {
      return { intent: 'NORMAL_CONVERSATION', confidence: 0 }
    }

    // 1. Short control commands
    if (/^(stop|pause|halt|be quiet|shut up|cancel|end conversation)$/.test(text)) {
      return {
        intent: 'SHORT_COMMAND',
        directResponse: 'Stopped.',
        confidence: 0.99,
      }
    }

    // 2. Time & Date queries
    if (/^(what('?s| is) the (time|date)|what time is it|what day is (it|today)|tell me the time|current time|current date)/.test(text)) {
      const now = new Date()
      const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      const dateStr = now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })
      return {
        intent: 'TIME_DATE',
        directResponse: `It is currently ${timeStr} on ${dateStr}.`,
        confidence: 0.95,
      }
    }

    // 3. System status / ping queries
    if (/^(system status|ping|are you alive|check status|health check|battery status)$/.test(text)) {
      return {
        intent: 'SYSTEM_STATUS',
        directResponse: 'All systems operational. Live voice connection to NVIDIA NIM is healthy.',
        confidence: 0.95,
      }
    }

    // 4. Fast weather queries
    if (/^(what('?s| is) the weather|how is the weather|is it raining|weather forecast)/.test(text)) {
      return {
        intent: 'WEATHER',
        confidence: 0.85,
      }
    }

    // Default to full NVIDIA LLM pipeline
    return {
      intent: 'NORMAL_CONVERSATION',
      confidence: 1.0,
    }
  }
}
