# Billing & Subscription Operator Runbook

This document is the canonical operator reference for the eTradie billing
subsystem (Paddle + Lemon Squeezy). Everything below is verified against the
code on `main` at the time of writing. If you change behaviour, update this
file in the same merge request.

---

## 1. What the billing service does

The billing service is a standalone Go microservice (`src/billing`) that owns
every interaction with our payment providers. It is the only process that:

- Holds the Paddle and Lemon Squeezy **API keys** and **webhook secrets**.
- Accepts provider **webhooks** and verifies their HMAC signatures.
- Writes to **`billing_subscriptions`** (the canonical tier/status table).
- Writes the **`billing_subscription_events`** audit trail.
- Records processed events in **`processed_webhook_events`** for idempotency.
- Calls **`auth.SessionStore.RevokeAllUserSessions`** so JWTs cannot stay
  stale across a tier change.
- Runs the **period-end reconciler** that demotes
  `paused`/`past_due`/`canceled`/`refunded` subscriptions once
  `current_period_end` has elapsed, and prunes the idempotency table.

Nothing in the gateway or any user-facing service talks to Paddle or Lemon
Squeezy directly. The gateway only calls the billing service's internal
endpoint over a shared secret.

---

## 2. End-to-end request flow

```
  ┌──────────┐   1. POST /api/billing/checkout (user JWT)
  │ Frontend │ ─────────────────────────────────────────────────────────┐
  └──────────┘                                                          │
                                                                        ▼
                                              ┌────────────────────────────────┐
                                              │  Gateway (src/gateway)         │
                                              │  - authenticates user JWT      │
                                              │  - resolves tier from claims   │
                                              └─────────────┬──────────────────┘
                                                            │  2. POST /internal/checkout
                                                            │     X-Internal-Auth: <secret>
                                                            ▼
                                              ┌────────────────────────────────┐
                                              │  Billing service               │
                                              │  /internal/checkout            │
                                              │  - constant-time secret cmp    │
                                              │  - validates provider + tier   │
                                              │  - calls provider create-      │
                                              │    transaction / create-       │
                                              │    checkout REST API           │
                                              └─────────────┬──────────────────┘
                                                            │  3. checkout_url
                                                            ▼
                                                       redirect user
                                                            │
                                                            ▼
                                                  user completes payment
                                                            │
                                                            ▼
                                              ┌────────────────────────────────┐
                                              │  Provider (Paddle / LS)        │
                                              └─────────────┬──────────────────┘
                                                            │  4. POST webhook
                                                            ▼
                                              ┌────────────────────────────────┐
                                              │  Billing service               │
                                              │  /webhooks/paddle              │
                                              │  /webhooks/lemonsqueezy        │
                                              │  - max-body read               │
                                              │  - HMAC verify                 │
                                              │  - parse → NormalizedEvent     │
                                              │  - idempotency insert (tx)     │
                                              │  - subscription upsert (tx)    │
                                              │  - audit append (tx)           │
                                              │  - commit                      │
                                              │  - post-commit: revoke sessions│
                                              └────────────────────────────────┘
```

The upsert in step 4 is race-safe against out-of-order provider deliveries:
the SQL is `WHERE billing_subscriptions.event_timestamp <= EXCLUDED.event_timestamp`
so a stale duplicate retried by the provider after a newer event has already
landed is silently dropped without regressing the row.

---

## 3. HTTP surface

All routes are served by `src/billing/server/http.go` on `BILLING_HTTP_PORT`
(default `8082`). Webhook handlers are mounted **outside any auth middleware**
because providers cannot present JWTs.

### 3.1 Public endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/webhooks/paddle` | Paddle Billing v1 webhook intake |
| `POST` | `/webhooks/lemonsqueezy` | Lemon Squeezy webhook intake |
| `GET`  | `/health` | Liveness (always 200 once the process is up) |
| `GET`  | `/readiness` | Readiness — does a 2 s `pool.Ping` and returns 503 if the DB is unreachable |
| `GET`  | `/metrics` | Prometheus exposition on a private registry |

Response-code contract for the two webhook endpoints (matches
`applyAndRespond` in `src/billing/server/http.go`):

