import type { SlashCommand, CommandCategory } from '@/types/command'

class CommandRegistry {
  private commands: Map<string, SlashCommand> = new Map()

  constructor() {
    this.registerDefaults()
  }

  /**
   * Register a new command object without modifying UI code.
   */
  public register(command: SlashCommand): void {
    const normalizedId = command.id || command.command.replace(/^\//, '')
    this.commands.set(normalizedId, {
      ...command,
      id: normalizedId,
      command: command.command.startsWith('/') ? command.command : `/${command.command}`,
    })
  }

  /**
   * Unregister a command by ID or trigger
   */
  public unregister(idOrTrigger: string): void {
    const cleanId = idOrTrigger.replace(/^\//, '')
    this.commands.delete(cleanId)
  }

  /**
   * Retrieve all registered commands
   */
  public getAll(): SlashCommand[] {
    return Array.from(this.commands.values())
  }

  /**
   * Get commands grouped by category
   */
  public getGrouped(): Record<CommandCategory, SlashCommand[]> {
    const grouped: Record<string, SlashCommand[]> = {}
    for (const cmd of this.commands.values()) {
      if (!grouped[cmd.category]) {
        grouped[cmd.category] = []
      }
      grouped[cmd.category].push(cmd)
    }
    return grouped
  }

  /**
   * Find command by command trigger (e.g. "/chat") or alias
   */
  public findByTrigger(trigger: string): SlashCommand | undefined {
    const clean = trigger.trim().toLowerCase()
    for (const cmd of this.commands.values()) {
      if (cmd.command.toLowerCase() === clean) return cmd
      if (cmd.aliases?.some(a => a.toLowerCase() === clean)) return cmd
    }
    return undefined
  }

  /**
   * Register initial default commands across all categories
   */
  private registerDefaults(): void {
    const defaults: SlashCommand[] = [
      // AI Category
      {
        id: 'chat',
        name: 'Chat AI',
        command: '/chat',
        description: 'Start a clean conversation with selected AI model',
        icon: 'MessageSquare',
        category: 'AI',
        aliases: ['/talk', '/ask'],
        promptTemplate: 'Let\'s discuss: ',
      },
      {
        id: 'image',
        name: 'Generate Image',
        command: '/image',
        description: 'Create high quality AI graphics and illustrations',
        icon: 'Image',
        category: 'AI',
        aliases: ['/draw', '/img', '/generate-image'],
        promptTemplate: 'Generate an image of: ',
      },
      {
        id: 'edit-image',
        name: 'Edit Image',
        command: '/edit-image',
        description: 'Modify or iterate on an existing image or prompt',
        icon: 'Wand2',
        category: 'AI',
        aliases: ['/image-edit', '/modify-image'],
        promptTemplate: 'Edit image with instructions: ',
      },
      {
        id: 'analyze',
        name: 'Deep Analysis',
        command: '/analyze',
        description: 'Analyze documents, data, or complex code snippets',
        icon: 'Brain',
        category: 'AI',
        aliases: ['/eval', '/inspect'],
        promptTemplate: 'Please perform a deep analysis on the following: ',
      },
      {
        id: 'summarize',
        name: 'Summarize',
        command: '/summarize',
        description: 'Summarize lengthy text, articles, or transcripts',
        icon: 'FileText',
        category: 'AI',
        aliases: ['/tldr', '/summary'],
        promptTemplate: 'Summarize the following content in concise bullet points: ',
      },
      {
        id: 'translate',
        name: 'Translate',
        command: '/translate',
        description: 'Translate text into any target language',
        icon: 'Languages',
        category: 'AI',
        aliases: ['/lang', '/tr'],
        promptTemplate: 'Translate the following text into [Language]: ',
      },
      {
        id: 'research',
        name: 'Research Topic',
        command: '/research',
        description: 'In-depth multi-faceted research and synthesis',
        icon: 'Search',
        category: 'AI',
        aliases: ['/investigate', '/study'],
        promptTemplate: 'Conduct thorough research on: ',
      },

      // Programming Category
      {
        id: 'code',
        name: 'Generate Code',
        command: '/code',
        description: 'Write production-ready, clean, well-tested code',
        icon: 'Code',
        category: 'Programming',
        aliases: ['/program', '/dev'],
        promptTemplate: 'Write code for: ',
      },
      {
        id: 'debug',
        name: 'Debug & Fix',
        command: '/debug',
        description: 'Identify errors, trace bugs, and suggest fixes',
        icon: 'Bug',
        category: 'Programming',
        aliases: ['/fix', '/trace'],
        promptTemplate: 'Help me debug this issue: ',
      },
      {
        id: 'review',
        name: 'Code Review',
        command: '/review',
        description: 'Perform security, performance, and style code review',
        icon: 'ShieldCheck',
        category: 'Programming',
        aliases: ['/audit', '/check'],
        promptTemplate: 'Review the following code for best practices and security: ',
      },
      {
        id: 'explain',
        name: 'Explain Code',
        command: '/explain',
        description: 'Break down complex code line-by-line',
        icon: 'HelpCircle',
        category: 'Programming',
        aliases: ['/how-it-works', '/walkthrough'],
        promptTemplate: 'Explain step-by-step how this code works: ',
      },
      {
        id: 'terminal',
        name: 'Terminal Command',
        command: '/terminal',
        description: 'Generate shell, bash, or PowerShell commands',
        icon: 'Terminal',
        category: 'Programming',
        aliases: ['/cli', '/bash', '/cmd'],
        promptTemplate: 'Provide terminal commands for: ',
      },
      {
        id: 'git',
        name: 'Git Helper',
        command: '/git',
        description: 'Generate Git commands, rebase steps, or commit messages',
        icon: 'GitBranch',
        category: 'Programming',
        aliases: ['/commit', '/vcs'],
        promptTemplate: 'Generate Git command/commit message for: ',
      },
      {
        id: 'deploy',
        name: 'Deployment Guide',
        command: '/deploy',
        description: 'Build scripts, Dockerfile, and CI/CD pipelines',
        icon: 'Rocket',
        category: 'Programming',
        aliases: ['/docker', '/ci-cd'],
        promptTemplate: 'Create a deployment configuration for: ',
      },

      // Documents Category
      {
        id: 'pdf',
        name: 'PDF Processor',
        command: '/pdf',
        description: 'Parse, extract, or summarize PDF files',
        icon: 'FileSpreadsheet',
        category: 'Documents',
        aliases: ['/document', '/pdf-parse'],
        promptTemplate: 'Process this PDF document: ',
      },
      {
        id: 'ocr',
        name: 'Extract Text (OCR)',
        command: '/ocr',
        description: 'Extract readable text from images or scanned docs',
        icon: 'ScanText',
        category: 'Documents',
        aliases: ['/read-image', '/scan'],
        promptTemplate: 'Extract all readable text from this image: ',
      },
      {
        id: 'extract',
        name: 'Extract Structured Data',
        command: '/extract',
        description: 'Pull JSON, entities, or schemas from text',
        icon: 'Database',
        category: 'Documents',
        aliases: ['/json', '/parse'],
        promptTemplate: 'Extract structured JSON data from: ',
      },
      {
        id: 'table',
        name: 'Format Table',
        command: '/table',
        description: 'Format data into markdown tables or CSV',
        icon: 'Table',
        category: 'Documents',
        aliases: ['/csv', '/grid'],
        promptTemplate: 'Convert the following data into a Markdown table: ',
      },

      // Workspace Category
      {
        id: 'project',
        name: 'Project Overview',
        command: '/project',
        description: 'Summarize project context and workspace structure',
        icon: 'Folder',
        category: 'Workspace',
        aliases: ['/workspace', '/dir'],
        promptTemplate: 'Give an overview of this project context',
      },
      {
        id: 'memory',
        name: 'Manage Memory',
        command: '/memory',
        description: 'View or adjust AI persistent memory & context',
        icon: 'Cpu',
        category: 'Workspace',
        aliases: ['/context', '/recollect'],
        promptTemplate: 'What background memory do you have stored?',
      },
      {
        id: 'agent',
        name: 'Switch Agent',
        command: '/agent',
        description: 'Activate specific agent persona or tool set',
        icon: 'Bot',
        category: 'Workspace',
        aliases: ['/persona', '/mode'],
        promptTemplate: 'Switch agent mode to: ',
      },
      {
        id: 'settings',
        name: 'Settings',
        command: '/settings',
        description: 'Open assistant preferences and provider config',
        icon: 'Settings',
        category: 'Workspace',
        aliases: ['/config', '/pref'],
      },
    ]

    for (const cmd of defaults) {
      this.register(cmd)
    }
  }
}

export const commandRegistry = new CommandRegistry()
