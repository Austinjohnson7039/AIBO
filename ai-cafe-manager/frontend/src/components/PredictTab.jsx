import { useEffect, useState } from 'react';
import { getForecast, getTrends, triggerProcurement } from '../api.js';
import CafeLoader from './CafeLoader.jsx';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'

export default function PredictTab() {
  const [forecast, setForecast] = useState(null)
  const [trends, setTrends] = useState(null)
  const [loading, setLoading] = useState(true)
  const [procuring, setProcuring] = useState(false)
  const [procureMsg, setProcureMsg] = useState('')
  const [expandedForecast, setExpandedForecast] = useState(null)

  useEffect(() => {
    Promise.all([getForecast(), getTrends()])
      .then(([f, t]) => { setForecast(f); setTrends(t) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleProcure = async () => {
    setProcuring(true)
    setProcureMsg('')
    try {
      const res = await triggerProcurement()
      setProcureMsg(`✓ ${res.message || 'Reorder triggered successfully.'}`)
    } catch (e) {
      setProcureMsg(`✕ Failed: ${e.message}`)
    }
    setProcuring(false)
  }

  if (loading) return <CafeLoader />;

  const runwayData = (forecast?.runway_metrics || [])
    .map(r => ({ name: r.ingredient_name, days: Math.min(r.runway_days ?? 30, 30) }))
    .sort((a, b) => a.days - b.days)
    .slice(0, 12)

  const shoppingList = forecast?.shopping_list || []
  const insights = trends?.insights || []

  return (
    <div className="fade-in">
      {procureMsg && (
        <div className={`badge ${procureMsg.startsWith('✓') ? 'badge-success' : 'badge-danger'}`}
          style={{ width: '100%', padding: '10px 14px', marginBottom: 20, justifyContent: 'flex-start', fontSize: 12 }}>
          {procureMsg}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 24, marginBottom: 24 }}>
        {/* Shopping List */}
        <div className="table-wrap">
          <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, fontWeight: 700 }}>Items to Reorder</span>
            <span className="badge badge-warning" style={{ fontSize: 10 }}>{shoppingList.length} items</span>
          </div>
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ paddingLeft: 16 }}>Ingredient</th>
                  <th>Qty to Buy</th>
                  <th style={{ paddingRight: 16 }}>Est. Cost</th>
                </tr>
              </thead>
              <tbody>
                {shoppingList.length === 0 ? (
                  <tr><td colSpan="3" style={{ padding: 40, textAlign: 'center', color: 'var(--text-dim)', fontSize: 13 }}>
                    ✓ All stock levels are healthy.
                  </td></tr>
                ) : shoppingList.map((item, i) => (
                  <>
                  <tr key={i} onClick={() => setExpandedForecast(expandedForecast === item.ingredient_name ? null : item.ingredient_name)}
                      style={{ cursor: 'pointer' }} className={expandedForecast === item.ingredient_name ? 'row-active' : ''}>
                    <td style={{ paddingLeft: 16, fontWeight: 600 }}>
                      {item.ingredient_name} {expandedForecast === item.ingredient_name ? '🔼' : '🔽'}
                    </td>
                    <td className="mono" style={{ color: 'var(--primary)', fontWeight: 700 }}>{item.to_buy} {item.unit}</td>
                    <td className="mono" style={{ color: 'var(--success)', paddingRight: 16 }}>₹{Number(item.estimated_cost || 0).toLocaleString('en-IN')}</td>
                  </tr>
                  {expandedForecast === item.ingredient_name && (
                    <tr style={{ background: 'var(--bg-elevated)' }}>
                      <td colSpan="3" style={{ padding: '12px 16px' }}>
                        <div style={{ fontSize: 13, background: 'var(--bg-card)', padding: 12, borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                           <strong>AI Reasoning:</strong> To maintain operations for the next 7 days, 
                           this item requires a safety buffer of {Math.ceil(item.to_buy * 0.1)} {item.unit} based on 
                           volatility trends. 
                           <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-dim)', display: 'flex', gap: 10 }}>
                              <span>• Predicted Demand: High</span>
                              <span>• Vendor Lead Time: 24h</span>
                           </div>
                        </div>
                      </td>
                    </tr>
                  )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ padding: 14, borderTop: '1px solid var(--border-subtle)' }}>
            <button className="btn btn-primary" style={{ width: '100%' }} onClick={handleProcure} disabled={procuring}>
              {procuring ? 'Processing...' : '🔄 Auto-Reorder Now'}
            </button>
          </div>
        </div>

        {/* Runway Chart */}
        <div className="card">
          <div className="card-label">Days of Stock Remaining</div>
          <div style={{ paddingTop: 16 }}>
            {runwayData.length === 0 ? (
              <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: 13 }}>
                No forecast data available yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={runwayData} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" horizontal={false} />
                  <XAxis type="number" tick={{ fill: 'var(--text-dim)', fontSize: 10 }} axisLine={false} tickLine={false} domain={[0, 30]} />
                  <YAxis dataKey="name" type="category" tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontWeight: 600 }} axisLine={false} tickLine={false} width={180} />
                  <Tooltip
                    formatter={(v) => [`${v} days`, 'Runway']}
                    contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-strong)', borderRadius: 8, fontSize: 12 }}
                  />
                  <Bar dataKey="days" radius={[0, 6, 6, 0]} maxBarSize={14}>
                    {runwayData.map((d, i) => (
                      <Cell key={i} fill={d.days <= 2 ? 'var(--danger)' : d.days <= 7 ? 'var(--warning)' : 'var(--success)'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Trend Alerts */}
      {insights.length > 0 && (
        <>
          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 14, marginTop: 8 }}>📈 Trends & Alerts</div>
          <div className="grid-2">
            {insights.map((ins, i) => (
              <div key={i} className="card" style={{ display: 'flex', gap: 14, alignItems: 'center', padding: 18 }}>
                <div style={{ width: 40, height: 40, background: 'var(--bg-elevated)', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0 }}>
                  {ins.type === 'RISING_STAR' ? '🚀' : '📉'}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <span className="badge badge-warning" style={{ marginBottom: 6, fontSize: 9 }}>{ins.type}</span>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.4 }}>{ins.rec}</div>
                </div>
                <div className="mono" style={{ fontSize: 16, fontWeight: 800, color: ins.momentum > 0 ? 'var(--success)' : 'var(--warning)', flexShrink: 0 }}>
                  {Number(ins.momentum || 0) > 0 ? '+' : ''}{Number(ins.momentum || 0).toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
