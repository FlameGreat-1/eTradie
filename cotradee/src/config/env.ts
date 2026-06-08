/**
 * Runtime configuration sourced from VITE_-prefixed build-time env vars.
 *
 * Only public, non-secret values belong here. The Google OAuth client
 * secret is held exclusively by the gateway; the frontend never sees it.
 * The googleOAuthEnabled flag mirrors the gateway's
 * AUTH_GOOGLE_OAUTH_ENABLED toggle so the UI can hide the social
 * sign-in affordances when the feature is disabled in this environment.
 *
 * oauthCallbackPath defaults to '/auth/callback/google' so it matches
 * the AUTH_GOOGLE_REDIRECT_URI value the gateway is configured with;
 * override via VITE_OAUTH_CALLBACK_PATH if a deployment uses a
 * different path.
 */
function parseBoolean(raw: string | undefined, fallback: boolean): boolean {
  if (raw === undefined) return fallback;
  return /^(1|true|yes|on)$/i.test(raw.trim());
}

// Single public entry point (Option B). The browser talks ONLY to the
// gateway origin (api.exoper.com in production); the gateway reverse-
// proxies the dashboard's engine/execution/management calls to the
// internal services. There is exactly ONE HTTP base URL and ONE
// WebSocket base URL for the whole SPA.
//
//   VITE_API_URL     HTTP(S) base, e.g. https://api.exoper.com
//   VITE_API_WS_URL  WebSocket base, e.g. wss://api.exoper.com
//
// Local-dev defaults point at the gateway on :8080 (HTTP) and its WS
// listener on :8080. The legacy per-service VITE_ENGINE_URL /
// VITE_EXECUTION_URL / VITE_MANAGEMENT_URL / VITE_GATEWAY_* variables
// are intentionally removed: the browser no longer knows where the
// internal services live.
function firstDefined(...vals: Array<string | undefined>): string | undefined {
  for (const v of vals) {
    if (v !== undefined && v !== '') return v;
  }
  return undefined;
}

const apiUrl =
  firstDefined(
    import.meta.env.VITE_API_URL,
    // Back-compat fallback so an environment that still only sets the
    // old gateway HTTP var keeps working during rollout.
    import.meta.env.VITE_GATEWAY_HTTP_URL,
  ) || 'http://localhost:8080';

const apiWsUrl =
  firstDefined(
    import.meta.env.VITE_API_WS_URL,
    import.meta.env.VITE_GATEWAY_WS_URL,
  ) || 'ws://localhost:8080';

export const env = {
  // Canonical single-origin values.
  apiUrl,
  apiWsUrl,

  // Deprecated aliases retained ONLY so any not-yet-migrated import
  // keeps compiling and resolves to the single gateway origin. All four
  // now point at the SAME base URL; the gateway proxies to the right
  // internal service by path prefix. Do not add new usages.
  gatewayHttpUrl: apiUrl,
  gatewayWsUrl: apiWsUrl,
  engineUrl: apiUrl,
  executionUrl: apiUrl,
  managementUrl: apiUrl,

  googleOAuthEnabled: parseBoolean(import.meta.env.VITE_GOOGLE_OAUTH_ENABLED, false),
  oauthCallbackPath: import.meta.env.VITE_OAUTH_CALLBACK_PATH || '/auth/callback/google',
} as const;
