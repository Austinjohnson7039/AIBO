import { useEffect, useState, useRef } from 'react'
import { getDashboard, exportSalesExcel, uploadExcelSales } from '../api.js'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'

function KpiCard({ label, value, sub, accent }) {
  return (
    <div className="card">
      <div className="card-label">{label}</div>
      <div className={`card-value ${accent ? 'accent' : ''}`}>{value}</div>
      {sub && <div className="card-sub">{sub}</div>}
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: 'var(--bg-1)', border: '1px solid var(--border-md)', borderRadius: 'var(--r-md)', padding: '10px 14px', boxShadow: 'var(--shadow-2)' }}>
        <p style={{ fontWeight: 650, fontSize: 11, marginBottom: 5, letterSpacing: '0.8px', textTransform: 'uppercase', color: 'var(--ink-3)' }}>{label}</p>
        <p style={{ color: 'var(--gold)', fontSize: 16, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>₹{Number(payload[0].value).toLocaleString('en-IN')}</p>
      </div>
    )
  }
  return null
}

export default function DashboardTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  
  const fileInputRef = useRef(null)
  const [downloading, setDownloading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [msg, setMsg] = useState('')

  const handleExport = async () => {
    setDownloading(true)
    setMsg('')
    try {
      await exportSalesExcel()
      setMsg('✓ Sales export downloaded successfully.')
    } catch (e) { setMsg(`⨯ Export failed: ${e.message}`) }
    setDownloading(false)
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    setMsg('')
    try {
      const res = await uploadExcelSales(file)
      setMsg(res.message ? `✓ ${res.message}` : '✓ Excel data uploaded.')
      // Refresh dashboard data instantly 
      getDashboard().then(setData)
    } catch (err) {
      setMsg(`⨯ Upload error: ${err.message}`)
    }
    setUploading(false)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div>
      <div className="kpi-grid">
        {[1,2,3,4].map(i => <div key={i} className="skeleton" style={{ height: 110 }} />)}
      </div>
      <div className="skeleton" style={{ height: 350 }} />
    </div>
  )

  const kpis = data?.kpis || {}
  const top5 = kpis.top_5 || {}
  const chartData = Object.entries(top5).map(([name, rev]) => ({ name, revenue: rev }))
  const COLORS = ['#C9962A', '#E3B44A', '#D4A017', '#B3831F', '#A07010']

  return (
    <div>
      <h2 className="section-head"><span className="icon">⬡</span> Revenue Intelligence</h2>
      <div className="kpi-grid">
        <KpiCard
          label="Today's Velocity"
          value={`₹${(kpis.today_rev || 0).toLocaleString('en-IN', {maximumFractionDigits:0})}`}
          sub="Live from Supabase Cloud"
          accent
        />
        <KpiCard
          label="Weekly Bookings"
          value={`₹${(kpis.week_rev || 0).toLocaleString('en-IN', {maximumFractionDigits:0})}`}
          sub="Last 7 calendar days"
        />
        <KpiCard
          label="Monthly Revenue"
          value={`₹${(kpis.month_rev || 0).toLocaleString('en-IN', {maximumFractionDigits:0})}`}
          sub="Month to date aggregate"
        />
        <KpiCard
          label="Units Moved"
          value={(kpis.total_items || 0).toLocaleString('en-IN')}
          sub="All time transactions"
        />
      </div>

      <div className="divider" />

      <h2 className="section-head"><span className="icon">↓↑</span> Excel Data Gateway</h2>
      <div className="card" style={{ marginBottom: 32, padding: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <p style={{ fontSize: 13, color: 'var(--ink-4)', marginTop: 4 }}>
              Upload unformatted POS Excel reports for intelligent parsing, or download live analytical databases.
            </p>
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <input 
            type="file" 
            accept=".xlsx, .xls" 
            style={{ display: 'none' }} 
            ref={fileInputRef} 
            onChange={handleUpload} 
          />
          <button className="btn btn-gold" onClick={() => fileInputRef.current?.click()} disabled={uploading || downloading}>
            <span className="icon">↑</span> {uploading ? 'Processing XL...' : 'Upload Daily Sales (.xlsx)'}
          </button>
          
          <button className="btn btn-ghost" onClick={handleExport} disabled={downloading || uploading}>
            <span className="icon">↓</span> {downloading ? 'Exporting...' : 'Download Export (.xlsx)'}
          </button>
        </div>
        
        {msg && (
          <div style={{ marginTop: 16, fontSize: 12.5, color: msg.startsWith('✓') ? 'var(--green)' : 'var(--red)', fontWeight: 650, letterSpacing: '0.5px' }}>
            {msg}
          </div>
        )}
      </div>

      <div className="divider" />

      <h2 className="section-head"><span className="icon">🏆</span> Bestseller Analysis</h2>
      
      <div className="card" style={{ padding: '28px 20px 10px' }}>
        {chartData.length === 0
          ? <div className="empty"><div className="empty-icon">📊</div><p>Insufficient transaction data to model.</p></div>
          : (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={chartData} margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: 'var(--ink-3)', fontSize: 12, fontWeight: 500 }} axisLine={false} tickLine={false} dy={10} />
                <YAxis tick={{ fill: 'var(--ink-4)', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }} axisLine={false} tickLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} dx={-10} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--bg-2)' }} />
                <Bar dataKey="revenue" radius={[6, 6, 0, 0]} maxBarSize={55}>
                  {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )
        }
      </div>
    </div>
  )
}
