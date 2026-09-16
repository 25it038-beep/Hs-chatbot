/**
 * HSBot Live Voice System - Live LLM Client Stream Abstraction
 * 
 * Aggregates streaming assistant tokens from NVIDIA LLM.
 */

import { LiveTranscriptItem } from './LiveTypes'

export class LiveLLM {
  private accumulatedText = ''
  private onChunkCallback?: (chunk: string, fullText: string) => void
  private onFinalCallback?: (item: LiveTranscriptItem) => void

  constructor(
    onChunk?: (chunk: string, fullText: string) => void,
    onFinal?: (item: LiveTranscriptItem) => void
  ) {
    this.onChunkCallback = onChunk
    this.onFinalCallback = onFinal
  }

  appendChunk(chunk: string) {
    this.accumulatedText += chunk
    this.onChunkCallback?.(chunk, this.accumulatedText)
  }

  finalize() {
    const text = this.accumulatedText.trim()
    if (!text) return

    const item: LiveTranscriptItem = {
      id: 'ast_' + Date.now(),
      role: 'assistant',
      text,
      isFinal: true,
      timestamp: Date.now(),
    }
    this.onFinalCallback?.(item)
    this.accumulatedText = ''
  }

  reset() {
    this.accumulatedText = ''
  }

  getCurrent(): string {
    return this.accumulatedText
  }
}
