import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Send, Paperclip, Square, Mic, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { SlashCommandPalette } from './SlashCommandPalette'
import { commandRegistry } from '@/lib/commandRegistry'
import { fuzzySearch } from '@/lib/fuzzySearch'
import { executeCommand } from '@/lib/commandExecutionHandler'
import type { SlashCommand, CommandExecutionContext } from '@/types/command'

interface ChatInputProps {
  onSend: (message: string) => void
  onStop: () => void
  onUploadFile?: (file: File) => Promise<void>
  onOpenSettings?: () => void
  streaming: boolean
  disabled?: boolean
}

export function ChatInput({
  onSend,
  onStop,
  onUploadFile,
  onOpenSettings,
  streaming,
  disabled,
}: ChatInputProps) {
  const [input, setInput] = useState('')
  const [uploading, setUploading] = useState(false)
  const [recording, setRecording] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(true)
  const [isFocused, setIsFocused] = useState(false)

  // Slash Command Palette State
  const [showPalette, setShowPalette] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)

  const containerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const recognitionRef = useRef<any>(null)

  // Determine query from input
  const slashQuery = useMemo(() => {
    if (!input.startsWith('/')) return null
    const spaceIndex = input.indexOf(' ')
    if (spaceIndex !== -1) return null // Closed once space is typed after command
    return input.slice(1)
  }, [input])

  // Filter commands in real time with fuzzy search
  const filteredCommands = useMemo(() => {
    if (slashQuery === null) return []
    const all = commandRegistry.getAll()
    const matches = fuzzySearch(all, slashQuery)
    return matches.map(m => m.command)
  }, [slashQuery])

  // Open/Close palette based on query state
  useEffect(() => {
    if (slashQuery !== null && filteredCommands.length > 0) {
      setShowPalette(true)
      setActiveIndex(0)
    } else {
      setShowPalette(false)
    }
  }, [slashQuery, filteredCommands.length])

  // Close palette on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowPalette(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

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
    setShowPalette(false)
  }

  const handleSelectCommand = async (command: SlashCommand) => {
    setShowPalette(false)
    const context: CommandExecutionContext = {
      input,
      setInput,
      sendMessage: async (msg: string) => {
        onSend(msg)
      },
      triggerFileUpload: () => {
        fileInputRef.current?.click()
      },
      openSettings: onOpenSettings,
    }

    let args = ''
    if (input.startsWith('/')) {
      const spaceIdx = input.indexOf(' ')
      if (spaceIdx !== -1) {
        args = input.slice(spaceIdx + 1)
      }
    }

    await executeCommand(command, context, args, false)

    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus()
      }
    }, 50)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showPalette && filteredCommands.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIndex(prev => (prev + 1) % filteredCommands.length)
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIndex(prev => (prev - 1 + filteredCommands.length) % filteredCommands.length)
        return
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault()
        const selected = filteredCommands[activeIndex]
        if (selected) {
          handleSelectCommand(selected)
        }
        return
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        setShowPalette(false)
        return
      }
    }

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
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    setSpeechSupported(!!SpeechRecognition)
  }, [])

  const startRecording = useCallback(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      setSpeechSupported(false)
      return
    }
    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'
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
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    setRecording(false)
  }, [])

  const handleMicClick = () => {
    if (recording) stopRecording()
    else startRecording()
  }

  return (
    <div
      ref={containerRef}
      className="relative border-t border-border/30 bg-gradient-to-t from-background/90 via-background/60 to-transparent pb-[calc(0.5rem+env(safe-area-inset-bottom))] pt-2 sm:pt-3 backdrop-blur-sm"
    >
      <div className="max-w-4xl mx-auto px-2 sm:px-3 md:px-4 relative">
        {/* Floating Slash Command Palette */}
        <SlashCommandPalette
          isOpen={showPalette}
          query={slashQuery || ''}
          filteredCommands={filteredCommands}
          activeIndex={activeIndex}
          onSelect={handleSelectCommand}
          onClose={() => setShowPalette(false)}
        />

        <div
          className={cn(
            'relative flex items-end gap-1.5 sm:gap-2 rounded-2xl border px-2.5 sm:px-3 py-1.5 sm:py-2 transition-all duration-200',
            'bg-muted/20 backdrop-blur-md glass-reflection',
            'focus-within:border-ring/30 focus-within:shadow-[0_0_0_1px] focus-within:shadow-ring/20',
            isFocused ? 'border-ring/30 shadow-soft' : 'border-border/40 hover:border-border/60'
          )}
        >
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
            className="flex-shrink-0 p-2 sm:p-1.5 text-muted-foreground/60 hover:text-foreground hover:bg-muted/60 transition-all rounded-xl disabled:opacity-50 touch-target sm:touch-auto flex items-center justify-center"
            title="Attach files"
          >
            {uploading ? <Loader2 size={18} className="animate-spin" /> : <Paperclip size={18} />}
          </button>

          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Type / for commands, or message HSBot..."
            rows={1}
            disabled={disabled}
            aria-expanded={showPalette}
            aria-haspopup="listbox"
            aria-controls="slash-command-palette"
            aria-activedescendant={
              showPalette && filteredCommands[activeIndex]
                ? `slash-cmd-item-${activeIndex}`
                : undefined
            }
            className={cn(
              'flex-1 bg-transparent resize-none outline-none text-xs sm:text-sm py-1.5 leading-relaxed max-h-[200px]',
              'placeholder:text-muted-foreground/40',
              'disabled:opacity-50'
            )}
          />

          <div className="flex items-center gap-1 flex-shrink-0">
            <button
              onClick={handleMicClick}
              disabled={streaming || !speechSupported}
              className={cn(
                'p-2 sm:p-1.5 rounded-xl transition-all flex items-center justify-center',
                recording
                  ? 'text-red-500 bg-red-500/10 hover:bg-red-500/20'
                  : 'text-muted-foreground/60 hover:text-foreground hover:bg-muted/60',
                'disabled:opacity-50'
              )}
              title={
                !speechSupported
                  ? 'Voice input not supported'
                  : recording
                  ? 'Stop recording'
                  : 'Voice input'
              }
            >
              <Mic size={18} className={recording ? 'animate-pulse' : ''} />
            </button>

            {streaming ? (
              <Button
                onClick={onStop}
                size="icon"
                variant="secondary"
                className="h-9 w-9 rounded-xl bg-destructive/10 text-destructive hover:bg-destructive/20 border-0 flex-shrink-0"
                title="Stop generating"
              >
                <Square size={14} />
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                size="icon"
                className={cn(
                  'h-9 w-9 rounded-xl transition-all flex-shrink-0',
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
        <p className="text-[10px] text-muted-foreground/25 text-center mt-1 px-2">
          HSBot can make mistakes. Verify important information.
        </p>
      </div>
    </div>
  )
}
