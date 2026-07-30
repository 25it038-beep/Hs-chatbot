import React, { useRef, useEffect, useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Send, Paperclip, Square, Mic, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatInputProps {
  onSend: (message: string) => void
  onStop: () => void
  onUploadFile?: (file: File) => Promise<void>
  streaming: boolean
  disabled?: boolean
}

export function ChatInput({ onSend, onStop, onUploadFile, streaming, disabled }: ChatInputProps) {
  const [input, setInput] = React.useState('')
  const [uploading, setUploading] = useState(false)
  const [recording, setRecording] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(true)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const recognitionRef = useRef<any>(null)
  const [isFocused, setIsFocused] = useState(false)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
    }
  }, [input])

  const handleSubmit = () => {
    const trimmed = input.trim()
    if (!trimmed || streaming) return
    onSend(trimmed)
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      if (onUploadFile) {
        await onUploadFile(file)
      } else {
        const api = await import('@/lib/api').then(m => m.api)
        const uploadRes: any = await api.uploadFile(file)
        onSend(`[File: ${uploadRes.filename || file.name}]`)
      }
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    setSpeechSupported(!!SpeechRecognition)
  }, [])

  const startRecording = useCallback(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) { setSpeechSupported(false); return }
    const recognition = new SpeechRecognition()
    recognition.continuous = false; recognition.interimResults = false; recognition.lang = 'en-US'
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript
      if (transcript) setInput(prev => prev + transcript)
    }
    recognition.onerror = () => setRecording(false)
    recognition.onend = () => setRecording(false)
    recognitionRef.current = recognition
    recognition.start()
    setRecording(true)
  }, [])

  const stopRecording = useCallback(() => {
    if (recognitionRef.current) { recognitionRef.current.stop(); recognitionRef.current = null }
    setRecording(false)
  }, [])

  const handleMicClick = () => { if (recording) stopRecording(); else startRecording() }

  return (
    <div className="relative border-t border-border/30 bg-gradient-to-t from-background/90 via-background/60 to-transparent pb-2 pt-3 backdrop-blur-sm">
      <div className="max-w-4xl mx-auto px-3 md:px-4">
        <div className={cn(
          'relative flex items-end gap-2 rounded-2xl border px-3 py-2 transition-all duration-200',
          'bg-muted/20 backdrop-blur-md glass-reflection',
          'focus-within:border-ring/30 focus-within:shadow-[0_0_0_1px] focus-within:shadow-ring/20',
          isFocused ? 'border-ring/30 shadow-soft' : 'border-border/40 hover:border-border/60'
        )}>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,.pdf,.txt,.doc,.docx,.csv"
            className="hidden"
            onChange={handleFileSelect}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || streaming}
            className="flex-shrink-0 p-1.5 text-muted-foreground/50 hover:text-foreground hover:bg-muted/60 transition-all rounded-xl disabled:opacity-50"
            title="Attach files"
          >
            {uploading ? <Loader2 size={18} className="animate-spin" /> : <Paperclip size={18} />}
          </button>

          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Message HSBot..."
            rows={1}
            disabled={disabled}
            className={cn(
              'flex-1 bg-transparent resize-none outline-none text-sm py-1.5 leading-relaxed max-h-[200px]',
              'placeholder:text-muted-foreground/40',
              'disabled:opacity-50'
            )}
          />

          <div className="flex items-center gap-1 flex-shrink-0">
            <button
              onClick={handleMicClick}
              disabled={streaming || !speechSupported}
              className={cn(
                'p-1.5 rounded-xl transition-all',
                recording
                  ? 'text-red-500 bg-red-500/10 hover:bg-red-500/20'
                  : 'text-muted-foreground/50 hover:text-foreground hover:bg-muted/60',
                'disabled:opacity-50'
              )}
              title={!speechSupported ? 'Voice input not supported' : recording ? 'Stop recording' : 'Voice input'}
            >
              <Mic size={18} className={recording ? 'animate-pulse' : ''} />
            </button>

            {streaming ? (
              <Button
                onClick={onStop}
                size="icon"
                variant="secondary"
                className="h-9 w-9 rounded-xl bg-destructive/10 text-destructive hover:bg-destructive/20 border-0"
                title="Stop generating"
              >
                <Square size={14} />
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                size="icon"
                className={cn(
                  'h-9 w-9 rounded-xl transition-all',
                  input.trim()
                    ? 'bg-gradient-to-br from-primary to-primary/80 shadow-sm hover:shadow-md'
                    : ''
                )}
                disabled={!input.trim() || disabled}
                title="Send message"
              >
                <Send size={14} />
              </Button>
            )}
          </div>
        </div>
        <p className="text-[10px] text-muted-foreground/25 text-center mt-1.5">
          HSBot can make mistakes. Verify important information.
        </p>
      </div>
    </div>
  )
}
