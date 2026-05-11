# Billing Service Operator Runbook

This document is the operator-facing companion to `src/billing/` and
the gateway-side billing handler. Read it end-to-end before deploying
the service to production. Anything that can ruin a paid SaaS
company lives in this directory; treat the runbook as production-
critical infrastructure.

## 1. Configuration invariants

The service refuses to boot unless every required value is present and
valid. The validation happens at startup in `src/billing/config/config.go::Load`.

### 1.1 `BILLING_PUBLIC_BASE_URL`

This is the **operator-visible** HTTPS origin where Paddle and Lemon
Squeezy POST webhooks. It MUST exactly match the URL you register in
each provider's dashboard:

| Provider       | Where it's registered                                   |
| -------------- | ------------------------------------------------------- |
| Paddle         | Dashboard → Developer Tools → Notifications              |
| Lemon Squeezy  | Dashboard → Settings → Webhooks                          |

A mismatch between `BILLING_PUBLIC_BASE_URL` and the dashboard value
is the most common cause of "webhooks not arriving" incidents. The
booting service logs the resolved value with the `billing_starting`
event; cross-check it against the provider dashboards on every
deploy.

### 1.2 Shared secrets

| Variable                          | Minimum length | Notes                                                  |
| --------------------------------- | -------------- | ------------------------------------------------------ |
| `BILLING_INTERNAL_SHARED_SECRET`  | 32 chars       | Constant-time compared against the `X-Internal-Auth` header on `/internal/*`. |
| `PADDLE_WEBHOOK_SECRET`           | non-empty      | HMAC-SHA256 key for `Paddle-Signature` verification. |
| `LEMONSQUEEZY_WEBHOOK_SECRET`     | non-empty      | HMAC-SHA256 key for `X-Signature` verification. |
| `PADDLE_API_KEY`                  | non-empty      | Bearer for `/transactions` and `/customers/.../portal-sessions`. |
| `LEMONSQUEEZY_API_KEY`            | non-empty      | Bearer for `/v1/checkouts` and `/v1/customers/{id}`. |

The service never persists these. The gateway must hold the **same**
`BILLING_INTERNAL_SHARED_SECRET` (via `GATEWAY_BILLING_INTERNAL_SHARED_SECRET`)
or every `/internal/*` call returns 401.

### 1.3 Product IDs

Every tier needs a Paddle `price_id` and a Lemon Squeezy `variant_id`:

| Variable                              | Maps to                       |
| ------------------------------------- | ----------------------------- |
| `PADDLE_PRICE_PRO_BYOK`               | tier `pro_byok` on Paddle     |
| `PADDLE_PRICE_PRO_MANAGED`            | tier `pro_managed` on Paddle  |
| `LEMONSQUEEZY_VARIANT_PRO_BYOK`       | tier `pro_byok` on LS         |
| `LEMONSQUEEZY_VARIANT_PRO_MANAGED`    | tier `pro_managed` on LS      |

If a webhook arrives for an unmapped `price_id` / `variant_id` the
parser returns 422 (permanent rejection). Provider stops retrying;
operator must add the mapping and replay manually.

## 2. Custom data (user_id) is mandatory on checkout

The checkout flow is the SAAS-critical correlation point between a
provider customer record and a platform user. The gateway populates
`custom_data.user_id` on every `POST /internal/checkout`, which
billingservice forwards to:

- Paddle: `custom_data.user_id` on the `POST /transactions` payload.
- Lemon Squeezy: `checkout_data.custom.user_id` on `POST /v1/checkouts`.

Both providers preserve this through every subsequent subscription
lifecycle event. **The platform's invariant** is that
`subscription.created` (Paddle) and `subscription_created` (LS) MUST
carry the `user_id` in custom data. If you create a subscription
through provider tooling (manual test, support migration, retroactive
upgrade) you MUST attach `user_id` matching the platform `auth_users.id`
before the first webhook is delivered.

What happens if the rule is violated:

- **`subscription.created` with no user_id** → parser returns 422
  (`paddle: missing custom_data.user_id`). Provider stops retrying.
  The customer's payment succeeded but the platform never recorded
  it. **This is the only billing failure that requires manual
  intervention; everything else self-heals.**
- Subsequent events (`subscription.updated`, `subscription.canceled`,
  etc.) can recover via provider-subscription-id lookup against an
  existing `billing_subscriptions` row — see `service/recovery.go`.

### Recovery procedure for an unresolvable create

1. Pull the failing notification body from the provider's dashboard.
2. Identify the platform `user_id` (cross-reference customer email).
3. Manually upsert the `billing_subscriptions` row with the correct
   `(user_id, payment_provider, provider_customer_id, provider_subscription_id,
   tier, status, current_period_end)` values. Use the same
   `event_timestamp` as the provider's `occurred_at` so the next
   webhook is not race-discarded.
