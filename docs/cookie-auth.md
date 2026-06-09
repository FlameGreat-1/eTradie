# Cookie Auth + CSRF — Operator Runbook

This document is the canonical reference for the cookie-auth + CSRF
model introduced in batches and finalised. It tells operators what each
cookie does, how to configure the deployment for the three supported
topologies (local-dev HTTP, single-host HTTPS, cross-subdomain HTTPS),
and how to triage every failure mode we have seen in development.

## 1. Cookie inventory

The gateway sets three cookies on every successful `/auth/login`,
`/auth/register`, `/auth/refresh`, and OAuth sign-in callback. All
three share the same `Domain`, `Secure`, and `SameSite` policy so a
browser cannot accidentally drop one while keeping the others (see
`src/auth/cookies.go`).

| Cookie          | HttpOnly | Path     | Lifetime                    | Purpose                                                                 |
|-----------------|----------|----------|-----------------------------|-------------------------------------------------------------------------|
| `access_token`  | yes      | `/`      | `AUTH_ACCESS_TOKEN_TTL`     | Short-lived JWT. Sent on every authenticated request and WS handshake.  |
| `refresh_token` | yes      | `/auth`  | `AUTH_REFRESH_TOKEN_TTL`    | Long-lived; scoped to `/auth/*` so it never rides on regular API calls. |
| `csrf_token`    | **no**   | `/`      | `AUTH_ACCESS_TOKEN_TTL`     | Random hex; the SPA reads it and echoes it as `X-CSRF-Token`.           |

The `csrf_token` cookie is deliberately not `HttpOnly` — the SPA
double-submit pattern requires JS to read it. XSS that can read this
cookie still cannot read the `access_token`, so no exfiltration is
possible; the CSRF cookie alone is useless without the matching
HttpOnly access cookie.

Cookies are rotated in lockstep on every login, register, refresh,
and OAuth callback (`src/auth/handlers.go::writeSessionCookies`) and
cleared together on logout, logout-all, and password change
(`src/auth/handlers.go::clearSessionCookies`).

## 2. CSRF (double-submit)

- `RequireCSRF` (`src/auth/csrf.go`) is mounted after `RequireAuth`
  on every protected route in the gateway HTTP server
  (`src/gateway/internal/server/http_server.go`).
- Safe methods (GET, HEAD, OPTIONS) pass through unmodified.
- Mutating methods (POST, PUT, PATCH, DELETE) require
  `csrf_token` cookie value == `X-CSRF-Token` header value, byte-for-
  byte under constant-time compare. Mismatch returns 403 with a
  generic message.
- The SPA reads `csrf_token` from `document.cookie` and attaches the
  `X-CSRF-Token` header automatically via the request interceptor in
  `cotradee/src/lib/axios.ts`. No feature code needs to think about it.

## 3. Deployment matrix

The gateway's `auth.Config.validate()` enforces every constraint at
startup so a misconfigured deployment fails fast.

### 3.1 Local-dev HTTP (Vite on `:5173` → gateway on `:8080`)

```
AUTH_COOKIE_DOMAIN=
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=Lax
AUTH_CSRF_HEADER=X-CSRF-Token
GATEWAY_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000
```

`ALLOWED_ORIGINS` is shared by the engine, management, and execution
HTTP servers; `GATEWAY_ALLOWED_ORIGINS` is the gateway's own list.
The SPA origin must appear in BOTH variables because the SPA talks
to all four services directly via `api.gateway`, `api.engine`,
`api.management`, and `api.execution`.

Why `Secure=false`: browsers refuse to store cookies with the
`Secure` attribute over plain HTTP. The next request arrives without
cookies and the gateway responds `unauthorized: missing
authorization header`. This is exactly the symptom that broke local
login on `main` before this MR.

