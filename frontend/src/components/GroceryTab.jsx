import { useEffect, useState } from 'react'
import { getDashboard, restockGrocery, addGrocery, removeGrocery, getVendors, addVendor } from '../api.js'

function StockItem({ item }) {
  let stock = item.current_stock
  let unit = item.unit || ''
  const reorder = item.reorder_level
  
  // Smart metric aggregation
  if (stock >= 1000) {
    if (unit.toLowerCase() === 'g') { stock = stock / 1000; unit = 'kg' }
    if (unit.toLowerCase() === 'ml') { stock = stock / 1000; unit = 'L' }
  }
  const displayStock = (typeof stock === 'number' && stock % 1 !== 0) ? stock.toFixed(2).replace(/\.00$/, '') : stock;

  // The ratio bar requires the raw base units logically, but we use the new string for UI
  const ratio = reorder > 0 ? Math.min(item.current_stock / (reorder * 2), 1) : 1
  const cls = item.current_stock <= 0 ? 'danger' : item.current_stock <= reorder ? 'warn' : 'ok'

  return (
    <div className="stock-item">
      <div className="stock-item-name">{item.ingredient_name}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
        <span className={`stock-qty ${cls}`}>{displayStock}</span>
        <span className="stock-unit">{unit}</span>
      </div>
      <div className="stock-bar">
        <div className={`stock-bar-fill ${cls}`} style={{ width: `${ratio * 100}%` }} />
      </div>
      <div className="stock-reorder">Reorder at {reorder}</div>
    </div>
  )
}

function AlertBanner({ alert }) {
  const cls = alert.level === 'CRITICAL' ? 'alert-red' : alert.level === 'LOW' ? 'alert-amber' : 'alert-green'
  const icon = alert.level === 'CRITICAL' ? '⨯' : alert.level === 'LOW' ? '⚠' : 'ℹ'
  return (
    <div className={`alert ${cls}`} style={{ marginBottom: 12 }}>
      <span className="alert-icon" style={{ fontWeight: 800 }}>{icon}</span>
      <div>{alert.msg}</div>
    </div>
  )
}

