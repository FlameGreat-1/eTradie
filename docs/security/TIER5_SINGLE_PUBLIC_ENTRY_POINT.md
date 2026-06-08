# TIER 5 — Single Public Entry Point (Option B) Execution Plan

> Status: **Plan / not yet implemented.** This document is the authoritative,
> no-assumptions record of the current architecture as it exists on `main`,
> plus the exact, file-by-file work required to move the platform to a
> single public API origin (`api.exoper.com`).
>
> It supersedes the loose notes in `/NOTE.md`. Everything below was verified
> by reading the real source on the `main` branch (not git history, not
> diffs).

---

## 0. Decision

We execute **Option B — Single Public Entry Point**:

```text
Browser
   ↓
Cloudflare        (DNS, WAF, HSTS, edge rate-limit)
   ↓
edge-ingress      (Rust; TLS, geo-routing, connection limiting)
   ↓
Envoy             (security headers, local rate-limit, request validation)
   ↓
Gateway           (auth, CSRF, cookies; reverse-proxy to internal services)
   ↓
Internal services (Engine, Execution, Management, Billing, Journal)
```

The browser must reach **only** `api.exoper.com`. Engine, Execution,
Management, Billing and Journal become **internal-only** and are reached by
the browser **exclusively through the Gateway** under unified `/api/*`
prefixes.

We DO NOT keep the current multi-origin model where the browser holds
`VITE_ENGINE_URL`, `VITE_EXECUTION_URL`, `VITE_MANAGEMENT_URL`, etc.

---

## 1. Verified current architecture (as-is on `main`)

### 1.1 What the browser calls today

The SPA builds **four** axios clients in `cotradee/src/lib/axios.ts` from the
values in `cotradee/src/config/env.ts`:

| Client            | Env var                  | Local default            |
| ----------------- | ------------------------ | ------------------------ |
| `gatewayApi`      | `VITE_GATEWAY_HTTP_URL`  | `http://localhost:8080`  |
| `engineApi`       | `VITE_ENGINE_URL`        | `http://localhost:8000`  |
| `executionApi`    | `VITE_EXECUTION_URL`     | `http://localhost:8081`  |
| `managementApi`   | `VITE_MANAGEMENT_URL`    | `http://localhost:8083`  |
| WebSocket base    | `VITE_GATEWAY_WS_URL`    | `ws://localhost:8080`    |

All four clients are created with `withCredentials: true`. Auth is
**cookie-based** (`__Secure-access_token` HttpOnly, `__Secure-refresh_token`
HttpOnly scoped to `/auth`, `__Secure-csrf_token` JS-readable). The request
interceptor stamps `X-CSRF-Token` on mutating methods; the 401 response
interceptor performs a cross-tab-locked silent refresh; multi-tab logout is
broadcast via `localStorage`.

Structured error envelopes the SPA depends on (MUST be preserved by the proxy):
* 403 `{ error_code: "tier_required", required_tier, feature }`
* 429 `{ error_code: "llm_quota_exceeded", ... }`

### 1.2 What the Gateway exposes today

`src/gateway/internal/server/api_handlers.go::RegisterProtectedRoutes` mounts
ONLY:

* `POST /api/v1/cycle/run`
* `GET|PUT /api/v1/symbols`
* `POST /api/v1/symbols/reset`
* `GET /api/v1/config`
* `PUT /api/v1/config/interval`
* `GET /api/v1/health`

`src/gateway/internal/server/http_server.go` additionally mounts: `/health`,
`/readiness`, `/metrics`, waitlist, `/auth/*`, `/ws/notifications`,
`/events/recent`, `/events/since`, billing, metering, consent, support,
trading-system, trading-plan, performance-review, admin-billing, admin-quota,
user-billing, kill-switch.

The Gateway does **NOT** currently proxy `/api/broker/*`, `/api/analysis/*`,
`/api/llm/*`, `/api/usage/*`, `/api/processor/*` (engine), nor the execution
`/api/v1/state|account|settings|orders/cancel`, nor management
`/api/v1/management/*`.

