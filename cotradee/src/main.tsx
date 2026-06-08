import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './assets/index.css';

// Note: the navigator.userAgentData polyfill required by
// lightweight-charts 4.2.0 loads as an EXTERNAL classic script
// (public/uad-polyfill.js) referenced from index.html's <head>. A
// classic <head> script still executes before any ES module
// (including Vite's pre-bundled deps and HMR re-evaluations), and
// being external keeps the page CSP at script-src 'self' with no
// inline-script hash to maintain. See
// cotradee/src/lib/userAgentDataPolyfill.ts for the typed reference
// implementation.

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
