import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// Vite config for the cotradee dashboard.
//
// The SPA talks to the backend through axios clients whose base URLs
// come from VITE_* env vars at build time (see src/config/env.ts).
// For local development we also expose a convenience proxy so
// operators who prefer same-origin URLs can hit /api/engine and
// /api/gateway without thinking about CORS. The SPA itself does not
// depend on the proxy; production builds go directly to the configured
// engine/gateway hosts.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  const engineUrl = env.VITE_ENGINE_URL || 'http://localhost:8000';
  const gatewayUrl = env.VITE_GATEWAY_HTTP_URL || 'http://localhost:8080';

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      host: true,
      // Dev-only: same-origin proxy so developers can use relative
      // URLs like /api/engine/... when CORS is inconvenient (e.g.
      // behind a corporate VPN that rewrites Origin headers). The
      // application code does NOT use these paths in production;
      // it calls engineUrl/gatewayUrl directly.
      proxy: {
        '/api/engine': {
          target: engineUrl,
          changeOrigin: true,
          // Preserve SSE framing: vite's default buffering can break
          // text/event-stream responses on slow LLM calls.
          ws: false,
          rewrite: (requestPath) => requestPath.replace(/^\/api\/engine/, ''),
        },
        '/api/gateway': {
          target: gatewayUrl,
          changeOrigin: true,
          rewrite: (requestPath) => requestPath.replace(/^\/api\/gateway/, ''),
        },
      },
    },
    build: {
      target: 'esnext',
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['react', 'react-dom', 'react-router-dom'],
            query: ['@tanstack/react-query'],
          },
        },
      },
    },
  };
});
