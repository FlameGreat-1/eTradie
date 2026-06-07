# TIER 4 — Abuse Prevention: Defense-in-Depth Execution Plan

> Status: PLAN / NOT YET EXECUTED (except where noted).
> Owner branch: `security/tier4-bodylimit-hardening` (MR !107).
> This document is the single source of truth for finishing the TIER 4
> "Abuse Prevention" row of `CHECKLIST.md`. It is written to be
> resumable: a fresh session can execute it end-to-end from this file
> alone, with no re-audit required.

---

## 0. Context & decision (read first)

**Question answered:** should anonymous/volumetric abuse controls live
only at Cloudflare, or also internally?

**Decision (enterprise / money-platform best practice): DEFENSE IN DEPTH.**
Each layer enforces what it is best at AND assumes the others may fail:

| Layer | Owns | Best at |
|-------|------|---------|
| Cloudflare (edge) | volumetric DDoS, bot mgmt, IP reputation, broad WAF, coarse per-IP HTTP rate limit | anonymous / volumetric abuse, absorbed before origin |
| edge-ingress (Rust, L4) | global + per-IP **connection** caps, TLS posture, AOP mTLS | connection-level abuse, cheap, no HTTP awareness |
| Envoy (L7) | per-connection L7 rate-limit backstop, request-byte limit, circuit breaking, overload | always-on origin backstop independent of Cloudflare |
| App (gateway) | **per-user** (JWT-scoped) rate limits, tier policy, brute-force | authenticated / business-logic abuse |

**Rationale:** the edge handles anonymous/volumetric abuse; the origin
handles authenticated/business-logic abuse AND is the backstop. Never
rely on a single edge you do not control end-to-end. A money platform's
threat model must assume the CDN can be bypassed or misconfigured.

---

## 1. Audit findings (confirmed line-by-line on `main`, this session)

### 1.1 edge-ingress (Rust) — `src/edge-ingress/`
- It is a **Layer-4 TLS-terminating TCP proxy**, NOT an HTTP proxy.
  `crates/edge-server/src/handler.rs` does: TLS handshake -> geo-route
  -> `copy_bidirectional(client, upstream)`. It never parses HTTP
  (no method/path/header/body inspection).
- ✅ `crates/connection-limiter/src/global.rs` — `GlobalConnectionLimiter`,
  atomic, RAII guard release on drop. Cap `MAX_GLOBAL_CONNECTIONS = 100_000`.
- ✅ `crates/connection-limiter/src/per_ip.rs` — `PerIpConnectionLimiter`,
  `DashMap<IpAddr, AtomicUsize>`, cap `MAX_CONNECTIONS_PER_IP = 1_000`,
  cleanup of idle IPs. Race-free.
- ✅ TLS posture (`crates/common/src/constants.rs::tls`): min 1.2,
  preferred 1.3, 3 modern AEAD suites; handshake timeout 10s; idle 300s.
- ✅ Production config `config/production/edge-ingress-production.yaml`
  enforces **Cloudflare Authenticated Origin Pulls (mTLS)** via
  `tls.client_auth.ca_path`. A connection without a Cloudflare-signed
  client cert fails at ServerHello. This + origin firewall (TCP/443
  restricted to Cloudflare ranges) strongly mitigates direct-to-origin
  bypass.
- 🔴 **FINDING E5 (dead config):** `constants.rs` declares
  `MAX_REQUEST_SIZE = 10_485_760` and `MAX_HEADER_SIZE = 16_384` but
  the L4 `copy_bidirectional` path NEVER reads them. They are dead
  constants that imply a protection that does not exist. Either wire
  a meaning or delete + document that byte limits live at Envoy.
  (Recommended: delete from the L4 crate and document, because an L4
  proxy genuinely cannot enforce HTTP byte limits; keeping them is
  misleading.)

### 1.2 Envoy — `helm/envoy/templates/configmap.yaml`
- ✅ Present: circuit breakers (gateway + billing clusters), outlier
  detection, overload manager (fixed_heap shrink at 0.95 / stop at
  0.98), `global_downstream_max_connections` (default 50000), health
  checks, retry policies, JSON access log, WASM integration filter,
  `use_remote_address: true`, `xff_num_trusted_hops: 1`.
