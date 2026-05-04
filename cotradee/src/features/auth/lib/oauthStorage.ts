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

export interface PendingOAuthFlow {
  state: string;
  returnTo: string;
  startedAt: number;
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
    return parsed;
  } catch {
    clearPendingOAuthFlow();
    return null;
  }
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
 * back to '/'. Mirrors the gateway's sanitiseReturnTo logic so the
 * frontend behaves identically when the user arrives via a direct
 * link or a bookmarked URL.
 */
export function sanitiseReturnTo(raw: string | null | undefined): string {
  if (!raw) return '/';
  const trimmed = raw.trim();
  if (!trimmed.startsWith('/')) return '/';
  if (trimmed.startsWith('//') || trimmed.startsWith('/\\')) return '/';
  if (trimmed.length > 512) return '/';
  return trimmed;
}
