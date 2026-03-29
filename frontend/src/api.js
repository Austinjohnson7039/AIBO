const BASE = import.meta.env.VITE_API_URL || '/api';

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
  return res.json();
}

// ── AI Chat ──────────────────────────────────────────────────────────────────
export const queryAI = (query) => request('POST', '/query/', { query });

// ── Dashboard ────────────────────────────────────────────────────────────────
export const getDashboard = () => request('GET', '/dashboard/');

// ── Grocery ──────────────────────────────────────────────────────────────────
export const restockGrocery = (ingredient_name, added_amount) =>
  request('POST', '/grocery/restock/', { ingredient_name, added_amount });

export const addGrocery = (data) => request('POST', '/grocery/add/', data);

export const removeGrocery = (ingredient_name) =>
  request('DELETE', '/grocery/remove/', { ingredient_name });

// ── Procurement & Vendors ────────────────────────────────────────────────────
export const getVendors = () => request('GET', '/vendors/');
export const addVendor = (data) => request('POST', '/vendors/add/', data);
export const triggerProcurement = () => request('POST', '/procurement/trigger', {});

// ── Analytics ────────────────────────────────────────────────────────────────
export const getForecast = () => request('GET', '/analytics/forecast/');
export const getTrends = () => request('GET', '/analytics/trends/');

// ── Sync ─────────────────────────────────────────────────────────────────────
export const triggerSync = () => request('POST', '/sync/manual/');

export async function exportSalesExcel() {
  const res = await fetch(`${BASE}/sync/export/sales`, { method: 'GET' });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to export sales');
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'AIBO_Premium_Sales_Report.xlsx';
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function uploadExcelSales(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE}/sync/upload/excel`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || 'Upload failed due to server error.');
  }
  return res.json();
}