| Condition | HTTP | Provider behaviour |
|---|---|---|
| Body exceeds `BILLING_WEBHOOK_MAX_BODY_BYTES` | `413` | Permanent — stops retrying |
| Signature missing / malformed / mismatched | `401` with empty body | Permanent — stops retrying |
| Body parses but is for an unsupported event / unknown price / unknown variant / missing user id | `422` with generic message | Permanent — stops retrying |
| Event references a user that cannot be resolved | `422` | Permanent — stops retrying |
| Duplicate (same `provider, event_id` already processed) | `200` with `already_processed: true` | Stops retrying |
| Out-of-order (older `event_timestamp` than stored) | `200` with `out_of_order: true` | Stops retrying |
| Applied successfully | `200` with `applied: true` and `tier_changed` / `status_changed` flags | Stops retrying |
| Internal / DB error during apply | `500` with generic message | Provider retries |

The Go error chain is never echoed to the provider. Parse errors are logged at
Warn with the full error and event label; the response body only carries a
fixed generic string.

### 3.2 Internal endpoint

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/internal/checkout` | `X-Internal-Auth: <BILLING_INTERNAL_SHARED_SECRET>` | Create a provider checkout URL |

Request body (validated via `DisallowUnknownFields`, max 16 KiB):

```json
{
  "provider":   "paddle" | "lemonsqueezy",
  "tier":       "pro_byok" | "pro_managed",
  "user_id":    "<platform user id>",
  "user_email": "<optional, forwarded to provider>"
}
```

Response:

```json
{ "checkout_url": "https://..." }
```

Response-code contract:

| Condition | HTTP |
|---|---|
| Missing or wrong `X-Internal-Auth` | `401` empty body |
| Invalid JSON / unknown field | `400` |
| Invalid provider / invalid tier / tier has no provider product configured | `400` |
| Provider API rejected / returned empty `checkout_url` | `502` |
| Provider call exceeded `HTTPTimeout` (10 s) or DNS / TCP / TLS error | `502` |
| Success | `200` with `checkout_url` |

The shared secret comparison uses `crypto/subtle.ConstantTimeCompare`. The
gateway must always include the header; an empty-string header is also
rejected by length check before the constant-time compare.

---

## 4. Environment variables

Validated at startup by `src/billing/config/config.go`. A misconfigured
deployment fails fast — the process exits with a non-zero status before the
listener binds.

### 4.1 Core

| Variable | Default | Required | Notes |
|---|---|---|---|
| `BILLING_HTTP_PORT` | `8082` | no | Validated `1..65535` |
| `BILLING_LOG_LEVEL` | `INFO` | no | Parsed by zerolog; unknown values fall back to `INFO` |
| `BILLING_LOG_JSON` | `true` | no | `false` switches to console writer |
| `BILLING_DATABASE_URL` | — | required if `POSTGRES_*` not set | Falls back to a URL built from `POSTGRES_HOST`/`PORT`/`USER`/`PASSWORD`/`DB`/`SSLMODE` |
| `BILLING_PUBLIC_BASE_URL` | — | **yes** | Must parse as `http(s)://host[...]`. Logged on startup so operators can verify it matches the URL registered in the Paddle and Lemon Squeezy dashboards. A mismatch between this and the dashboard is the most common cause of "webhooks not arriving". |
| `BILLING_WEBHOOK_REPLAY_WINDOW_SECONDS` | `300s` | no | Validated positive. Applies to Paddle only (Lemon Squeezy does not sign a timestamp). |
| `BILLING_WEBHOOK_MAX_BODY_BYTES` | `1048576` (1 MiB) | no | Validated positive. Enforced by `http.MaxBytesReader` *before* HMAC work. |
| `BILLING_RECONCILER_INTERVAL_SECONDS` | `900s` (15 min) | no | Validated positive — a non-positive value refuses to boot, so the reaper can never be silently disabled. |
| `BILLING_IDEMPOTENCY_RETENTION_DAYS` | `30` | no | Validated positive |
| `BILLING_INTERNAL_SHARED_SECRET` | — | **yes** | Minimum 32 characters. Compared constant-time against the `X-Internal-Auth` header on `/internal/checkout`. Generate with `openssl rand -hex 32`. The gateway has its own matching minimum-length check on the value it sends. |
| `BILLING_CHECKOUT_SUCCESS_URL` | — | **yes** | Forwarded to provider as the post-payment return URL |
| `BILLING_CHECKOUT_CANCEL_URL` | — | **yes** | Forwarded to provider as the cancel return URL |
| `BILLING_SERVICE_URL` | `http://billing:8082` | no (gateway-side) | The gateway reads this to know where to send `/internal/checkout`. It lives in `.env.example` next to the billing block for co-location. |