### 1.3 How the Gateway talks to backends internally today

From `src/gateway/internal/config/config.go`:

* Engine: **HTTP** via `GATEWAY_ENGINE_HTTP_URL` (default `http://localhost:8000`),
  client `src/gateway/internal/infra/engine_http.go`.
* Execution: **gRPC** via `GATEWAY_EXECUTION_ADDR` (default `localhost:50053`).
* Management: **gRPC** via `GATEWAY_MANAGEMENT_ADDR` (default `localhost:50054`).
* Billing: **HTTP** via `GATEWAY_BILLING_SERVICE_URL` (default `http://billing:8082`).

IMPORTANT: Execution and Management ALSO run their own **HTTP servers** that
the browser hits directly today (this is the browser surface we must proxy):
* Execution HTTP: `src/execution/internal/server/http_server.go` (port `:8081`).
* Management HTTP: `src/management/internal/http/server.go` (port `:8083`).

The Gateway's existing gRPC links to execution/management are for the
orchestrator/kill-switch and are unrelated to the browser surface. They stay.

### 1.4 Uniform cookie auth across all browser surfaces (KEY ENABLER)

Every browser-facing service validates the **same** cookies with the **same**
middleware shape:

* Gateway & Execution & Management (Go): `auth.RequireAuth(tokenService)` then
  `auth.RequireCSRF(authCfg)`.
* Engine (FastAPI, `src/engine/main.py`): `CSRFMiddleware` + `get_current_user`
  reading the same `access_token` cookie; `/internal/*` is exempt (uses
  `X-Internal-Auth`).

Consequence: the Gateway proxy can forward the **cookie jar + `X-CSRF-Token`
header unchanged** and each upstream re-validates identically. The proxy does
NOT need to translate auth. It only needs to rewrite the path prefix.

### 1.5 Verified browser-facing route inventory (authoritative)

**Engine (`:8000`, FastAPI) — routers in `src/engine/routers/`:**
* `analysis.py`: `GET /api/analysis/latest`, `/history`, `/stats`,
  `/{analysis_id}`, `POST /api/analysis/rerun`, **SSE** `GET /api/analysis/stream-live`,
  `GET /api/usage/me`.
* `broker_connections.py`: `GET|POST /api/broker/connections`,
  `/connections/active`, `/connections/{id}` (`GET|PUT|DELETE`),
  `/connections/{id}/activate|deactivate|set-primary|test` (`POST`).
* `chart.py`: `GET /api/broker/symbols`, `GET /api/broker/candles`,
  **WS** `/api/broker/stream-ticks`, **WS** `/api/broker/stream-positions`.
* `llm_connections.py`: `GET /api/llm/providers`, `/connections`,
  `/connections/active`, `POST /api/llm/connections`, `PUT|DELETE
  /api/llm/connections/{id}`, `/connections/{id}/activate|deactivate`,
  `GET|POST|DELETE /api/llm/platform/connection`.
* `processor_config.py`: `GET /api/processor/models`, `GET|PUT /api/processor/config`.
* `broker_bridge.py`, `trading_plan.py`, `performance_review.py`,
  `internal.py`, `health.py` — either `/internal/*` (engine-only) or already
  proxied via gateway-native handlers; NOT part of the direct browser surface
  except where listed above.

**Execution (`:8081`, Go) — `src/execution/internal/server/http_server.go`:**
* `GET|PUT /api/v1/settings`
* `GET /api/v1/state`
* `POST /api/v1/orders/cancel`
* `GET /api/v1/account`
* `GET /internal/audit/replay` (operator/executionctl, NOT browser)
* `GET /ws/notifications` (NOT consumed by the browser — see 1.6)

