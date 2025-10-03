import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// Bootstrap validation policy (default lenient) so it's sticky across reloads
try {
  const saved = localStorage.getItem('validation_policy');
  const policy = saved ?? 'lenient';
  (window as any)._VALIDATION_POLICY = policy;
  if (!saved) localStorage.setItem('validation_policy', policy);
  // Housekeep expired fixed copy at app boot
  try {
    const metaRaw = localStorage.getItem('censys_fixed_meta');
    const copy = localStorage.getItem('censys_fixed_copy');
    if (metaRaw && copy) {
      const meta = JSON.parse(metaRaw);
      const exp = Number(meta?.expires_at || 0);
      if (exp && Date.now() > exp) {
        localStorage.removeItem('censys_fixed_copy');
        localStorage.removeItem('censys_fixed_meta');
      }
    }
  } catch {}
} catch {}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)