### 4.2 Paddle

| Variable | Default | Required |
|---|---|---|
| `PADDLE_WEBHOOK_SECRET` | — | **yes** |
| `PADDLE_API_KEY` | — | **yes** |
| `PADDLE_API_BASE_URL` | `https://api.paddle.com` | no |
| `PADDLE_PRICE_PRO_BYOK` | — | **yes** |
| `PADDLE_PRICE_PRO_MANAGED` | — | **yes** |

### 4.3 Lemon Squeezy

| Variable | Default | Required |
|---|---|---|
| `LEMONSQUEEZY_WEBHOOK_SECRET` | — | **yes** |
| `LEMONSQUEEZY_API_KEY` | — | **yes** |
| `LEMONSQUEEZY_API_BASE_URL` | `https://api.lemonsqueezy.com` | no |
| `LEMONSQUEEZY_STORE_ID` | — | **yes** |
| `LEMONSQUEEZY_VARIANT_PRO_BYOK` | — | **yes** |
| `LEMONSQUEEZY_VARIANT_PRO_MANAGED` | — | **yes** |

---

## 5. Tier and status reference

Defined in `src/billing/events/normalized.go`. These are the only legal
values anywhere in the codebase; any value outside this set is a bug.

### 5.1 Tiers (`events.Tier`)

| Constant | String | Notes |
|---|---|---|
| `TierFree` | `free` | The default for any user without a `billing_subscriptions` row, and the demoted state |
| `TierProBYOK` | `pro_byok` | "Bring your own LLM key" Pro |
| `TierProManaged` | `pro_managed` | Platform-managed LLM Pro |

### 5.2 Statuses (`events.Status`)

| Constant | String | Meaning |
|---|---|---|
| `StatusActive` | `active` | Paid and current |
| `StatusPastDue` | `past_due` | Last payment failed; in grace until `current_period_end` |
| `StatusPaused` | `paused` | Customer paused; tier preserved until `current_period_end` |
| `StatusCanceled` | `canceled` | Cancelled by customer or provider; tier preserved until `current_period_end` |
| `StatusRefunded` | `refunded` | A payment was refunded; tier preserved until `current_period_end` (see §6.3) |
| `StatusUnpaid` | `unpaid` | Lemon Squeezy terminal-unpaid state |
| `StatusExpired` | `expired` | Lemon Squeezy terminal-expired state |

At the application layer the **tier** is what gates features. The **status**
is informational for the UI and is the input the reconciler keys on to decide
whether a subscription is eligible for period-end demotion.

---

## 6. Webhook contracts

### 6.1 Paddle

Verifier: `src/billing/paddle/webhook.go`.

- **Provider name** (used in the idempotency table): `paddle`.
- **Signature header**: `Paddle-Signature` — format `ts=<unix>;h1=<hex-hmac>` (unknown sub-fields are tolerated for forward compatibility).
- **Notification id header** (preferred event id source): `Paddle-Notification-Id`. The body's `notification_id` / `event_id` are used as fallbacks.
- **HMAC**: `HMAC-SHA256(secret, "<ts>:<raw_body>")`. Both digests are hex-decoded; `hmac.Equal` compares fixed-length byte slices.
- **Replay window**: `|now - ts| > BILLING_WEBHOOK_REPLAY_WINDOW_SECONDS` is rejected. The check is symmetric — future-skewed timestamps are rejected the same way past-skewed ones are.
- **Body**: read once under `http.MaxBytesReader(BILLING_WEBHOOK_MAX_BODY_BYTES)` before any HMAC work. The verifier receives the exact bytes from the wire; no JSON re-marshal happens.