- ✅ `http_filters` order is `envoy.filters.http.wasm` ->
  `envoy.filters.http.router`. Inserting `local_ratelimit` between
  wasm and router is clean and correct.
- 🔴 **FINDING A2a (confirmed absent): no `envoy.filters.http.local_ratelimit`.**
  No L7 rate limiting at the origin at all.
- 🔴 **FINDING A2b (confirmed absent): no request-byte / header limit.**
  The `http_connection_manager` has no `max_request_headers_kb` and no
  body/buffer byte cap. No L7 request-size backstop.

### 1.3 Cloudflare — `infrastructure/cloudflare/main.tf`
- ✅ Manages: zone TLS (`ssl=strict`, min TLS, TLS1.3 on, always-HTTPS),
  Authenticated Origin Pulls (zone-level), Tunnel DNS (`proxied=true`,
  `cfargotunnel.com`, `prevent_destroy`).
- 🔴 **FINDING A2c: NO WAF ruleset, NO rate-limiting rule, NO bot
  management in Terraform.** Any such rules currently exist only as
  click-ops in the Cloudflare dashboard (unversioned, unreviewed,
  not deployed by code) — an audit failure for a money platform.

### 1.4 App layer — `src/gateway/internal/server/api_handlers.go`
- ✅ Per-user tiered token bucket on `POST /api/v1/cycle/run`
  (keyed by JWT subject, fail-safe to free tier, `Retry-After`).
- ✅ Object-level ownership: every dashboard route derives `userID`
  from `claims.UserID`, never from a request param (no IDOR).
- 🔴 **FINDING A2d: the OTHER `/api/v1/*` routes** (`/symbols`,
  `/symbols/reset`, `/config`, `/config/interval`, `/health`) and the
  other protected surfaces (billing, support, consent, trading-system,
  trading-plan, perf-review) have **no per-user rate limit** — only
  `/cycle/run` does.

### 1.5 Authentication & Authorization (prior session, for completeness)
- ✅ JWT alg pinned to HMAC (`*jwt.SigningMethodHMAC`) -> blocks
  `alg:none` + RS/HS confusion; `exp` enforced twice; `iss` validated;
  `status` fail-closed; service-token epoch revocation fail-closed.
- ⚠️ **FINDING A1 (LOW): no `aud` (audience) claim** set or verified.
  Single shared HMAC secret means `iss` is the only separator today.
  Best practice: add + verify `aud`.

### 1.6 Abuse monitoring
- ✅ Metrics exist: edge-ingress `record_connection_*`, gateway
  rate-limit + guard-rejection counters, Envoy access logs.
- 🔴 **FINDING A2e: no alerting rules** tying abuse metrics to on-call.
  `helm/engine/templates/prometheusrule.yaml` exists for the engine;
  there is no equivalent abuse/rate-limit PrometheusRule for
  gateway/envoy/edge-ingress.

---

## 2. EXECUTION TASKS (do in this order)

> Convention: each task lists EXACT files, the change, and verification.
> Check the box when merged. Keep everything on MR !107 unless it grows
> too large, in which case spin a follow-up MR and link it here.

### TASK 1 — Envoy L7 local rate limit (FINDING A2a) 🔴 HIGH
- [ ] File: `helm/envoy/templates/configmap.yaml`
  - Insert `envoy.filters.http.local_ratelimit` in `http_filters`
    BETWEEN the `wasm` filter and the `router` filter.
  - Use a token-bucket: `token_bucket.max_tokens`,
    `tokens_per_fill`, `fill_interval`. Enable with `filter_enabled` /
    `filter_enforced` runtime fractions at 100% in prod.
  - `stat_prefix: http_local_rate_limiter`.
  - Set `status: code: 429` and add a `Retry-After` response header via
    `response_headers_to_add`.
  - This is a COARSE per-Envoy-instance limit (defense-in-depth
    backstop), NOT a substitute for the per-user app limiter or
    Cloudflare. Document that explicitly in a YAML comment.
