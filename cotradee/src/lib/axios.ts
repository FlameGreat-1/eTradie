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
 * URL prefixes that NEVER produce a toast on 403. These are the
 * auth / consent / health endpoints whose 403s always indicate a
 * CSRF mismatch or a server bug, never a tier denial. Kept as a
 * defence-in-depth even though the structured `error_code` check
 * below is the primary discriminator.
 */
export const NON_TIER_GATED_403_PREFIXES = [
  '/auth/',
  '/api/v1/consent',
  '/health',
  '/readiness',
] as const;

/**
 * Pure predicate: true when `url` starts with any prefix in
 * NON_TIER_GATED_403_PREFIXES. Exported for testability and so any
 * future endpoint client can re-use the same toast-suppression rule.
 */
export function isNonTierGated403(url: string | undefined): boolean {
  if (!url) return false;
  return NON_TIER_GATED_403_PREFIXES.some((prefix) => url.startsWith(prefix));
}

/**
 * Shape of a tier-denial response body emitted by the gateway after
 * the structured-403 migration. See writeTierRequired in
 * src/gateway/internal/server/api_handlers.go. Exported as a type
 * helper so any component that wants to deep-link the upsell can
 * read the same fields without re-deriving them.
 */
export interface TierRequiredBody {
  error?: string;
  error_code?: string;
  required_tier?: 'pro_byok' | 'pro_managed' | string;
  feature?: string;
}

/**
 * Pure predicate: returns true when the parsed JSON body of a 403
 * response carries the structured tier-denial envelope. Any other
 * shape (plain {"error": "..."} CSRF failures, generic forbidden
 * responses, foreign-key violations) returns false.
 */
export function is403TierDenial(body: unknown): body is TierRequiredBody {
  if (!body || typeof body !== 'object') return false;
  const code = (body as { error_code?: unknown }).error_code;
  return typeof code === 'string' && code === 'tier_required';
}

/**
 * Shape of a platform-quota 429 response body emitted by the gateway
 * (api_handlers.go::preflightLLMQuota and metering_handler.go::handleReserve).
 * Carries the exact dimension and reset timestamp the platform quota
 * modal renders without a follow-up fetch. Audit ref: ADMIN-QUOTA-11.
 */
export interface LLMQuotaExceededBody {
  error?: string;
  error_code?: string;
  dimension?: string;
  limit?: number;
  used?: number;
  requested?: number;
  resets_at?: string;
  retry_after?: number;
  is_admin?: boolean;
}

/**
 * Pure predicate: true when a 429 response body is the platform LLM
 * quota envelope, i.e. carries error_code === 'llm_quota_exceeded'.
 * Any other 429 (cycle-rpm rate-limit, admin handler rate-limit) lacks
 * this code and is handled by the generic 'Limit Reached' toast.
 */
export function is429PlatformQuota(body: unknown): body is LLMQuotaExceededBody {
  if (!body || typeof body !== 'object') return false;
  const code = (body as { error_code?: unknown }).error_code;
  return typeof code === 'string' && code === 'llm_quota_exceeded';
}

/**
 * Window CustomEvent name the platform quota modal listens for. Kept
 * in lock-step with cotradee/src/features/realtime/RealtimeProvider.tsx
 * (MODAL_DISPATCH_MAP) so the WS path and the axios path open the
 * SAME modal subscription. Drift between the two would break the
 * manual-button-click UX silently. Audit ref: ADMIN-QUOTA-11.
 */
export const LLM_QUOTA_MODAL_EVENT = 'open-llm-quota-modal';

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

      // Global interceptor for 403 responses.
      //
      // Pre-fix behaviour: every 403 from a non-allowlisted URL
      // produced an "Upgrade Required" toast. That was a false
      // positive: CSRF mismatches, expired-cookie races,
      // foreign-key violations, and any other server-side 403 on
      // /api/broker/* or /api/llm/* would surface as a tier upsell
      // unrelated to the user's plan.
      //
      // New behaviour: surface the upgrade prompt ONLY when the
      // server explicitly says so via the structured envelope
      //   { error_code: "tier_required", required_tier, feature }
      // emitted by writeTierRequired() on the gateway. Every other
      // 403 renders a neutral "Forbidden" toast carrying the
      // server's message, OR nothing at all when the message is
      // empty so the calling component can render its own UI.
      //
      // The allowlist of paths that never produce ANY toast is
      // kept as a hard guard for the auth / consent / health
      // surfaces whose 403s are always remediable by retry-after-
      // refresh and should never surprise the user with a popup.
      if (
        error.response?.status === 403 &&
        !isNonTierGated403(original?.url)
      ) {
        const data = error.response.data as TierRequiredBody | undefined;
        if (is403TierDenial(data)) {
          toast({
            title: 'Upgrade Required',
            description:
              data?.error || 'Action restricted by your subscription tier.',
            variant: 'warning',
          });
        } else if ((data as any)?.error) {
          // Surface the server's real reason instead of guessing.
          toast({
            title: 'Forbidden',
            description: (data as any).error,
            variant: 'destructive',
          });
        }
        // No body / empty error: let the calling component decide.
      }

      if (error.response?.status === 429) {
        const data = error.response.data as
          | { detail?: string; error?: string; error_code?: string }
          | undefined;

        // Platform LLM quota 429: open the dedicated modal (Step 13)
        // and SUPPRESS the generic 'Limit Reached' toast so the user
        // gets exactly one notification. The CustomEvent name MUST
        // match RealtimeProvider's MODAL_DISPATCH_MAP so the WS path
        // and the HTTP path open the same modal subscription. Audit
        // ref: ADMIN-QUOTA-11.
        if (is429PlatformQuota(data)) {
          if (typeof window !== 'undefined') {
            try {
              window.dispatchEvent(
                new CustomEvent(LLM_QUOTA_MODAL_EVENT, { detail: data }),
              );
            } catch {
              /* SSR or non-DOM env: dispatch is a best-effort optimisation */
            }
          }
        } else {
          const retryAfterHeader = error.response.headers?.['retry-after'];
          const retryAfterSecs = retryAfterHeader ? parseInt(retryAfterHeader, 10) : null;
          const baseMsg = data?.detail || data?.error || 'Rate limit exceeded.';
          const retryMsg =
            retryAfterSecs && !isNaN(retryAfterSecs)
              ? ` Try again in ${retryAfterSecs < 60 ? `${retryAfterSecs}s` : `${Math.ceil(retryAfterSecs / 60)} min`}.`
              : '';
          toast({
            title: 'Limit Reached',
            description: baseMsg + retryMsg,
            variant: 'warning',
          });
        }
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

// Single public entry point (Option B). There is now exactly ONE axios
// client, pointed at the gateway origin (env.apiUrl). The gateway
// reverse-proxies the dashboard's engine/execution/management calls to
// the internal services by path prefix, so the browser only ever talks
// to one origin.
//
// The four named exports below are kept as ALIASES of the single client
// so existing call sites (api.gateway / api.engine / api.execution /
// api.management) keep compiling unchanged. They are the same instance;
// there is no per-service client anymore. Path prefixes at the call
// sites determine which internal service the gateway forwards to:
//   /api/analysis|broker|llm|usage|processor/*  -> engine
//   /api/execution/*                            -> execution
//   /api/management/*                           -> management
//   everything else (/api/v1/*, /auth/*, ...)   -> gateway-native
const client = createClient(env.apiUrl);

export const gatewayApi = client;
export const engineApi = client;
export const executionApi = client;
export const managementApi = client;

export const api = {
  gateway: client,
  engine: client,
  execution: client,
  management: client,
} as const;