Handled `event_type` values (parser: `src/billing/paddle/parser.go`):

| Paddle `event_type` | Mapped status | Tier source |
|---|---|---|
| `subscription.created` | `active` | Active price item → `PriceTierMap` |
| `subscription.activated` | `active` | Active price item → `PriceTierMap` |
| `subscription.updated` | derived from `subscription.status` | Active price item → `PriceTierMap` |
| `subscription.paused` | `paused` | Active price item if resolvable; otherwise empty and the service inherits the stored tier |
| `subscription.past_due` | `past_due` | Same fallback policy as `paused` |
| `subscription.resumed` | `active` | Active price item → `PriceTierMap` |
| `subscription.canceled` | `canceled` | **Forced to `free`** — a fully-cancelled subscription is the only Paddle event that immediately demotes the user |

Any other `event_type` returns `422`.

`custom_data.user_id` is required for all events **except** `updated`, `canceled`, `paused`, `resumed`, and `past_due`, for which the service layer can recover the user via `(provider, provider_subscription_id)` lookup.

### 6.2 Lemon Squeezy

Verifier: `src/billing/lemonsqueezy/webhook.go`.

- **Provider name** (idempotency table): `lemonsqueezy`.
- **Signature header**: `X-Signature` — hex-encoded HMAC-SHA256 of the **raw body** with the dashboard signing secret. No timestamp is signed; replay defense is delegated to the idempotency table.
- **Event name header**: `X-Event-Name`. Used both for routing and as a metrics label.
- **Event id**: read from `meta.event_id` in the JSON body. A missing `event_id` returns `422` (the parser refuses to insert an unkeyed row into `processed_webhook_events`).
- **Body**: same `MaxBytesReader` policy as Paddle.

Handled `event_name` values (parser: `src/billing/lemonsqueezy/parser.go`):

| LS `event_name` | Mapped status | Tier source |
|---|---|---|
| `subscription_created` | `active` | Variant id → `VariantTierMap` |
| `subscription_updated` | derived from `attributes.status` | Variant id → `VariantTierMap` |
| `subscription_resumed` | `active` | Variant id → `VariantTierMap` |
| `subscription_unpaused` | `active` | Variant id → `VariantTierMap` |
| `subscription_payment_success` | `active` | Variant id → `VariantTierMap` |
| `subscription_paused` | `paused` | Variant id if resolvable; otherwise inherit stored tier |
| `subscription_payment_failed` | `past_due` | Same fallback as `paused` |
| `subscription_payment_refunded` | `refunded` | **Tier is preserved** (see §6.3) |
| `subscription_cancelled` | `canceled` | **Forced to `free`** |
| `subscription_expired` | `canceled` | **Forced to `free`** |

Any other `event_name` returns `422`.

`user_id` is read from `meta.custom_data.user_id` first, then
`data.attributes.custom_data.user_id`. Recovery via
`(provider, provider_subscription_id)` is permitted for the same set of
update/cancel/pause/refund event names listed in `canRecoverByProviderID`.

### 6.3 Refund policy (verified — addresses audit item B3)

`subscription_payment_refunded` does **not** instantly demote the user to
`free`. The status flips to `refunded` but the tier stays at whatever the
variant resolves to (or, if the variant is no longer in the configured map,
the stored tier is inherited via the recovery path). The user is only
demoted when one of these happens:

1. A later `subscription_cancelled` / `subscription_expired` event arrives → the parser maps to `tier=free, status=canceled` and the service applies it immediately, revoking sessions.
2. The reconciler tick (§7) sees `status='refunded'` AND `current_period_end < NOW()` and demotes the user inside its own transaction, with audit row and post-commit session revoke.

This is a deliberate product choice: a single refund of one invoice (e.g. a
disputed renewal) does not cut off the user mid-period. The reconciler
guarantees we still demote them once the paid-for window actually ends, so
there is no "paused forever" loophole.

---

## 7. Reconciler — period-end demotion + idempotency janitor

