import type { SlashCommand, CommandExecutionContext } from '@/types/command'
import { useSlashCommandsStore } from '@/stores/slashCommands'

/**
 * Execute selected slash command.
 * Updates recently used history, executes custom command action or populates input prompt template.
 */
export async function executeCommand(
  command: SlashCommand,
  ctx: CommandExecutionContext,
  args: string = '',
  immediateSubmit: boolean = false
): Promise<void> {
  // Add to recently used commands store
  useSlashCommandsStore.getState().addRecentlyUsed(command.id)

  const trimmedArgs = args.trim()

  // 1. Custom action attached to command object
  if (command.action) {
    await command.action(ctx, trimmedArgs)
    return
  }

  // 2. Special built-in command handlers
  if (command.id === 'settings') {
    ctx.setInput('')
    if (ctx.openSettings) {
      ctx.openSettings()
    }
    return
  }

  if (command.id === 'pdf' || command.id === 'ocr') {
    if (!trimmedArgs && ctx.triggerFileUpload) {
      ctx.setInput('')
      ctx.triggerFileUpload()
      return
    }
  }

  // 3. Prompt Template handling
  const template = command.promptTemplate || `${command.command} `

  if (trimmedArgs) {
    const fullText = template.endsWith(' ')
      ? `${template}${trimmedArgs}`
      : `${template} ${trimmedArgs}`

    if (immediateSubmit) {
      ctx.setInput('')
      await ctx.sendMessage(fullText)
    } else {
      ctx.setInput(fullText)
    }
  } else {
    // Just populate the input for the user to continue typing
    ctx.setInput(template)
  }
}
