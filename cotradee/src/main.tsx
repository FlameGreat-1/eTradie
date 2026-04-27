import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { installUserAgentDataPolyfill } from '@/lib/userAgentDataPolyfill';
import App from './App';
import './assets/index.css';

// Must run before any module that touches navigator.userAgentData.
// In our codebase that's lightweight-charts (loaded lazily by the
// dashboard route), but we install eagerly so any future caller is
// covered too.
installUserAgentDataPolyfill();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