- [ ] Files: `helm/envoy/values.yaml`, `values-production.yaml`,
      `values-staging.yaml`
  - Add a `config.envoy.localRateLimit` block:
    `enabled`, `maxTokens`, `tokensPerFill`, `fillIntervalSeconds`,
    `enforcedFraction`. Template the configmap off these.
  - Production values must be sized ABOVE the legitimate p99 aggregate
    rps per Envoy pod (the long-lived `/api/v1/cycle/run` calls are few
    but slow; the chatty calls are dashboard polls). Start generous
    (e.g. maxTokens high, fill every 1s) so it only trips on genuine
    floods. DO NOT clip normal traffic.
  - Staging: set enforcedFraction lower or maxTokens lower to test the
    429 path without a prod incident.
- [ ] Verify: `helm template helm/envoy -f helm/envoy/values-production.yaml`
      renders valid Envoy v3 config; `func-e`/`envoy --mode validate`
      if available in CI; confirm filter ORDER is wasm -> local_ratelimit
      -> router.
- [ ] CAUTION: the `/webhooks/paddle` and `/webhooks/lemonsqueezy`
      routes go to `billing_cluster`. Payment-provider webhooks must
      NOT be rate-limited (dropping a webhook = lost billing event).
      Either scope the local_ratelimit to the gateway route only (per
      virtual-host / per-route `typed_per_filter_config` with the
      webhook routes setting an effectively-unlimited bucket or
      `filter_enabled: 0`), OR document that the bucket is sized so
      webhooks never trip it. PREFER per-route disable on the two
      webhook prefixes.

### TASK 2 — Envoy request-size backstop (FINDING A2b) 🔴 HIGH
- [ ] File: `helm/envoy/templates/configmap.yaml`
  - On `http_connection_manager`, add
    `max_request_headers_kb: {{ ... | default 64 }}`.
  - Add `envoy.filters.http.buffer` OR a per-route
    `max_request_bytes` via the `Buffer` filter / connection-manager
    `max_request_bytes` on the route's `typed_per_filter_config`.
  - CRITICAL SIZING: must NOT clip the heavy gateway->engine internal
    payloads NOR the dashboard `POST /api/v1/cycle/run` body. But note:
    the heavy TA+Macro+RAG+Processor traffic is gateway<->engine
    (east-west, behind Envoy on the gateway path? VERIFY the topology:
    Envoy fronts the gateway, the engine calls are gateway->engine and
    may NOT traverse this Envoy). If engine traffic does NOT pass this
    Envoy, an 8 MiB cap here is safe. If it DOES, size >= the engine
    body cap (8 MiB, see `src/engine/shared/body_limit.py`) plus margin.
    VERIFY before choosing the number. Recommended default: 8–10 MiB on
    the gateway route, smaller (e.g. 256 KiB) on webhook routes.
- [ ] Files: `helm/envoy/values*.yaml` — add
      `config.envoy.maxRequestHeadersKb` and
      `config.envoy.maxRequestBytes` knobs (+ per-route webhook value).
- [ ] Verify: render + validate; confirm a >cap request gets 413, a
      normal cycle/run body passes.

### TASK 3 — Cloudflare WAF + rate-limit + bot rules in Terraform (FINDING A2c) 🔴 HIGH
- [ ] File: `infrastructure/cloudflare/main.tf` (+ `variables.tf`,
      `outputs.tf`)
  - Add `cloudflare_ruleset` of phase `http_request_firewall_managed`
    to enable Cloudflare Managed Ruleset (WAF).
  - Add `cloudflare_ruleset` of phase `http_ratelimit` with a coarse
    per-IP rate rule on `/api/*` and a TIGHTER rule on `/auth/*`
    (login/register/refresh/password-reset) to blunt credential
    stuffing at the edge.
  - Add bot management config (`cloudflare_bot_management`) IF the plan
    includes it; otherwise add a Super Bot Fight Mode setting and note
    the plan dependency.
  - Gate everything behind `variables.tf` toggles
    (`enable_waf`, `enable_rate_limiting`, `enable_bot_management`)
    defaulting ON for production, so envs can differ.
  - Add a YAML/HCL comment cross-referencing this doc and stating these
    rules are the FIRST layer; the Envoy + app limits are the backstop.
