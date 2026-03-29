import { useState, useRef } from 'react';
import { downloadTemplate, uploadExcelSales } from '../api.js';

export default function Onboarding({ onComplete }) {
  const [step, setStep] = useState(1);
  const [msg, setMsg] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setMsg('');
    setUploading(true);
    try {
      await uploadExcelSales(file);
      setMsg('✓ Sales data analyzed successfully! AI is now trained on your menu.');
      setTimeout(() => setStep(3), 2000);
    } catch (err) { 
      setMsg(`✕ ${err.message}`); 
    }
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="auth-page">
      <div className="auth-card" style={{ maxWidth: 500 }}>
        {step === 1 && (
          <div className="fade-in">
            <h1 className="brand-title" style={{ fontSize: 24, marginBottom: 12 }}>Welcome to AIBO 👋</h1>
            <p className="brand-sub" style={{ textAlign: 'left', marginBottom: 20 }}>
              You're about to supercharge your café. AIBO acts as your <strong>Senior Business Intelligence Consultant</strong>.
            </p>
            <div style={{ background: 'var(--bg-elevated)', padding: 16, borderRadius: 'var(--radius-md)', marginBottom: 20, fontSize: 13, lineHeight: 1.6, color: 'var(--text-secondary)' }}>
              <strong>Here's what you get:</strong>
              <ul style={{ paddingLeft: 20, marginTop: 10 }}>
                <li><strong>Predictive Forecasting:</strong> Know exactly what ingredients will run out before it happens.</li>
                <li><strong>Dynamic Smart Menu:</strong> Get AI-powered pricing strategies based on your inventory and the live weather.</li>
                <li><strong>Always-on Analyst:</strong> Ask the AI Assistant anything about your sales data naturally.</li>
              </ul>
            </div>
            <button className="btn btn-primary" style={{ width: '100%', padding: '12px' }} onClick={() => setStep(2)}>
              Get Started →
            </button>
            <div style={{ textAlign: 'center', marginTop: 16 }}>
              <button className="btn btn-ghost btn-sm" style={{ border: 'none' }} onClick={onComplete}>Skip setup</button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="fade-in">
            <h1 className="brand-title" style={{ fontSize: 24, marginBottom: 12 }}>Upload Your First Data 📊</h1>
            <p className="brand-sub" style={{ textAlign: 'left', marginBottom: 20 }}>
              To train your AI, we need to inject your historical sales. It only takes a second.
            </p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ border: '1px solid var(--border-regular)', borderRadius: 'var(--radius-md)', padding: 16 }}>
                <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>1. Download the Template</div>
                <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 12 }}>We've formatted a clean Excel file. Drop your past POS sales directly into it.</div>
                <button className="btn btn-ghost btn-sm" onClick={downloadTemplate}>⬇️ Download Template</button>
              </div>

              <div style={{ border: '1px solid var(--border-regular)', borderRadius: 'var(--radius-md)', padding: 16 }}>
                <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>2. Upload Sales Data</div>
                <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 12 }}>Upload the filled template. The AI will immediately parse and learn your top sellers.</div>
                <input type="file" accept=".xlsx, .xls" style={{ display: 'none' }} ref={fileInputRef} onChange={handleUpload} />
                <button className="btn btn-primary btn-sm" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
                  {uploading ? 'Processing...' : '⬆️ Upload Excel File'}
                </button>
              </div>
            </div>

            {msg && (
              <div style={{ marginTop: 16, padding: '10px', borderRadius: 'var(--radius-sm)', fontSize: 12, background: 'var(--bg-elevated)', color: msg.startsWith('✓') ? 'var(--success)' : 'var(--danger)', fontWeight: 600, whiteSpace: 'pre-wrap' }}>
                {msg}
              </div>
            )}

            <div style={{ textAlign: 'center', marginTop: 24 }}>
              <button className="btn btn-ghost btn-sm" style={{ border: 'none' }} onClick={onComplete}>I'll enter data manually later</button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="fade-in" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🚀</div>
            <h1 className="brand-title" style={{ fontSize: 24, marginBottom: 12 }}>You're All Set!</h1>
            <p className="brand-sub" style={{ marginBottom: 24 }}>
              Your café data has been synchronized. AIBO is fully online and ready to assist you.
            </p>
            <button className="btn btn-primary" style={{ width: '100%', padding: '12px' }} onClick={onComplete}>
              Go to Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
