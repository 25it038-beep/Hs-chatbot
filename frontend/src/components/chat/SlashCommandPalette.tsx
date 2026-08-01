import React, { useEffect, useRef, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import * as LucideIcons from 'lucide-react'
import { Pin, Star, Sparkles, Command as CommandIcon, CornerDownLeft } from 'lucide-react'
import type { SlashCommand, CommandCategory } from '@/types/command'
import { useSlashCommandsStore } from '@/stores/slashCommands'
import { cn } from '@/lib/utils'

interface SlashCommandPaletteProps {
  isOpen: boolean
  query: string
  filteredCommands: SlashCommand[]
  activeIndex: number
  onSelect: (command: SlashCommand) => void
  onClose: () => void
}

/**
 * Dynamic Icon Helper component to render Lucide icons safely by name
 */
function DynamicIcon({ name, className }: { name: string; className?: string }) {
  const IconComponent = (LucideIcons as any)[name] || LucideIcons.Terminal
  return <IconComponent className={className || 'w-4 h-4'} />
}

interface CommandSection {
  title: string
  items: SlashCommand[]
  isPinned?: boolean
  isRecent?: boolean
}

export function SlashCommandPalette({
  isOpen,
  query,
  filteredCommands,
  activeIndex,
  onSelect,
  onClose,
}: SlashCommandPaletteProps) {
  const listRef = useRef<HTMLDivElement>(null)
  const activeItemRef = useRef<HTMLDivElement>(null)
  const { pinnedCommands, recentlyUsed, togglePin } = useSlashCommandsStore()

  // Scroll active item into view smoothly
  useEffect(() => {
    if (activeItemRef.current) {
      activeItemRef.current.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth',
      })
    }
  }, [activeIndex])

  // Group commands by Category or Pinned/Recent if query is empty
  const groupedSections: CommandSection[] = useMemo(() => {
    const trimmed = query.trim().toLowerCase().replace(/^\//, '')
    
    // If user is searching specifically, group by Search Results or Category
    if (trimmed.length > 0) {
      const categories: Record<string, SlashCommand[]> = {}
      for (const cmd of filteredCommands) {
        if (!categories[cmd.category]) categories[cmd.category] = []
        categories[cmd.category].push(cmd)
      }
      return Object.entries(categories).map(([category, items]) => ({
        title: category,
        items,
      }))
    }

    // Default view: Pinned, Recent, and Categories
    const pinnedSet = new Set(pinnedCommands)
    const pinnedItems = filteredCommands.filter(c => pinnedSet.has(c.id))
    
    const recentSet = new Set(recentlyUsed)
    const recentItems = filteredCommands.filter(c => !pinnedSet.has(c.id) && recentSet.has(c.id))

    const remainingItems = filteredCommands.filter(c => !pinnedSet.has(c.id) && !recentSet.has(c.id))

    const categories: Record<string, SlashCommand[]> = {}
    for (const cmd of remainingItems) {
      if (!categories[cmd.category]) categories[cmd.category] = []
      categories[cmd.category].push(cmd)
    }

    const sections: CommandSection[] = []
    if (pinnedItems.length > 0) {
      sections.push({ title: 'Pinned Commands', items: pinnedItems, isPinned: true })
    }
    if (recentItems.length > 0) {
      sections.push({ title: 'Recently Used', items: recentItems, isRecent: true })
    }
    for (const [category, items] of Object.entries(categories)) {
      sections.push({ title: category, items })
    }

    return sections
  }, [filteredCommands, query, pinnedCommands, recentlyUsed])


  if (!isOpen || filteredCommands.length === 0) {
    return null
  }

  let globalItemCounter = 0

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 8, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 6, scale: 0.98 }}
        transition={{ duration: 0.15, ease: 'easeOut' }}
        className="absolute bottom-full left-0 right-0 mb-2.5 z-50 max-h-[340px] sm:max-h-[380px] flex flex-col rounded-2xl border border-border/50 bg-background/95 backdrop-blur-xl shadow-2xl overflow-hidden glass-reflection"
        role="listbox"
        id="slash-command-palette"
        aria-label="Slash commands"
      >
        {/* Header bar */}
        <div className="flex items-center justify-between px-3.5 py-2 border-b border-border/30 bg-muted/30 text-xs text-muted-foreground select-none">
          <div className="flex items-center gap-1.5 font-medium">
            <CommandIcon className="w-3.5 h-3.5 text-primary" />
            <span>Slash Commands</span>
            {query && (
              <span className="text-[11px] px-1.5 py-0.5 rounded-md bg-primary/10 text-primary font-mono">
                /{query.replace(/^\//, '')}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground/60 hidden sm:flex">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-muted border border-border/40 font-mono">↑</kbd>
              <kbd className="px-1.5 py-0.5 rounded bg-muted border border-border/40 font-mono">↓</kbd>
              Navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-muted border border-border/40 font-mono">↵</kbd>
              Select
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-muted border border-border/40 font-mono">esc</kbd>
              Dismiss
            </span>
          </div>
        </div>

        {/* Command List */}
        <div
          ref={listRef}
          className="flex-1 overflow-y-auto p-1.5 space-y-3 custom-scrollbar max-h-[300px]"
        >
          {groupedSections.map((section, sIdx) => (
            <div key={section.title + sIdx} className="space-y-1">
              <div className="px-2.5 py-1 text-[11px] font-semibold text-muted-foreground/70 tracking-wider uppercase flex items-center gap-1.5">
                {section.isPinned && <Star className="w-3 h-3 text-amber-400 fill-amber-400" />}
                {section.isRecent && <Sparkles className="w-3 h-3 text-primary" />}
                <span>{section.title}</span>
              </div>

              <div className="space-y-0.5">
                {section.items.map((command) => {
                  const itemIndex = globalItemCounter++
                  const isActive = itemIndex === activeIndex
                  const isItemPinned = pinnedCommands.includes(command.id)

                  return (
                    <div
                      key={command.id}
                      ref={isActive ? activeItemRef : null}
                      id={`slash-cmd-item-${itemIndex}`}
                      role="option"
                      aria-selected={isActive}
                      onClick={() => onSelect(command)}
                      className={cn(
                        'group relative flex items-center justify-between px-3 py-2 rounded-xl transition-all cursor-pointer text-xs sm:text-sm select-none',
                        isActive
                          ? 'bg-primary/10 text-foreground font-medium border border-primary/20 shadow-xs'
                          : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground border border-transparent'
                      )}
                    >
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <div
                          className={cn(
                            'p-2 rounded-lg transition-colors flex-shrink-0',
                            isActive
                              ? 'bg-primary/20 text-primary'
                              : 'bg-muted/60 text-muted-foreground group-hover:bg-muted group-hover:text-foreground'
                          )}
                        >
                          <DynamicIcon name={command.icon} className="w-4 h-4" />
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-foreground truncate">
                              {command.name}
                            </span>
                            <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-muted/80 text-muted-foreground flex-shrink-0">
                              {command.command}
                            </span>
                          </div>
                          <p className="text-[11px] text-muted-foreground/80 truncate mt-0.5">
                            {command.description}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                        {/* Pin button */}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            togglePin(command.id)
                          }}
                          className={cn(
                            'p-1.5 rounded-lg transition-all',
                            isItemPinned
                              ? 'text-amber-400 opacity-100 hover:bg-amber-400/10'
                              : 'opacity-0 group-hover:opacity-100 text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted'
                          )}
                          title={isItemPinned ? 'Unpin command' : 'Pin command'}
                        >
                          <Star className={cn('w-3.5 h-3.5', isItemPinned && 'fill-amber-400')} />
                        </button>

                        {isActive && (
                          <CornerDownLeft className="w-3.5 h-3.5 text-primary opacity-70 hidden sm:block" />
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    </AnimatePresence>
  )
}
