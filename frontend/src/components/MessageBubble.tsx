import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { Copy, Check, Volume2, Pause } from 'lucide-react'

interface MessageBubbleProps {
  sender: 'user' | 'bot'
  text: string
  timestamp: string
}

export default function MessageBubble({ sender, text, timestamp }: MessageBubbleProps) {
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [copied, setCopied] = useState(false)
  const [utterance, setUtterance] = useState<SpeechSynthesisUtterance | null>(null)

  useEffect(() => {
    return () => {
      if (utterance) {
        window.speechSynthesis.cancel()
      }
    }
  }, [utterance])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy text:', err)
    }
  }

  const handleReadAloud = () => {
    if (isSpeaking) {
      window.speechSynthesis.cancel()
      setIsSpeaking(false)
      setUtterance(null)
    } else {
      const synth = window.speechSynthesis
      const newUtterance = new SpeechSynthesisUtterance(text)
      
      newUtterance.onend = () => {
        setIsSpeaking(false)
        setUtterance(null)
      }
      
      newUtterance.onerror = () => {
        setIsSpeaking(false)
        setUtterance(null)
      }
      
      synth.speak(newUtterance)
      setIsSpeaking(true)
      setUtterance(newUtterance)
    }
  }

  // Only show buttons for bot messages
  const isBot = sender === 'bot'

  return (
    <div className={`flex gap-2 ${sender === 'user' ? 'flex-row-reverse' : ''} animate-fadeIn group relative`}>
      <div className={`w-8 h-8 rounded-full grid place-items-center flex-shrink-0 ${sender === 'user' ? 'bg-black text-white dark:bg-white dark:text-black' : 'bg-neutral-200 dark:bg-neutral-800'}`}>
        {sender === 'user' ? 'U' : 'B'}
      </div>
      <div className={`max-w-[80%] px-4 py-2 rounded-2xl shadow-sm border relative ${
        sender === 'user' 
          ? 'bg-black text-white dark:bg-white dark:text-black border-black/10 dark:border-white/10' 
          : 'bg-white/70 dark:bg-neutral-900/50 backdrop-blur border-neutral-200 dark:border-neutral-800'
      }`}>
        {/* Message content with markdown */}
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown
            components={{
              // Custom styling for markdown elements
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>,
              li: ({ children }) => <li className="leading-relaxed">{children}</li>,
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
              em: ({ children }) => <em className="italic">{children}</em>,
              code: ({ children }) => (
                <code className="bg-black/10 dark:bg-white/10 px-1 py-0.5 rounded text-xs font-mono">
                  {children}
                </code>
              ),
              pre: ({ children }) => (
                <pre className="bg-black/10 dark:bg-white/10 p-2 rounded text-xs font-mono overflow-x-auto mb-2">
                  {children}
                </pre>
              ),
              a: ({ href, children }) => (
                <a 
                  href={href} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="text-blue-600 dark:text-blue-400 underline hover:opacity-80"
                >
                  {children}
                </a>
              ),
              h1: ({ children }) => <h1 className="text-lg font-bold mb-2 mt-2">{children}</h1>,
              h2: ({ children }) => <h2 className="text-base font-bold mb-2 mt-2">{children}</h2>,
              h3: ({ children }) => <h3 className="text-sm font-bold mb-1 mt-1">{children}</h3>,
            }}
          >
            {text}
          </ReactMarkdown>
        </div>
        
        {/* Timestamp */}
        <span className="block mt-1 text-[10px] opacity-60">
          {new Date(timestamp).toLocaleTimeString()}
        </span>

        {/* Action buttons (only for bot messages) */}
        {isBot && (
          <div className="absolute bottom-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-lg hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
              title={copied ? 'Copied!' : 'Copy message'}
            >
              {copied ? <Check size={16} /> : <Copy size={16} />}
            </button>
            <button
              onClick={handleReadAloud}
              className="p-1.5 rounded-lg hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
              title={isSpeaking ? 'Stop reading' : 'Read aloud'}
            >
              {isSpeaking ? <Pause size={16} /> : <Volume2 size={16} />}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