**Management (`:8083`, Go) — `src/management/internal/http/server.go`:**
* `GET /api/v1/management/trades`
* `GET /api/v1/management/journal`
* `GET /api/v1/management/metrics`
* `GET /api/v1/management/pnl-calendar`
* `POST /internal/performance-review/aggregate` (engine shared-secret, NOT browser)

**Gateway-native (`:8080`) — stays as-is:** `/api/v1/cycle/run`,
`/api/v1/symbols*`, `/api/v1/config*`, `/api/v1/health`, `/auth/*`,
`/api/v1/billing/*`, `/api/v1/admin/*`, `/api/v1/performance-review/*`,
`/api/v1/trading-plan*`, `/api/v1/trading-system*`, `/api/v1/execution/kill-switch`,
`/api/v1/admin/execution/kill-switch`, `/ws/notifications`, `/events/*`.

### 1.6 WebSocket / streaming inventory (CRITICAL)

| Endpoint                       | Type | Browser target today | Action under Option B            |
| ------------------------------ | ---- | --------------------- | -------------------------------- |
| `/ws/notifications`            | WS   | **Gateway** already   | No change. (Execution's own WS is NOT used by the browser; events fan out via the gateway alert hub + Redis transport.) |
| `/api/broker/stream-ticks`     | WS   | **Engine** directly   | Gateway must **WS-proxy** → engine |
| `/api/broker/stream-positions` | WS   | **Engine** directly   | Gateway must **WS-proxy** → engine |
| `/api/analysis/stream-live`    | SSE  | **Engine** directly   | Gateway must **stream-proxy** → engine |

Verified sources: `cotradee/src/features/realtime/useNotificationsSocket.ts`
(uses `env.gatewayWsUrl`), `cotradee/src/features/chart/hooks/useTickStream.ts`
(derives WS from `env.engineUrl` → `/api/broker/stream-ticks`),
`src/engine/routers/chart.py` (declares both WS + the SSE in `analysis.py`).

### 1.7 Edge chain (verified)

* `infrastructure/cloudflare/main.tf`: zone TLS, AOP, DNS CNAMEs to the
  Cloudflare Tunnel UUID, WAF managed ruleset, **edge rate-limit already keyed
  on `^/api/` and `^/auth/`**, Super Bot Fight Mode, and **HSTS** (response
  header transform). Browser security headers (CSP, X-Frame-Options,
  X-Content-Type-Options, Referrer-Policy) are emitted at **Envoy**
  (`helm/envoy/values.yaml::securityHeaders`), NOT here.
* edge-ingress (Rust): `src/edge-ingress/` + `helm/edge-ingress` (cloudflared
  tunnel deployment, configmap, networkpolicy). Only the gateway is
  tunnel-routed today.
* Envoy: `src/envoy/config/{local,staging,production}/*.yaml` + `helm/envoy`.
* Because the existing Cloudflare rate-limit/WAF already match `^/api/`, the
  unified `/api/*` prefix design needs **no new public hostname** and inherits
  the existing edge protections automatically.

### 1.8 Helm layout (verified)

`helm/` contains one chart each for: `billing`, `data-layer`, `edge-ingress`,
`engine`, `envoy`, `execution`, `gateway`, `management`, `mt-node`,
`observability-logs`. Each service chart has `service.yaml`,
`networkpolicy.yaml`, `linkerd-authzpolicy.yaml`, `configmap.yaml`,
`deployment.yaml`, and `values{,-staging,-production}.yaml`.

---

## 2. Target gateway proxy route table (browser → upstream)

All routes below are mounted behind the existing `authMiddleware` +
`csrfMiddleware` chain and forward cookies, `X-CSRF-Token`, and `X-Trace-ID`
unchanged. Path prefix is rewritten as shown.

| Browser path (on `api.exoper.com`)                 | Upstream service | Upstream path                         |
| --------------------------------------------------- | ---------------- | ------------------------------------- |
| `/api/analysis/*`                                   | Engine (HTTP)    | `/api/analysis/*` (incl. SSE stream-live) |
| `/api/broker/*`                                     | Engine (HTTP/WS) | `/api/broker/*` (incl. WS stream-ticks, stream-positions) |
| `/api/llm/*`                                        | Engine (HTTP)    | `/api/llm/*`                          |
| `/api/usage/*`                                      | Engine (HTTP)    | `/api/usage/*`                        |
| `/api/processor/*`                                  | Engine (HTTP)    | `/api/processor/*`                    |
| `/api/execution/state`                              | Execution (HTTP) | `/api/v1/state`                       |
| `/api/execution/account`                            | Execution (HTTP) | `/api/v1/account`                     |
| `/api/execution/settings`                           | Execution (HTTP) | `/api/v1/settings`                    |
| `/api/execution/orders/cancel`                      | Execution (HTTP) | `/api/v1/orders/cancel`               |
| `/api/management/trades`                            | Management (HTTP)| `/api/v1/management/trades`           |
| `/api/management/journal`                           | Management (HTTP)| `/api/v1/management/journal`          |
| `/api/management/metrics`                           | Management (HTTP)| `/api/v1/management/metrics`          |
| `/api/management/pnl-calendar`                      | Management (HTTP)| `/api/v1/management/pnl-calendar`     |

Billing, performance-review, trading-plan, trading-system, admin, kill-switch,
symbols, config, cycle/run remain **gateway-native** (already single-origin).

NOTE on prefixes: Execution natively uses `/api/v1/*`, which COLLIDES with
gateway-native `/api/v1/symbols|config|...`. That is why execution/management
are re-prefixed to `/api/execution/*` and `/api/management/*` at the browser
edge and rewritten to the service-native paths by the proxy.

---

## 3. Exact changes — file by file

### 3.1 Gateway (Go)

1. **`src/gateway/internal/config/config.go`**
   * Add `ExecutionHTTPURL string \`envconfig:"EXECUTION_HTTP_URL" default:"http://localhost:8081"\``.
   * Add `ManagementHTTPURL string \`envconfig:"MANAGEMENT_HTTP_URL" default:"http://localhost:8083"\``.
   * (Engine HTTP URL `EngineHTTPURL` and `BillingServiceURL` already exist.)
   * Add `validate()` checks: non-empty; parseable URL; in prod-like env
     refuse `localhost`/`127.0.0.1` (mirror the existing Redis prod guard).

2. **`src/gateway/internal/server/` — new file `proxy_handler.go`**
   * Implement a reverse-proxy handler built on `net/http/httputil.ReverseProxy`
     with a custom `Director` that:
     - rewrites the browser prefix to the upstream prefix per the table in §2,
     - preserves `Cookie`, `X-CSRF-Token`, `X-Trace-ID`, `Content-Type`,
     - sets `X-Forwarded-*` correctly.
   * Make it WebSocket-aware (detect `Upgrade: websocket` and hijack/copy
     bidirectionally) for `/api/broker/stream-ticks` and `/api/broker/stream-positions`.
   * Make it SSE/streaming-safe: `FlushInterval = -1` (or a small positive
     value) so `/api/analysis/stream-live` streams without buffering.
   * Preserve upstream status codes and bodies verbatim so the SPA's
     `tier_required` (403) and `llm_quota_exceeded` (429) envelopes pass through.
   * Add panic recovery consistent with `APIHandler.withPanicRecovery`.

3. **`src/gateway/internal/server/http_server.go`**
   * After the existing `api.RegisterProtectedRoutes(...)` call, mount the new
     proxy routes wrapped with `authMiddleware(csrfMiddleware(proxy))` for each
     prefix in §2. Use distinct `mux.Handle(prefix, ...)` registrations.
   * Add the three upstream base URLs (engine/execution/management HTTP) to
     `NewHTTPServer` inputs (or read from `cfg`).

4. **`src/gateway/internal/container/container.go`**
   * Pass `cfg.ExecutionHTTPURL` and `cfg.ManagementHTTPURL` (and existing
     `cfg.EngineHTTPURL`) into the HTTP server constructor so the proxy knows
     its upstreams. (gRPC adapters remain untouched.)

5. **Tests**
   * `src/gateway/e2etest/` already has a mock engine server pattern
     (`mock_engine_server.go`). Add proxy-routing tests: assert that a
     browser call to `/api/execution/state` reaches the (mock) execution
     upstream at `/api/v1/state` with cookies + CSRF intact, and that a
     `tier_required` 403 and `llm_quota_exceeded` 429 pass through unchanged.

### 3.2 Frontend (TypeScript, `cotradee/`)

1. **`cotradee/src/config/env.ts`**
   * Replace `engineUrl`/`executionUrl`/`managementUrl`/`gatewayHttpUrl` with a
     single `apiUrl` (`VITE_API_URL`, default `http://localhost:8080`) and
     `apiWsUrl` (`VITE_API_WS_URL`, default `ws://localhost:8080`).
   * Keep `googleOAuthEnabled` / `oauthCallbackPath` unchanged.

2. **`cotradee/src/lib/axios.ts`**
   * Collapse the four `createClient(...)` calls to ONE client pointed at
     `env.apiUrl`. Keep the `api` object keys (`gateway`, `engine`, `execution`,
     `management`) as **aliases of the single client** so existing imports keep
     compiling, OR refactor call sites to a single `api`. (Aliasing is the
     lower-risk path; the interceptors, CSRF stamping, and 401-refresh logic
     are unchanged.)
   * Update the `/auth/refresh` call to use `env.apiUrl`.

3. **Rewrite call-site paths** (engine/execution/management → unified prefixes):
   * `cotradee/src/features/broker/api/brokerConnections.ts`: keep `/api/broker/*` (now proxied).
   * `cotradee/src/features/analysis/api/analysis.ts`: keep `/api/analysis/*`.
   * `cotradee/src/features/llm/api/llmConnections.ts`: keep `/api/llm/*`.
   * `cotradee/src/features/symbols/api/symbols.ts`: keep `/api/broker/symbols`.
   * `cotradee/src/features/chart/api/chartData.ts`: keep `/api/broker/candles`.
   * `cotradee/src/features/chart/hooks/useTickStream.ts`: change WS base from
     `env.engineUrl.replace(/^http/, 'ws')` to `env.apiWsUrl`; path stays
     `/api/broker/stream-ticks`.
   * `cotradee/src/features/execution/api/brokerAccount.ts`: change
     `/api/v1/account` → `/api/execution/account`, `/api/v1/state` →
     `/api/execution/state`, `/api/v1/settings` → `/api/execution/settings`,
     `/api/v1/orders/cancel` → `/api/execution/orders/cancel`. (The kill-switch
     calls already use `api.gateway` + `/api/v1/execution/kill-switch`; leave
     those.)
   * `cotradee/src/features/journal/api/journal.ts`: change
     `/api/v1/management/*` → `/api/management/*`.
   * `cotradee/src/features/admin/api/admin.ts`: keep `/api/processor/*`.
   * Any component using the engine SSE (`/api/analysis/stream-live`) must use
     `env.apiUrl`.

4. **`cotradee/.env.example`**
   * Replace the five `VITE_*_URL` entries with `VITE_API_URL` and
     `VITE_API_WS_URL` only.

5. **`cotradee/vercel.json`**
   * Set CSP `connect-src` to exactly:
     `connect-src 'self' https://api.exoper.com wss://api.exoper.com`.
   * Update the header-generator / `npm run lint:headers` baseline so the
     committed `vercel.json` matches the generator output for the new env set.

### 3.3 Engine / Execution / Management (backends)

No route changes are required (the Gateway proxies the existing paths). The
only hardening is to ensure these services are **not publicly reachable**:

* Confirm their `ALLOWED_ORIGINS` no longer needs to include the SPA origin
  for direct browser CORS (the browser no longer calls them cross-origin;
  the Gateway is the only caller). Keep CORS permissive only for the gateway
  origin if any same-cluster preflight is needed; otherwise the credentialed
  CORS allowlist can be emptied for these services.

### 3.4 Infrastructure / edge

* **`infrastructure/cloudflare/main.tf`** (`var.hostnames`): ensure ONLY the
  public hostnames (SPA + `api.exoper.com`) are CNAMEd to the tunnel. Remove
  any `engine.*`, `execution.*`, `management.*`, `billing.*` public records if
  present. The existing `^/api/` and `^/auth/` rate-limit + WAF rules already
  cover the unified surface.
* **edge-ingress / cloudflared** (`helm/edge-ingress`): confirm the tunnel
  ingress rules route only to the gateway service. No per-service public
  ingress.
* **Envoy** (`src/envoy/config/*`, `helm/envoy`): route table targets the
  gateway cluster only (already the case). No new clusters for the browser
  surface.

### 3.5 Helm — make internal services internal-only

For `helm/engine`, `helm/execution`, `helm/management`, `helm/billing`:
* `service.yaml`: keep `ClusterIP` (no `LoadBalancer`/`NodePort`).
* `networkpolicy.yaml`: restrict ingress to the **gateway** pod selector
  (engine also accepts gateway `/internal/*`; management accepts engine
  `/internal/performance-review/aggregate`; execution accepts gateway gRPC).
* `linkerd-authzpolicy.yaml`: allow only gateway (and the documented internal
  callers) as authorized clients.
* Add the new gateway env wiring in `helm/gateway`:
  `configmap.yaml`/`values*.yaml` set `GATEWAY_EXECUTION_HTTP_URL` and
  `GATEWAY_MANAGEMENT_HTTP_URL` to the in-cluster service DNS
  (e.g. `http://execution.<ns>.svc.cluster.local:8081`,
  `http://management.<ns>.svc.cluster.local:8083`).

### 3.6 docker-compose (local dev)

* `docker-compose.yml` / `docker-compose.override.yml`: set the gateway's
  `GATEWAY_EXECUTION_HTTP_URL` / `GATEWAY_MANAGEMENT_HTTP_URL` to the compose
  service names; the SPA dev env uses only `VITE_API_URL=http://localhost:8080`.

---

## 4. Constraints / invariants (MUST NOT break)

1. Cookie auth flow: `__Secure-access_token` / `__Secure-refresh_token`
   (scoped `/auth`) / `__Secure-csrf_token`; silent 401 refresh with cross-tab
   Web Locks; multi-tab logout broadcast.
2. Structured error envelopes must pass through the proxy verbatim:
   403 `tier_required`, 429 `llm_quota_exceeded`.
3. WebSocket (`stream-ticks`, `stream-positions`) and SSE (`stream-live`) must
   stream through the gateway without buffering or idle-timeout kills.
4. The gateway's existing gRPC links to execution/management (orchestrator,
   kill-switch) are unrelated and must remain untouched.