Implementation: `src/billing/service/reconciler.go`. Wired in
`src/billing/cmd/server/main.go` as a goroutine started **after** the
HTTP listener has been bound, with a cancellable context tied to SIGTERM.

One tick runs:

1. **Sweep.** `SubscriptionStore.ListExpiredForDemotion(now, 200)` is called in a loop. Each returned row is demoted in **its own transaction** (`ReadCommitted`):
   - `DemoteToFreeTx` runs the atomic SQL update guarded by `event_timestamp <= now` so a newer event landing concurrently wins the race.
   - If `applied=true`, the audit row is appended in the same transaction with a synthesised event id `reconciler:<user_id>:<period_end.Unix()>` so a re-run cannot duplicate.
   - On commit, sessions are revoked with a 5 s detached context. A revoke failure is logged but does **not** roll back the demotion (revocation is best-effort; the next JWT refresh still sees `free` via the `billing_subscriptions` join in `auth_users`).
2. **Prune.** `processed_webhook_events` rows with `received_at < now - BILLING_IDEMPOTENCY_RETENTION_DAYS` are deleted. The provider retry window is ≤72 h in practice, so 30 days of retention is generous.

Both stages are independent — an error in one does not abort the other. The
tick logs `demoted`, `idempotency_pruned`, `duration`, and `outcome`
(`ok` / `sweep_error` / `prune_error` / `sweep_and_prune_error`).

Graceful shutdown: SIGTERM cancels the reconciler context. `main.go` waits
up to 10 s for the in-flight tick to drain, then calls
`srv.Shutdown(30s)`. The DB pool is closed last via `defer pool.Close()`.

### 7.1 Reconciler metrics

Exposed under `/metrics`:

- `billing_reconciler_run_seconds{outcome}` (histogram)
- `billing_reconciler_demoted_total{previous_tier}` (counter)
- `billing_reconciler_errors_total{stage}` (counter; stage ∈ `list`, `begin_tx`, `demote`, `audit`, `commit`, `prune`)
- `billing_idempotency_pruned_total` (counter)

### 7.2 Manual reconciliation

If a webhook was missed (e.g. a provider outage exceeded their retry window),
you can replay the period-end check immediately by restarting the billing
process — `Reconciler.Run` does one full sweep on startup before the ticker
begins. If you cannot restart, the equivalent SQL is:

```sql
-- Inspect candidates (read-only)
SELECT user_id, tier, status, current_period_end, payment_provider, provider_subscription_id
FROM   billing_subscriptions
WHERE  status IN ('paused', 'past_due', 'canceled', 'refunded')
  AND  current_period_end IS NOT NULL
  AND  current_period_end < NOW()
ORDER  BY current_period_end
LIMIT  200;

-- Force-demote a single user (DO NOT run in bulk — use the reconciler).
-- This is a recovery tool. The reconciler will append the audit row itself
-- on its next tick because the synthesised event id is deterministic per
-- (user_id, current_period_end). After running this manually, restart the
-- billing service to also revoke that user's sessions, or call the auth
-- revoke endpoint directly.
UPDATE billing_subscriptions
SET    tier            = 'free',
       status          = 'canceled',
       updated_at      = NOW(),
       event_timestamp = NOW()
WHERE  user_id = $1
  AND  event_timestamp <= NOW();
```

---

## 8. Schema reference

DDL: `src/billing/store/schema.go`. Idempotent — re-applied on every start.

### `billing_subscriptions`

One row per user. Canonical source of `tier` / `status`.

Key columns:

- `user_id` (PK, FK → `auth_users.id`, ON DELETE CASCADE)
- `tier`, `status` — text, default `free` / `active`
- `payment_provider` — `paddle` or `lemonsqueezy`
- `provider_customer_id`, `provider_subscription_id`
- `current_period_end`
- `event_timestamp` — the **race-safety key**: an upsert is only applied when the incoming event's timestamp is `>=` the stored one.
- `created_at`, `updated_at`

Indexes on `tier`, `status`, `(payment_provider, provider_customer_id)`,
`(payment_provider, provider_subscription_id)`.

### `processed_webhook_events`

