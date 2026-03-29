import { useState } from 'react'
import { triggerSync } from '../api.js'

export default function SystemTab() {
  const [syncing, setSyncing] = useState(false)
  const [msg, setMsg] = useState('')

  const handleSync = async () => {
    setSyncing(true)
    setMsg('')
    try {
      const res = await triggerSync()
      setMsg(res.message ? `✓ ${res.message}` : '✓ Sync execution completed.')
    } catch { setMsg('⨯ Sync aborted due to timeout.') }
    setSyncing(false)
  }

  return (
    <div>
      {/* Component Status */}
      <h2 className="section-head"><span className="icon">⊞</span> Telemetry Matrix</h2>
      <div className="status-grid">
        <div className="status-card">
          <div className="status-icon">🚀</div>
          <div className="status-name">Backend API</div>
          <span className="badge badge-green">Running</span>
          <div className="status-detail">FastAPI (8001)</div>
        </div>
        <div className="status-card">
          <div className="status-icon">☁️</div>
          <div className="status-name">Central DB</div>
          <span className="badge badge-green">Linked</span>
          <div className="status-detail">Supabase PSQL</div>
        </div>
        <div className="status-card" style={{ borderColor: 'var(--gold-dim)', background: 'var(--bg-2)' }}>
          <div className="status-icon">🧠</div>
          <div className="status-name">Logic Core</div>
          <span className="badge badge-gold">Active</span>
          <div className="status-detail" style={{ color: 'var(--gold)' }}>Groq Llama-3</div>
        </div>
      </div>

      <div className="divider" />

      {/* Architecture */}
      <h2 className="section-head"><span className="icon">⚙</span> Stack Configuration</h2>
      <div className="card" style={{ padding: '16px 0 0', overflow: 'hidden' }}>
        <table className="table">
          <thead>
            <tr>
              <th style={{ paddingLeft: 24 }}>Node</th>
              <th>Protocol / Framework</th>
              <th style={{ paddingRight: 24, textAlign: 'right' }}>Condition</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['Routing Interface',   'React Vite App',         'Stable'],
              ['Logic Processor',     'LangGraph StateMachine', 'Stable'],
              ['Retrieval Engine',    'Agentic RAG / FAISS',    'Online'],
              ['Persistence Layer',   'SQLAlchemy ORM',         'Online'],
              ['Integration Watcher', 'Sys Watchdog Process',   'Polling'],
              ['Security Module',     'Session Verification',   'Enabled'],
            ].map(([n, t, s], i) => (
              <tr key={i}>
                <td style={{ fontWeight: 600, paddingLeft: 24, color: 'var(--ink-2)' }}>{n}</td>
                <td className="mono" style={{ color: 'var(--ink-4)', fontSize: 13 }}>{t}</td>
                <td style={{ textAlign: 'right', paddingRight: 24, fontSize: 12, fontWeight: 700, color: 'var(--green)', letterSpacing: '0.8px', textTransform: 'uppercase' }}>
                  {s}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
