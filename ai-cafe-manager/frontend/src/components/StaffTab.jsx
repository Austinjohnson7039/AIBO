import { useState, useEffect } from 'react';
import { getStaff, getStaffSalaries, addStaff, clockIn, clockOut, getStaffingRecommendation, getWastage, addWastage } from '../api.js';

export default function StaffTab() {
  const [activeSubTab, setActiveSubTab] = useState('employees');
  
  // Data
  const [employees, setEmployees] = useState([]);
  const [salaries, setSalaries] = useState([]);
  const [wastage, setWastage] = useState([]);
  const [recommendation, setRecommendation] = useState('');
  
  // Forms
  const [newStaff, setNewStaff] = useState({ name: '', role: 'Barista', hourly_rate: 150 });
  const [newWastage, setNewWastage] = useState({ item_name: '', quantity: 1, loss_amount: 0, reason: 'expired' });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [staffRes, salRes, wasRes, recRes] = await Promise.all([
        getStaff(),
        getStaffSalaries(),
        getWastage(),
        getStaffingRecommendation()
      ]);
      setEmployees(staffRes.employees || []);
      setSalaries(salRes.salaries || []);
      setWastage(wasRes.wastage || []);
      setRecommendation(recRes.recommendation || '');
    } catch (err) {
      console.error("Error fetching staff data:", err);
    }
  };

  const handleAddStaff = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await addStaff(newStaff);
      setNewStaff({ name: '', role: 'Barista', hourly_rate: 150 });
      await fetchData();
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddWastage = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await addWastage(newWastage);
      setNewWastage({ item_name: '', quantity: 1, loss_amount: 0, reason: 'expired' });
      await fetchData();
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClock = async (id, action) => {
    try {
      if (action === 'in') await clockIn(id);
      else await clockOut(id);
      await fetchData();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      
      {/* AI Recommendation Alert */}
      {recommendation && (
        <div className="card" style={{ background: 'var(--surface-hover)', borderLeft: '4px solid var(--accent)', display: 'flex', gap: 16, alignItems: 'center' }}>
          <div style={{ fontSize: 32 }}>🤖</div>
          <div>
            <h3 style={{ margin: '0 0 4px 0', fontSize: 16 }}>AI Staffing Insight</h3>
            <p style={{ margin: 0, color: 'var(--text-dim)' }}>
              {recommendation}
            </p>
          </div>
        </div>
      )}

      {/* Sub Tabs */}
      <div className="auth-tabs" style={{ width: 'fit-content' }}>
        <button className={`auth-tab ${activeSubTab === 'employees' ? 'active' : ''}`} onClick={() => setActiveSubTab('employees')}>Staff & Shifts</button>
        <button className={`auth-tab ${activeSubTab === 'salaries' ? 'active' : ''}`} onClick={() => setActiveSubTab('salaries')}>Salaries</button>
        <button className={`auth-tab ${activeSubTab === 'wastage' ? 'active' : ''}`} onClick={() => setActiveSubTab('wastage')}>Expiry & Wastage</button>
      </div>

      {activeSubTab === 'employees' && (
        <div className="responsive-grid">
          {/* Employee List */}
          <div className="card">
            <h2 className="card-title">Employee Roster</h2>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <th style={{ padding: '12px 8px', color: 'var(--text-dim)', fontWeight: 500 }}>Name</th>
                    <th style={{ padding: '12px 8px', color: 'var(--text-dim)', fontWeight: 500 }}>Role</th>
                    <th style={{ padding: '12px 8px', color: 'var(--text-dim)', fontWeight: 500 }}>Rate/Hr</th>
                    <th style={{ padding: '12px 8px', color: 'var(--text-dim)', fontWeight: 500, textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.map(emp => (
                    <tr key={emp.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '16px 8px' }}>{emp.name}</td>
                      <td style={{ padding: '16px 8px' }}>
                        <span className="badge">{emp.role}</span>
                      </td>
                      <td style={{ padding: '16px 8px' }}>₹{emp.hourly_rate}</td>
                      <td style={{ padding: '16px 8px', textAlign: 'right' }}>
                        <button className="btn btn-ghost" style={{ fontSize: 13, padding: '4px 8px', marginRight: 8, border: '1px solid var(--border-subtle)' }} onClick={() => handleClock(emp.id, 'in')}>Clock In</button>
                        <button className="btn btn-ghost" style={{ fontSize: 13, padding: '4px 8px', border: '1px solid var(--border-subtle)' }} onClick={() => handleClock(emp.id, 'out')}>Clock Out</button>
                      </td>
                    </tr>
                  ))}
                  {employees.length === 0 && (
                    <tr><td colSpan="4" style={{ padding: 16, textAlign: 'center', color: 'var(--text-dim)' }}>No staff added.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Add Employee Form */}
          <div className="card">
            <h2 className="card-title">Hire Staff</h2>
            <form onSubmit={handleAddStaff} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="form-group">
                <label className="form-label">Name</label>
                <input className="input" value={newStaff.name} onChange={e => setNewStaff({...newStaff, name: e.target.value})} required />
              </div>
              <div className="form-group">
                <label className="form-label">Role</label>
                <select className="input" value={newStaff.role} onChange={e => setNewStaff({...newStaff, role: e.target.value})}>
                  <option>Barista</option>
                  <option>Chef</option>
                  <option>Manager</option>
                  <option>Cleaner</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Hourly Rate (₹)</label>
                <input type="number" className="input" value={newStaff.hourly_rate} onChange={e => setNewStaff({...newStaff, hourly_rate: e.target.value === '' ? '' : parseFloat(e.target.value)})} required />
              </div>
              <button disabled={loading} className="btn btn-primary" style={{ width: '100%' }}>Add Employee</button>
            </form>
          </div>
        </div>
      )}

      {activeSubTab === 'salaries' && (
        <div className="card">
          <h2 className="card-title">Salary Calculations</h2>
          <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <th style={{ padding: '12px 8px', color: 'var(--text-dim)', fontWeight: 500 }}>Name</th>
                <th style={{ padding: '12px 8px', color: 'var(--text-dim)', fontWeight: 500 }}>Total Hours</th>
                <th style={{ padding: '12px 8px', color: 'var(--text-dim)', fontWeight: 500 }}>Calculated Salary</th>
              </tr>
            </thead>
            <tbody>
              {salaries.map(sal => (
                <tr key={sal.employee_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '16px 8px' }}>{sal.name} <span style={{color: 'var(--text-dim)', fontSize: 12}}>({sal.role})</span></td>
                  <td style={{ padding: '16px 8px' }}>{sal.total_hours} hrs</td>
                  <td style={{ padding: '16px 8px', fontWeight: 'bold' }}>₹{sal.salary}</td>
                </tr>
              ))}
              {salaries.length === 0 && (
                <tr><td colSpan="3" style={{ padding: 16, textAlign: 'center', color: 'var(--text-dim)' }}>No salary data available.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeSubTab === 'wastage' && (
        <div className="responsive-grid">
          {/* Wastage Log */}
          <div className="card">
            <h2 className="card-title">Expiry & Wastage Ledger</h2>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <th style={{ padding: '12px 8px', color: 'var(--text-dim)', fontWeight: 500 }}>Date</th>
                    <th style={{ padding: '12px 8px', color: 'var(--text-dim)', fontWeight: 500 }}>Item</th>
                    <th style={{ padding: '12px 8px', color: 'var(--text-dim)', fontWeight: 500 }}>Qty</th>
                    <th style={{ padding: '12px 8px', color: 'var(--text-dim)', fontWeight: 500 }}>Reason</th>
                    <th style={{ padding: '12px 8px', color: 'var(--text-dim)', fontWeight: 500, color: '#ff6b6b' }}>Loss</th>
                  </tr>
                </thead>
                <tbody>
                  {wastage.map(w => (
                    <tr key={w.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '16px 8px' }}>{new Date(w.logged_at).toLocaleDateString()}</td>
                      <td style={{ padding: '16px 8px' }}>{w.item_name}</td>
                      <td style={{ padding: '16px 8px' }}>{w.quantity}</td>
                      <td style={{ padding: '16px 8px' }}><span className="badge" style={{background: 'var(--surface-hover)'}}>{w.reason}</span></td>
                      <td style={{ padding: '16px 8px', color: '#ff6b6b' }}>₹{w.loss_amount}</td>
                    </tr>
                  ))}
                  {wastage.length === 0 && (
                    <tr><td colSpan="5" style={{ padding: 16, textAlign: 'center', color: 'var(--text-dim)' }}>No wastage logged.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Add Wastage Form */}
          <div className="card">
            <h2 className="card-title">Log Loss</h2>
            <form onSubmit={handleAddWastage} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="form-group">
                <label className="form-label">Item Name</label>
                <input className="input" placeholder="e.g. Milk" value={newWastage.item_name} onChange={e => setNewWastage({...newWastage, item_name: e.target.value})} required />
              </div>
              <div style={{ display: 'flex', gap: 16 }}>
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label">Quantity</label>
                  <input type="number" step="0.1" className="input" value={newWastage.quantity} onChange={e => setNewWastage({...newWastage, quantity: e.target.value === '' ? '' : parseFloat(e.target.value)})} required />
                </div>
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label">Loss (₹)</label>
                  <input type="number" step="0.1" className="input" value={newWastage.loss_amount} onChange={e => setNewWastage({...newWastage, loss_amount: e.target.value === '' ? '' : parseFloat(e.target.value)})} required />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Reason</label>
                <select className="input" value={newWastage.reason} onChange={e => setNewWastage({...newWastage, reason: e.target.value})}>
                  <option value="expired">Expired</option>
                  <option value="spilled">Spilled / Damaged</option>
                  <option value="quality">Failed Quality Check</option>
                </select>
              </div>
              <button disabled={loading} className="btn" style={{ width: '100%', background: '#ff6b6b', color: 'white' }}>Record Wastage</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
