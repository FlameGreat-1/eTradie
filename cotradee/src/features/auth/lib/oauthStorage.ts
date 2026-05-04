/**
 * Browser-side storage helpers for the in-flight OAuth authorize step.
 *
 * The gateway is the source of truth for state / nonce / verifier
 * (those live in PostgreSQL and are consumed atomically). The browser
 * only needs to remember:
 *
 *   - the `state` it was handed at /auth/oauth/google/start, so it can
 *     compare it against the `state` Google echoes back on redirect.
 *     This catches stale tabs and is a defence-in-depth check on top
 *     of the gateway's own validation.
 *   - the original `returnTo` path the user clicked from, so the
 *     callback page can navigate back without an extra round-trip
 *     even if the user opens a new tab manually.
 *   - a wall-clock `startedAt` timestamp so we can fail fast on
 *     callbacks that arrive after the gateway-side TTL would have
 *     expired (the gateway will of course also reject them).
 *
 * sessionStorage is used so the record is bound to the tab and is
 * cleared automatically when the tab closes.
 */

const KEY = 'etradie_oauth_pending';
const MAX_LIFETIME_MS = 30 * 60 * 1000; // hard cap; gateway TTL is the real authority

/**
 * Discriminates the two OAuth flows the dashboard supports:
 *   - 'signin' : unauthenticated; gateway returns a TokenPair.
 *   - 'link'   : authenticated; gateway binds the verified Google
 *                identity to the current user and returns 204.
 *
 * The two flows hit different gateway endpoints, land on different
 * callback routes, and have different success contracts; conflating
 * them on the client is exactly the class of bug that produces
 * account-linking CSRF, so they are kept strictly separate.
 */
export type OAuthFlowMode = 'signin' | 'link';

export interface PendingOAuthFlow {
  state: string;
  returnTo: string;
  startedAt: number;
  /**
   * Optional for backward compatibility with sessionStorage records
   * written by builds that predate the link feature. Consumers MUST
   * default to 'signin' when this field is absent.
   */
  mode?: OAuthFlowMode;
}

export function savePendingOAuthFlow(flow: PendingOAuthFlow): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(flow));
  } catch {
    // sessionStorage may be unavailable in private modes; fall back
    // to a no-op. The gateway will still validate state on callback.
  }
}

export function readPendingOAuthFlow(): PendingOAuthFlow | null {
  let raw: string | null;
  try {
    raw = sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as PendingOAuthFlow;
    if (
      typeof parsed?.state !== 'string' ||
      typeof parsed?.returnTo !== 'string' ||
      typeof parsed?.startedAt !== 'number'
    ) {
      clearPendingOAuthFlow();
      return null;
    }
    if (Date.now() - parsed.startedAt > MAX_LIFETIME_MS) {
      clearPendingOAuthFlow();
      return null;
    }
    // Defensive: reject any unrecognised mode value rather than
    // silently coercing it. Older records without the field at all
    // are accepted and treated as 'signin' by callers.
    if (
      parsed.mode !== undefined &&
      parsed.mode !== 'signin' &&
      parsed.mode !== 'link'
    ) {
      clearPendingOAuthFlow();
      return null;
    }
    return parsed;
  } catch {
    clearPendingOAuthFlow();
    return null;
  }
}

/**
 * Returns the mode of the pending flow, defaulting to 'signin' for
 * records written by older builds. Centralised so every caller agrees
 * on the default.
 */
export function pendingFlowMode(flow: PendingOAuthFlow): OAuthFlowMode {
  return flow.mode ?? 'signin';
}

export function clearPendingOAuthFlow(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

/**
 * Coerce a raw user-supplied path into a same-origin path or fall
 * back to '/'. Mirrors the gateway's sanitiseReturnTo logic byte for
 * byte so the frontend and the server agree on what is acceptable;
 * any value the gateway would reject is rejected here too, and vice
 * versa.
 *
 * Rejects, in addition to obvious cross-origin URLs:
 *   - control characters and CR/LF (header-splitting / log-injection)
 *   - percent-encoded slashes / backslashes that the browser would
 *     decode at navigate time and turn into a schemaless URL
 *   - anything longer than 512 bytes
 */
export function sanitiseReturnTo(raw: string | null | undefined): string {
  if (!raw) return '/';
  const trimmed = raw.trim();
  if (trimmed.length === 0 || trimmed.length > 512) return '/';
  if (!trimmed.startsWith('/')) return '/';
  if (trimmed.startsWith('//') || trimmed.startsWith('/\\')) return '/';
  // Reject control characters anywhere in the path (NUL through 0x1f,
  // and 0x7f).
  for (let i = 0; i < trimmed.length; i++) {
    const code = trimmed.charCodeAt(i);
    if (code < 0x20 || code === 0x7f) return '/';
  }
  // Reject percent-encoded slash/backslash, which the browser would
  // decode and which can otherwise produce '//evil.com' after the
  // leading-slash check has passed.
  const lower = trimmed.toLowerCase();
  if (lower.startsWith('/%2f') || lower.startsWith('/%5c')) return '/';
  return trimmed;
}
