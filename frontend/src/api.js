const rawBase = import.meta.env.VITE_API_URL || '';
const BASE = rawBase.endsWith('/api') ? rawBase : `${rawBase}/api`;

/**
 * Universal request handler with JWT injection
 * Modern SaaS Secure Layer
 */
async function request(method, path, body = null, isFormData = false) {
  const token = localStorage.getItem('aibo_token');
  const headers = {};
  
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Ensure path starts with /
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  
  const opts = { method, headers };
  if (body) {
    opts.body = isFormData ? body : JSON.stringify(body);
  }

  const res = await fetch(`${BASE}${cleanPath}`, opts);
  
  // Handle Session Expiry
  if (res.status === 401 && !path.includes('/auth/')) {
    localStorage.removeItem('aibo_token');
    window.location.reload(); 
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server Error ${res.status}`);
  }
  
  return res.json();
}

// ── Auth ─────────────────────────────────────────────────────────────────────
export const login = (email, password) => {
  const formData = new URLSearchParams();
  formData.append('username', email); 
  formData.append('password', password);
  
  return fetch(`${BASE}/auth/login`, {
    method: 'POST',
    body: formData
  }).then(res => {
     if (!res.ok) throw new Error('Authentication failed');
     return res.json();
  });
};

export const signup = (data) => request('POST', '/auth/signup', data);

// ── Dashboard & Stock ────────────────────────────────────────────────────────
export const getDashboard = () => request('GET', '/dashboard/');
export const restockGrocery = (ingredient_name, added_amount) =>
  request('POST', '/grocery/restock/', { ingredient_name, added_amount });
export const addGrocery = (data) => request('POST', '/grocery/add/', data);
export const updateGrocery = (data) => request('PATCH', '/grocery/update/', data);
export const removeGrocery = (ingredient_name) =>
  request('DELETE', `/grocery/remove/?ingredient_name=${encodeURIComponent(ingredient_name)}`);

// ── Smart Menu ───────────────────────────────────────────────────────────────
export const getSmartMenu = () => request('GET', '/analytics/smart-menu/');

// ── AI Chat ──────────────────────────────────────────────────────────────────
export const queryAI = (query) => request('POST', '/query/', { query });

// ── Forecasting & Procurement ────────────────────────────────────────────────
export const getForecast = () => request('GET', '/analytics/forecast/');
export const getTrends = () => request('GET', '/analytics/trends/');
export const getVendors = () => request('GET', '/vendors/');
export const addVendor = (data) => request('POST', '/vendors/add/', data);
export const triggerProcurement = () => request('POST', '/procurement/trigger', {});

// ── Sync ─────────────────────────────────────────────────────────────────────
export async function uploadExcelSales(file) {
  const formData = new FormData();
  formData.append('file', file);
  return request('POST', '/sync/upload/excel', formData, true);
}

export async function exportSalesExcel() {
  const token = localStorage.getItem('aibo_token');
  const res = await fetch(`${BASE}/sync/export/sales`, {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Status ${res.status}: ${text}`);
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'AIBO_Premium_Export.xlsx';
  a.click();
}

export async function downloadTemplate() {
  const token = localStorage.getItem('aibo_token');
  const res = await fetch(`${BASE}/sync/template`, {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!res.ok) throw new Error('Failed to download template');
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'AIBO_Sales_Template.xlsx';
  a.click();
}

// ── Employee & Staffing ──────────────────────────────────────────────────────
export const getStaff = () => request('GET', '/staff/');
export const getStaffSalaries = () => request('GET', '/staff/salaries/');
export const addStaff = (data) => request('POST', '/staff/add/', data);
export const clockIn = (id) => request('POST', `/staff/clock-in/${id}`, {});
export const clockOut = (id) => request('POST', `/staff/clock-out/${id}`, {});
export const getStaffingRecommendation = () => request('GET', '/analytics/staffing-recommendation/');

// ── Wastage ──────────────────────────────────────────────────────────────────
export const getWastage = () => request('GET', '/wastage/');
export const addWastage = (data) => request('POST', '/wastage/add/', data);
