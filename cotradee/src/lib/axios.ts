import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { env } from '@/config/env';
import { toast } from '@/hooks/useToast';

// ---------------------------------------------------------------------------
// Cookie-auth (Batch 11)
//
// The browser no longer stores any JWT. The gateway sets three cookies on
// every successful /auth/* response:
//
//   __Secure-access_token   - HttpOnly, Secure, scoped to '/', short-lived.
//   __Secure-refresh_token  - HttpOnly, Secure, scoped to '/auth', long-lived.
//   __Secure-csrf_token     - NOT HttpOnly, Secure, scoped to '/'.
//
// When Secure=false (local dev), the cookies are written without the
// __Secure- prefix. The SPA reads the CSRF cookie by trying the prefixed
// name first, then falling back to the unprefixed name, so an in-flight
// rollout (rolling pod restart) is safe in both directions.
//
// XSS cannot read the access or refresh cookie; the only JS-readable
// cookie is csrf_token, which is per-session and useless without the
// matching HttpOnly access cookie that only the legitimate browser holds.
// Every state-changing request must echo csrf_token back in the
// X-CSRF-Token header (configurable server-side; the default name
// matches AUTH_CSRF_HEADER and we mirror it here).
//
// All axios clients are constructed with withCredentials:true so the
// browser sends the cookie jar on every request.
// ---------------------------------------------------------------------------

const CSRF_COOKIE_NAMES = ['__Secure-csrf_token', 'csrf_token'] as const;
const CSRF_HEADER_NAME = 'X-CSRF-Token';

// ---------------------------------------------------------------------------
// Multi-tab logout sync
//
// When one tab calls logout(), the SPA writes a value to localStorage
// under this key; every other tab's `storage` event listener triggers
// a hard reload to /login. The same channel is fired by the 401
// silent-refresh path when the refresh itself 401s, since the cookies
// have either expired or been revoked server-side.
// ---------------------------------------------------------------------------
export const AUTH_LOGOUT_BROADCAST_KEY = 'etradie:auth:logout';

// ---------------------------------------------------------------------------
// Multi-tab refresh lock
//
// When two tabs both receive a 401 simultaneously, only one should call
// POST /auth/refresh. The server rotates the refresh token on every
// successful refresh (refresh-token rotation), so the second tab's
// refresh attempt would use the already-invalidated token and get 401,
// triggering a spurious logout across all tabs.
//
// We use the Web Locks API (navigator.locks) to serialize the refresh
// across all tabs of the same origin. The lock name is stable so every
// tab competes for the same lock. The tab that wins the lock performs
// the refresh; the others wait and then re-dispatch their original
// request (which now succeeds because the cookies were rotated by the
// winner).
//
// Fallback: Safari < 16 and some older browsers do not support
// navigator.locks. In that case we fall back to the single-tab
// in-process queue (isRefreshing + pendingQueue), which is correct
// within a single tab but cannot coordinate across tabs. The fallback
// is safe: the worst case is a spurious logout on the second tab,
// which is the same behaviour as before this fix.
// ---------------------------------------------------------------------------
const REFRESH_LOCK_NAME = 'etradie:auth:refresh';

const MUTATING_METHODS = new Set(['post', 'put', 'patch', 'delete']);

/**
 * Read a cookie value by name from document.cookie.
 * Returns '' when the cookie is absent.
 */
function readCookie(name: string): string {
  if (typeof document === 'undefined') return '';
  const target = `${name}=`;
  const parts = document.cookie.split(';');
  for (const part of parts) {
    const c = part.trimStart();
    if (c.startsWith(target)) {
      return decodeURIComponent(c.substring(target.length));
    }
  }
  return '';
}

/**
 * Read the CSRF cookie value, trying the __Secure- prefixed name first
 * then falling back to the unprefixed name. Returns '' when absent.
 */
function readCSRFCookie(): string {
  for (const name of CSRF_COOKIE_NAMES) {
    const val = readCookie(name);
    if (val) return val;
  }
  return '';
}

/**
 * Broadcast a logout to every other tab on the same origin and route
 * the current tab to /login. Safe to call multiple times.
 */
export function broadcastLogoutAndRedirect(reason: 'user' | 'session-expired'): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(
      AUTH_LOGOUT_BROADCAST_KEY,
      JSON.stringify({ reason, at: Date.now() }),
    );
  } catch {
    /* private mode / quota-exceeded — swallow */
  }
  window.location.assign('/login');
}

// Install the cross-tab listener exactly once per document.
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key !== AUTH_LOGOUT_BROADCAST_KEY) return;
    if (!event.newValue) return;
    if (window.location.pathname === '/login') return;
    window.location.assign('/login');
  });
}

// ---------------------------------------------------------------------------
// Legacy token-helper exports (deprecated, kept for compat)
// ---------------------------------------------------------------------------

/** Returns a coarse client-side hint: is a csrf_token cookie present? */
export function hasSession(): boolean {
  return readCSRFCookie() !== '';
}

/** @deprecated post-Batch-11: access token is an HttpOnly cookie. */
export function getAccessToken(): string { return ''; }

/** @deprecated post-Batch-11: refresh token is an HttpOnly cookie. */
export function getRefreshToken(): string { return ''; }

/** @deprecated post-Batch-11: cookies are set by the server. */
export function setTokens(_access: string, _refresh: string): void { /* no-op */ }

/** @deprecated post-Batch-11: cookies are cleared by the server on /auth/logout. */
export function clearTokens(): void { /* no-op */ }

// ---------------------------------------------------------------------------
// CSRF header stamping
// ---------------------------------------------------------------------------

/**
 * Attach the CURRENT csrf_token cookie to a mutating request. Called
 * both on first dispatch (request interceptor) and on the 401 retry
 * path (after silent refresh rotated the cookie).
 */
