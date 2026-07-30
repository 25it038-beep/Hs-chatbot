import React from 'react'
import { useChat } from '@/stores/chat'
import { useSettings } from '@/stores/settings'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import {
  Plus, MessageSquare, Trash2, Pin, Folder, Settings as SettingsIcon,
  Search, PanelLeftClose, PanelLeft, Bot, Sparkles,
} from 'lucide-react'
import { formatDate } from '@/lib/utils'

export function Sidebar() {
  const { chats, folders, currentChat, selectChat, createChat, deleteChat } = useChat()
  const { sidebarOpen, toggleSidebar, toggleSettings } = useSettings()
  const [search, setSearch] = React.useState('')

  const filteredChats = chats.filter(c =>
    !search || c.title?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <>
      <div
        className={cn(
          'flex flex-col h-full relative z-20 transition-all duration-300 ease-out',
          'border-r border-border/30 bg-sidebar backdrop-blur-2xl shadow-glass',
          sidebarOpen ? 'w-72' : 'w-0 overflow-hidden'
        )}
      >
        <div className="flex items-center justify-between p-3 pb-2">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl overflow-hidden shadow-sm border border-primary/10">
              <img src="/logo.jpg" alt="HSBot" className="w-full h-full object-cover" />
            </div>
            <div>
              <span className="font-semibold text-sm tracking-tight">HSBot</span>
              <span className="flex items-center gap-1 text-[10px] text-muted-foreground/50 mt-0.5">
                <Sparkles size={8} />
                AI Assistant
              </span>
            </div>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8 rounded-xl text-muted-foreground/50 hover:text-foreground" onClick={toggleSidebar}>
            <PanelLeftClose size={15} />
          </Button>
        </div>

        <div className="px-3 pb-3">
          <Button
            onClick={createChat}
            className="w-full justify-start gap-2 rounded-xl bg-gradient-to-r from-primary/10 to-primary/5 hover:from-primary/15 hover:to-primary/10 border border-primary/10 text-foreground shadow-sm"
            variant="ghost"
          >
            <Plus size={16} />
            New Chat
          </Button>
        </div>

        <div className="px-3 pb-2">
          <div className="relative">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/40" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search chats..."
              className="w-full h-9 pl-8 pr-3 rounded-xl bg-muted/40 border border-border/30 text-xs outline-none focus:border-ring/30 focus:bg-muted/60 transition-all placeholder:text-muted-foreground/30"
            />
          </div>
        </div>

        {folders.length > 0 && (
          <div className="px-3 pb-2">
            {folders.map((folder) => (
              <div key={folder.id} className="mb-1">
                <div className="flex items-center gap-2 px-2.5 py-1.5 text-xs text-muted-foreground/60 hover:text-foreground rounded-lg hover:bg-muted/30 transition-colors cursor-pointer">
                  <Folder size={12} />
                  <span>{folder.name}</span>
                </div>
              </div>
            ))}
            <Separator className="my-2 opacity-20" />
          </div>
        )}

        <ScrollArea className="flex-1 px-2">
          {filteredChats.map((chat) => (
            <div
              key={chat.id}
              className={cn(
                'group flex items-center gap-2.5 px-3 py-2.5 rounded-xl cursor-pointer mb-0.5 transition-all duration-150 text-sm',
                currentChat?.id === chat.id
                  ? 'bg-muted/60 text-foreground shadow-sm border border-border/20'
                  : 'text-muted-foreground/70 hover:bg-muted/30 hover:text-foreground border border-transparent'
              )}
              onClick={() => selectChat(chat.id)}
            >
              <MessageSquare size={13} className="flex-shrink-0 opacity-50" />
              <span className="flex-1 truncate">{chat.title || 'New Chat'}</span>
              <span className="text-[10px] text-muted-foreground/30 flex-shrink-0 font-mono">
                {formatDate(chat.updated_at)}
              </span>
              {chat.is_pinned && <Pin size={9} className="text-muted-foreground/30 flex-shrink-0" />}
              <button
                onClick={(e) => { e.stopPropagation(); deleteChat(chat.id) }}
                className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-destructive/10 hover:text-destructive transition-all flex-shrink-0"
              >
                <Trash2 size={11} />
              </button>
            </div>
          ))}
          {filteredChats.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
              <MessageSquare size={24} className="text-muted-foreground/15 mb-3" />
              <p className="text-xs text-muted-foreground/40">
                {search ? 'No chats found' : 'No chats yet'}
              </p>
            </div>
          )}
        </ScrollArea>

        <div className="p-3 border-t border-border/20">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2.5 rounded-xl text-muted-foreground/60 hover:text-foreground hover:bg-muted/40 h-9"
            onClick={toggleSettings}
          >
            <SettingsIcon size={14} />
            Settings
          </Button>
        </div>
      </div>

      {!sidebarOpen && (
        <button
          onClick={toggleSidebar}
          className="absolute top-3 left-3 z-30 h-8 w-8 rounded-xl glass-panel shadow-soft flex items-center justify-center hover:bg-muted/70 transition-all animate-fade-in"
        >
          <PanelLeft size={15} />
        </button>
      )}
    </>
  )
}