5. CSRF: mutating proxied requests carry `X-CSRF-Token`; the upstream
   re-validates. Safe methods bypass CSRF (existing `RequireCSRF` behavior).
6. No production break: every change is additive on the gateway (new routes),
   path-only on the SPA, and exposure-only on infra/helm.

---

## 5. Operator / deploy follow-ups

1. Set `GATEWAY_EXECUTION_HTTP_URL` and `GATEWAY_MANAGEMENT_HTTP_URL` in the
   gateway's environment (Helm values / ExternalSecret as appropriate).
2. Set the SPA build env to `VITE_API_URL=https://api.exoper.com` and
   `VITE_API_WS_URL=wss://api.exoper.com`; rebuild + redeploy Vercel.
3. Confirm `vercel.json` CSP `connect-src` is
   `'self' https://api.exoper.com wss://api.exoper.com` and `npm run lint:headers` passes.
4. Remove any public DNS for engine/execution/management/billing subdomains.
5. Toggle Cloudflare HSTS on at the live zone (see `CLOUDFLARE.md`) once the
   server is confirmed healthy.
6. Verify NetworkPolicy + linkerd authz restrict the internal services to
   gateway-only ingress after rollout.

---

## 5b. Implementation progress tracker

This section is updated as each step lands on branch
`docs/tier5-single-entry-point-execution-plan` (MR !118). If a chat ends,
resume from the first unchecked item.

