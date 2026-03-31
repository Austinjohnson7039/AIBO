import React from 'react';

export default function CafeLoader() {
  return (
    <div className="cafe-loader-container fade-in">
      <div className="coffee-cup">
        <div className="steam steam-1"></div>
        <div className="steam steam-2"></div>
        <div className="steam steam-3"></div>
      </div>
      <div className="loader-text">Brewing data...</div>
      <style>{`
        .cafe-loader-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 250px;
          height: 100%;
          width: 100%;
        }
        
        .coffee-cup {
          position: relative;
          width: 44px;
          height: 36px;
          background: var(--primary);
          border-bottom-left-radius: 18px;
          border-bottom-right-radius: 18px;
          margin-bottom: 24px;
          animation: bounce 1.5s infinite ease-in-out;
        }

        .coffee-cup::after {
          content: '';
          position: absolute;
          top: 4px;
          right: -12px;
          width: 14px;
          height: 18px;
          border: 4px solid var(--primary);
          border-left: none;
          border-radius: 0 10px 10px 0;
        }

        .steam {
          position: absolute;
          width: 3px;
          height: 14px;
          background: var(--text-dim);
          border-radius: 4px;
          bottom: 40px;
          opacity: 0;
          animation: rise 1.5s infinite ease-in;
        }

        .steam-1 { left: 12px; animation-delay: 0.1s; background: var(--primary); }
        .steam-2 { left: 21px; animation-delay: 0.5s; background: var(--accent); }
        .steam-3 { left: 30px; animation-delay: 0.3s; background: var(--warning); }

        @keyframes rise {
          0% { transform: translateY(0) scale(1); opacity: 0; }
          40% { opacity: 0.8; }
          100% { transform: translateY(-24px) scale(1.5); opacity: 0; }
        }

        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-6px); }
        }

        .loader-text {
          font-family: 'JetBrains Mono', monospace;
          font-size: 13px;
          font-weight: 500;
          color: var(--text-dim);
          letter-spacing: 0.05em;
          animation: pulse-text 1.5s infinite ease-in-out;
          text-transform: uppercase;
        }

        @keyframes pulse-text {
          0%, 100% { opacity: 0.5; }
          50% { opacity: 1; color: var(--primary); }
        }
      `}</style>
    </div>
  );
}
