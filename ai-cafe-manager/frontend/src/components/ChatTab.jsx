import { useState, useRef, useEffect } from 'react'
import { queryAI } from '../api.js'

export default function ChatTab() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState([])
  const scrollRef = useRef(null)
  const textareaRef = useRef(null)

  const submit = async () => {
    const q = input.trim()
    if (!q || loading) return

    const userMsg = { role: 'user', text: q, time: new Date() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const data = await queryAI(q)
      const aiMsg = { role: 'ai', text: data.response || data.answer || 'No response.', time: new Date() }
      setMessages(prev => [...prev, aiMsg])
    } catch {
      setMessages(prev => [...prev, { role: 'ai', text: 'Something went wrong. Please try again.', time: new Date(), error: true }])
    }
    setLoading(false)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, loading])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px'
    }
  }, [input])

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 160px)', maxWidth: 800, margin: '0 auto' }}>

      {/* Messages Area */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', paddingBottom: 16 }}>
        {messages.length === 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12, opacity: 0.6 }}>
            <span style={{ fontSize: 48 }}>☕</span>
            <h3 style={{ fontSize: 18, fontFamily: "'Playfair Display', serif", color: 'var(--primary)' }}>Ask AIBO Anything</h3>
            <p style={{ fontSize: 13, color: 'var(--text-dim)', textAlign: 'center', maxWidth: 360, lineHeight: 1.6 }}>
              Try: "What's our total revenue?" or "Add 20 burger buns to grocery"
            </p>
          </div>
        )}

        <div className="chat-container">
          {messages.map((msg, i) => (
            <div key={i} className={`chat-bubble ${msg.role}`} style={msg.error ? { borderColor: 'var(--danger)' } : {}}>
              {msg.text}
            </div>
          ))}

          {loading && (
            <div className="chat-bubble ai" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
              <span style={{ fontSize: 13, color: 'var(--text-dim)' }}>Thinking...</span>
            </div>
          )}
        </div>
      </div>

      {/* Input Bar */}
      <div className="chat-input-bar">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask about sales, inventory, or give instructions..."
          rows={1}
        />
        <button
          className="btn btn-primary"
          style={{ borderRadius: 'var(--radius-md)', padding: '8px 16px', minWidth: 60 }}
          onClick={submit}
          disabled={loading || !input.trim()}
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  )
}