Idempotency table. Composite PK `(provider, event_id)`. Inserted inside the
same transaction as the subscription upsert with `ON CONFLICT DO NOTHING`.

Index on `received_at` powers the reconciler's retention janitor.

### `billing_subscription_events`

Append-only audit log. Every applied transition writes one row:
`provider`, `event_name`, `event_id`, `previous_tier`, `new_tier`,
`previous_status`, `new_status`, `event_timestamp`. Reconciler-driven
demotions are written with `provider='reconciler'` and
`event_name='reconciler.period_end_expired'`.

### `billing_usage`

Per-user runtime counters (analyses, LLM tokens, execution attempts, active
watchers, TA / macro cycles). Decrements on `watcher_count` are clamped at
zero in SQL (`GREATEST(0, watcher_count + delta)`) so a stray decrement
before the matching increment cannot drift the counter negative.

---

## 9. Provider dashboard setup

### 9.1 Paddle (Billing v1)

1. **API key**: dashboard → Developer Tools → Authentication → create a new key. Set as `PADDLE_API_KEY`.
2. **Prices**: dashboard → Catalog → Products → your Pro product. Create two prices (one per tier). Record their `pri_…` ids as `PADDLE_PRICE_PRO_BYOK` and `PADDLE_PRICE_PRO_MANAGED`.
3. **Webhook destination**: dashboard → Notifications → New destination.
   - URL: `${BILLING_PUBLIC_BASE_URL}/webhooks/paddle`
   - Subscribed events: `subscription.created`, `subscription.activated`, `subscription.updated`, `subscription.paused`, `subscription.past_due`, `subscription.resumed`, `subscription.canceled`. Sending events the parser does not understand will produce 422s but does not corrupt state.
   - Copy the signing secret into `PADDLE_WEBHOOK_SECRET`.
4. Smoke-test by creating a sandbox transaction and confirming a `subscription_created` row appears in `billing_subscription_events`.

### 9.2 Lemon Squeezy

1. **API key**: dashboard → Settings → API → create. Set as `LEMONSQUEEZY_API_KEY`.
2. **Store**: dashboard → Stores → your store. Record the numeric id as `LEMONSQUEEZY_STORE_ID`.
3. **Variants**: dashboard → Products → your Pro product. Each variant has a numeric id visible in the variant page URL. Record them as `LEMONSQUEEZY_VARIANT_PRO_BYOK` and `LEMONSQUEEZY_VARIANT_PRO_MANAGED`.
4. **Webhook**: dashboard → Settings → Webhooks → New.
   - URL: `${BILLING_PUBLIC_BASE_URL}/webhooks/lemonsqueezy`
   - Subscribed events: `subscription_created`, `subscription_updated`, `subscription_cancelled`, `subscription_resumed`, `subscription_expired`, `subscription_paused`, `subscription_unpaused`, `subscription_payment_success`, `subscription_payment_failed`, `subscription_payment_refunded`.
   - Copy the **signing secret** into `LEMONSQUEEZY_WEBHOOK_SECRET`.
5. Smoke-test the same way — confirm a `subscription_created` audit row.

---

## 10. Operational runbook

### 10.1 "Webhooks are not arriving"

1. Check the billing service startup log line — it prints `public_base_url`. Compare against the URL in both provider dashboards. The most common cause of this incident is a divergence between `BILLING_PUBLIC_BASE_URL` and what was actually registered.
2. Check the upstream — your reverse proxy / edge ingress must forward `POST` requests on `/webhooks/paddle` and `/webhooks/lemonsqueezy` to the billing service. The body **must** be passed through byte-for-byte (no re-encoding); the HMAC is computed against the wire bytes.
3. Both providers expose a "recent deliveries" view in their dashboard. A `401` there means the signing secret you configured in the dashboard does not match `PADDLE_WEBHOOK_SECRET` / `LEMONSQUEEZY_WEBHOOK_SECRET`. A `413` means a body somehow exceeded `BILLING_WEBHOOK_MAX_BODY_BYTES` (effectively impossible in normal traffic — investigate before lowering the limit). A `422` means the parser refused the payload; check the billing logs for `paddle_webhook_parse_failed` / `lemonsqueezy_webhook_parse_failed`.