4. The next `subscription.updated` event from the provider will be
   absorbed correctly via the provider-subscription-id lookup path.

## 3. Alert events: state-change vs. UX-upsell

The service emits two semantically distinct families of
`alert.Event` types. Confusing them in dashboards or paging rules
has caused alert-fatigue incidents in the past.

| Event                          | Trigger                                                                                  | Severity |
| ------------------------------ | ---------------------------------------------------------------------------------------- | -------- |
| `SUBSCRIPTION_UPGRADED`        | Webhook committed; tier rank increased.                                                  | Info     |
| `SUBSCRIPTION_DOWNGRADED`      | Webhook committed; tier rank decreased (incl. reaper-driven demotion to free).           | Info     |
| `SUBSCRIPTION_STATUS_CHANGED`  | Webhook committed; tier unchanged but status moved (active ↔ past_due, etc.).            | Info     |
| `SUBSCRIPTION_REQUIRED`        | **NOT a state change.** Gateway refused a tier-gated action (e.g. Free user attempted automated execution). | Info     |

The first three are emitted by the billing service post-commit; the
fourth is emitted by the gateway routing layer. Page on the first
three, NOT on `SUBSCRIPTION_REQUIRED`.

## 4. Reconciler & janitor

`service.Reconciler` runs every `BILLING_RECONCILER_INTERVAL_SECONDS`
(default 900s). Each tick:

1. **Sweep**: demote subscriptions in `paused`/`past_due`/`canceled`/
   `refunded` whose `current_period_end < NOW()` to `(tier=free, status=canceled)`.
   Per-user transaction with race-safe `event_timestamp` gate, then
   audit row + post-commit session revoke.
2. **Prune**: delete `processed_webhook_events` rows older than
   `BILLING_IDEMPOTENCY_RETENTION_DAYS` (default 30) AND expired
   `billing_checkout_intents` rows (TTL 5 min).

Good metrics to alert on:

- `billing_reconciler_runs_total{outcome=~"sweep_error|prune_error|sweep_and_prune_error"}` — if rate > 0 over 15 min, page.
- `billing_reconciler_duration_seconds` p99 > 30s — investigate DB pressure.
- `billing_webhook_received_total{result="unresolvable"}` > 0 — manual recovery (§2.1) required.

## 5. Customer portal

The gateway exposes `POST /api/v1/billing/portal` (auth-bound,
CSRF-protected). The handler:

1. Looks up the authenticated user's `billing_subscriptions` row.
2. Returns 404 if there is no `provider_customer_id` on file (the
   user must complete a checkout first).
3. Forwards `(provider, provider_customer_id)` to billing's
   `/internal/portal`.
4. Billing calls the provider:
   - Paddle: `POST /customers/{id}/portal-sessions` → `data.urls.general`.
   - Lemon Squeezy: `GET /v1/customers/{id}` → `attributes.urls.customer_portal`.
5. Returns 501 with `ErrPortalNotSupported` when the provider has no
   portal URL for the customer (most often a freshly-created LS
   customer who has not yet completed checkout). The SPA surfaces a
   'portal unavailable' toast.

**Portal URLs are one-shot and short-lived.** The service does NOT
cache them. Every click on 'Manage Subscription' creates a fresh
session.

## 6. Resilience primitives

### 6.1 Circuit breaker

Every outbound call to Paddle or Lemon Squeezy passes through a
per-provider circuit breaker (`src/billing/service/breaker.go`).
Defaults:

| Setting               | Default | Tuning notes                                             |
| --------------------- | ------- | -------------------------------------------------------- |
| `FailureThreshold`    | 5       | Consecutive 5xx / transport errors that trip the breaker.|
| `OpenCooldown`        | 30s     | Time spent in Open before allowing a half-open probe.    |
| `HalfOpenProbeTimeout`| 30s     | Defensive: a stuck probe past this re-opens automatically. |

4xx responses are **never** counted as failure: a malformed user input
must not impact other users.

Metrics:
  - `billing_breaker_transitions_total{name, from, to}` — alert on
    `rate(...{to="open"}[5m]) > 0`.
  - `billing_breaker_state{name}` — 0=closed, 1=half_open, 2=open.

### 6.2 Per-endpoint semaphores

Three counting semaphores cap goroutine fanout under load:

