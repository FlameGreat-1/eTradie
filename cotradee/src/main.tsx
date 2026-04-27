import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './assets/index.css';

// Note: the navigator.userAgentData polyfill required by
// lightweight-charts 4.2.0 runs as an inline <script> in index.html,
// which is the only place guaranteed to execute before any ES module
// (including Vite's pre-bundled deps and HMR re-evaluations).
// See cotradee/src/lib/userAgentDataPolyfill.ts for the typed
// reference implementation.

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
