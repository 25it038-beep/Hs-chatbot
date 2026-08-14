import React from 'react'
import { useChat } from '@/stores/chat'
import { useAuth } from '@/stores/auth'
import { useSettings } from '@/stores/settings'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import {
  Plus, MessageSquare, Trash2, Pin, Folder, Settings as SettingsIcon,
  Search, PanelLeftClose, PanelLeft, X, Check,
} from 'lucide-react'

type DateGroup = 'Today' | 'Yesterday' | 'Previous 7 days' | 'Older'

function getDateGroup(date: string): DateGroup {
  const d = new Date(date)
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const startOfDay = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  const diffDays = Math.floor((startOfToday - startOfDay) / (1000 * 60 * 60 * 24))
  if (diffDays <= 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return 'Previous 7 days'
  return 'Older'
}

function timeLabel(date: string): string {
  const d = new Date(date)
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const startOfDay = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  const diffDays = Math.floor((startOfToday - startOfDay) / (1000 * 60 * 60 * 24))
  if (diffDays <= 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return d.toLocaleDateString([], { weekday: 'short' })
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

const GROUP_ORDER: DateGroup[] = ['Today', 'Yesterday', 'Previous 7 days', 'Older']

export function Sidebar() {
  const { chats, folders, currentChat, selectChat, createChat, deleteChat } = useChat()
  const { user } = useAuth()
  const { sidebarOpen, setSidebarOpen, toggleSidebar, toggleSettings } = useSettings()
  const [search, setSearch] = React.useState('')
  const [activeFolder, setActiveFolder] = React.useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = React.useState<string | null>(null)

  const sortedChats = React.useMemo(
    () => [...chats].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()),
    [chats],
  )

  const filteredChats = React.useMemo(
    () =>
      sortedChats.filter(c =>
        (!search || c.title?.toLowerCase().includes(search.toLowerCase())) &&
        (!activeFolder || c.folder_id === activeFolder),
      ),
    [sortedChats, search, activeFolder],
  )

  const pinnedChats = filteredChats.filter(c => c.is_pinned)
  const restChats = filteredChats.filter(c => !c.is_pinned)

  const grouped = React.useMemo(() => {
    const map: Record<DateGroup, typeof restChats> = { Today: [], Yesterday: [], 'Previous 7 days': [], Older: [] }
    for (const chat of restChats) {
      map[getDateGroup(chat.updated_at)].push(chat)
    }
    return GROUP_ORDER.filter(g => map[g].length > 0).map(g => ({ group: g, items: map[g] }))
  }, [restChats])

  const handleSelectChat = (id: string) => {
    selectChat(id)
    if (window.innerWidth < 768) setSidebarOpen(false)
  }

  const handleCreateChat = async () => {
    await createChat()
    if (window.innerWidth < 768) setSidebarOpen(false)
  }

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    if (confirmDeleteId === id) {
      deleteChat(id)
      setConfirmDeleteId(null)
    } else {
      setConfirmDeleteId(id)
      setTimeout(() => setConfirmDeleteId(prev => (prev === id ? null : prev)), 3000)
    }
  }

  const ChatRow = ({ chat }: { chat: typeof chats[number] }) => {
    const isActive = currentChat?.id === chat.id
    const confirming = confirmDeleteId === chat.id
    return (
      <div
        role="button"
        tabIndex={0}
        aria-current={isActive ? 'page' : undefined}
        onClick={() => handleSelectChat(chat.id)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') handleSelectChat(chat.id)
        }}
        className={cn(
          'group flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer mb-0.5 transition-colors duration-150 text-[13px]',
          isActive
            ? 'bg-accent text-foreground font-medium'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground',
        )}
      >
        <MessageSquare size={13} className={cn('flex-shrink-0', isActive ? 'text-foreground' : 'opacity-40')} />
        <span className="flex-1 truncate">{chat.title || 'New Chat'}</span>
        <span className="text-[10px] text-muted-foreground/50 flex-shrink-0 font-mono">
          {timeLabel(chat.updated_at)}
        </span>
        {chat.is_pinned && <Pin size={9} className="text-muted-foreground/50 flex-shrink-0" fill="currentColor" />}
        <button
          onClick={(e) => handleDelete(e, chat.id)}
          onKeyDown={(e) => e.stopPropagation()}
          aria-label={confirming ? 'Confirm delete chat' : 'Delete chat'}
          title={confirming ? 'Click again to confirm' : 'Delete chat'}
          className={cn(
            'p-1 rounded-md transition-all flex-shrink-0',
            confirming
              ? 'opacity-100 bg-destructive/10 text-destructive'
              : 'opacity-0 group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100',
          )}
        >
          {confirming ? <Check size={11} /> : <Trash2 size={11} />}
        </button>
      </div>
    )
  }

  return (
    <>
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-foreground/20 backdrop-blur-[2px] z-30 md:hidden animate-fade-in"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div
        className={cn(
          'flex flex-col h-full z-40 md:z-20 transition-all duration-300 ease-out',
          'border-r border-border bg-sidebar',
          'fixed md:relative inset-y-0 left-0',
          sidebarOpen ? 'w-72 translate-x-0' : 'w-0 -translate-x-full md:translate-x-0 overflow-hidden border-none',
        )}
      >
        <div className="flex items-center justify-between px-4 pt-4 pb-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-lg overflow-hidden border border-border flex-shrink-0">
              <img src="/logo.jpg" alt="HSBot" className="w-full h-full object-cover" />
            </div>
            <span className="font-semibold text-[15px] tracking-tight">HSBot</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 rounded-lg text-muted-foreground/50 hover:text-foreground"
            onClick={toggleSidebar}
            aria-label="Close sidebar"
          >
            <PanelLeftClose size={15} />
          </Button>
        </div>

        <div className="px-3 pb-2">
          <Button
            onClick={handleCreateChat}
            className="w-full justify-start gap-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 h-9 text-[13px] font-medium shadow-soft"
          >
            <Plus size={15} />
            New Chat
          </Button>
        </div>

        <div className="px-3 pb-1.5">
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/40 pointer-events-none" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search conversations"
              aria-label="Search conversations"
              className="w-full h-8 pl-8 pr-7 rounded-lg bg-muted/50 border border-transparent text-xs outline-none focus:border-border focus:bg-background focus:ring-2 focus:ring-ring/20 transition-all placeholder:text-muted-foreground/40"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                aria-label="Clear search"
                className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded text-muted-foreground/50 hover:text-foreground hover:bg-muted/60 transition-all"
              >
                <X size={11} />
              </button>
            )}
          </div>
        </div>

        {folders.length > 0 && (
          <div className="px-3 py-1.5 max-h-32 overflow-y-auto no-scrollbar">
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                onClick={() => setActiveFolder(null)}
                className={cn(
                  'flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-medium border transition-all',
                  activeFolder === null
                    ? 'bg-accent border-border text-foreground'
                    : 'border-transparent text-muted-foreground/60 hover:text-foreground hover:bg-muted',
                )}
              >
                <MessageSquare size={10} />
                All
              </button>
              {folders.map((folder) => (
                <button
                  key={folder.id}
                  onClick={() => setActiveFolder(activeFolder === folder.id ? null : folder.id)}
                  title={`Filter chats in ${folder.name}`}
                  className={cn(
                    'flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-medium border transition-all',
                    activeFolder === folder.id
                      ? 'bg-accent border-border text-foreground'
                      : 'border-transparent text-muted-foreground/60 hover:text-foreground hover:bg-muted',
                  )}
                >
                  <Folder size={10} />
                  <span className="truncate max-w-24">{folder.name}</span>
                </button>
              ))}
            </div>
            <Separator className="my-2 opacity-40" />
          </div>
        )}

        <div className="px-4 pt-1 pb-1.5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/50">
            Conversations
          </p>
        </div>

        <ScrollArea className="flex-1 px-2">
          {pinnedChats.length > 0 && (
            <div className="mb-1">
              <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/40 flex items-center gap-1">
                <Pin size={9} /> Pinned
              </p>
              {pinnedChats.map(chat => <ChatRow key={chat.id} chat={chat} />)}
            </div>
          )}
          {grouped.map(({ group, items }) => (
            <div key={group} className="mb-1">
              <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/40">
                {group}
              </p>
              {items.map(chat => <ChatRow key={chat.id} chat={chat} />)}
            </div>
          ))}
          {filteredChats.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
              <MessageSquare size={22} className="text-muted-foreground/20 mb-3" />
              <p className="text-xs text-muted-foreground/50">
                {search || activeFolder ? 'No conversations found' : 'No conversations yet'}
              </p>
            </div>
          )}
        </ScrollArea>

        <div className="border-t border-border mt-auto">
          <div className="p-2">
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start gap-2.5 rounded-lg text-muted-foreground/70 hover:text-foreground hover:bg-muted h-9 text-[13px]"
              onClick={() => {
                toggleSettings()
                if (window.innerWidth < 768) setSidebarOpen(false)
              }}
            >
              <SettingsIcon size={14} />
              Settings
            </Button>
          </div>
          {user && (
            <div className="flex items-center gap-2.5 px-3.5 pb-3.5 pt-1">
              <div className="w-7 h-7 rounded-full overflow-hidden border border-border flex-shrink-0">
                <img src="/logo.jpg" alt="" className="w-full h-full object-cover" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium truncate">{user.display_name || user.username}</p>
                <p className="text-[10px] text-muted-foreground/60 truncate">{user.email}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {!sidebarOpen && (
        <button
          onClick={toggleSidebar}
          aria-label="Open sidebar"
          className="fixed top-3 left-3 z-30 h-8 w-8 rounded-lg bg-card border border-border shadow-soft flex items-center justify-center hover:bg-muted transition-all animate-fade-in md:hidden"
        >
          <PanelLeft size={15} />
        </button>
      )}
    </>
  )
}