function stampCsrfHeader(config: InternalAxiosRequestConfig): InternalAxiosRequestConfig {
  const method = (config.method ?? 'get').toLowerCase();
  if (!MUTATING_METHODS.has(method)) return config;
  const csrf = readCSRFCookie();
  if (csrf) {
    config.headers.set(CSRF_HEADER_NAME, csrf);
  } else {
    // No cookie — strip any stale header so the server's RequireCSRF
    // returns a clean 403 rather than mis-matching against a value
    // copied from an earlier session.
    config.headers.delete(CSRF_HEADER_NAME);
  }
  return config;
}

// ---------------------------------------------------------------------------
// Axios client factory
// ---------------------------------------------------------------------------

/**
 * Perform the silent token refresh, serialized across all tabs via the
 * Web Locks API when available, falling back to a plain Promise otherwise.
 *
 * Returns true if the refresh succeeded, false if it failed (caller
 * should broadcast logout).
 */
async function performRefresh(): Promise<boolean> {
  const doRefresh = async (): Promise<boolean> => {
    try {
      // No body: the refresh_token cookie (scoped to /auth) is
      // attached automatically by the browser. withCredentials:true
      // is critical — without it the cookie would not be sent.
      await axios.post(
        `${env.gatewayHttpUrl}/auth/refresh`,
        {},
        { withCredentials: true },
      );
      return true;
    } catch {
      return false;
    }
  };

  // Use the Web Locks API when available to serialize across tabs.
  if (typeof navigator !== 'undefined' && 'locks' in navigator) {
    return navigator.locks.request(
      REFRESH_LOCK_NAME,
      // exclusive: only one tab holds the lock at a time.
      // steal: false (default) — other tabs queue behind the winner.
      async () => doRefresh(),
    );
  }

  // Fallback for browsers without Web Locks (Safari < 16).
  return doRefresh();
}

function createClient(baseURL: string): AxiosInstance {
  const client = axios.create({
    baseURL,
    timeout: 300_000,
    headers: { 'Content-Type': 'application/json' },
    withCredentials: true,
  });

  // Attach CSRF token on state-changing requests.
  client.interceptors.request.use((config: InternalAxiosRequestConfig) => stampCsrfHeader(config));

  // ---------------------------------------------------------------------------
  // Silent token refresh on 401
  //
  // Single-tab in-process queue: if a refresh is already in flight on
  // THIS tab, queue subsequent 401s behind it rather than firing multiple
  // concurrent refresh requests. This is the inner guard; the Web Locks
  // API is the outer guard that coordinates across tabs.
  // ---------------------------------------------------------------------------
  let isRefreshing = false;
  let pendingQueue: Array<{
    resolve: () => void;
    reject: (err: unknown) => void;
  }> = [];

  const processQueue = (error?: unknown) => {
    pendingQueue.forEach((p) => {
      if (error) p.reject(error);
      else p.resolve();
    });
    pendingQueue = [];
  };

  client.interceptors.response.use(
    (res) => res,
    async (error: AxiosError) => {
      const original = error.config;

      // Global interceptor for tier restrictions.
      if (error.response?.status === 403) {
        const data = error.response.data as { error?: string } | undefined;
        const msg = data?.error || 'Action restricted by your subscription tier.';
        toast({
          title: 'Upgrade Required',
          description: msg,
          variant: 'warning',
        });
      }

      if (error.response?.status === 429) {
        const data = error.response.data as { detail?: string; error?: string } | undefined;
        const msg = data?.detail || data?.error || 'Rate limit exceeded.';
        toast({
          title: 'Limit Reached',
          description: msg,
          variant: 'warning',
        });
      }

      if (!original || error.response?.status !== 401) {
        return Promise.reject(error);
      }

      // Skip refresh loop for auth endpoints: a 401 on /auth/login or
      // /auth/refresh is a permanent failure, not something we retry.
      if (original.url?.startsWith('/auth/')) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Another refresh is already in flight on this tab. Queue this
        // request behind it.
        return new Promise<void>((resolve, reject) => {
          pendingQueue.push({ resolve, reject });
        }).then(() => {
          // The CSRF cookie was rotated by /auth/refresh; re-stamp
          // the queued request's header from the fresh cookie before
          // we redispatch it.
          stampCsrfHeader(original as InternalAxiosRequestConfig);
          return client(original);
        });
      }

      isRefreshing = true;

      try {
        // performRefresh acquires the cross-tab Web Lock before calling
        // POST /auth/refresh. If another tab already holds the lock and
        // is refreshing, this tab waits until the lock is released, then
        // re-dispatches the original request (the cookies are now fresh).
        const refreshed = await performRefresh();

        if (!refreshed) {
          processQueue(new Error('refresh failed'));
          broadcastLogoutAndRedirect('session-expired');
          return Promise.reject(error);
        }

        processQueue();
        // Re-stamp the originating request's CSRF header from the
        // newly-rotated cookie before redispatching it.
        stampCsrfHeader(original as InternalAxiosRequestConfig);
        return client(original);
      } catch (refreshError) {
        processQueue(refreshError);
        broadcastLogoutAndRedirect('session-expired');
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    },
  );

  return client;
}

// ---------------------------------------------------------------------------
// Exported per-service clients
// ---------------------------------------------------------------------------

export const gatewayApi = createClient(env.gatewayHttpUrl);
export const engineApi = createClient(env.engineUrl);
export const executionApi = createClient(env.executionUrl);
export const managementApi = createClient(env.managementUrl);

export const api = {
  gateway: gatewayApi,
  engine: engineApi,
  execution: executionApi,
  management: managementApi,
} as const;
