import { useEffect, useState } from 'react';
import { getSmartMenu } from '../api.js';

export default function SmartMenuTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getSmartMenu()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="fade-in">
      <div className="card" style={{ height: 400, opacity: 0.3 }} />
    </div>
  );

  if (error) return (
    <div className="fade-in">
      <div className="card" style={{ textAlign: 'center', padding: 40 }}>
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>Could not load menu insights. {error}</p>
      </div>
    </div>
  );

  const recommendations = data?.recommendations || [];

  return (
    <div className="fade-in">
      {/* Location Banner */}
      <div className="card" style={{ marginBottom: 20, padding: '18px 24px', display: 'flex', alignItems: 'center', gap: 20, background: 'var(--bg-elevated)', borderColor: 'var(--border-regular)', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 36 }}>{data?.location === 'Bengaluru' ? '☀️' : '⛅'}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="card-label" style={{ marginBottom: 2 }}>Location: {data?.location}</div>
          <div style={{ fontSize: 14, fontWeight: 700 }}>
            {recommendations.length > 0 ? 'Price Suggestions Ready' : 'Pricing is Optimised'}
          </div>
          <p style={{ color: 'var(--text-dim)', fontSize: 12, marginTop: 4, lineHeight: 1.5 }}>
            AIBO analyses real-time local weather and demand trends in {data?.location} to suggest optimal pricing.
          </p>
        </div>
      </div>

      {/* Recommendations Table */}
      <div className="table-wrap">
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
          <span style={{ fontSize: 13, fontWeight: 700 }}>Menu Price Suggestions</span>
        </div>
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th style={{ paddingLeft: 16 }}>Item</th>
                <th>Current Price</th>
                <th>Suggested Price</th>
                <th>Strategy</th>
                <th style={{ paddingRight: 16 }}>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {recommendations.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ padding: 50, textAlign: 'center', color: 'var(--text-dim)', fontSize: 13 }}>
                    <span style={{ fontSize: 30, display: 'block', marginBottom: 10 }}>✓</span>
                    Your prices are already optimised for current conditions.
                  </td>
                </tr>
              ) : (
                recommendations.map((rec, i) => (
                  <tr key={i}>
                    <td style={{ paddingLeft: 16 }}>
                      <div style={{ fontWeight: 600 }}>{rec.item}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>{rec.reason}</div>
                    </td>
                    <td className="mono" style={{ color: 'var(--text-dim)' }}>₹{rec.current_price}</td>
                    <td className="mono" style={{ color: 'var(--primary)', fontWeight: 700 }}>₹{rec.suggested_price}</td>
                    <td>
                      <span className={`badge ${rec.type === 'SURGE' ? 'badge-warning' : 'badge-success'}`}>
                        {rec.type === 'SURGE' ? '📈 Surge' : '📉 Discount'}
                      </span>
                    </td>
                    <td style={{ paddingRight: 16 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 50, height: 4, background: 'var(--border-strong)', borderRadius: 2 }}>
                          <div style={{ width: `${rec.confidence || 85}%`, height: '100%', background: 'var(--success)', borderRadius: 2 }} />
                        </div>
                        <span className="mono" style={{ fontSize: 10, color: 'var(--text-dim)' }}>{rec.confidence || 85}%</span>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
