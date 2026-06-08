import { defineConfig, loadEnv, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

/**
 * Build-time source patch for lightweight-charts v4.2.x.
 *
 * The library's internal `isChromiumBased()` function calls
 *   navigator.userAgentData.brands.some(...)
 * at module top-level without guarding `.brands` with optional
 * chaining. On any browser that does not implement the User-Agent
 * Client Hints API (Firefox, Safari, iOS WebViews, Chrome DevTools
 * mobile emulation, privacy-hardened browsers) this throws:
 *   TypeError: Cannot read properties of undefined (reading 'some')
 *
 * Runtime polyfills are unreliable because:
 *   - Module-eval crashes before any React error boundary fires.
 *   - Some mobile runtimes have read-only navigator descriptors.
 *   - Chrome DevTools device emulation resets userAgentData after
 *     page scripts have already patched it.
 *
 * The industry-standard fix: patch the source at build time.
 * We add optional chaining to `.brands` → `.brands?.` which is a
 * safe no-op on compliant browsers and returns `undefined` (falsy)
 * on non-compliant ones, making `isChromiumBased()` return `false`.
 */
function patchLightweightCharts(): Plugin {
  return {
    name: 'patch-lightweight-charts',
    enforce: 'pre',
    transform(code, id) {
      if (!id.includes('lightweight-charts')) return null;
      // Guard .brands.some( → .brands?.some(
      // Guard .brands.filter( and similar patterns while we're at it
      if (!code.includes('.brands.some') && !code.includes('.brands.filter')) return null;
      const patched = code
        .replace(/\.brands\.some\(/g, '.brands?.some(')
        .replace(/\.brands\.filter\(/g, '.brands?.filter(');
      return { code: patched, map: null };
    },
  };
}

/**
 * Vite config for the cotradee dashboard.
 *
 * Single public entry point (Option B): the SPA talks to ONE origin,
 * the gateway, whose base URL comes from VITE_API_URL at build time
 * (see src/config/env.ts). The gateway reverse-proxies the dashboard's
 * engine/execution/management calls to the internal services by path
 * prefix, so there is no per-service origin to proxy here.
 *
 * The dev `server.proxy` below forwards EVERY backend path the SPA uses
 * (/api/*, /auth/*, /ws/*, /events/*) to the local gateway on :8080 so
 * the Vite dev server (:5173) is same-origin with the app and there is
 * no CORS or cookie-domain friction in local development. Production
 * builds are served by Vercel and talk directly to VITE_API_URL
 * (https://api.exoper.com); this proxy is dev-only.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  // Single origin. VITE_API_URL is the canonical var; VITE_GATEWAY_HTTP_URL
  // is accepted as a back-compat fallback to match src/config/env.ts.
  const apiUrl =
    env.VITE_API_URL || env.VITE_GATEWAY_HTTP_URL || 'http://localhost:8080';
  // WebSocket upstream for the dev proxy (/ws/*). Derived from apiUrl so
  // a single override flips both; mirrors env.apiWsUrl.
  const apiWsUrl =
    env.VITE_API_WS_URL || apiUrl.replace(/^http/, 'ws');

  return {
    plugins: [patchLightweightCharts(), react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        '@tanstack/react-query',
        'lightweight-charts',
        'lucide-react',
        'axios',
        'date-fns',
      ],
    },
    server: {
      port: 5173,
      host: true,
      strictPort: true,
      // usePolling forces 100% CPU on macOS and slows HMR; the native
      // fs watcher is fine for our project size and runs in <50 ms.
      hmr: {
        protocol: 'ws',
        clientPort: 5173,
        overlay: false,
      },
      // Dev-only same-origin proxy to the local gateway. The keys are
      // the real backend path prefixes the SPA calls (no rewrite): the
      // gateway owns /api/*, /auth/*, /events/* and the /ws/* upgrade.
      // ws:true on /ws so the live notifications + chart tick streams
      // upgrade through the dev proxy exactly as they do in production.
      proxy: {
        '/api': {
          target: apiUrl,
          changeOrigin: true,
        },
        '/auth': {
          target: apiUrl,
          changeOrigin: true,
        },
        '/events': {
          target: apiUrl,
          changeOrigin: true,
        },
        '/ws': {
          target: apiWsUrl,
          changeOrigin: true,
          ws: true,
        },
      },
    },
    build: {
      target: 'es2020',
      sourcemap: false,
      cssCodeSplit: true,
      minify: 'esbuild',
      reportCompressedSize: false,
      chunkSizeWarningLimit: 800,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return undefined;
            if (id.includes('lightweight-charts')) return 'chart';
            if (id.includes('lucide-react'))      return 'icons';
            if (id.includes('@tanstack'))         return 'query';
            if (id.includes('react-router'))      return 'router';
            if (id.includes('react'))             return 'react';
            if (id.includes('@radix-ui'))         return 'ui';
            return 'vendor';
          },
        },
      },
    },
  };
});