- [ ] Verify: `terraform validate` + `terraform plan` against the
      cloudflare workspace; confirm no change to existing TLS/DNS/AOP
      resources (additive only). Respect existing `prevent_destroy`.

### TASK 4 — Per-user default limiter on remaining gateway routes (FINDING A2d) 🟠 MEDIUM
- [ ] File: `src/gateway/internal/server/api_handlers.go`
  - Add a default per-user token-bucket limiter (reuse
    `billingservice.TokenBucketRateLimiter`) applied in `wrap(...)` or
    via a new middleware so ALL `/api/v1/*` mutating routes get a
    sane per-user cap, not just `/cycle/run`.
  - Keep `/cycle/run`'s dedicated tiered limiter as-is (it is the
    expensive path); the default limiter is a looser catch-all for the
    chatty routes.
  - Key by `claims.UserID`; fail-safe to a conservative bucket when
    claims are nil (should not happen behind RequireAuth, but be safe).
- [ ] Files: `src/auth/config.go` — add
      `AUTH_API_DEFAULT_RPM` / `AUTH_API_DEFAULT_BURST` envconfig knobs
      with bounds validation in `validate()` (mirror the existing
      cycle-RPM validation block).
- [ ] Consider applying the same to the OTHER protected handlers
      (billing/support/consent/trading-system/trading-plan/perf-review)
      by wrapping their `RegisterRoutes` middleware chain, OR document
      that the Envoy local_ratelimit (Task 1) is the backstop for those
      and the per-user limiter is only on the gateway API handler.
      DECISION REQUIRED: prefer a shared middleware so coverage is
      uniform.
- [ ] Verify: `go test ./src/gateway/... ./src/auth/...`; add a unit
      test asserting the limiter returns 429 after burst.

### TASK 5 — edge-ingress dead constants (FINDING E5) 🟡 LOW
- [ ] File: `src/edge-ingress/crates/common/src/constants.rs`
  - Either (preferred) DELETE `MAX_REQUEST_SIZE` and `MAX_HEADER_SIZE`
    and add a comment that HTTP byte limits are enforced at Envoy
    (Task 2), because an L4 proxy cannot enforce them; OR wire them
    into a pre-proxy guard if a meaningful L4 use exists (there is not
    one today).
  - Grep the whole `src/edge-ingress` workspace first to confirm they
    are truly unreferenced before deleting (`rg MAX_REQUEST_SIZE
    MAX_HEADER_SIZE`).
- [ ] Verify: `cargo build` + `cargo test` in `src/edge-ingress`.

### TASK 6 — JWT audience claim (FINDING A1) 🟡 LOW
- [ ] Files: `src/auth/token.go`, `src/auth/config.go`
  - Add `aud` to `IssueTokenPair` + `IssueServiceToken` claims (value
    from a new `AUTH_AUDIENCE` config, default `etradie-api`).
  - In `VerifyAccessToken`, validate `aud` matches the configured
    audience (mirror the existing `iss` check), fail-closed.
  - Keep BACKWARD COMPATIBILITY during rollout: a tolerant window
    where a missing `aud` is allowed, then flip to required. Document
    the two-deploy sequence so live sessions are not invalidated.
- [ ] Verify: `go test ./src/auth/...`; add a test for aud mismatch
      rejection and the tolerant-window behaviour.

### TASK 7 — Abuse-monitoring alert rules (FINDING A2e) 🟠 MEDIUM
- [ ] New file: `helm/gateway/templates/prometheusrule.yaml`
      (model on `helm/engine/templates/prometheusrule.yaml`).
  - Alerts: high rate of gateway 429s (per-user limiter tripping
    broadly), auth attempt-limiter saturation (credential stuffing),
    Envoy `http_local_rate_limiter` 429 spike, edge-ingress
    `PerIpConnectionLimitExceeded` / `ConnectionLimitExceeded` spike.
  - Wire to the existing Alertmanager routing / on-call receiver.
