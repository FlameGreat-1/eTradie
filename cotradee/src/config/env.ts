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

export const env = {
  engineUrl: import.meta.env.VITE_ENGINE_URL || 'http://localhost:8000',
  gatewayHttpUrl: import.meta.env.VITE_GATEWAY_HTTP_URL || 'http://localhost:8080',
  gatewayWsUrl: import.meta.env.VITE_GATEWAY_WS_URL || 'ws://localhost:8080',
  executionUrl: import.meta.env.VITE_EXECUTION_URL || 'http://localhost:8081',
  managementUrl: import.meta.env.VITE_MANAGEMENT_URL || 'http://localhost:8083',

  googleOAuthEnabled: parseBoolean(import.meta.env.VITE_GOOGLE_OAUTH_ENABLED, false),
  oauthCallbackPath: import.meta.env.VITE_OAUTH_CALLBACK_PATH || '/auth/callback/google',
} as const;