export default function GroceryTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')

  const [vendors, setVendors] = useState([])

  const refresh = () => {
    setLoading(true)
    getDashboard()
      .then(setData)
      .catch(() => setMsg('Failed to fetch stock DB.'))
      .finally(() => setLoading(false))
  }
  
  const refreshVendors = () => {
    getVendors().then(r => setVendors(r.vendors || [])).catch(()=>{})
  }

  useEffect(() => { 
    refresh()
    refreshVendors()
  }, [])

  const [rsSel, setRsSel] = useState('')
  const [rsAmt, setRsAmt] = useState('')
  const [rsLoading, setRsLoading] = useState(false)

  const [addForm, setAddForm] = useState({ ingredient_name: '', category: 'Vegetable', unit: 'g', current_stock: '', reorder_level: '', unit_cost_inr: '' })
  const [addLoading, setAddLoading] = useState(false)

  const [delSel, setDelSel] = useState('')
  const [delConfirm, setDelConfirm] = useState(false)
  const [delLoading, setDelLoading] = useState(false)

  const [vForm, setVForm] = useState({ name: '', contact_name: '', whatsapp_number: '', category: 'Produce' })
  const [vLoading, setVLoading] = useState(false)

  const allIngredients = data ? Object.values(data.stock_by_category || {}).flat().map(i => i.ingredient_name).sort() : []

  const handleRestock = async () => {
    if (!rsSel || !rsAmt) return
    setRsLoading(true)
    try {
      const res = await restockGrocery(rsSel, parseFloat(rsAmt))
      setMsg(res.status === 'success' ? `✅ ${res.message}` : `⚠ ${res.message}`)
      refresh()
    } catch { setMsg('⚠ Restock operation failed.') }
    setRsLoading(false)
  }

  const handleAdd = async () => {
    if (!addForm.ingredient_name) return
    setAddLoading(true)
    try {
      const p = { ...addForm, current_stock: parseFloat(addForm.current_stock) || 0, reorder_level: parseFloat(addForm.reorder_level) || 0, unit_cost_inr: parseFloat(addForm.unit_cost_inr) || 0 }
      const res = await addGrocery(p)
      setMsg(res.status === 'success' ? `✅ ${res.message}` : `⚠ ${res.message}`)
      if (res.status === 'success') {
        setAddForm({ ingredient_name: '', category: 'Vegetable', unit: 'g', current_stock: '', reorder_level: '', unit_cost_inr: '' })
        refresh()
      }
    } catch { setMsg('⚠ Item registration failed.') }
    setAddLoading(false)
  }

  const handleRemove = async () => {
    if (!delSel || !delConfirm) return
    setDelLoading(true)
    try {
      const res = await removeGrocery(delSel)
      setMsg(res.status === 'success' ? `✅ ${res.message}` : `⚠ ${res.message}`)
      setDelConfirm(false); setDelSel('')
      refresh()
    } catch { setMsg('⚠ Deletion failed.') }
    setDelLoading(false)
  }

  const handleAddVendor = async () => {
    if (!vForm.name || !vForm.whatsapp_number) return
    setVLoading(true)
    try {
      const res = await addVendor(vForm)
      setMsg(res.status === 'success' ? `✅ ${res.message}` : `⚠ ${res.message}`)
      if (res.status === 'success') {
        setVForm({ name: '', contact_name: '', whatsapp_number: '', category: 'Produce' })
        refreshVendors()
      }
    } catch { setMsg('⚠ Vendor registration failed.') }
    setVLoading(false)
  }

  if (loading) return <div className="skeleton" style={{ height: 400 }} />

  return (
    <div>
      {msg && (
        <div className={`alert ${msg.startsWith('✅') ? 'alert-green' : 'alert-red'}`} style={{ marginBottom: 20 }}>
          <span className="alert-icon">{msg.startsWith('✅') ? '✓' : '⚠'}</span>
          <div>{msg.slice(2)}</div>
        </div>
      )}

      {/* Alerts */}
      <h2 className="section-head"><span className="icon">◈</span> Operational Alerts</h2>
      {data?.alerts?.length > 0 ? (
        data.alerts.map((a, i) => <AlertBanner key={i} alert={a} />)
      ) : (
        <div className="alert alert-green">
          <span className="alert-icon">✓</span>
          <div>All raw materials are adequately stocked. Zero disruptions predicted.</div>
        </div>
      )}

      <div className="divider" />

      {/* Stock Graph */}
      <h2 className="section-head"><span className="icon">⊞</span> Live Inventory Matrix</h2>
      {Object.entries(data?.stock_by_category || {}).map(([cat, items]) => (
        <div key={cat} style={{ marginBottom: 24 }}>
          <div className="cat-label">
            {cat} <span style={{ opacity: 0.5, marginLeft: 4 }}>({items.length})</span>
          </div>
          <div className="stock-grid">
            {items.map((item, i) => <StockItem key={i} item={item} />)}
          </div>
        </div>
      ))}

      <div className="divider" />

      {/* Management Cards */}
      <h2 className="section-head"><span className="icon">⬡</span> Inventory Administration</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>

        {/* Restock */}
        <div className="card">
          <div className="card-label" style={{ marginBottom: 16 }}>Log Inbound Shipment</div>
          <div className="field" style={{ marginBottom: 14 }}>
            <label className="field-label">SKU / Item</label>
            <select className="select" value={rsSel} onChange={e => setRsSel(e.target.value)}>
              <option value="">-- View Catalog --</option>
              {allIngredients.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div className="field" style={{ marginBottom: 20 }}>
            <label className="field-label">Quantity Received</label>
            <input className="input mono" type="number" min="0" value={rsAmt} onChange={e => setRsAmt(e.target.value)} placeholder="0.00" />
          </div>
          <button className="btn btn-gold btn-full" onClick={handleRestock} disabled={rsLoading || !rsSel || !rsAmt}>
            {rsLoading ? 'Recording...' : 'Append Stock +'}
          </button>
        </div>

        {/* Add New */}
        <div className="card">
          <div className="card-label" style={{ marginBottom: 16 }}>Register New SKU</div>
          <div className="form-2col">
            <div className="field">
              <label className="field-label">Name</label>
              <input className="input" value={addForm.ingredient_name} onChange={e => setAddForm(f => ({...f, ingredient_name: e.target.value}))} placeholder="Almond Milk" />
            </div>
            <div className="field">
              <label className="field-label">Category</label>
              <select className="select" value={addForm.category} onChange={e => setAddForm(f => ({...f, category: e.target.value}))}>
                {['Vegetable','Meat','Dairy','Bakery','Sauce','Fruit','Grocery','Other'].map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div className="field">
              <label className="field-label">UoM (Unit)</label>
              <select className="select" value={addForm.unit} onChange={e => setAddForm(f => ({...f, unit: e.target.value}))}>
                {['g','pcs','ml','slice','kg','L'].map(u => <option key={u}>{u}</option>)}
              </select>
            </div>
            <div className="field">
              <label className="field-label">Cost/Unit Value</label>
              <input className="input mono" type="number" min="0" step="0.1" value={addForm.unit_cost_inr} onChange={e => setAddForm(f => ({...f, unit_cost_inr: e.target.value}))} placeholder="0.00" />
            </div>
            <div className="field">
              <label className="field-label">Initial Volume</label>
              <input className="input mono" type="number" min="0" value={addForm.current_stock} onChange={e => setAddForm(f => ({...f, current_stock: e.target.value}))} placeholder="0" />
            </div>
            <div className="field">
              <label className="field-label">Alert Threshold</label>
              <input className="input mono" type="number" min="0" value={addForm.reorder_level} onChange={e => setAddForm(f => ({...f, reorder_level: e.target.value}))} placeholder="0" />
            </div>
          </div>
          <button className="btn btn-ghost btn-full" onClick={handleAdd} disabled={addLoading || !addForm.ingredient_name} style={{ marginTop: 20 }}>
            {addLoading ? 'Registering...' : 'Save New Material'}
          </button>
        </div>

        {/* Remove */}
        <div className="card">
          <div className="card-label" style={{ marginBottom: 16 }}>Deprecate SKU</div>
          <div className="field" style={{ marginBottom: 18 }}>
            <label className="field-label">Target Item</label>
            <select className="select" value={delSel} onChange={e => setDelSel(e.target.value)}>
              <option value="">-- View Catalog --</option>
              {allIngredients.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: 'var(--ink-2)', marginBottom: 20, cursor: 'pointer' }}>
            <input type="checkbox" checked={delConfirm} onChange={e => setDelConfirm(e.target.checked)} />
            Verify permanent deletion
          </label>
          <button className="btn btn-danger btn-full" onClick={handleRemove} disabled={delLoading || !delSel || !delConfirm}>
            {delLoading ? 'Erasing...' : 'Delete Completely'}
          </button>
        </div>

      </div>

      <div className="divider" />

      {/* Vendors */}
      <h2 className="section-head"><span className="icon">🤝</span> Wholesale Network</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>
        <div className="card">
          <div className="card-label" style={{ marginBottom: 16 }}>Register Supply Partner</div>
          <div className="field" style={{ marginBottom: 14 }}>
            <label className="field-label">Company Name</label>
            <input className="input" value={vForm.name} onChange={e=>setVForm(f=>({...f, name: e.target.value}))} placeholder="Heritage Dairy" />
          </div>
          <div className="field" style={{ marginBottom: 14 }}>
            <label className="field-label">Contact Person</label>
            <input className="input" value={vForm.contact_name} onChange={e=>setVForm(f=>({...f, contact_name: e.target.value}))} placeholder="John Doe" />
          </div>
          <div className="field" style={{ marginBottom: 14 }}>
            <label className="field-label">WhatsApp Num (w/ code)</label>
            <input className="input mono" value={vForm.whatsapp_number} onChange={e=>setVForm(f=>({...f, whatsapp_number: e.target.value}))} placeholder="+919876543210" />
          </div>
          <div className="field" style={{ marginBottom: 20 }}>
            <label className="field-label">Supply Category</label>
            <select className="select" value={vForm.category} onChange={e=>setVForm(f=>({...f, category: e.target.value}))}>
               {['Produce','Dairy','Meat','Bakery','Coffee','Packaging','Hardware'].map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <button className="btn btn-ghost btn-full" onClick={handleAddVendor} disabled={vLoading || !vForm.name || !vForm.whatsapp_number}>
            {vLoading ? 'Adding...' : 'Establish Partnership'}
          </button>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <div className="card-label" style={{ marginBottom: 16 }}>Active Directory</div>
          {vendors.length === 0 ? (
            <div className="empty"><div className="empty-icon">♢</div><p>No external vendors registered yet.</p></div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {vendors.map(v => (
                <div key={v.id} style={{ padding: 12, border: '1px solid var(--border)', borderRadius: 8, background: 'var(--bg-2)' }}>
                  <div style={{ fontWeight: 650, color: 'var(--ink-1)', fontSize: 13 }}>{v.name} <span style={{ opacity: 0.5, fontWeight: 500 }}>({v.category})</span></div>
                  <div style={{ fontSize: 12, color: 'var(--ink-4)', marginTop: 4 }}>
                    {v.contact} • <span className="mono">{v.whatsapp}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
