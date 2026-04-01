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
      const aiMsg = {
        role: 'ai',
        text: data.response || data.answer || 'No response.',
        time: new Date(),
        thinking: data.thinking || [],
        evaluation: data.evaluation || {},
        safe: data.safe !== undefined ? data.safe : true,
      }
      setMessages(prev => [...prev, aiMsg])
    } catch {
      setMessages(prev => [...prev, { role: 'ai', text: 'Something went wrong. Please try again.', time: new Date(), error: true, thinking: [] }])
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
              Try: "What's our total revenue?" or "Who's working right now?" or "What's the profit margin on lattes?"
            </p>
          </div>
        )}

        <div className="chat-container">
          {messages.map((msg, i) => (
            <div key={i}>
              <div className={`chat-bubble ${msg.role}`} style={msg.error ? { borderColor: 'var(--danger)' } : {}}>
                {msg.text}
              </div>

              {/* Thinking Panel — only for AI messages with thinking data */}
              {msg.role === 'ai' && msg.thinking && msg.thinking.length > 0 && (
                <ThinkingPanel thinking={msg.thinking} evaluation={msg.evaluation} />
              )}
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
          placeholder="Ask about sales, inventory, staff, procurement, or give instructions..."
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

// ─── Thinking Panel Component ────────────────────────────────────────────────

function ThinkingPanel({ thinking, evaluation }) {
  const [expanded, setExpanded] = useState(false)
  
  if (!thinking || thinking.length === 0) return null

  const score = evaluation?.score
  const scoreColor = score >= 8 ? '#22c55e' : score >= 5 ? '#f59e0b' : '#ef4444'

  return (
    <div style={{ marginLeft: 12, marginTop: 4, marginBottom: 8 }}>
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 8px',
          borderRadius: 6,
          fontSize: 11,
          color: 'var(--text-dim)',
          transition: 'all 0.2s ease',
          opacity: 0.7,
        }}
        onMouseEnter={e => { e.target.style.opacity = '1'; e.target.style.background = 'var(--bg-elevated)' }}
        onMouseLeave={e => { e.target.style.opacity = '0.7'; e.target.style.background = 'none' }}
      >
        <span style={{ fontSize: 13 }}>🧠</span>
        <span>{expanded ? 'Hide' : 'See'} how AIBO thought</span>
        {score !== undefined && (
          <span style={{
            background: scoreColor + '20',
            color: scoreColor,
            padding: '1px 6px',
            borderRadius: 4,
            fontSize: 10,
            fontWeight: 700,
            marginLeft: 4,
          }}>
            {score}/10
          </span>
        )}
        <span style={{ fontSize: 10, transition: 'transform 0.2s', transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</span>
      </button>

      {expanded && (
        <div style={{
          marginTop: 6,
          padding: '12px 14px',
          background: 'var(--bg-elevated)',
          borderRadius: 10,
          border: '1px solid var(--border-subtle)',
          animation: 'fadeIn 0.2s ease',
        }}>
          {thinking.map((step, idx) => (
            <div key={idx} style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 8,
              padding: '6px 0',
              borderBottom: idx < thinking.length - 1 ? '1px solid var(--border-subtle)' : 'none',
            }}>
              <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>{step.icon || '•'}</span>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 2 }}>
                  {step.step}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.4 }}>
                  {step.detail}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