- [x] **Step 1 — Gateway config**: `EXECUTION_HTTP_URL` + `MANAGEMENT_HTTP_URL`
      added to `src/gateway/internal/config/config.go` with `validateProxyUpstream`
      (http(s) + host required; no localhost in prod) applied to execution,
      management, and engine HTTP URLs.
- [x] **Step 2 — Proxy handler**: `src/gateway/internal/server/proxy_handler.go`
      (`ReverseProxyHandler`, per-upstream `httputil.ReverseProxy` with
      `Rewrite`, `FlushInterval=-1` for SSE, native WS upgrade, `ErrorHandler`
      → 502 JSON, prefix-rewrite route table).
- [x] **Step 3 — Mount proxy**: wired into `src/gateway/internal/server/http_server.go`
      after `RegisterProtectedRoutes`, wrapped with the same auth+CSRF chain.
- [x] **Step 4a — Frontend env**: `cotradee/src/config/env.ts` collapsed to
      `apiUrl`/`apiWsUrl` (`VITE_API_URL`/`VITE_API_WS_URL`) with deprecated
      aliases pointing at the single origin.
- [x] **Step 4b — Frontend axios**: `cotradee/src/lib/axios.ts` collapsed to
      ONE client; `api.{gateway,engine,execution,management}` are aliases.
