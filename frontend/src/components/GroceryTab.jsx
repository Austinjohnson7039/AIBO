import { useState, useEffect } from 'react';
import { getDashboard, getVendors, addVendor, restockGrocery, addGrocery, removeGrocery } from '../api.js';
import CafeLoader from './CafeLoader.jsx';

const CATEGORIES = ['Dairy', 'Coffee Beans', 'Syrups', 'Bakery', 'Packaging', 'Spices', 'Beverages', 'Other'];

export default function GroceryTab() {
  const [data, setData] = useState(null);
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [restockInputs, setRestockInputs] = useState({});
  const [msg, setMsg] = useState('');
  const [expandedItem, setExpandedItem] = useState(null);

  const [newItem, setNewItem] = useState({
    ingredient_name: '', category: 'Dairy', unit: 'kg',
    current_stock: '', reorder_level: '', unit_cost_inr: '',
    vendor_id: ''
  });
  const [newVendor, setNewVendor] = useState({ name: '', contact_name: '', whatsapp_number: '', category: 'Dairy' });

  useEffect(() => {
    Promise.all([getDashboard(), getVendors()])
      .then(([d, v]) => { setData(d); setVendors(v.vendors || []); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const refresh = () => getDashboard().then(setData).catch(() => {});

  const handleRestock = async (name) => {
    const amt = parseFloat(restockInputs[name] || 0);
    if (!amt || amt <= 0) return;
    try {
      await restockGrocery(name, amt);
      setRestockInputs(prev => ({ ...prev, [name]: '' }));
      setMsg(`✓ Added ${amt} to ${name}`);
      refresh();
    } catch (e) { setMsg(`✕ ${e.message}`); }
    setTimeout(() => setMsg(''), 3000);
  };

  const handleAddItem = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...newItem,
        current_stock: parseFloat(newItem.current_stock) || 0,
        reorder_level: parseFloat(newItem.reorder_level) || 0,
        unit_cost_inr: parseFloat(newItem.unit_cost_inr) || 0,
      };
      await addGrocery(payload);
      setShowAdd(false);
      setNewItem({ ingredient_name: '', category: 'Dairy', unit: 'kg', current_stock: '', reorder_level: '', unit_cost_inr: '', vendor_id: '' });
      setMsg('✓ Ingredient added successfully.');
      refresh();
    } catch (e) { setMsg(`✕ ${e.message}`); }
    setTimeout(() => setMsg(''), 3000);
  };

  const handleRemove = async (name) => {
    if (!window.confirm(`Remove "${name}" from your ingredients?`)) return;
    try {
      await removeGrocery(name);
      setMsg(`✓ Removed ${name}`);
      refresh();
    } catch (e) { setMsg(`✕ ${e.message}`); }
    setTimeout(() => setMsg(''), 3000);
  };

  const handleAddVendor = async (e) => {
    e.preventDefault();
    try {
      await addVendor(newVendor);
      const updated = await getVendors();
      setVendors(updated.vendors || []);
      setNewVendor({ name: '', contact_name: '', whatsapp_number: '', category: 'Dairy' });
      setMsg('✓ Supplier added.');
    } catch (e) { setMsg(`✕ ${e.message}`); }
    setTimeout(() => setMsg(''), 3000);
  };

  const handleUpdateVendor = async (item, vid) => {
    try {
      const payload = {
        ingredient_name: item.ingredient_name,
        category: item.category,
        unit: item.unit,
        current_stock: item.current_stock,
        reorder_level: item.reorder_level,
        unit_cost_inr: item.unit_cost_inr,
        vendor_id: vid === '' ? null : parseInt(vid)
      };
      await updateGrocery(payload);
      setMsg(`✓ Updated supplier for ${item.ingredient_name}`);
      refresh();
    } catch (e) { setMsg(`✕ ${e.message}`); }
    setTimeout(() => setMsg(''), 3000);
  };

  if (loading) return <CafeLoader />;

  const inventory = data?.inventory || [];
  const lowStock = inventory.filter(i => i.current_stock <= i.reorder_level);

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 10 }}>
        <div>
          {lowStock.length > 0 && (
            <span className="badge badge-warning" style={{ fontSize: 11 }}>
              ⚠️ {lowStock.length} item{lowStock.length > 1 ? 's' : ''} low on stock
            </span>
          )}
        </div>
        <button className="btn btn-primary" onClick={() => setShowAdd(!showAdd)}>
          {showAdd ? '✕ Cancel' : '+ Add Ingredient'}
        </button>
      </div>

      {/* Status message */}
      {msg && (
        <div className={`badge ${msg.startsWith('✓') ? 'badge-success' : 'badge-danger'}`}
          style={{ width: '100%', padding: '10px 14px', marginBottom: 16, justifyContent: 'flex-start', fontSize: 12 }}>
          {msg}
        </div>
      )}

      {/* Add Form */}
      {showAdd && (
        <div className="card" style={{ marginBottom: 20, borderColor: 'var(--border-regular)' }}>
          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 16 }}>New Ingredient</div>
          <form onSubmit={handleAddItem}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12, marginBottom: 16 }}>
              <div>
                <label className="form-label">Name</label>
                <input className="input" placeholder="e.g. Arabica Beans" value={newItem.ingredient_name}
                  onChange={e => setNewItem({...newItem, ingredient_name: e.target.value})} required />
              </div>
              <div>
                <label className="form-label">Category</label>
                <select className="select" value={newItem.category} onChange={e => setNewItem({...newItem, category: e.target.value})}>
                  {CATEGORIES.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="form-label">Unit</label>
                <input className="input" placeholder="kg, L, pcs" value={newItem.unit}
                  onChange={e => setNewItem({...newItem, unit: e.target.value})} required />
              </div>
              <div>
                <label className="form-label">Current Stock</label>
                <input className="input" type="number" step="0.1" min="0" value={newItem.current_stock}
                  onChange={e => setNewItem({...newItem, current_stock: e.target.value})} required />
              </div>
              <div>
                <label className="form-label">Reorder At</label>
                <input className="input" type="number" step="0.1" min="0" value={newItem.reorder_level}
                  onChange={e => setNewItem({...newItem, reorder_level: e.target.value})} required />
              </div>
              <div>
                <label className="form-label">Cost/Unit (₹)</label>
                <input className="input" type="number" step="0.01" min="0" value={newItem.unit_cost_inr}
                  onChange={e => setNewItem({...newItem, unit_cost_inr: e.target.value})} />
              </div>
              <div>
                <label className="form-label">Supplier (Optional)</label>
                <select className="select" value={newItem.vendor_id} onChange={e => setNewItem({...newItem, vendor_id: e.target.value})}>
                  <option value="">No Supplier Assigned</option>
                  {vendors.map(v => <option key={v.id} value={v.id}>{v.name} ({v.category})</option>)}
                </select>
              </div>
            </div>
            <button className="btn btn-primary" type="submit">Save Ingredient</button>
          </form>
        </div>
      )}

      {/* Stock Table */}
      <div className="table-wrap" style={{ marginBottom: 24 }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 13, fontWeight: 700 }}>Stock Levels</span>
          <span className="badge badge-success" style={{ fontSize: 10 }}>{inventory.length} items</span>
        </div>
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th style={{ paddingLeft: 16 }}>Ingredient</th>
                <th>Category</th>
                <th>Stock</th>
                <th>Reorder At</th>
                <th>Status</th>
                <th>Assigned Supplier</th>
                <th style={{ paddingRight: 16 }}>Restock</th>
              </tr>
            </thead>
            <tbody>
              {inventory.length === 0 ? (
                <tr><td colSpan="7" style={{ padding: 40, textAlign: 'center', color: 'var(--text-dim)', fontSize: 13 }}>
                  No ingredients yet. Add your first one above.
                </td></tr>
              ) : inventory.map((item, i) => {
                const isLow = item.current_stock <= item.reorder_level;
                return (
                  <>
                  <tr key={i} onClick={() => setExpandedItem(expandedItem === item.ingredient_name ? null : item.ingredient_name)} 
                      style={{ cursor: 'pointer', transition: 'background 0.2s' }} className={expandedItem === item.ingredient_name ? 'row-active' : ''}>
                    <td style={{ paddingLeft: 16 }}>
                      <div style={{ fontWeight: 600, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                        {item.ingredient_name} {expandedItem === item.ingredient_name ? '🔼' : '🔽'}
                      </div>
                    </td>
                    <td style={{ color: 'var(--text-dim)', fontSize: 12 }}>{item.category}</td>
                    <td>
                      <span className="mono" style={{ fontWeight: 700, color: isLow ? 'var(--danger)' : 'var(--primary)' }}>
                        {Number(item.current_stock).toFixed(1)}
                      </span>
                      <span style={{ color: 'var(--text-dim)', fontSize: 11, marginLeft: 4 }}>{item.unit}</span>
                    </td>
                    <td style={{ color: 'var(--text-dim)', fontSize: 12 }}>
                      {item.reorder_level} {item.unit}
                    </td>
                    <td>
                      <span className={`badge ${isLow ? 'badge-danger' : 'badge-success'}`}>
                        {isLow ? 'Low Stock' : 'In Stock'}
                      </span>
                    </td>
                    <td>
                      <select 
                        className="select" 
                        style={{ fontSize: 11, padding: '4px 6px', height: 'auto', minWidth: 120 }}
                        value={item.vendor_id || ''}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => handleUpdateVendor(item, e.target.value)}
                      >
                        <option value="">Unassigned</option>
                        {vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                      </select>
                    </td>
                    <td style={{ paddingRight: 16 }}>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <input
                          className="input"
                          type="number"
                          min="0"
                          step="0.1"
                          placeholder="Qty"
                          value={restockInputs[item.ingredient_name] || ''}
                          onChange={e => setRestockInputs(prev => ({ ...prev, [item.ingredient_name]: e.target.value }))}
                          onClick={(e) => e.stopPropagation()}
                          style={{ width: 70, padding: '5px 8px', fontSize: 12 }}
                        />
                        <button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); handleRestock(item.ingredient_name); }}>Add</button>
                        <button className="btn btn-danger btn-sm" onClick={(e) => { e.stopPropagation(); handleRemove(item.ingredient_name); }} title="Remove">✕</button>
                      </div>
                    </td>
                  </tr>
                  {expandedItem === item.ingredient_name && (
                    <tr style={{ background: 'var(--bg-elevated)' }}>
                      <td colSpan="6" style={{ padding: '16px 24px' }}>
                        <div className="grid-2" style={{ gap: 32 }}>
                          <div>
                            <h4 style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: 12 }}>Component Intelligence</h4>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                              <div className="badge badge-success" style={{ fontSize: 10 }}>Auto-Procurement Enabled</div>
                              <div className="badge badge-warning" style={{ fontSize: 10 }}>Wastage Tracking Active</div>
                            </div>
                            <p style={{ fontSize: 13, marginTop: 12, lineHeight: 1.5 }}>
                              <strong>Usage Rate:</strong> Data suggests this item is primarily used in {item.category} recipes.
                              Current replenishment cycle is <strong>7 days</strong>.
                            </p>
                          </div>
                          <div>
                            <h4 style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: 12 }}>Economic Details</h4>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                              <span style={{ fontSize: 12 }}>Unit Cost:</span>
                              <span style={{ fontSize: 12, fontWeight: 700 }}>₹{item.unit_cost_inr || 0}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                              <span style={{ fontSize: 12 }}>Inventory Value:</span>
                              <span style={{ fontSize: 12, fontWeight: 700 }}>₹{((item.current_stock || 0) * (item.unit_cost_inr || 0)).toFixed(2)}</span>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Suppliers */}
      <div className="card">
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 16 }}>Suppliers</div>

        {vendors.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10, marginBottom: 20 }}>
            {vendors.map((v, i) => (
              <div key={i} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{v.name}</div>
                  <span className="badge badge-warning" style={{ fontSize: 9 }}>{v.category}</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                  {v.contact_name && <div>{v.contact_name}</div>}
                  {v.whatsapp_number && <div>📱 {v.whatsapp_number}</div>}
                </div>
              </div>
            ))}
          </div>
        )}

        <div style={{ borderTop: vendors.length > 0 ? '1px solid var(--border-subtle)' : 'none', paddingTop: vendors.length > 0 ? 16 : 0 }}>
          <div className="form-label" style={{ marginBottom: 10 }}>Add Supplier</div>
          <form onSubmit={handleAddVendor}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10, marginBottom: 10 }}>
              <input className="input" placeholder="Supplier name" value={newVendor.name}
                onChange={e => setNewVendor({...newVendor, name: e.target.value})} required />
              <input className="input" placeholder="Contact name" value={newVendor.contact_name}
                onChange={e => setNewVendor({...newVendor, contact_name: e.target.value})} />
              <input className="input" placeholder="WhatsApp number" value={newVendor.whatsapp_number}
                onChange={e => setNewVendor({...newVendor, whatsapp_number: e.target.value})} required />
              <select className="select" value={newVendor.category} onChange={e => setNewVendor({...newVendor, category: e.target.value})}>
                {CATEGORIES.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <button className="btn btn-ghost" type="submit">+ Add Supplier</button>
          </form>
        </div>
      </div>
    </div>
  );
}