- [ ] Files: `helm/gateway/values*.yaml` (+ edge-ingress/envoy values if
      adding rules there) — add a `prometheusRule.enabled` toggle and
      thresholds.
- [ ] Verify: `helm template` renders; `promtool check rules` on the
      rendered output in CI.

---

## 3. Cross-cutting verification (run before merge)
- [ ] `helm template` for envoy + gateway charts (all value files) renders.
- [ ] `terraform validate` + `plan` for cloudflare (additive only).
- [ ] `go build ./... && go test ./src/gateway/... ./src/auth/...`.
- [ ] `cargo build && cargo test` in `src/edge-ingress`.
- [ ] Confirm the heavy TA+Macro+RAG+Processor pipeline path is NOT
      clipped by any new size cap (cross-check Envoy `max_request_bytes`
      vs engine 8 MiB body cap; verify whether engine traffic traverses
      this Envoy at all).
- [ ] Confirm payment webhooks (`/webhooks/paddle`,
      `/webhooks/lemonsqueezy`) are exempt from L7 rate limiting.
- [ ] CI pipeline green (this is the authoritative compile/lint check;
      the assistant cannot run builds locally).

## 4. Out-of-band (cannot be done in code — operator action)
- [ ] **F5 (still open):** rotate/revoke the committed NVIDIA `nvapi-...`
      key + SSH creds in `CLOUDFLARE.md` and purge from git history.
- [ ] Enable Cloudflare bot-management plan entitlement if Task 3 needs it.
- [ ] Confirm origin firewall restricts TCP/443 to Cloudflare ranges
      (pairs with edge-ingress AOP mTLS).

## 5. Progress log (update every session)
- Session 1: full TIER 4 audit; F1–F4 fixed + merged (!106); F5 left for
  operator. E1 (engine body-limit streaming) + E4 (gateway compile-break
  unused import) found + fixed on `security/tier4-bodylimit-hardening`
  (MR !107). Engine body cap raised 1 MiB -> 8 MiB (heavy-payload safety).
  Authentication + Authorization rows verified strong. Abuse-Prevention
  row audited: edge-ingress L4 conn-limits good, Envoy L7 rate-limit +
  byte-limit absent, Cloudflare WAF/rate/bot not in Terraform, app
  per-user limit only on /cycle/run. This plan written + committed to
  MR !107. TASKS 1–7 NOT yet executed.
- Session 2: <fill in>









## Edge-ingress + Envoy + Cloudflare — complete audit & the real best-practice answer

### What the edge-ingress actually is (the decisive fact)
The Rust edge-ingress is a **Layer-4 TLS-terminating TCP proxy**, not an HTTP proxy. `handler.rs` does TLS handshake → geo-route → `copy_bidirectional(client, upstream)`. It **never parses HTTP**: no method, path, header, or body inspection. That means:
- ✅ It enforces **connection-level** abuse controls: `GlobalConnectionLimiter` (100k cap) and `PerIpConnectionLimiter` (1,000/IP), both atomic, with correct RAII guard release on drop. Solid, race-free.
- ✅ TLS posture pinned (1.2 min, 1.3 preferred, 3 modern AEAD suites), handshake timeout 10s, idle timeout 300s.
- 🔴 **It cannot do per-route HTTP rate limiting, request-byte limits, or bot protection** — by design it has no HTTP awareness. `MAX_REQUEST_SIZE` (10 MiB) and `MAX_HEADER_SIZE` (16 KiB) constants exist in `constants.rs` but are **dead constants** — I traced the handler and they are never enforced on the L4 path. That's a real finding: misleading dead config.

### What Cloudflare actually owns (it IS in-repo, via Terraform)
`infrastructure/cloudflare/main.tf` manages zone TLS (`ssl=strict`, min TLS, TLS1.3, AOP, always-HTTPS) and **Cloudflare Tunnel** DNS (`proxied=true`, origin reached only via `cfargotunnel.com`). 

**This materially changes my earlier "trust the edge" warning.** Because ingress is via Cloudflare Tunnel with **Authenticated Origin Pulls**, the origin is **not directly reachable on the public internet** — there's no public origin IP to bypass to. So the "direct-to-origin bypass" risk I raised is **largely mitigated by the tunnel architecture**, *provided* AOP is enabled in prod and no public LoadBalancer exposes the origin. That's a much stronger posture than I credited.