| Endpoint              | Default cap | Override (Options field)   |
| --------------------- | ----------- | -------------------------- |
| /internal/checkout    | 64          | CheckoutInFlightCap        |
| /internal/portal      | 64          | PortalInFlightCap          |
| /webhooks/* (combined)| 256         | WebhookInFlightCap         |

Saturation returns 503 + `Retry-After: 1`. Tune up if your provider
latency is high (each in-flight slot is one goroutine + one open HTTP
connection). The hardened http.Transport limits per-host TCP
connections to 32 idle / 32 max, so the checkout semaphore cap of 64
is a deliberate 2x to allow some queueing in front of the transport.

Metrics:
  - `billing_semaphore_in_flight{name}` vs. `billing_semaphore_capacity{name}`.
  - `billing_semaphore_rejected_total{name}` — alert on rate > 0.

### 6.3 Per-IP webhook rate limit

Both webhook endpoints are rate-limited per source IP via a bounded
LRU token bucket (`src/billing/service/ratelimit.go`). Defaults:

| Setting     | Default | Notes                                                |
| ----------- | ------- | ---------------------------------------------------- |
| `MaxKeys`   | 4096    | LRU cap; evicts oldest when full.                    |
| `RatePerSec`| 50      | Refill rate per source IP.                           |
| `Burst`     | 100     | Maximum tokens; bursts up to this without throttling. |

**Source IP resolution**: by default the limiter uses `r.RemoteAddr`
only. If the billing service runs behind a known reverse proxy
(Cloudflare, an ALB, nginx) set `Options.WebhookProxy.TrustHeader` to
the header name (e.g. `X-Forwarded-For`) and
`Options.WebhookProxy.TrustedCIDRs` to the proxy's IP ranges. The
handler walks the header right-to-left and returns the first IP that
is NOT in any trusted CIDR. **Never set TrustHeader without TrustedCIDRs**
— doing so makes the limit trivially bypassable by spoofed headers.

Metrics:
  - `billing_webhook_rate_limited_total{reason}` — reason is
    `rate_limit` or `saturated`.
  - `billing_webhook_rate_tracked_keys` — LRU saturation gauge.

### 6.4 Per-user gateway rate limit

The gateway's `/api/v1/billing/checkout` and `/api/v1/billing/portal`
are additionally rate-limited per **user_id** (resolved from the JWT,
un-spoofable). Default budget: 10 requests/minute, burst 20 per user.
Saturation returns 429 + `Retry-After: 60`. The SPA's
`useBillingPortal` and `UpgradeModal` hooks already handle 429.

## 7. Portal access audit trail

Every `/api/v1/billing/portal` call is recorded in
`billing_portal_access_events` regardless of outcome. This is the
compliance trail SOC 2 CC6.1 / PCI-DSS 10.2.5 expect. Schema:

```
id           BIGSERIAL PRIMARY KEY,
user_id      TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
provider     TEXT,
client_ip    TEXT,
user_agent   TEXT,
status       TEXT NOT NULL,    -- success | not_found | not_supported | rate_limited | upstream_rejected | upstream_error | error
error        TEXT,
created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

The table is append-only by convention; the codebase has no UPDATE
or DELETE path. **No janitor**: deletion is a deliberate compliance
decision driven by the operator's retention policy (typical: 12-24
months). Set up a separate retention job if your policy requires it.

Useful queries:

```sql
-- All portal accesses for one user, newest first
SELECT * FROM billing_portal_access_events
WHERE user_id = $1 ORDER BY created_at DESC LIMIT 100;

-- Failure rate over the last hour, by status
SELECT status, COUNT(*) FROM billing_portal_access_events
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY status ORDER BY 2 DESC;
```

## 8. Provider retry policy

The service's provider-call helper `attemptWithBackoff` retries up to
3 times on 5xx and transport errors with jittered exponential
backoff (200ms, 500ms ± 50ms). 4xx is permanent and short-circuits.
The total wall-clock is bounded by the caller's context (gateway:
20s for checkout, 20s for portal).

Provider retries on **incoming** webhooks are handled by Paddle and
Lemon Squeezy themselves; the service guarantees idempotency via
`processed_webhook_events.(provider, event_id)` so duplicate
deliveries are no-ops.

## 7. Cross-service alert delivery

Webhook commit → Redis `etradie:alerts` channel PUBLISH → gateway
`alertredis.Transport.subscribeLoop` → in-process `alert.Hub` →
user-scoped WebSocket frame on `/ws/notifications`. The SPA's
`eventMap.ts` invalidates `['billing']` and `['auth', 'me']` on
`SUBSCRIPTION_*` so the dashboard reflects the new tier within ~1s.

If operators see a 'tier changed in DB but dashboard still shows old
tier' incident, the chain to debug is:

1. Did the webhook commit? → `billing_subscription_apply_total{outcome="applied"}`.
2. Did Redis receive the publish? → `alert_redis_published_total`.
3. Did the gateway receive it? → `alert_redis_received_total`.
4. Did the SPA stay connected? → the SPA `RealtimeProvider` logs
   reconnection events; absence of `latestEvent` updates points to a
   WebSocket disconnect.
