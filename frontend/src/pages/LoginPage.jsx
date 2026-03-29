import { useState } from 'react'

export default function LoginPage({ onLogin, theme, toggleTheme }) {
  const [user, setUser] = useState('')
  const [pass, setPass] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    await new Promise(r => setTimeout(r, 350))
    if (!onLogin(user, pass)) setError('Incorrect username or password.')
    setLoading(false)
  }

  return (
    <div className="login-wrap" style={{ padding: '0 20px' }}>
      <div className="login-ambient" />
      <button className="login-theme-toggle" onClick={toggleTheme}>
        {theme === 'dark' ? '☀ Light' : '⏾ Dark'}
      </button>

      <div className="login-card">
        <div className="login-mark">
          <div className="login-mark-icon">☕</div>
          <div className="login-mark-name">AIBO</div>
        </div>
        <p className="login-tagline">AI-Powered Cafe Intelligence Platform</p>

        <form onSubmit={submit} autoComplete="on">
          <label className="login-label">Username</label>
          <input
            id="username"
            className="login-input"
            type="text"
            autoComplete="username"
            placeholder="admin"
            value={user}
            onChange={e => setUser(e.target.value)}
            required
          />
          <label className="login-label">Password</label>
          <input
            id="password"
            className="login-input"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={pass}
            onChange={e => setPass(e.target.value)}
            required
          />
          <button id="login-btn" className="login-btn" type="submit" disabled={loading}>
            {loading ? 'Authenticating…' : 'Sign in →'}
          </button>
          {error && <div className="login-error">{error}</div>}
        </form>

        <p style={{ marginTop: 22, fontSize: 11, color: 'var(--ink-4)', textAlign: 'center', letterSpacing: '0.3px' }}>
          Authorised staff access only · AIBO v1.3
        </p>
      </div>
    </div>
  )
}