🔴 **But the gap is real: the Cloudflare Terraform contains NO WAF rules, NO rate-limiting rules, NO bot-management config.** It manages TLS + DNS only. So the per-route HTTP rate limiting / bot protection is **assumed to be configured manually in the Cloudflare dashboard, outside Terraform** — which means it is **unversioned, unreviewed, and undeployed-by-code**. For a money platform, security controls that exist only as click-ops in a vendor dashboard are an audit failure: they can be changed or lost with no trace.

### The direct answer to your question: Cloudflare-only, or handle some internally?
**Industry best practice for a money platform is defense-in-depth: do BOTH, at the layers each is good at.** Never rely on a single edge you don't control end-to-end. Specifically:

1. **Keep at the edge (Cloudflare):** volumetric DDoS, bot management, IP reputation, broad WAF, and a *coarse* per-IP HTTP rate limit. This is what CDNs do best and what your origin should never have to absorb. **But codify it in Terraform** (`cloudflare_ruleset` for WAF + `cloudflare_rate_limit`/ruleset rate rules + bot management), so it's reviewed and versioned like everything else. Today it's not.

2. **Keep at L4 (edge-ingress):** connection caps — already done well.

3. **Add internally (Envoy + app), as the authoritative backstop:** This is the non-negotiable part for enterprise grade. The origin must enforce its own limits regardless of what's in front of it, because (a) internal east-west traffic and any future non-Cloudflare path bypass the CDN, and (b) per-*user* (authenticated) limits can only be done where the JWT is understood. Concretely:
   - **Envoy:** add `envoy.filters.http.local_ratelimit` (coarse per-connection L7 rate limit) and `max_request_bytes` on the HTTP connection manager. You earlier confirmed both are absent. This is the single most valuable in-repo hardening: a cheap, always-on L7 backstop that does not depend on Cloudflare being in the path.
   - **App:** you already have the best layer for *per-user* limits — extend the gateway's token-bucket pattern (currently only on `/cycle/run`) to a default limiter on the other `/api/v1/*` mutating routes.

**Rule of thumb (industry standard):** the edge handles *anonymous/volumetric* abuse; the origin handles *authenticated/business-logic* abuse and acts as the backstop. Each layer assumes the others might fail. Cloudflare-only fails the "assume the edge is bypassed" test that money-handling threat models require.

### TIER 4 "Abuse Prevention" — corrected verdict
- Connection-level (edge-ingress): ✅ done well.
- Per-user app rate limiting on the money path (`/cycle/run`): ✅ done well.
- Auth brute-force (attempt_limiter): ✅ present.
- 🔴 **Gap A2 (confirmed real):** No L7 rate-limit or `max_request_bytes` in Envoy; no WAF/rate/bot rules in Cloudflare Terraform (click-ops only); `MAX_REQUEST_SIZE`/`MAX_HEADER_SIZE` are dead constants in edge-ingress.
- ⚠️ **Abuse monitoring:** metrics exist (`record_connection_*`, gateway counters) but I found **no alerting rules** wiring them to on-call.

### Honest scope note
I have **not** yet read the Envoy configmap *this session* (I'm relying on my earlier finding that `local_ratelimit`/`max_request_bytes` are absent), nor `geo-router/router.rs`, `tls/acceptor.rs`, or the production edge config YAML line-by-line. Before I write any Envoy/Terraform changes I will read the actual Envoy configmap on `main` to confirm exactly what's there.

### Recommendation
Want me to **(1)** read the Envoy configmap + production edge config to confirm the exact current state, then **(2)** implement the defense-in-depth backstop: Envoy `local_ratelimit` + `max_request_bytes`, codify Cloudflare WAF/rate/bot rules in Terraform, wire `MAX_REQUEST_SIZE`/`MAX_HEADER_SIZE` into the edge handler (or delete them as dead), and add a default per-user limiter to the remaining `/api/v1/*` routes? I'll show findings and a concrete plan before committing anything.