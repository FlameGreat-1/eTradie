import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { env } from '@/config/env';
import { toast } from '@/hooks/useToast';

// ---------------------------------------------------------------------------
// Cookie-auth migration (Batch 11)
//
// The browser no longer stores any JWT. The gateway sets three cookies on
// every successful /auth/* response:
//
//   access_token   - HttpOnly, Secure, scoped to '/', short-lived.
//   refresh_token  - HttpOnly, Secure, scoped to '/auth', long-lived.
//   csrf_token     - NOT HttpOnly, Secure, scoped to '/', short-lived.
//
// XSS cannot read the access or refresh cookie; the only JS-readable
// cookie is csrf_token, which is per-session and useless without the
// matching HttpOnly access cookie that only the legitimate browser
// holds. Every state-changing request must echo csrf_token back in
// the X-CSRF-Token header (configurable server-side; the default name
// matches AUTH_CSRF_HEADER and we mirror it here).
//
// All axios clients are constructed with withCredentials:true so the
// browser sends the cookie jar on every request. Authorization-header
// injection has been removed; the access cookie IS the auth channel.
// ---------------------------------------------------------------------------

const CSRF_COOKIE_NAME = 'csrf_token';
const CSRF_HEADER_NAME = 'X-CSRF-Token';

const MUTATING_METHODS = new Set(['post', 'put', 'patch', 'delete']);

/**
 * Read a cookie value by name from document.cookie. Returns '' when
 * the cookie is absent. Used to attach csrf_token to mutating
 * requests and to provide a coarse client-side 'do I look logged in?'
 * hint (the server is the ultimate authority).
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

// ---------------------------------------------------------------------------
// Legacy token-helper exports.
//
// Pre-Batch-11 code in this codebase imports getAccessToken / getRefreshToken
// / setTokens / clearTokens from this module. Removing the named exports
// would require touching every caller; instead we keep the names and make
// them documented no-ops. The new canonical helper is hasSession(), which
// answers a presence question only.
//
// getAccessToken / getRefreshToken return '' because the actual tokens are
// in HttpOnly cookies and JS cannot read them. setTokens / clearTokens are
// no-ops because the server owns cookie lifecycle.
// ---------------------------------------------------------------------------

/** Returns a coarse client-side hint: is a csrf_token cookie present? */
export function hasSession(): boolean {
  return readCookie(CSRF_COOKIE_NAME) !== '';
}

/** @deprecated post-Batch-11: access token is an HttpOnly cookie and is unreadable from JS. */
export function getAccessToken(): string {
  return '';
}

/** @deprecated post-Batch-11: refresh token is an HttpOnly cookie and is unreadable from JS. */
export function getRefreshToken(): string {
  return '';
}

/** @deprecated post-Batch-11: cookies are set by the server on /auth/login, /auth/register, /auth/refresh, OAuth callback. */
export function setTokens(_access: string, _refresh: string): void {
  /* no-op: server-managed cookies */
}

/** @deprecated post-Batch-11: cookies are cleared by the server on /auth/logout. */
export function clearTokens(): void {
  /* no-op: server-managed cookies */
}

/* ─── Factory ───────────────────────────────────────────────── */

function createClient(baseURL: string): AxiosInstance {
  const client = axios.create({
    baseURL,
    timeout: 300_000,
    headers: { 'Content-Type': 'application/json' },
    // Cookies (access_token, refresh_token, csrf_token) must ride
    // along on every request; without this, the browser drops them
    // on cross-origin XHR even when the server allows it via CORS.
    withCredentials: true,
  });

  // Attach CSRF token on state-changing requests. The server's
  // RequireCSRF middleware short-circuits safe methods, so omitting
  // the header on GET/HEAD/OPTIONS is correct and avoids a useless
  // round-trip through document.cookie on read-heavy paths.
  client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const method = (config.method ?? 'get').toLowerCase();
    if (MUTATING_METHODS.has(method)) {
      const csrf = readCookie(CSRF_COOKIE_NAME);
      if (csrf) {
        // axios v1 headers is an AxiosHeaders instance; .set is the
        // typed accessor and avoids a Record<string,string> coercion.
        config.headers.set(CSRF_HEADER_NAME, csrf);
      }
    }
    return config;
  });

  /* Silent token refresh on 401. */
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

      // Global Interceptor for Restrictions / Limits.
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

      // Skip refresh loop for auth endpoints themselves: a 401 on
      // /auth/login or /auth/refresh is a permanent failure, not
      // something we retry by refreshing.
      if (original.url?.startsWith('/auth/')) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise<void>((resolve, reject) => {
          pendingQueue.push({ resolve, reject });
        }).then(() => client(original));
      }

      isRefreshing = true;

      try {
        // No body: the refresh_token cookie (scoped to /auth) is
        // attached automatically by the browser. withCredentials:true
        // is critical here — without it the cookie would not be sent
        // and the refresh would 400 with 'refresh_token is required'.
        await axios.post(
          `${env.gatewayHttpUrl}/auth/refresh`,
          {},
          { withCredentials: true },
        );
        processQueue();
        return client(original);
      } catch (refreshError) {
        processQueue(refreshError);
        // We cannot clear the HttpOnly cookies from JS; the server's
        // /auth/logout (called on logout) and the now-invalid cookies
        // (rejected on every subsequent /auth/me) take care of the
        // user state. Navigate to /login so the user sees the login
        // screen rather than a half-broken app.
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    },
  );

  return client;
}

/* ─── Exported per-service clients ──────────────────────────── */

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