### 10.2 "User says they paid but they're still on free"

1. Query `processed_webhook_events` for the provider's event id (visible in the dashboard delivery view). If the row exists, the webhook reached us.
2. Query `billing_subscription_events` for that user — the audit trail shows every applied transition. If the most recent row is `previous_tier=free, new_tier=pro_*, new_status=active`, the user **was** upgraded; their JWT may be stale. Have them log out and back in. (Sessions are revoked automatically on tier/status change, so this should normally happen on the next API call.)
3. If `processed_webhook_events` has no row but the dashboard says "delivered 200", check that we're not pointing at a different environment's database.
4. If we returned `422` to the provider, the dashboard delivery view will show that. The billing log will contain the exact reason at Warn level.

### 10.3 "A cancelled user is still on Pro"

A `subscription.canceled` (Paddle) or `subscription_cancelled` /
`subscription_expired` (Lemon Squeezy) demotes immediately — the parser maps
to `tier=free`. If the user is still seeing Pro after a cancellation:

1. Confirm an audit row was written: `SELECT * FROM billing_subscription_events WHERE user_id=$1 ORDER BY created_at DESC LIMIT 5;`. If `new_tier='free'` is there, the DB is correct.
2. Force a session revoke if the post-commit revoke logged an error. `auth.SessionStore.RevokeAllUserSessions(user_id)` is idempotent.
3. If no audit row was written, no cancel webhook arrived. Either the dashboard never sent it (check delivery history) or the reconciler hasn't reached the period-end yet — the user is still in the paid-for window of a `paused` / `past_due` / `refunded` subscription, which is correct behaviour. Wait until `current_period_end` and the reconciler will demote them on its next tick (max `BILLING_RECONCILER_INTERVAL_SECONDS`).

### 10.4 "Idempotency table is growing"

The reconciler prunes rows older than `BILLING_IDEMPOTENCY_RETENTION_DAYS`
on every tick. Verify:

```sql
SELECT COUNT(*) FROM processed_webhook_events;
SELECT MIN(received_at), MAX(received_at) FROM processed_webhook_events;
```

If the minimum `received_at` is older than the retention window, check the
billing logs for `billing_reconciler_prune_failed` and the
`billing_reconciler_errors_total{stage="prune"}` counter.

### 10.5 "DB pool exhausted" / "begin_tx failed"

The service uses a single `pgxpool` shared across HTTP and the reconciler.
The reconciler chunks at 200 expired rows and runs one transaction per
user, so it never holds more than one connection at a time. Webhook
transactions are short (idempotency insert + upsert + audit insert + commit).
If you see `begin_tx` errors:

1. Confirm DB latency from the billing host (network partition / failover).
2. Confirm pool size is sufficient. Default pgx pool sizing follows
   `pgxpool` defaults; tune via the connection string
   (`pool_max_conns=...`) if your traffic profile requires it.

### 10.6 "How do I roll the internal shared secret?"

