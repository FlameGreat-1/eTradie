/// <reference types="vite/client" />

// Single public entry point (Option B). The SPA talks to ONE origin
// (the gateway), so there are exactly two API-origin vars. The legacy
// per-service vars (VITE_ENGINE_URL / VITE_EXECUTION_URL /
// VITE_MANAGEMENT_URL) were removed; VITE_GATEWAY_HTTP_URL and
// VITE_GATEWAY_WS_URL are retained ONLY as documented back-compat
// fallbacks (read by src/config/env.ts::firstDefined and
// vite.config.ts during a rollout). All entries are optional because
// env.ts supplies localhost defaults when they are unset, matching
// Vite's real runtime shape (every VITE_* key is string | undefined).
interface ImportMetaEnv {
  // Canonical single-origin vars.
  readonly VITE_API_URL?: string;
  readonly VITE_API_WS_URL?: string;
  // Back-compat fallbacks (deprecated; do not add new usages).
  readonly VITE_GATEWAY_HTTP_URL?: string;
  readonly VITE_GATEWAY_WS_URL?: string;
  // OAuth feature flags.
  readonly VITE_GOOGLE_OAUTH_ENABLED?: string;
  readonly VITE_OAUTH_CALLBACK_PATH?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
