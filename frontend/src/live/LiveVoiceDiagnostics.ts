/**
 * Real-time 14-Metric Telemetry & Diagnostics Tracker for HSBot Live Voice.
 */

import { LiveDiagnosticsData, LiveEngine, LiveState } from './LiveVoiceTypes'

export class LiveVoiceDiagnostics {
  private data: LiveDiagnosticsData = {
    engine: 'cascaded',
    connectionState: 'IDLE',
    wsLatencyMs: 0,
    micActive: false,
    micSampleRate: 16000,
    micInputLevel: -100,
    audioOutputActive: false,
    audioBufferQueueLength: 0,
    asrLatencyMs: 0,
    llmFirstTokenLatencyMs: 0,
    ttsFirstAudioLatencyMs: 0,
    totalTurnLatencyMs: 0,
    packetCount: 0,
  }

  private listeners: Set<(data: LiveDiagnosticsData) => void> = new Set()

  public getSnapshot(): LiveDiagnosticsData {
    return { ...this.data }
  }

  public subscribe(listener: (data: LiveDiagnosticsData) => void): () => void {
    this.listeners.add(listener)
    listener(this.getSnapshot())
    return () => this.listeners.delete(listener)
  }

  public update(partial: Partial<LiveDiagnosticsData>): void {
    this.data = { ...this.data, ...partial }
    this.notify()
  }

  public setEngine(engine: LiveEngine): void {
    this.data.engine = engine
    this.notify()
  }

  public setConnectionState(state: LiveState): void {
    this.data.connectionState = state
    this.notify()
  }

  public setMicState(active: boolean, sampleRate?: number): void {
    this.data.micActive = active
    if (sampleRate) this.data.micSampleRate = sampleRate
    this.notify()
  }

  public setInputLevel(levelDb: number): void {
    this.data.micInputLevel = levelDb
    this.notify()
  }

  public setPlaybackState(active: boolean, queueLength: number): void {
    this.data.audioOutputActive = active
    this.data.audioBufferQueueLength = queueLength
    this.notify()
  }

  public incrementPacketCount(): void {
    this.data.packetCount++
    this.notify()
  }

  public recordTiming(metric: string, valueMs: number): void {
    if (metric === 'asr_latency_ms' || metric === 'asr_ms') {
      this.data.asrLatencyMs = valueMs
    } else if (metric === 'asr_to_llm_first_token_ms' || metric === 'ttft_ms') {
      this.data.llmFirstTokenLatencyMs = valueMs
    } else if (metric === 'llm_first_token_to_tts_first_audio_ms' || metric === 'tts_first_chunk_ms') {
      this.data.ttsFirstAudioLatencyMs = valueMs
    } else if (metric === 'total_latency_ms' || metric === 'total_turn_ms') {
      this.data.totalTurnLatencyMs = valueMs
    }
    this.notify()
  }

  public recordError(code: string, message: string, details?: any): void {
    this.data.lastErrorCode = code
    this.data.lastErrorMessage = message
    this.data.lastErrorDetails = details
    this.notify()
  }

  public clearError(): void {
    this.data.lastErrorCode = undefined
    this.data.lastErrorMessage = undefined
    this.data.lastErrorDetails = undefined
    this.notify()
  }

  private notify(): void {
    const snap = this.getSnapshot()
    this.listeners.forEach((listener) => {
      try {
        listener(snap)
      } catch (err) {
        console.error('[LiveVoiceDiagnostics] Listener error:', err)
      }
    })
  }
}
