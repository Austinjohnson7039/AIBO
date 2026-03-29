import { useState, useRef, useEffect } from 'react'
import { queryAI } from '../api.js'

function Badge({ score }) {
  if (score >= 8) return <span className="badge badge-green">High Confidence</span>
  if (score >= 5) return <span className="badge badge-amber">Medium Confidence</span>
  return <span className="badge badge-red">Low Confidence</span>
}

export default function ChatTab() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState(null)
  const [error, setError] = useState('')
  const textareaRef = useRef()

  const submit = async () => {
    const q = input.trim()
    if (!q) return
    setLoading(true)
    setError('')
    setResponse(null)
    try {
      const data = await queryAI(q)
      setResponse(data)
    } catch (e) {
      setError(e.message || 'Connection lost to the AI Engine.')
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px'
    }
  }, [input])

  const ev = response?.evaluation || {}
  const score = ev?.score ?? 0

  return (
    <div className="chat-page">
      <div className="chat-composer">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask AIBO about sales, inventory, or forecasting... (Press Enter)"
          rows={1}
        />
        <button className="chat-send" onClick={submit} disabled={loading || !input.trim()}>
          {loading ? '⟳' : '↑'}
        </button>
      </div>

      {error && (
        <div className="alert alert-red">
          <span className="alert-icon">⚠</span>
          <div>{error}</div>
        </div>
      )}

      {loading && (
        <div className="chat-result">
          <div className="thinking">
            AIBO is analysing
            <div className="dots">
              <div className="dot" /><div className="dot" /><div className="dot" />
            </div>
          </div>
        </div>
      )}

      {response && !loading && (
        <div className="chat-result">
          <div className="chat-result-body">
            <div className="chat-result-eyebrow">
              <span className="icon">◈</span> AI Insights
            </div>
            <div className="chat-result-text">
              {response.response || response.answer || 'No intelligent response generated.'}
            </div>
          </div>

          <div className="chat-result-footer">
            <div className="chat-meta-cell">
              <div className="chat-meta-label">Assurance</div>
              <Badge score={score} />
            </div>
            <div className="chat-meta-cell">
              <div className="chat-meta-label">Accuracy Score</div>
              <div className="mono" style={{ fontSize: 22, fontWeight: 700, color: 'var(--ink-1)' }}>
                {score}<span style={{ fontSize: 13, color: 'var(--ink-4)', fontWeight: 400 }}>/10</span>
              </div>
            </div>
            <div className="chat-meta-cell">
              <div className="chat-meta-label">Safety Filter</div>
              {response.safe
                ? <span className="badge badge-green">Verified</span>
                : <span className="badge badge-amber">Flagged</span>}
            </div>
          </div>

          {(score < 5 || ev?.hallucination) && ev?.reason && (
            <div style={{ padding: '14px 22px', borderTop: '1px solid var(--border)' }}>
              <div className="alert alert-amber">
                <span className="alert-icon">⚠</span>
                <div><strong>Judge Flag:</strong> {ev.reason}</div>
              </div>
            </div>
          )}

          {response.sources?.length > 0 && (
            <div className="chat-sources">
              <div className="chat-meta-label" style={{ marginRight: 8 }}>References:</div>
              {response.sources.map((s, i) => (
                <span key={i} className="source-tag">{s}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {!response && !loading && !error && (
        <div className="empty" style={{ marginTop: 40 }}>
          <div className="empty-icon">☕</div>
          <p>I am AIBO, your Cafe Intelligence Engine.<br/>Ask me anything about your business data.</p>
        </div>
      )}
    </div>
  )
}
