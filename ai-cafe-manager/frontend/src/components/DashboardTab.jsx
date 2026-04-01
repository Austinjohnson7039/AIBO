import { useEffect, useState, useRef } from 'react';
import { getDashboard, exportSalesExcel, uploadExcelSales, queryAI } from '../api.js';
import CafeLoader from './CafeLoader.jsx';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  AreaChart, Area, PieChart, Pie, Legend
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-strong)', borderRadius: 'var(--radius-md)', padding: '10px 14px', boxShadow: 'var(--shadow-md)' }}>
        <p style={{ fontWeight: 600, fontSize: 10, marginBottom: 4, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-dim)' }}>{label}</p>
        <p style={{ color: 'var(--primary)', fontSize: 16, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>₹{Number(payload[0].value).toLocaleString('en-IN')}</p>
      </div>
    )
  }
  return null
}

export default function DashboardTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')
  const [expandedKpi, setExpandedKpi] = useState(null) // 'revenue', 'items', 'margin' or null
  const fileInputRef = useRef(null)

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const askAI = async () => {
    // Deprecated in Dashboard
  }

  const handleExport = async () => {
    setMsg('')
    try {
      await exportSalesExcel()
      setMsg('✓ Data exported successfully.')
    } catch (e) { setMsg(`✕ Export failed: ${e.message}`) }
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setMsg('')
    try {
      const res = await uploadExcelSales(file)
      setMsg(res.message ? `✓ ${res.message}` : '✓ Upload complete.')
      getDashboard().then(setData)
    } catch (err) { setMsg(`✕ Upload error: ${err.message}`) }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  if (loading) return <CafeLoader />;

  const kpis = data?.kpis || {}
  const chartData = Object.entries(kpis.top_5 || {}).map(([name, rev]) => ({ name, revenue: rev }))
  const COLORS = ['#F59E0B', '#10B981', '#3B82F6', '#8B5CF6', '#EC4899', '#34D399', '#FBBF24']
  const alerts = data?.alerts || []
  const advanced = data?.advanced_reports || {}

  return (
    <div className="fade-in">

      {/* ── KPIs ── */}
      <div className="kpi-grid">
        <div className={`kpi-card ${expandedKpi === 'revenue' ? 'active' : ''}`} 
             onClick={() => setExpandedKpi(expandedKpi === 'revenue' ? null : 'revenue')}
             style={{ cursor: 'pointer', transition: 'all 0.2s', border: expandedKpi === 'revenue' ? '1px solid var(--primary)' : '1px solid transparent' }}>
          <div className="kpi-icon" style={{ background: 'var(--primary-dim)' }}>☕</div>
          <div className="card-label">Revenue Overview 🔍</div>
          <div className="card-value accent">₹{(kpis.total_rev || 0).toLocaleString('en-IN')}</div>
        </div>
        <div className={`kpi-card ${expandedKpi === 'items' ? 'active' : ''}`}
             onClick={() => setExpandedKpi(expandedKpi === 'items' ? null : 'items')}
             style={{ cursor: 'pointer', transition: 'all 0.2s', border: expandedKpi === 'items' ? '1px solid var(--accent)' : '1px solid transparent' }}>
          <div className="kpi-icon" style={{ background: 'var(--accent-dim)' }}>📦</div>
          <div className="card-label">Items Sold 🔍</div>
          <div className="card-value">{(kpis.total_items || 0).toLocaleString('en-IN')}</div>
        </div>
        <div className={`kpi-card ${expandedKpi === 'margin' ? 'active' : ''}`}
             onClick={() => setExpandedKpi(expandedKpi === 'margin' ? null : 'margin')}
             style={{ cursor: 'pointer', transition: 'all 0.2s', border: expandedKpi === 'margin' ? '1px solid var(--warning)' : '1px solid transparent' }}>
          <div className="kpi-icon" style={{ background: 'var(--warning-dim)' }}>📈</div>
          <div className="card-label">Gross Margin 🔍</div>
          <div className="card-value">{advanced.gross_margin_pct || 0}%</div>
        </div>
        <div className="kpi-card" style={{ opacity: 0.8 }}>
          <div className="kpi-icon" style={{ background: 'var(--success-dim)' }}>💰</div>
          <div className="card-label">Today's Revenue</div>
          <div className="card-value" style={{ color: 'var(--success)' }}>₹{(kpis.today_rev || 0).toLocaleString('en-IN')}</div>
        </div>
      </div>

      {/* ── Drill-down Detail View ── */}
      {expandedKpi && (
        <div className="card fade-in" style={{ marginBottom: 20, border: '1px solid var(--border-strong)', background: 'var(--bg-card)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ margin: 0, fontSize: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
               {expandedKpi === 'revenue' ? '💰 Revenue Deep Dive' : expandedKpi === 'items' ? '📦 Item Breakdown' : '📉 Profitability Analysis'}
            </h3>
            <button className="btn btn-ghost" onClick={() => setExpandedKpi(null)} style={{ padding: '4px 8px' }}>Close</button>
          </div>

          <div style={{ overflowX: 'auto' }}>
            {expandedKpi === 'revenue' && (
              <div className="grid-3" style={{ gap: 20 }}>
                <div>
                  <h4 style={{ fontSize: 12, color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: 10 }}>Daily (Recent)</h4>
                  <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
                    <thead><tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border-subtle)' }}><th style={{ padding: 8 }}>Date</th><th style={{ padding: 8 }}>Rev</th></tr></thead>
                    <tbody>
                      {advanced.daily_sales?.slice(-5).reverse().map((r, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: 8 }}>{r.date}</td>
                          <td style={{ padding: 8, fontWeight: 600 }}>₹{(Number(r.revenue) || 0).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div>
                  <h4 style={{ fontSize: 12, color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: 10 }}>Weekly</h4>
                  <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
                    <thead><tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border-subtle)' }}><th style={{ padding: 8 }}>Week Start</th><th style={{ padding: 8 }}>Rev</th></tr></thead>
                    <tbody>
                      {advanced.weekly_sales?.slice(-5).reverse().map((r, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: 8 }}>{r.week}</td>
                          <td style={{ padding: 8, fontWeight: 600 }}>₹{(Number(r.revenue) || 0).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div>
                  <h4 style={{ fontSize: 12, color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: 10 }}>Monthly</h4>
                  <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
                    <thead><tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border-subtle)' }}><th style={{ padding: 8 }}>Month</th><th style={{ padding: 8 }}>Rev</th></tr></thead>
                    <tbody>
                      {advanced.monthly_sales?.slice(-5).reverse().map((r, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: 8 }}>{r.month}</td>
                          <td style={{ padding: 8, fontWeight: 600 }}>₹{(Number(r.revenue) || 0).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            
            {expandedKpi === 'items' && (
              <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
                    <thead><tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border-subtle)' }}>
                      <th style={{ padding: 12 }}>Product Name</th>
                      <th style={{ padding: 12 }}>Total Revenue Generated</th>
                    </tr></thead>
                    <tbody>
                      {Object.entries(kpis.top_5 || {}).map(([name, rev], i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: 12, fontWeight: 500 }}>{name}</td>
                          <td style={{ padding: 12, fontWeight: 700, color: 'var(--primary)' }}>₹{(Number(rev) || 0).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
              </table>
            )}

            {expandedKpi === 'margin' && (
              <div>
                <p style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 16 }}>
                  Gross Margin reflects Earnings after Cost of Goods Sold (COGS). 
                  Target: <strong>&gt; 65%</strong> for café stability.
                </p>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  {advanced.category_performance?.map((c, i) => (
                    <div key={i} className="card" style={{ flex: '1 1 150px', padding: 12, textAlign: 'center', background: 'var(--bg-elevated)' }}>
                      <div className="card-label" style={{ fontSize: 10 }}>{c.category}</div>
                      <div style={{ fontSize: 18, fontWeight: 700 }}>₹{(Number(c.revenue) || 0).toLocaleString()}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Alerts ── */}
      {alerts.length > 0 && (
        <div style={{ marginBottom: 20, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {alerts.slice(0, 3).map((a, i) => (
            <div key={i} className={`badge ${a.level === 'CRITICAL' ? 'badge-danger' : 'badge-warning'}`}
              style={{ padding: '8px 14px', fontSize: 12, width: '100%', justifyContent: 'flex-start' }}>
              {a.level === 'CRITICAL' ? '🚨' : '⚠️'} {a.msg}
            </div>
          ))}
        </div>
      )}

      {/* ── AI Insight Banner ── */}
      {advanced.ai_insight && advanced.ai_insight !== "Not enough data for insights." && (
        <div className="card fade-in" style={{ marginBottom: 20, background: 'var(--bg-elevated)', borderLeft: '4px solid #F59E0B', display: 'flex', gap: 16, alignItems: 'center', padding: '16px 24px' }}>
          <div style={{ fontSize: 24 }}>🧠</div>
          <div>
            <h3 style={{ margin: '0 0 4px 0', fontSize: 14 }}>Advanced Analytics</h3>
            <p style={{ margin: 0, color: 'var(--text-dim)', fontSize: 13 }}>
              {advanced.ai_insight}
            </p>
          </div>
        </div>
      )}

      {/* ── Data Actions ── */}
      <div className="card" style={{ marginBottom: 20, display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
        <div>
          <div className="card-label">Sales Data</div>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', margin: '4px 0 0' }}>
            Import your POS sales from Excel, or export your café data for offline analysis.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <input type="file" accept=".xlsx, .xls" style={{ display: 'none' }} ref={fileInputRef} onChange={handleUpload} />
          <button className="btn btn-primary" onClick={() => fileInputRef.current?.click()}>Import Sales</button>
          <button className="btn btn-ghost" onClick={handleExport}>Export Data</button>
          {msg && (
            <div style={{ fontSize: 12, color: msg.startsWith('✓') ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }}>
              {msg}
            </div>
          )}
        </div>
      </div>

      {/* ── Advanced Analytics Charts ── */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        {/* Daily Sales Trend */}
        <div className="card">
          <div className="card-label">14-Day Revenue Trend</div>
          <div style={{ paddingTop: 16 }}>
            {(!advanced.daily_sales || advanced.daily_sales.length === 0) ? (
              <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: 13 }}>No recent data.</div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={advanced.daily_sales} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: 'var(--text-dim)', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: 'var(--text-dim)', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="revenue" stroke="#10B981" fillOpacity={1} fill="url(#colorRev)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Peak Hours Analysis */}
        <div className="card">
          <div className="card-label">Peak Operating Hours</div>
          <div style={{ paddingTop: 16 }}>
            {(!advanced.peak_hours || advanced.peak_hours.length === 0) ? (
              <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: 13 }}>No operational data.</div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={advanced.peak_hours} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                  <XAxis dataKey="hour" tick={{ fill: 'var(--text-dim)', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: 'var(--text-dim)', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--border-subtle)' }} />
                  <Bar dataKey="revenue" fill="#3B82F6" radius={[4, 4, 0, 0]} maxBarSize={40} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        {/* Category Performance */}
        <div className="card">
          <div className="card-label">Sales by Category</div>
          <div style={{ paddingTop: 16 }}>
            {(!advanced.category_performance || advanced.category_performance.length === 0) ? (
              <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: 13 }}>No category data.</div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={advanced.category_performance} dataKey="revenue" nameKey="category" cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={2}>
                    {advanced.category_performance?.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 11, color: 'var(--text-dim)' }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* ── Original Charts ── */}
        <div className="card">
          <div className="card-label">Top Selling Items</div>
          <div style={{ paddingTop: 16 }}>
            {chartData.length === 0 ? (
              <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: 13 }}>
                No sales data yet. Import your first Excel or record sales through AI chat.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" horizontal={false} />
                  <XAxis type="number" tick={{ fill: 'var(--text-dim)', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }} axisLine={false} tickLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
                  <YAxis dataKey="name" type="category" tick={{ fill: 'var(--text-primary)', fontSize: 11, fontWeight: 500 }} axisLine={false} tickLine={false} width={100} />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--border-subtle)' }} />
                  <Bar dataKey="revenue" radius={[0, 6, 6, 0]} maxBarSize={24}>
                    {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
