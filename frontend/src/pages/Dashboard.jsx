import { useState, useEffect } from 'react';
import ChatTab from '../components/ChatTab';
import DashboardTab from '../components/DashboardTab';
import GroceryTab from '../components/GroceryTab';
import PredictTab from '../components/PredictTab';
import SmartMenuTab from '../components/SmartMenuTab';
import StaffTab from '../components/StaffTab';
import Onboarding from '../components/Onboarding';
import { login, signup } from '../api.js';

const TABS = [
  { id: 'chat',      label: 'AI Assistant', icon: '✨' },
  { id: 'dashboard', label: 'Dashboard', icon: '☕' },
  { id: 'grocery',   label: 'Ingredients', icon: '🧺' },
  { id: 'predict',   label: 'Forecast', icon: '📊' },
  { id: 'smart-menu',label: 'Menu', icon: '📋' },
  { id: 'staff',     label: 'Staff Settings', icon: '👥' },
];

export default function Dashboard() {
  const [token, setToken] = useState(localStorage.getItem('aibo_token'));
  const [view, setView] = useState('chat');
  const [authView, setAuthView] = useState('login');
  const [authData, setAuthData] = useState({ email: '', password: '', name: '', location: 'Bengaluru' });
  const [error, setError] = useState('');
  const [theme, setTheme] = useState(localStorage.getItem('aibo_theme') || 'dark');
  const [onboarding, setOnboarding] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('aibo_theme', theme);
  }, [theme]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const res = await login(authData.email, authData.password);
      localStorage.setItem('aibo_token', res.access_token);
      setToken(res.access_token);
    } catch {
      setError('Invalid email or password. Please try again.');
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await signup(authData);
      // Auto-login after successful signup to trigger the onboarding wizard immediately
      const res = await login(authData.email, authData.password);
      localStorage.setItem('aibo_token', res.access_token);
      setToken(res.access_token);
      setOnboarding(true);
      setError('');
    } catch (err) {
      setError(err.message || 'Signup failed.');
    }
  };

  const logout = () => {
    localStorage.removeItem('aibo_token');
    setToken(null);
  };

  // ── Auth Screen ──
  if (!token) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <div style={{ textAlign: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 36 }}>☕</span>
          </div>
          <h1 className="brand-title">AIBO</h1>
          <p className="brand-sub">AI-Powered Café Manager</p>

          <div className="auth-tabs">
            <button className={`auth-tab ${authView === 'login' ? 'active' : ''}`} onClick={() => { setAuthView('login'); setError(''); }}>Sign In</button>
            <button className={`auth-tab ${authView === 'signup' ? 'active' : ''}`} onClick={() => { setAuthView('signup'); setError(''); }}>Register</button>
          </div>

          <form onSubmit={authView === 'login' ? handleLogin : handleSignup}>
            {authView === 'signup' && (
              <div className="form-group">
                <label className="form-label">Café Name</label>
                <input className="input" placeholder="e.g. Brew & Bloom" onChange={e => setAuthData({...authData, name: e.target.value})} required />
              </div>
            )}
            <div className="form-group">
              <label className="form-label">Email</label>
              <input className="input" type="email" placeholder="you@cafe.com" onChange={e => setAuthData({...authData, email: e.target.value})} required />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input className="input" type="password" placeholder="••••••••" onChange={e => setAuthData({...authData, password: e.target.value})} required />
            </div>
            {authView === 'signup' && (
              <div className="form-group">
                <label className="form-label">City</label>
                <select className="select" onChange={e => setAuthData({...authData, location: e.target.value})}>
                  <option>Bengaluru</option><option>Mumbai</option><option>Delhi</option><option>Pune</option><option>Chennai</option>
                </select>
              </div>
            )}

            {error && <div className="badge badge-danger" style={{ width: '100%', padding: '10px 14px', marginBottom: 16, justifyContent: 'center' }}>{error}</div>}

            <button className="btn btn-primary" style={{ width: '100%', padding: 12 }}>
              {authView === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (onboarding) {
    return <Onboarding onComplete={() => setOnboarding(false)} />;
  }

  // ── Main App ──
  return (
    <div className="app-layout">
      {/* Sidebar — desktop only */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>☕ AIBO</h1>
          <p>Café Intelligence</p>
        </div>
        <nav className="sidebar-nav">
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={`nav-item ${view === tab.id ? 'active' : ''}`}
              onClick={() => setView(tab.id)}
            >
              <span className="nav-icon">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
        <div style={{ paddingTop: 16, borderTop: '1px solid var(--border-subtle)', marginTop: 'auto' }}>
          <button className="nav-item" style={{ color: 'var(--text-dim)' }} onClick={logout}>
            <span className="nav-icon">🚪</span> Log Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="page-header">
          <div>
            <h1>{TABS.find(t => t.id === view)?.icon} {TABS.find(t => t.id === view)?.label}</h1>
            <p className="page-header-sub">Manage your café with AI</p>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <button className="btn btn-ghost" style={{ padding: '6px 10px', fontSize: 16, border: 'none' }} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
            <div className="status-pill">
              <span className="status-dot" />
              Online
            </div>
          </div>
        </header>

        <section className="fade-in" key={view}>
          {view === 'dashboard' && <DashboardTab />}
          {view === 'chat' && <ChatTab />}
          {view === 'grocery' && <GroceryTab />}
          {view === 'predict' && <PredictTab />}
          {view === 'smart-menu' && <SmartMenuTab />}
          {view === 'staff' && <StaffTab />}
        </section>
      </main>

      {/* Mobile Bottom Tabs */}
      <div className="mobile-tabs">
        <div className="mobile-tabs-inner">
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={`mobile-tab ${view === tab.id ? 'active' : ''}`}
              onClick={() => setView(tab.id)}
            >
              <span className="tab-icon">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
