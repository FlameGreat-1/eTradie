import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

/**
 * Vite config for the cotradee dashboard.
 *
 * The SPA talks to the backend through axios clients whose base URLs
 * come from VITE_* env vars at build time (see src/config/env.ts). For
 * local development we also expose a convenience proxy so operators
 * who prefer same-origin URLs can hit /api/engine and /api/gateway
 * without thinking about CORS. The SPA itself does not depend on the
 * proxy; production builds go directly to the configured engine /
 * gateway hosts.
 */
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
        host: 'localhost',
        clientPort: 5173,
        overlay: false,
      },
      proxy: {
        '/api/engine': {
          target: engineUrl,
          changeOrigin: true,
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