Why `SameSite=Lax`: `Strict` would block the cookie on any cross-
origin XHR (`:5173 → :8080` is cross-origin by browser definition
even though it's same-host). `Lax` is permissive enough to let
login work while still defeating CSRF (we also have the explicit
double-submit token).

Why origin allow-list: `withCredentials:true` requests need the
server to echo the exact `Origin` back in
`Access-Control-Allow-Origin` AND set `Access-Control-Allow-
Credentials: true`. Both are handled by `corsMiddleware` in
`http_server.go`; the allow-list is the only operator knob.

### 3.2 Production single-host HTTPS (SPA + API on the same host)

```
AUTH_COOKIE_DOMAIN=
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=Strict
AUTH_CSRF_HEADER=X-CSRF-Token
GATEWAY_ALLOWED_ORIGINS=https://app.example.com
ALLOWED_ORIGINS=https://app.example.com
```

This is the most secure topology: same-site `Strict` cookies cannot
ride any cross-site request at all, the double-submit token defends
against XSS-driven same-site POSTs, and the SPA + API share a host
so `Origin` checks are trivial.

### 3.3 Production cross-subdomain HTTPS (`app.exoper.com` ↔ `api.exoper.com`)

```
AUTH_COOKIE_DOMAIN=.exoper.com
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=None
AUTH_CSRF_HEADER=X-CSRF-Token
GATEWAY_ALLOWED_ORIGINS=https://app.exoper.com
ALLOWED_ORIGINS=https://app.exoper.com
```

`AUTH_COOKIE_DOMAIN=.exoper.com` is the **mandatory** knob that
makes the cookies set by the gateway (`api.exoper.com`) reach the
engine (`engine.exoper.com`) and any other backend that lives on
`*.exoper.com`. Per RFC 6265 §5.4 the browser does not send a
host-only cookie to a sibling subdomain; setting the registrable
domain (with a leading dot) is the only fix. If your engine lives
at an entirely different registrable domain (e.g.
`api.example.com` + `engine.elsewhere.com`), cookies will NOT cross
the boundary and the engine must be made same-origin by routing it
through the gateway or by serving it from a sibling subdomain of
the SPA.

`SameSite=None` is required for the browser to attach cookies on a
true cross-site fetch. Browsers reject `None`+`Secure=false`; the
gateway's `validate()` rejects it too. The leading dot on
`AUTH_COOKIE_DOMAIN` is required for sub-domain matching under RFC
6265 §5.1.3.

## 4. WebSocket and SSE

### 4.1 WebSocket (notifications)

The gateway middleware (`src/auth/middleware.go::extractAndVerifyHTTP`)
reads the access token from one of three channels, in order:

1. `Authorization: Bearer <token>` header (CLI tooling, server-to-
   server).
2. `Sec-WebSocket-Protocol: Bearer, <token>` (non-browser WS clients
   that hold the token explicitly).
3. `access_token` cookie. Used by **cookie-auth browsers for both
   HTTP and WS**: the browser cannot read an HttpOnly cookie from JS
   to put it into the subprotocol header, so the cookie itself
   (attached automatically to the WS handshake) is the only
   browser-safe WS auth signal.

`cotradee/src/features/realtime/useNotificationsSocket.ts` calls
`new WebSocket(url)` with no subprotocol — the cookie does the work.

### 4.2 SSE (live reasoning stream)

`cotradee/src/features/alerts/hooks/useLiveReasoningStream.ts` calls
`fetch(url, { credentials: 'include' })`. Cookies set on the gateway
host are sent to the engine host under RFC 6265 because cookies are
scoped by host (not port). The Python engine reads the
`access_token` cookie the same way it reads the `Authorization`
header.

### 4.3 Tick stream

`cotradee/src/features/chart/hooks/useTickStream.ts` calls
`new WebSocket(url)`. The init frame is `{ symbol }` only; the user
identity is resolved from the access cookie on the upgrade request,
not from the body.

### 4.4 Cookie scoping on the engine SSE / WS streams

Cookies are scoped by **host** (not port) under RFC 6265 §5.4. The
implication for the engine streams is:

* **Local dev** (`localhost:8080` gateway + `localhost:8000` engine):
  cookies set on `localhost` are sent to both ports. No action needed.
* **Same-host production** (gateway + engine reverse-proxied behind
  one hostname): same as local dev.
* **Cross-subdomain production** (`api.exoper.com` gateway,
  `engine.exoper.com` engine): `AUTH_COOKIE_DOMAIN=.exoper.com` is
  mandatory. Without it, the cookie set by the gateway never reaches
  the engine and every SSE / WS handshake 401s.
* **Cross-registrable-domain production** (e.g. gateway on
  `api.example.com`, engine on `engine.elsewhere.com`): the cookie
  cannot cross the boundary at all. Move the engine behind the same
  registrable domain or proxy its routes through the gateway.

## 5. CORS

The gateway HTTP server (`src/gateway/internal/server/http_server.go::
corsMiddleware`) emits the headers required for credentialed cross-
origin requests:

```
Access-Control-Allow-Origin:      <echoed if in allow-list>
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods:     GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers:     Content-Type, Authorization, X-Trace-ID, X-CSRF-Token
Access-Control-Max-Age:           86400
```

No change is needed for the cookie-auth migration; the headers are
already correct.

## 6. Troubleshooting

| Symptom                                                                 | Root cause                                                                                  | Fix                                                                                                                                |
|-------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| `unauthorized: missing authorization header` on the FIRST request after login on local dev | `AUTH_COOKIE_SECURE=true` over plain HTTP. Browser drops `Set-Cookie` silently.             | Set `AUTH_COOKIE_SECURE=false` and `AUTH_COOKIE_SAMESITE=Lax` for local dev. Restart the gateway so `validate()` re-runs.          |
| Login succeeds, dashboard mounts, immediate 401 from `/api/v1/billing/subscription` | Stale frontend bundle still using `localStorage.getItem('access_token')` (returns `null`).  | Rebuild the SPA (`npm run build` or restart `vite`) so it picks up the cookie-auth `api.gateway` client.                            |
| 403 `csrf token missing or invalid` on a POST that worked before        | `csrf_token` cookie absent or stale (e.g. after a tab kept open across a logout in another tab). | Reload the SPA. The login response will mint a fresh `csrf_token` cookie that the axios interceptor will pick up on the next call. |
| Cookies set in browser dev-tools but not sent on subsequent requests    | Origin mismatch — the SPA is being served from a hostname NOT in `GATEWAY_ALLOWED_ORIGINS`. | Add the exact origin (scheme + host + port) to `GATEWAY_ALLOWED_ORIGINS` and restart the gateway.                                  |
| WS notification socket never connects but `/auth/me` works              | Pre-fix gateway binary refusing the access-cookie on WS upgrades.                            | Run the binary built from `fix/cookie-auth-finalize-frontend` or newer. Middleware now reads the cookie on WS handshakes.          |
| SSE reasoning stream 401s repeatedly                                    | `ALLOWED_ORIGINS` on the engine does not include the SPA origin, OR cookies are not crossing hosts in cross-subdomain production. | Add the SPA origin to `ALLOWED_ORIGINS`. For cross-subdomain prod, set `AUTH_COOKIE_DOMAIN` to the registrable domain (`.example.com`). |
| Management or execution REST call 403 on CORS preflight                 | `MANAGEMENT_ALLOWED_ORIGINS` / `EXECUTION_ALLOWED_ORIGINS` / `ALLOWED_ORIGINS` empty.        | Set `ALLOWED_ORIGINS` (or the service-specific override) to include the SPA origin.                                                |
| POST 403 "csrf token missing or invalid" right after an idle period that triggered a silent refresh | Old `X-CSRF-Token` header on the QUEUED request was still attached after the refresh rotated the cookie. | Already fixed in `cotradee/src/lib/axios.ts` (re-stamps the header at retry). If you still see this, hard-reload the SPA.            |
| Logging out in one tab leaves a stale signed-in shell in another tab    | `storage` event listener not installed (very old SPA bundle).                                | Hard-reload every tab. Post-fix, `broadcastLogoutAndRedirect` writes `etradie:auth:logout` to `localStorage` and peer tabs redirect.|
| `COOKIE_SAMESITE=None requires COOKIE_SECURE=true` startup error        | Production deploy set `SameSite=None` without `Secure=true`.                                | Set `AUTH_COOKIE_SECURE=true`. Browsers reject the unsafe combination anyway; failing fast at startup is correct.                  |

## 7. Verifying the deployment

From a logged-in browser session:

1. Open dev-tools → Application → Cookies. Expect `access_token`,
   `refresh_token`, and `csrf_token` to be present for the gateway
   host. The first two must show `HttpOnly`; the last must not.
2. Inspect a mutating XHR (e.g. POST `/api/v1/cycle/run`). The
   request headers must contain `X-CSRF-Token: <same hex value as
   csrf_token cookie>`.
3. Inspect a WS connection (`/ws/notifications`). The handshake must
   show the `Cookie: access_token=…; csrf_token=…` header. No
   `Sec-WebSocket-Protocol` is required.
4. Issue a forced logout (`/auth/logout`) and re-inspect the cookie
   jar. All three cookies must be expired (`MaxAge=-1` on the
   response).

If any of these fail, walk back through Section 6 — the table is
ordered by frequency of occurrence in real deployments.