1. Generate a new secret: `openssl rand -hex 32` (≥ 32 chars).
2. Restart the billing service with both `BILLING_INTERNAL_SHARED_SECRET_OLD` and `BILLING_INTERNAL_SHARED_SECRET_NEW` set if you implement a dual-accept rotation (not currently in the codebase — today's behaviour is single-secret).
3. Update the gateway's matching env var and restart.
4. Confirm `/internal/checkout` still returns `200` on a smoke-test request.

Today's code accepts exactly one secret; if you need zero-downtime rotation,
add a second accepted value behind a new env var and gate it on a feature
flag. Until that lands, schedule a rotation as a coordinated billing +
gateway restart in a low-traffic window.

### 10.7 "How do I roll a provider webhook secret?"

Both Paddle and Lemon Squeezy allow you to rotate the signing secret from
the dashboard. The window between rotating in the dashboard and updating
your env var is the window in which webhooks will be rejected with `401`.
Because both providers retry, this is usually safe — but minimise the
window by preparing the env update ahead of the dashboard rotation. The
service does **not** support dual-accept on the webhook secret (HMAC compare
is single-secret). If you need it, add a second verifier behind an env-gated
feature flag.

---

## 11. Security model

- **Webhook signature** — HMAC-SHA256 over the exact wire bytes. Both digests are hex-decoded before `hmac.Equal` so the comparison is constant-time on equal-length slices. The body is read once under `http.MaxBytesReader` and the same captured `[]byte` is fed to both the verifier and the parser; nothing decodes JSON before the signature is verified.
- **Replay** — Paddle: timestamp-bound, symmetric window (`|now - ts| > window` rejects past **and** future skew). Lemon Squeezy: the provider does not sign a timestamp; replay defense is the idempotency table — a captured webhook replayed later is recorded once and the second insert is a no-op.
- **Idempotency** — `processed_webhook_events` insert and the subscription upsert and the audit insert all happen inside the **same transaction**. A duplicate webhook can never partially apply.
- **Race-safe upsert** — the upsert SQL has `WHERE event_timestamp <= EXCLUDED.event_timestamp`. Out-of-order deliveries are silently dropped without regressing newer state, and the helper returns `applied=false` so the HTTP layer reports `out_of_order: true`.
- **Internal endpoint** — `crypto/subtle.ConstantTimeCompare` against `BILLING_INTERNAL_SHARED_SECRET` (min 32 chars, validated at startup), with `DisallowUnknownFields` and a 16 KiB body cap on the request decoder.
- **Provider API keys** — only the billing service holds them. The gateway never sees a Paddle or Lemon Squeezy key. Provider HTTP calls bound by `HTTPTimeout=10s` with one 5xx retry and no retry on 4xx.
- **Session revocation** — fires on every applied tier change OR status change. Runs post-commit so a transient revoke failure cannot roll back a successful subscription change; the next JWT refresh still sees the new tier because `auth_users` joins `billing_subscriptions` on every fetch.
- **Defense-in-depth tier enforcement** — even if a stale JWT is somehow accepted, the execution gRPC service and the management gRPC service both re-check `claims.Tier != "free"` at ingress (`ExecuteTrade`, `RegisterFilledTrade`, `UpdateTradeStatus`). The scheduler additionally truncates symbols at runtime for free users.
- **Failure-mode defaults** — every required webhook secret / API key / price id / variant id is `required:"true"` in `envconfig`. A missing value refuses to boot. A misconfigured `BILLING_RECONCILER_INTERVAL_SECONDS=0` refuses to boot. There is no code path that silently disables either signature verification or the reconciler.

---

## 12. Platform-wide auth posture (cookie-auth, complete)

The frontend no longer stores any JWT in `localStorage`. The access
and refresh tokens are HttpOnly cookies set by the gateway on every
`/auth/*` response; the only JS-readable cookie is the CSRF
double-submit token which is useless without the matching HttpOnly
access cookie. The billing UI inherits this posture along with the
rest of the dashboard.

Reference: `docs/cookie-auth.md` (the canonical runbook). Anything
stored under `localStorage` by the SPA now is UI preference data only
(active symbol, active timeframe, dismissed-analysis id) and never a
credential.

---

## 13. Quick reference

```text
Service binary           src/billing/cmd/server
Docker image             src/billing/Dockerfile (port 8082)
Public endpoints         /webhooks/paddle, /webhooks/lemonsqueezy,
                         /health, /readiness, /metrics
Internal endpoint        /internal/checkout (X-Internal-Auth)
Tier values              free | pro_byok | pro_managed
Status values            active | past_due | paused | canceled |
                         refunded | unpaid | expired
Canonical tables         billing_subscriptions,
                         processed_webhook_events,
                         billing_subscription_events,
                         billing_usage
Reconciler interval      BILLING_RECONCILER_INTERVAL_SECONDS (default 900s)
Idempotency retention    BILLING_IDEMPOTENCY_RETENTION_DAYS (default 30d)
Internal-secret min      32 characters (constant-time compared)
Max webhook body         BILLING_WEBHOOK_MAX_BODY_BYTES (default 1 MiB)
Paddle replay window     BILLING_WEBHOOK_REPLAY_WINDOW_SECONDS (default 300s,
                         symmetric past/future)
```
