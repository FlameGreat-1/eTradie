/**
 * Client-side persistence for the cookie-consent feature.
 *
 * Two layers, in this order on read:
 *
 *   1. First-party cookie 'exoper_consent' (6 months Max-Age).
 *      Authoritative because it is the channel the server can
 *      observe directly on the very next request.
 *   2. localStorage 'exoper_consent_v1'.
 *      Mirror of the cookie. Faster cold-start read and unaffected
 *      by 3rd-party cookie blockers that occasionally strip first-
 *      party cookies on the first navigation.
 *
 * Both layers are written together on every persist; either layer is
 * authoritative on its own if the other is unavailable. Reads never
 * throw — a corrupted entry is treated as 'no decision'.
 *
 * Strictly-necessary cookies are never written or read here; they are
 * the auth/CSRF cookies managed by the gateway.
 */

import {
  type ConsentDecision,
  type ConsentRecord,
  CONSENT_POLICY_VERSION,
} from './types';

// ---------------------------------------------------------------------------
// Keys & TTLs
// ---------------------------------------------------------------------------

const LS_DECISION_KEY = 'exoper_consent_v1';
const LS_ANON_ID_KEY = 'exoper_consent_anon_id';
const COOKIE_NAME = 'exoper_consent';
const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 180; // 180 days

// ---------------------------------------------------------------------------
// Anonymous id
// ---------------------------------------------------------------------------

/**
 * Returns the stable anonymous id, generating one on first call. The
 * id is used to key consent decisions before the user signs in; on
 * sign-in AuthContext calls attachAnonymousToUser to link the prior
 * decisions to the now-known user.
 */
export function getOrCreateAnonymousId(): string {
  try {
    const existing = window.localStorage.getItem(LS_ANON_ID_KEY);
    if (existing && existing.length > 0 && existing.length <= 128) {
      return existing;
    }
  } catch {
    /* localStorage may be disabled (private mode); fall through. */
  }
  const id = generateAnonymousId();
  try {
    window.localStorage.setItem(LS_ANON_ID_KEY, id);
  } catch {
    /* swallow */
  }
  return id;
}

function generateAnonymousId(): string {
  // crypto.randomUUID is available in every browser this app supports
  // (per package.json: react 18 / vite / no IE). The fallback exists
  // only for SSR environments and tests that stub out crypto.
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // RFC 4122-style fallback. Used only when crypto.randomUUID is
  // absent; the resulting string is opaque to the server.
  const bytes = new Uint8Array(16);
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < bytes.length; i++) bytes[i] = Math.floor(Math.random() * 256);
  }
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

// ---------------------------------------------------------------------------
// Decision read / write
// ---------------------------------------------------------------------------

interface PersistedShape {
  v: string; // policy version
  c: ConsentDecision; // categories
  t: number; // unix ms when written
}

export interface StoredDecision {
  policyVersion: string;
  decision: ConsentDecision;
  recordedAt: number;
}

/**
 * Read the persisted decision, trying the cookie first then localStorage.
 * Returns null when no usable record is available.
 */
export function readStoredDecision(): StoredDecision | null {
  const fromCookie = readFromCookie();
  if (fromCookie) return fromCookie;
  return readFromLocalStorage();
}

/**
 * Persist a decision to both layers. Best-effort: any single layer
 * failure is swallowed so the user can still proceed.
 */
export function writeStoredDecision(decision: ConsentDecision): StoredDecision {
  const payload: PersistedShape = {
    v: CONSENT_POLICY_VERSION,
    c: decision,
    t: Date.now(),
  };
  const json = JSON.stringify(payload);

  try {
    window.localStorage.setItem(LS_DECISION_KEY, json);
  } catch {
    /* swallow */
  }

  try {
    document.cookie = buildCookieString(COOKIE_NAME, json, COOKIE_MAX_AGE_SECONDS);
  } catch {
    /* swallow — a sandboxed iframe may forbid document.cookie writes. */
  }

  return {
    policyVersion: payload.v,
    decision: payload.c,
    recordedAt: payload.t,
  };
}

/**
 * Mirror a server-returned ConsentRecord into local storage when the
 * server has a newer record than the client knows about. Called from
 * the context on hydrate after GET /api/v1/consent succeeds.
 */
export function mirrorServerRecord(rec: ConsentRecord): StoredDecision {
  const payload: PersistedShape = {
    v: rec.policy_version,
    c: rec.categories,
    t: Date.parse(rec.created_at) || Date.now(),
  };
  try {
    window.localStorage.setItem(LS_DECISION_KEY, JSON.stringify(payload));
  } catch {
    /* swallow */
  }
  try {
    document.cookie = buildCookieString(
      COOKIE_NAME,
      JSON.stringify(payload),
      COOKIE_MAX_AGE_SECONDS,
    );
  } catch {
    /* swallow */
  }
  return {
    policyVersion: payload.v,
    decision: payload.c,
    recordedAt: payload.t,
  };
}

// ---------------------------------------------------------------------------
// Internals
// ---------------------------------------------------------------------------

function readFromLocalStorage(): StoredDecision | null {
  try {
    const raw = window.localStorage.getItem(LS_DECISION_KEY);
    if (!raw) return null;
    return parsePayload(raw);
  } catch {
    return null;
  }
}

function readFromCookie(): StoredDecision | null {
  try {
    if (typeof document === 'undefined' || !document.cookie) return null;
    const target = `${COOKIE_NAME}=`;
    for (const part of document.cookie.split(';')) {
      const trimmed = part.trimStart();
      if (trimmed.startsWith(target)) {
        const raw = decodeURIComponent(trimmed.substring(target.length));
        return parsePayload(raw);
      }
    }
    return null;
  } catch {
    return null;
  }
}

function parsePayload(raw: string): StoredDecision | null {
  try {
    const obj = JSON.parse(raw) as Partial<PersistedShape>;
    if (!obj || typeof obj !== 'object') return null;
    if (typeof obj.v !== 'string' || typeof obj.t !== 'number') return null;
    if (!obj.c || typeof obj.c !== 'object') return null;
    if (typeof obj.c.functional !== 'boolean' || typeof obj.c.analytics !== 'boolean') return null;
    return {
      policyVersion: obj.v,
      decision: { functional: obj.c.functional, analytics: obj.c.analytics },
      recordedAt: obj.t,
    };
  } catch {
    return null;
  }
}

function buildCookieString(name: string, value: string, maxAgeSeconds: number): string {
  // SameSite=Lax + Secure (when served over https) is the right
  // default for a first-party preference cookie. We do not need
  // Strict here because the cookie is purely informational — a
  // top-level navigation from an external link should still surface
  // the same recorded decision.
  const secure = typeof location !== 'undefined' && location.protocol === 'https:' ? '; Secure' : '';
  return [
    `${name}=${encodeURIComponent(value)}`,
    'Path=/',
    `Max-Age=${maxAgeSeconds}`,
    'SameSite=Lax',
  ].join('; ') + secure;
}

