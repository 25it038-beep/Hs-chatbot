/**
 * HSBot Live Voice System - Live ASR Client Abstraction
 * 
 * Handles client-side tracking of user speech events and NVIDIA ASR transcriptions.
 */

import { LiveTranscriptItem } from './LiveTypes'

export class LiveASR {
  private currentTranscript = ''
  private onTranscriptCallback?: (item: LiveTranscriptItem) => void

  constructor(onTranscript?: (item: LiveTranscriptItem) => void) {
    this.onTranscriptCallback = onTranscript
  }

  handleServerTranscript(text: string, isFinal: boolean) {
    this.currentTranscript = text
    const item: LiveTranscriptItem = {
      id: 'usr_' + Date.now(),
      role: 'user',
      text,
      isFinal,
      timestamp: Date.now(),
    }
    this.onTranscriptCallback?.(item)
  }

  reset() {
    this.currentTranscript = ''
  }

  getCurrent(): string {
    return this.currentTranscript
  }
}