- [x] **Step 4c — Call sites**: execution paths → `/api/execution/*`,
      management paths → `/api/management/*`, tick WS → `env.apiWsUrl`.
      (Engine `/api/broker|analysis|llm|usage|processor/*` paths unchanged —
      identity proxy rewrite.)
- [x] **Step 5 — env.example + CSP**: `cotradee/.env.example` collapsed to the
      two vars; `cotradee/vercel.json` `connect-src` regenerated.
- [x] **Step 5b — Header generator**: `cotradee/scripts/generate-vercel-headers.mjs`
      now derives `connect-src` from `VITE_API_URL`/`VITE_API_WS_URL`; committed
      `vercel.json` matches the baseline output so `lint:headers` passes.
- [ ] **Step 6 — Gateway e2e proxy test** in `src/gateway/e2etest/`.
- [ ] **Step 7 — Helm wiring**: gateway `values*.yaml`/`configmap.yaml` set
      `GATEWAY_EXECUTION_HTTP_URL` + `GATEWAY_MANAGEMENT_HTTP_URL` to in-cluster
      service DNS; confirm engine/execution/management remain ClusterIP with
      gateway-only NetworkPolicy/authz.
- [ ] **Step 8 — docker-compose**: set the gateway's execution/management HTTP
      URLs to compose service names for local dev.

## 6. Verification checklist (post-implementation)

* [ ] Browser DevTools → Network shows ALL XHR/fetch/WS go to `api.exoper.com`
      only (no engine/execution/management origins).
* [ ] `GET /api/execution/state` returns the execution state through the gateway.
* [ ] `GET /api/management/trades` returns managed trades through the gateway.
* [ ] `/api/broker/stream-ticks` WS connects and streams ticks via the gateway.
* [ ] `/api/analysis/stream-live` SSE streams via the gateway without buffering.
* [ ] A `tier_required` 403 still opens the Upgrade modal; an
      `llm_quota_exceeded` 429 still opens the quota modal.
* [ ] Silent 401 refresh + multi-tab logout still work across proxied routes.
* [ ] Internal services are not reachable from outside the cluster.
* [ ] `connect-src` CSP contains only `'self'`, `https://api.exoper.com`,
      `wss://api.exoper.com`.
