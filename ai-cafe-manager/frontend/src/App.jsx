import { useState, useEffect } from 'react'
import LoginPage from './pages/LoginPage.jsx'
import Dashboard from './pages/Dashboard.jsx'

const CREDS = {
  user: import.meta.env.VITE_APP_USERNAME || 'admin',
  pass: import.meta.env.VITE_APP_PASSWORD || 'cafe123',
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('aibo-theme') || 'dark')
  const [authed, setAuthed] = useState(() => sessionStorage.getItem('aibo-auth') === 'true')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('aibo-theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')

  const login = (u, p) => {
    if (u === CREDS.user && p === CREDS.pass) {
      sessionStorage.setItem('aibo-auth', 'true')
      setAuthed(true)
      return true
    }
    return false
  }

  const logout = () => {
    sessionStorage.removeItem('aibo-auth')
    setAuthed(false)
  }

  if (!authed) return <LoginPage onLogin={login} theme={theme} toggleTheme={toggleTheme} />
  return <Dashboard onLogout={logout} theme={theme} toggleTheme={toggleTheme} />
}
