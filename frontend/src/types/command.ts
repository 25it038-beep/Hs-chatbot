import type { ComponentType } from 'react'

export type CommandCategory = 'AI' | 'Programming' | 'Documents' | 'Workspace' | string

export interface CommandExecutionContext {
  input: string
  setInput: (value: string) => void
  sendMessage: (message: string) => void | Promise<void>
  triggerFileUpload?: () => void
  openSettings?: () => void
  navigate?: (path: string) => void
  [key: string]: any
}

export interface SlashCommand {
  id: string
  name: string
  command: string // e.g. "/chat"
  description: string
  icon: string // Lucide icon identifier string
  category: CommandCategory
  aliases?: string[]
  promptTemplate?: string // Optional template inserted or executed
  action?: (ctx: CommandExecutionContext, args?: string) => void | Promise<void>
}

export interface FuzzyMatchResult {
  command: SlashCommand
  score: number
  matchedNameIndices?: number[]
  matchedCommandIndices?: number[]
}
