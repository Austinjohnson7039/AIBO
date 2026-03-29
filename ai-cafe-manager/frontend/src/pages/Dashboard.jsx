import { useState } from 'react'
import ChatTab from '../components/ChatTab.jsx'
import DashboardTab from '../components/DashboardTab.jsx'
import GroceryTab from '../components/GroceryTab.jsx'
import PredictTab from '../components/PredictTab.jsx'

const TABS = [
  { id: 'chat',      icon: '◈', label: 'Cafe Assistant' },
  { id: 'dashboard', icon: '⬡', label: 'Sales Dashboard' },
  { id: 'grocery',   icon: '⊞', label: 'Ingredients' },
  { id: 'predict',   icon: '◉', label: 'Forecasting' },
]

const META = {
  chat:      { h: 'Cafe Assistant',    sub: 'Natural language business intelligence.' },
  dashboard: { h: 'Sales Overview',   sub: 'Revenue KPIs and top performers.' },
  grocery:   { h: 'Ingredient Stock', sub: 'Raw material management and alerts.' },
  predict:   { h: 'AI Forecasting',   sub: 'Procurement needs and sales trends.' },
}

export default function Dashboard({ onLogout, theme, toggleTheme }) {
  const [tab, setTab] = useState('chat')
  const m = META[tab]

  return (
    <div className="layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="s-brand">
          <div className="s-brand-mark">☕</div>
          <div>
            <div className="s-brand-name">AIBO</div>
            <div className="s-brand-sub">Cafe Intelligence</div>
          </div>
        </div>

        <nav className="s-nav">
          <div className="s-section">Navigation</div>
          {TABS.map(t => (
            <button
              key={t.id}
              id={`nav-${t.id}`}
              className={`s-item${tab === t.id ? ' active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              <span className="s-icon">{t.icon}</span>
              <span>{t.label}</span>
            </button>
          ))}
        </nav>

        <div className="s-footer">
          <button className="s-footer-btn" onClick={toggleTheme}>
            <span>{theme === 'dark' ? '☀' : '⏾'}</span>
            <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
          </button>
          <button className="s-footer-btn danger" onClick={onLogout}>
            <span>↩</span>
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="content">
        <header className="topbar">
          <div className="topbar-left">
            <h1>{m.h}</h1>
            <div className="topbar-sub">{m.sub}</div>
          </div>
          <div className="topbar-right topbar-status">
            <span className="pulse" />
            <span>AI Online</span>
          </div>
        </header>

        <div className="page">
          {tab === 'chat'      && <ChatTab />}
          {tab === 'dashboard' && <DashboardTab />}
          {tab === 'grocery'   && <GroceryTab />}
          {tab === 'predict'   && <PredictTab />}
        </div>
      </div>
    </div>
  )
}
