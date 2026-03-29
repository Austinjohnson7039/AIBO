import { useEffect, useState } from 'react'
import { getForecast, getTrends, triggerProcurement } from '../api.js'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'

export default function PredictTab() {
  const [forecast, setForecast] = useState(null)
  const [trends, setTrends] = useState(null)
  const [loading, setLoading] = useState(true)
  const [procuring, setProcuring] = useState(false)
  const [procureMsg, setProcureMsg] = useState('')

  const handleProcure = async () => {
    setProcuring(true)
    setProcureMsg('')
    try {
      const res = await triggerProcurement()
      setProcureMsg(`✓ ${res.message}`)
    } catch (e) {
      setProcureMsg(`⨯ Agent failed: ${e.message}`)
    }
    setProcuring(false)
  }

  useEffect(() => {
    Promise.all([getForecast(), getTrends()])
      .then(([f, t]) => { setForecast(f); setTrends(t) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
      <div className="skeleton" style={{ height: 400 }} />
      <div className="skeleton" style={{ height: 400 }} />
    </div>
  )

  const shopList = forecast?.shopping_list || []
  const runway = forecast?.runway_metrics || []
  const insights = trends?.insights || []
  
  const criticalCount = runway.filter(r => r.runway_days <= 2.0).length
  const readyToOrder = criticalCount > 3

  // Prioritize urgent runways
  const runwayData = runway
    .map(r => ({ name: r.ingredient_name, days: Math.min(r.runway_days, 30) }))
    .sort((a, b) => a.days - b.days)
    .slice(0, 15)

  return (
    <div>
      {procureMsg && (
        <div className={`alert ${procureMsg.startsWith('✓') ? 'alert-green' : 'alert-amber'}`} style={{ marginBottom: 20 }}>
          <span className="alert-icon">{procureMsg.startsWith('✓') ? '✓' : '⚠'}</span>
          <div>{procureMsg}</div>
        </div>
      )}
      {forecast?.error && (
        <div className="alert alert-amber" style={{ marginBottom: 20 }}>
          <span className="alert-icon">⚠</span>
          <div>{forecast.error}</div>
        </div>
      )}

      <h2 className="section-head"><span className="icon">◉</span> Algorithmic Procurement</h2>

      <div className="dashboard-grid">

        {/* Shopping List */}
        <div className="card" style={{ padding: '24px 0 0', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 24px', marginBottom: 20 }}>
            <div>
              <div className="card-label">Auto-Generated PO</div>
              <p style={{ fontSize: 13, color: 'var(--ink-4)', marginTop: 4 }}>
                Optimised stock order for {forecast?.forecast_period_days || 7} days
              </p>
            </div>
            
            <button 
              className="btn btn-gold" 
              onClick={handleProcure} 
              disabled={procuring || !readyToOrder}
              style={{ 
                opacity: readyToOrder ? 1 : 0.6, 
                padding: '8px 16px', 
                fontSize: 13, 
                minWidth: 'max-content',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              {procuring ? 'Deploying...' : 'Force Manual Deploy'}
            </button>
          </div>
          
          <div style={{ padding: '0 24px 16px' }}>
            <span className={`badge ${readyToOrder ? 'badge-green' : 'badge-amber'}`} style={{ marginRight: 10 }}>
              Agent Status: {readyToOrder ? 'Ready To Dispatch' : 'Awaiting Threshold'}
            </span>
            <span style={{ fontSize: 12, color: 'var(--ink-4)', fontWeight: 500 }}>
              {criticalCount} critical items identified (Requires &gt; 3 to trigger automated batch order)
            </span>
          </div>

          {shopList.length === 0
            ? <div className="empty" style={{ padding: '40px 20px', flex: 1 }}><div className="empty-icon">✓</div><p>Inventory buffer sufficient.</p></div>
            : (
              <table className="table">
                <thead>
                  <tr>
                    <th style={{ paddingLeft: 24 }}>SKU</th>
                    <th>Volume</th>
                    <th>Unit</th>
                    <th style={{ paddingRight: 24 }}>Capex (Est)</th>
                  </tr>
                </thead>
                <tbody>
                  {shopList.map((item, i) => {
                    let qty = item.to_buy;
                    let u = item.unit || '';
                    if (qty >= 1000) {
                      if (u.toLowerCase() === 'g') { qty = qty / 1000; u = 'kg'; }
                      if (u.toLowerCase() === 'ml') { qty = qty / 1000; u = 'L'; }
                    }
                    const displayQty = (typeof qty === 'number' && qty % 1 !== 0) ? qty.toFixed(1).replace(/\.0$/, '') : qty;

                    return (
                      <tr key={i}>
                        <td style={{ fontWeight: 650, paddingLeft: 24 }}>{item.ingredient_name}</td>
                        <td className="mono" style={{ color: 'var(--gold)', fontWeight: 800 }}>
                          {displayQty}
                        </td>
                        <td style={{ color: 'var(--ink-4)' }}>{u}</td>
                        <td className="mono" style={{ color: 'var(--green)', paddingRight: 24 }}>
                          {item.estimated_cost ? `₹${Number(item.estimated_cost).toLocaleString('en-IN')}` : '—'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )
          }
        </div>

        {/* Runway Chart */}
        <div className="card" style={{ padding: '24px 20px 10px' }}>
          <div className="card-label">Runway Volatility</div>
          <p style={{ fontSize: 13, color: 'var(--ink-4)', marginBottom: 24 }}>
            Days of viable stock remaining per SKU
          </p>

          {runwayData.length === 0
            ? <div className="empty"><div className="empty-icon">📉</div><p>Insufficient consumption data.</p></div>
            : (
              <div style={{ width: '100%', overflowX: 'auto', overflowY: 'hidden' }}>
                <div style={{ minWidth: 400 }}>
                  <ResponsiveContainer width="100%" height={Math.max(260, runwayData.length * 28)}>
                    <BarChart data={runwayData} layout="vertical" margin={{ top: 0, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                      <XAxis type="number" tick={{ fill: 'var(--ink-4)', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }} axisLine={false} tickLine={false} domain={[0, 30]} />
                      <YAxis dataKey="name" type="category" tick={{ fill: 'var(--ink-3)', fontSize: 11, fontWeight: 500 }} axisLine={false} tickLine={false} width={130} interval={0} />
                      <Tooltip
                        formatter={(v) => [`${v} days`, 'Runway']}
                        contentStyle={{ background: 'var(--bg-1)', border: '1px solid var(--border-md)', borderRadius: 8, padding: '10px 14px', boxShadow: 'var(--shadow-3)' }}
                        itemStyle={{ color: 'var(--ink-1)', fontWeight: 600, fontSize: 13 }}
                        labelStyle={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-3)', textTransform: 'uppercase', marginBottom: 5 }}
                      />
                      <Bar dataKey="days" radius={[0, 4, 4, 0]} maxBarSize={14}>
                        {runwayData.map((d, i) => (
                          <Cell key={i} fill={d.days <= 2 ? 'var(--red)' : d.days <= 5 ? 'var(--amber)' : 'var(--green)'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )
          }
        </div>
      </div>

      <div className="divider" />

      <h2 className="section-head"><span className="icon">📣</span> Marketing Subroutines</h2>

      {trends?.error ? (
        <div className="empty"><div className="empty-icon">◇</div><p>{trends.error}</p></div>
      ) : insights.length === 0 ? (
        <div className="empty"><div className="empty-icon">◒</div><p>Trend deviations below threshold. Requires larger dataset.</p></div>
      ) : (
        insights.map((ins, i) => (
          <div key={i} className={`insight insight-${ins.type === 'RISING_STAR' ? 'rising' : 'slowing'}`}>
            <div style={{ flex: 1 }}>
              <div className={`insight-tag ${ins.type === 'RISING_STAR' ? 'rising' : 'slowing'}`}>
                {ins.type === 'RISING_STAR' ? 'Acceleration' : 'Deceleration'}
              </div>
              <div className="insight-text">{ins.rec}</div>
            </div>
            <div className="mono" style={{ alignSelf: 'center', fontSize: 18, fontWeight: 800, color: ins.type === 'RISING_STAR' ? 'var(--green)' : 'var(--amber)' }}>
              {ins.momentum > 0 ? '+' : ''}{ins.momentum}%
            </div>
          </div>
        ))
      )}
    </div>
  )
}
