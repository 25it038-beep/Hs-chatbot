import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import {
  Send, Paperclip, Square, Mic, MicOff, Volume2, VolumeX, Loader2, X, Pencil,
  Camera, Radio, Check, Sparkles, FileText, Code, Table, Image as ImageIcon,
  Eye, Plus, UploadCloud, Layers
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { SlashCommandPalette } from './SlashCommandPalette'
import { commandRegistry } from '@/lib/commandRegistry'
import { fuzzySearch } from '@/lib/fuzzySearch'
import { executeCommand } from '@/lib/commandExecutionHandler'
import { useAmbient } from '@/stores/ambient'
import { useVoiceStore } from '@/lib/speech'
import { inspectFileLocally, ParsedFileMetadata, getFileCategoryBadgeStyle } from '@/lib/fileEngine'
import { FileEngineModal } from './FileEngineModal'
import { formatBytes } from '@/lib/downloader'
import type { SlashCommand, CommandExecutionContext } from '@/types/command'

interface ChatInputProps {
  onSend: (message: string) => void
  onSendWithFile?: (file: File, prompt: string) => Promise<void>
  onSendWithFiles?: (files: File[], prompt: string) => Promise<void>
  onStop: () => void
  onOpenSettings?: () => void
  streaming: boolean
  disabled?: boolean
  variant?: 'default' | 'hero'
  editing?: { id: string; content: string } | null
  onEditSubmit?: (messageId: string, content: string) => void
  onCancelEdit?: () => void
  onStartLive?: () => void
}

export function ChatInput({
  onSend,
  onSendWithFile,
  onSendWithFiles,
  onStop,
  onOpenSettings,
  streaming,
  disabled,
  variant = 'default',
  editing,
  onEditSubmit,
  onCancelEdit,
  onStartLive,
}: ChatInputProps) {
  const [input, setInput] = useState('')
  const [pendingFiles, setPendingFiles] = useState<ParsedFileMetadata[]>([])
  const [inspectingFile, setInspectingFile] = useState<ParsedFileMetadata | null>(null)
  const [fileModalOpen, setFileModalOpen] = useState(false)
  const [isDraggingOver, setIsDraggingOver] = useState(false)
  const [sending, setSending] = useState(false)
  const [isFocused, setIsFocused] = useState(false)
  const { setUserTyping } = useAmbient()

  // Slash Command Palette State
  const [showPalette, setShowPalette] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)

  const containerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const isHero = variant === 'hero'
  const isEditing = Boolean(editing)

  // Load edited message content into composer
  useEffect(() => {
    if (!editing) return
    setInput(editing.content)
    setShowPalette(false)
    setTimeout(() => textareaRef.current?.focus(), 0)
  }, [editing?.id, editing?.content])

  // Determine query from input
  const slashQuery = useMemo(() => {
    if (!input.startsWith('/')) return null
    const spaceIndex = input.indexOf(' ')
    if (spaceIndex !== -1) return null
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

  const handleAddFiles = async (files: FileList | File[]) => {
    const fileArray = Array.from(files)
    if (fileArray.length === 0) return
    try {
      const inspected = await Promise.all(fileArray.map(f => inspectFileLocally(f)))
      setPendingFiles(prev => [...prev, ...inspected])
    } catch (err) {
      console.warn('[FileEngine] Error inspecting files:', err)
    }
  }

  const handleRemoveFile = (id: string) => {
    setPendingFiles(prev => prev.filter(f => f.id !== id))
  }

  const handleOpenInspector = (fileMeta: ParsedFileMetadata) => {
    setInspectingFile(fileMeta)
    setFileModalOpen(true)
  }

  const handleSubmit = () => {
    const trimmed = input.trim()
    if (editing) {
      if (!trimmed || sending) return
      onEditSubmit?.(editing.id, trimmed)
      setInput('')
      setUserTyping(false)
      setShowPalette(false)
      return
    }
    if (streaming || sending) return
    if (!trimmed && pendingFiles.length === 0) return

    if (pendingFiles.length > 0) {
      const rawFiles = pendingFiles.map(f => f.file)
      setSending(true)
      const sendPromise = onSendWithFiles
        ? onSendWithFiles(rawFiles, trimmed)
        : onSendWithFile
          ? onSendWithFile(rawFiles[0], trimmed)
          : Promise.resolve()

      sendPromise
        .finally(() => {
          setSending(false)
          setPendingFiles([])
        })
        .catch(() => {})

      setInput('')
      setUserTyping(false)
      setShowPalette(false)
      return
    }

    if (!trimmed) return
    onSend(trimmed)
    setInput('')
    setUserTyping(false)
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

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleAddFiles(e.target.files)
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleScreenshot = async () => {
    if (!navigator.mediaDevices?.getDisplayMedia) {
      return
    }
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true })
      const track = stream.getVideoTracks()[0]
      const imageCapture = new (window as any).ImageCapture(track)
      const bitmap = await imageCapture.grabFrame()
      const canvas = document.createElement('canvas')
      canvas.width = bitmap.width
      canvas.height = bitmap.height
      const ctx = canvas.getContext('2d')
      ctx?.drawImage(bitmap, 0, 0)
      track.stop()
      canvas.toBlob(async (blob) => {
        if (!blob) return
        const file = new File([blob], `screenshot-${Date.now()}.png`, { type: 'image/png' })
        await handleAddFiles([file])
      }, 'image/png')
    } catch (err) {
      console.warn('Screenshot canceled or failed', err)
    }
  }

  const {
    isListening,
    startListening,
    stopListening,
    recognitionSupported,
    interimTranscript,
    recognitionError,
    autoSpeak,
    setAutoSpeak,
  } = useVoiceStore()

  const handleMicClick = () => {
    if (isListening) {
      stopListening()
      return
    }

    if (!recognitionSupported) {
      if (onStartLive) {
        onStartLive()
      }
      return
    }

    const started = startListening((transcript, isFinal) => {
      if (isFinal && transcript.trim()) {
        setInput((prev) => {
          const trimmed = prev.trim()
          return trimmed ? `${trimmed} ${transcript.trim()}` : transcript.trim()
        })
        setUserTyping(true)
      }
    })

    if (!started && onStartLive) {
      onStartLive()
    }
  }

  const canSubmit = Boolean(input.trim() || pendingFiles.length > 0)

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDraggingOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDraggingOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDraggingOver(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleAddFiles(e.dataTransfer.files)
    }
  }

  const activeSuggestions = useMemo(() => {
    if (pendingFiles.length === 0) return []
    return pendingFiles[0].suggestedPrompts.slice(0, 3)
  }, [pendingFiles])

  return (
    <div
      ref={containerRef}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        'relative transition-all',
        !isHero &&
          'border-t border-border bg-background pb-[calc(0.5rem+env(safe-area-inset-bottom))] pt-3 backdrop-blur-sm',
      )}
    >
      <div className={cn('relative', isHero ? 'w-full' : 'max-w-3xl mx-auto px-3 sm:px-4 md:px-6')}>
        {/* Floating Slash Command Palette */}
        <SlashCommandPalette
          isOpen={showPalette}
          query={slashQuery || ''}
          filteredCommands={filteredCommands}
          activeIndex={activeIndex}
          onSelect={handleSelectCommand}
          onClose={() => setShowPalette(false)}
        />

        {/* Drag Overlay */}
        {isDraggingOver && (
          <div className="absolute inset-0 z-30 rounded-2xl border-2 border-dashed border-primary bg-primary/10 backdrop-blur-xs flex items-center justify-center pointer-events-none animate-fade-in">
            <div className="flex items-center gap-2 text-sm font-semibold text-primary">
              <UploadCloud size={18} className="animate-bounce" />
              <span>Drop files here to load into File Engine</span>
            </div>
          </div>
        )}

        {isEditing && (
          <div className="flex items-center justify-between gap-2 px-1 pb-1.5 animate-fade-in">
            <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <Pencil size={11} className="text-brand" />
              Editing message
            </span>
            <button
              onClick={onCancelEdit}
              className="text-[11px] font-medium text-muted-foreground/70 hover:text-foreground hover:bg-muted rounded-md px-2 py-1 transition-all"
              aria-label="Cancel editing"
            >
              Cancel
            </button>
          </div>
        )}

        {/* Active File Engine Shelf */}
        {pendingFiles.length > 0 && (
          <div className="mb-2 p-2.5 rounded-xl border border-border bg-muted/30 backdrop-blur-sm space-y-2 animate-fade-in">
            <div className="flex items-center justify-between gap-2 px-1">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                <Sparkles size={13} className="text-brand" />
                <span>File Engine ({pendingFiles.length} {pendingFiles.length === 1 ? 'file' : 'files'} loaded)</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-1 text-[11px] text-primary hover:underline font-medium"
                >
                  <Plus size={11} />
                  <span>Add More</span>
                </button>
                <button
                  type="button"
                  onClick={() => setPendingFiles([])}
                  className="text-[11px] text-muted-foreground hover:text-destructive transition-colors"
                >
                  Clear
                </button>
              </div>
            </div>

            {/* File Chips */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
              {pendingFiles.map((fileMeta) => {
                const badge = getFileCategoryBadgeStyle(fileMeta.category)
                return (
                  <div
                    key={fileMeta.id}
                    className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-card border border-border text-xs flex-shrink-0 shadow-2xs hover:border-foreground/20 transition-all"
                  >
                    <span className={`text-[10px] font-bold border px-1.5 py-0.5 rounded-md ${badge.badgeClass}`}>
                      {fileMeta.extension.toUpperCase() || 'FILE'}
                    </span>
                    <span className="font-medium text-foreground truncate max-w-[130px] sm:max-w-[180px]">
                      {fileMeta.name}
                    </span>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      {formatBytes(fileMeta.size)}
                    </span>
                    {fileMeta.estimatedTokens && (
                      <span className="text-[10px] text-muted-foreground/80 font-mono hidden sm:inline">
                        ~{fileMeta.estimatedTokens} tok
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => handleOpenInspector(fileMeta)}
                      className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted"
                      title="Inspect in File Engine"
                      aria-label="Inspect file"
                    >
                      <Eye size={12} />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRemoveFile(fileMeta.id)}
                      className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                      title="Remove file"
                      aria-label="Remove file"
                    >
                      <X size={12} />
                    </button>
                  </div>
                )
              })}
            </div>

            {/* Quick Prompt Suggestions */}
            {activeSuggestions.length > 0 && (
              <div className="flex items-center gap-1.5 overflow-x-auto pt-1 scrollbar-none">
                <span className="text-[10px] font-medium text-muted-foreground flex-shrink-0 flex items-center gap-1">
                  <Sparkles size={10} className="text-brand" />
                  Quick:
                </span>
                {activeSuggestions.map((promptText, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => {
                      setInput(promptText)
                      setTimeout(() => textareaRef.current?.focus(), 50)
                    }}
                    className="px-2.5 py-1 rounded-full border border-border/80 bg-card hover:bg-muted text-[11px] text-muted-foreground hover:text-foreground transition-all flex-shrink-0"
                  >
                    {promptText}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <div
          className={cn(
            'relative flex items-end gap-1.5 rounded-2xl border transition-all duration-200 bg-card',
            isHero ? 'px-3 py-2.5 sm:px-4 sm:py-3 shadow-soft' : 'px-2.5 py-1.5 sm:px-3 sm:py-2 shadow-soft',
            isFocused || isEditing
              ? 'border-foreground/25 shadow-elevated'
              : 'border-border hover:border-foreground/20',
          )}
        >
          {isListening && (
            <div className="absolute left-2.5 right-2.5 -top-12 flex items-center justify-between gap-2 rounded-xl border border-red-500/30 bg-card/95 backdrop-blur-md shadow-elevated px-3 py-2 animate-fade-in z-20">
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <span className="relative flex h-2.5 w-2.5 flex-shrink-0">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
                </span>
                <span className="text-xs font-medium text-foreground truncate">
                  {interimTranscript ? (
                    <span className="text-foreground italic">"{interimTranscript}"</span>
                  ) : (
                    <span className="text-muted-foreground">Listening... Speak your prompt</span>
                  )}
                </span>
              </div>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <button
                  type="button"
                  onClick={() => stopListening()}
                  className="px-2 py-1 rounded-md text-[11px] font-medium bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-all"
                >
                  Done
                </button>
                {input.trim() && (
                  <button
                    type="button"
                    onClick={() => {
                      stopListening()
                      handleSubmit()
                    }}
                    className="px-2 py-1 rounded-md text-[11px] font-medium bg-primary text-primary-foreground hover:opacity-90 transition-all"
                  >
                    Send
                  </button>
                )}
              </div>
            </div>
          )}

          {recognitionError && !isListening && (
            <div className="absolute left-2.5 right-2.5 -top-10 flex items-center justify-between gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[11px] text-amber-600 dark:text-amber-400 animate-fade-in z-20">
              <span className="truncate">{recognitionError}</span>
              <button
                type="button"
                onClick={() => useVoiceStore.setState({ recognitionError: null })}
                className="p-0.5 hover:opacity-75"
              >
                <X size={12} />
              </button>
            </div>
          )}

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="*/*"
            className="hidden"
            onChange={handleFileSelect}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={sending || streaming || isEditing}
            className="flex-shrink-0 p-2 text-muted-foreground/60 hover:text-foreground hover:bg-muted transition-all rounded-lg disabled:opacity-40 disabled:pointer-events-none touch-target sm:touch-auto flex items-center justify-center group"
            title={isEditing ? 'Attach is disabled while editing' : 'Attach files (PDF, Code, Data, Images, Text • Drag & Drop)'}
            aria-label="Attach files to File Engine"
          >
            {sending ? (
              <Loader2 size={17} className="animate-spin" />
            ) : (
              <div className="relative">
                <Paperclip size={17} className="group-hover:scale-105 transition-transform" />
                {pendingFiles.length > 0 && (
                  <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-primary" />
                )}
              </div>
            )}
          </button>

          <button
            onClick={handleScreenshot}
            disabled={sending || streaming || isEditing}
            className="flex-shrink-0 p-2 text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-all rounded-lg disabled:opacity-40 disabled:pointer-events-none touch-target sm:touch-auto flex items-center justify-center"
            title="Capture screen into File Engine"
            aria-label="Capture screen"
          >
            <Camera size={17} />
          </button>

          <textarea
            ref={textareaRef}
            id="hs-command-input"
            value={input}
            onChange={e => {
              const value = e.target.value
              setInput(value)
              setUserTyping(value.trim().length > 0)
            }}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={
              isEditing
                ? 'Edit your message...'
                : pendingFiles.length > 0
                  ? `Ask HSBot about ${pendingFiles.length === 1 ? pendingFiles[0].name : `${pendingFiles.length} files`}...`
                  : 'Type / for commands, drag files, or message HSBot...'
            }
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
              'flex-1 bg-transparent resize-none outline-none py-1.5 leading-relaxed max-h-[200px] placeholder:text-muted-foreground/40 disabled:opacity-50',
              isHero ? 'text-sm sm:text-[15px]' : 'text-xs sm:text-sm',
            )}
          />

          <div className="flex items-center gap-1 flex-shrink-0">
            {onStartLive && !isEditing && (
              <button
                type="button"
                onClick={onStartLive}
                disabled={streaming}
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all',
                  'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 active:scale-95 border border-emerald-500/20',
                  'disabled:opacity-40 disabled:pointer-events-none'
                )}
                title="Start continuous real-time voice conversation"
                aria-label="Start continuous real-time voice conversation"
              >
                <Radio size={13} className="animate-pulse text-emerald-500" />
                <span className="hidden sm:inline">Live</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleMicClick}
              disabled={streaming || isEditing}
              className={cn(
                'p-2 rounded-lg transition-all flex items-center justify-center relative',
                isListening
                  ? 'bg-red-500/15 text-red-500 ring-2 ring-red-500/30 animate-pulse'
                  : 'text-muted-foreground/50 hover:text-foreground hover:bg-muted',
                'disabled:opacity-40 disabled:pointer-events-none'
              )}
              title={isListening ? 'Stop listening' : 'Voice input (Speak to HSBot)'}
              aria-label={isListening ? 'Stop listening' : 'Voice input (Speak to HSBot)'}
            >
              {isListening ? <MicOff size={17} className="text-red-500" /> : <Mic size={17} />}
            </button>

            <button
              type="button"
              onClick={() => setAutoSpeak(!autoSpeak)}
              className={cn(
                'p-2 rounded-lg transition-all flex items-center justify-center',
                autoSpeak
                  ? 'text-primary bg-primary/10 hover:bg-primary/20'
                  : 'text-muted-foreground/40 hover:text-muted-foreground hover:bg-muted/50'
              )}
              title={
                autoSpeak
                  ? 'Auto-speak replies: ON (HSBot will read answers aloud)'
                  : 'Auto-speak replies: OFF (Click to have HSBot speak answers back)'
              }
              aria-label={autoSpeak ? 'Auto-speak replies: ON' : 'Auto-speak replies: OFF'}
            >
              {autoSpeak ? <Volume2 size={17} className="text-primary" /> : <VolumeX size={17} />}
            </button>

            {streaming && !isEditing ? (
              <Button
                onClick={onStop}
                size="icon"
                variant="secondary"
                className={cn(
                  'rounded-lg bg-destructive/10 text-destructive hover:bg-destructive/20 border-0 flex-shrink-0',
                  isHero ? 'h-9 w-9' : 'h-8 w-8',
                )}
                title="Stop generating"
                aria-label="Stop generating"
              >
                <Square size={13} />
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                size="icon"
                className={cn(
                  'rounded-lg bg-primary text-primary-foreground transition-all flex-shrink-0 hover:opacity-90 active:scale-[0.97]',
                  isHero ? 'h-9 w-9' : 'h-8 w-8',
                  !canSubmit && 'opacity-40 pointer-events-none',
                )}
                disabled={!canSubmit || disabled || sending}
                title={isEditing ? 'Send edited message' : 'Send message'}
                aria-label={isEditing ? 'Send edited message' : 'Send message'}
              >
                <Send size={14} />
              </Button>
            )}
          </div>
        </div>
        {!isHero && (
          <p className="text-[10px] text-muted-foreground/40 text-center mt-1.5 px-2">
            HSBot can make mistakes. Verify important information.
          </p>
        )}
      </div>

      <FileEngineModal
        fileMeta={inspectingFile}
        open={fileModalOpen}
        onOpenChange={setFileModalOpen}
        onApplyPrompt={(prompt) => {
          setInput(prompt)
          setTimeout(() => textareaRef.current?.focus(), 50)
        }}
      />
    </div>
  )
}