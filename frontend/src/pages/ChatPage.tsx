import { useEffect, useMemo, useRef, useState } from 'react'
import { createChat, getMessages, listChats, sendMessage } from '../lib/api'
import { useAuth } from '../auth/AuthContext'
import { setAuthToken } from '../lib/api'
import MessageBubble from '../components/MessageBubble'

interface ChatItem { id: string; createdAt: string }
interface MessageItem { id: string; sender: 'user' | 'bot'; text: string; timestamp: string }

function Avatar({ sender }: { sender: 'user' | 'bot' }) {
  return (
    <div className={`w-8 h-8 rounded-full grid place-items-center ${sender === 'user' ? 'bg-black text-white dark:bg-white dark:text-black' : 'bg-neutral-200 dark:bg-neutral-800'}`}>
      {sender === 'user' ? 'U' : 'B'}
    </div>
  )
}

function Typing() {
  return (
    <div className="flex items-center gap-2 text-neutral-500">
      <span className="w-2 h-2 rounded-full bg-neutral-400 animate-bounce [animation-delay:-200ms]"></span>
      <span className="w-2 h-2 rounded-full bg-neutral-400 animate-bounce [animation-delay:-100ms]"></span>
      <span className="w-2 h-2 rounded-full bg-neutral-400 animate-bounce"></span>
    </div>
  )
}

export default function ChatPage() {
  const { token, logout } = useAuth()
  const [chats, setChats] = useState<ChatItem[]>([])
  const [activeChatId, setActiveChatId] = useState<string | null>(null)
  const [messages, setMessages] = useState<MessageItem[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    setAuthToken(token)
  }, [token])

  async function refreshChats() {
    const data = await listChats()
    setChats(data)
    if (!activeChatId && data.length > 0) {
      setActiveChatId(data[0].id)
    }
  }

  useEffect(() => {
    refreshChats()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!activeChatId) return
    ;(async () => {
      const data = await getMessages(activeChatId)
      setMessages(data)
      scrollToBottom()
    })()
  }, [activeChatId])

  function scrollToBottom() {
    requestAnimationFrame(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }))
  }

  function groupedMessages() {
    const groups: { key: string; dateLabel: string; items: MessageItem[] }[] = []
    let currentKey = ''
    for (const m of messages) {
      const d = new Date(m.timestamp)
      const dateLabel = d.toLocaleDateString()
      const key = `${dateLabel}`
      if (key !== currentKey) {
        groups.push({ key, dateLabel, items: [m] })
        currentKey = key
      } else {
        groups[groups.length - 1].items.push(m)
      }
    }
    return groups
  }

  async function handleSend() {
    if (!input.trim() || !activeChatId) return
    setLoading(true)
    const userText = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), sender: 'user', text: userText, timestamp: new Date().toISOString() }])
    scrollToBottom()
    try {
      const res = await sendMessage(activeChatId, userText)
      setMessages((prev) => [...prev, res])
    } finally {
      setLoading(false)
      scrollToBottom()
    }
  }

  async function handleNewChat() {
    const chat = await createChat()
    await refreshChats()
    setActiveChatId(chat.id)
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if ((e.key === 'Enter' && !e.shiftKey) || (e.key.toLowerCase() === 'enter' && (e.ctrlKey || e.metaKey))) {
      e.preventDefault()
      handleSend()
    }
  }

  const groups = useMemo(groupedMessages, [messages])

  return (
    <div className="min-h-[calc(100vh-56px)]">
      <div className="container grid grid-cols-12 gap-0 md:gap-6 py-4">
        <aside className="col-span-12 md:col-span-4 lg:col-span-3 card p-4 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-medium">Your Chats</h2>
            <button onClick={handleNewChat} className="btn-primary text-xs">New</button>
          </div>
          <div className="space-y-2 overflow-y-auto pr-1" style={{ maxHeight: 'calc(100vh - 14rem)' }}>
            {chats.map((c) => (
              <button
                key={c.id}
                onClick={() => setActiveChatId(c.id)}
                className={`w-full text-left px-3 py-2 rounded-xl border transition-colors ${activeChatId === c.id ? 'border-black dark:border-white bg-black/5 dark:bg-white/10' : 'border-neutral-200 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-900'}`}
              >
                <div className="text-sm font-medium flex items-center gap-2">
                  <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  Chat {c.id.slice(-4)}
                </div>
                <div className="text-xs text-neutral-500">{new Date(c.createdAt).toLocaleString()}</div>
              </button>
            ))}
            {chats.length === 0 && <div className="text-sm text-neutral-500">No chats yet.</div>}
          </div>
          <div className="mt-auto pt-4">
            <button onClick={logout} className="text-xs text-neutral-500 underline">Logout</button>
          </div>
        </aside>

        <main className="col-span-12 md:col-span-8 lg:col-span-9 card p-0 overflow-hidden">
          <div className="flex flex-col h-[calc(100vh-8.5rem)]">
            <div className="flex-1 overflow-y-auto space-y-4 p-4">
              {groups.map((g) => (
                <div key={g.key}>
                  <div className="sticky top-2 z-10 w-fit mx-auto px-3 py-1 text-xs rounded-full border border-neutral-200 dark:border-neutral-800 bg-white/70 dark:bg-neutral-950/40 backdrop-blur text-neutral-500">
                    {g.dateLabel}
                  </div>
                  <div className="mt-2 space-y-3">
                    {g.items.map((m, idx) => (
                      <MessageBubble key={m.id} sender={m.sender} text={m.text} timestamp={m.timestamp} />
                    ))}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex items-center gap-2 text-neutral-500">
                  <Avatar sender="bot" />
                  <Typing />
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            <div className="p-3 border-t border-neutral-200 dark:border-neutral-800 bg-white/70 dark:bg-neutral-950/40 backdrop-blur">
              <div className="flex gap-2">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Type your message..."
                  className="flex-1 px-3 py-2 rounded-xl border border-neutral-300 dark:border-neutral-700 bg-transparent focus:outline-none focus:ring-2 focus:ring-black/10 dark:focus:ring-white/20"
                  onKeyDown={onKeyDown}
                />
                <button disabled={loading} onClick={handleSend} className="btn-primary">
                  {loading ? 'Sending…' : 'Send'}
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
