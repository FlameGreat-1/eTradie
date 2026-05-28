# Platform LLM Quota — Operator + Developer Runbook

This document captures the end-to-end design of the admin-managed LLM
token quota system landed by the `feat/admin-managed-quotas` MR. It is
the single source of truth for:

- what each tier sees,
- how the policy is persisted and edited,
- how the pre-flight and deep-path metering interact,
- which alert events fire, where they originate, and what the SPA does
  with them,
- the admin RBAC and rate-limit chain,
- the one-time operator action required when upgrading a deployment
  that had non-default values for the removed env-tier knobs.

---

## 1. Tier matrix (per QUOTA.md scope decision)

| Tier         | Default key   | Platform-metered? | Can switch to BYOK? | Modal on quota exhaustion         |
|--------------|---------------|-------------------|----------------------|-----------------------------------|
| `pro_managed`| Platform key  | Yes               | Yes                  | `QuotaExhaustedModal` (platform)  |
| `admin`      | Platform key  | Yes (same envelope as pro_managed) | Yes | `QuotaExhaustedModal` (platform)  |
| `pro_byok`   | BYOK only     | No                | n/a                  | `ProviderQuotaModal` (BYOK)       |
| `free`       | BYOK only     | No                | n/a                  | `ProviderQuotaModal` (BYOK)       |

**Why two distinct modals:** the cause and the remediation are
different. A platform-metered user hits a cap set by the admin in the
dashboard; remediation is "contact platform support" (for Pro Managed)
or "edit the policy" (for admins). A BYOK user hits their OWN provider
(Anthropic, OpenAI, Gemini, self-hosted); remediation is "top up your
provider account" or "wait a moment and retry" — the platform never
debited their account.

The single switch that maps a request to the right path is
`ProcessorConfig.uses_platform_key` (`engine/dependencies.py::_load_active_llm_connection`).
`True` → platform path. `False` → BYOK path.

---

## 2. Policy persistence and editing

### Schema

Table `tier_quota_policies` (migration `0028_tier_quota_policies.sql`):

| Column                       | Type    | Notes                                                                  |
|------------------------------|---------|------------------------------------------------------------------------|
| `tier`                       | TEXT PK | CHECK in (`free`, `pro_byok`, `pro_managed`, `admin`)                  |
| `daily_input_tokens`         | BIGINT  | >= 0                                                                    |
| `daily_output_tokens`        | BIGINT  | >= 0                                                                    |
| `monthly_input_tokens`       | BIGINT  | >= 0                                                                    |
| `monthly_output_tokens`      | BIGINT  | >= 0                                                                    |
| `max_input_tokens_per_call`  | BIGINT  | >= 0                                                                    |
| `soft_cap_percent`           | INT     | 0..100                                                                  |
| `reservation_ttl_seconds`    | INT     | 30..3600                                                                |
| `allowed_models`             | JSONB   | array of lowercase model names; empty array = any                       |
| `enforced`                   | BOOL    | When true, requires non-zero caps on every dimension                    |
| `updated_at`                 | TSTZ    | DB-set on every Upsert                                                  |
| `updated_by`                 | TEXT FK | `auth_users(id)`                                                        |

### Read path

`src/billing/store/quota_policy.go::QuotaPolicyStore.GetPolicy(ctx, tier)`

- Per-tier 30 s in-memory cache (`sync.Map`).
- Explicit invalidation on every `UpsertPolicy()` — admin edits are
  visible to the next `Reserve` / pre-flight without waiting for the
  TTL.
- Defensive copy of `AllowedModels` on both the cache-hit and the DB
  branches so concurrent readers cannot mutate the cached slice.
- `ErrPolicyNotFound` on a missing row. The metering handler converts
  this to a zero-access policy so the deep `Reserve` returns
  `tier_not_eligible` (fail-closed).

### Write path

Admin SPA `AdminQuotaPolicyPanel` → `PUT /api/v1/admin/quota/policies/{tier}`
→ `UpsertPolicy()`. The SPA renders ONLY the two enforced tiers
(`pro_managed`, `admin`). The other two rows still exist (zero caps,
`enforced=false`) as defense-in-depth on the server side but are
hidden from the admin UI by design.

### Cache invalidation contract

Any admin edit invalidates exactly the affected tier's cache entry
immediately. There is no global invalidation event because the cache
is already per-tier; an edit to `pro_managed` does not interfere with
`admin`'s cache.

---

## 3. Pre-flight contract

The pre-flight is a single, read-only SQL SELECT against `billing_usage`
that returns the four counter values used by `Reserve`'s cap checks
WITHOUT writing anything. Implemented at
`src/billing/store/usage.go::UsageStore.PreflightLLMQuota()`.

### Two call sites

1. **Manual button click** — `POST /api/v1/cycle/run` →
   `api_handlers.go::handleRunCycle()` calls
   `APIHandler.preflightLLMQuota()` at the top of the handler, BEFORE
   any TA / Macro / RAG work. On block:
   - HTTP 429 with `Retry-After` header.
   - Structured body: `{ error_code: "llm_quota_exceeded", dimension,
     limit, used, requested, resets_at, retry_after, is_admin }`.
   - User-scoped `LLM_QUOTA_EXCEEDED` alert event published.
   - `orchestrator.RunCycle` is NOT entered.

2. **Auto cycle** — `pipeline/scheduler.go::executeUserCycle()` calls
   `Scheduler.preflightUserQuotaBlocked()` at the top of every tick,
   BEFORE the symbol fetch. On block:
   - User-scoped `LLM_QUOTA_EXCEEDED` alert event published (with
     `source="scheduler"` so a future operator dashboard can split
     manual vs auto block volume).
   - The tick returns cleanly so the next `timer.Reset(interval)`
     fires normally. The user is auto-unblocked the moment they fall
     under cap or the monthly window rolls.

### Failure posture (both sites)

- Policy lookup error (transient DB blip, `ErrPolicyNotFound` from a
  missing seed migration): log a warning, **do not block** the
  request / tick. The deep `metering.reserve` inside the cycle stays
  as the correctness boundary.
- Usage lookup error: same — fail open on the optimisation.

The pre-flight is a **fast-path optimisation, not a correctness
boundary**. The deep `Reserve` path's `SELECT FOR UPDATE` inside the
metering handler is the authoritative cap check.

### Resource savings per blocked call

- 1 cached DB read (or 1 SQL SELECT in 1-of-N ticks where N ≈ 30s / tick interval).
- 0 LLM tokens.
- 0 TA / Macro / RAG cost.
- 1 alert publish (Redis LPUSH + WS fan-out — already cheap).

---

## 4. Deep-path metering (defence-in-depth)

Unchanged by this MR. `src/engine/processor/service.py::AnalysisProcessor.process()`
still calls `metering.reserve()` immediately before the LLM call when
`uses_platform_key=True`. On breach it raises
`engine.shared.exceptions.QuotaExceededError`, which propagates through
the internal router as HTTP 429 with the same structured body the
pre-flight emits. The SPA's modal opens identically whether the
rejection came from the pre-flight or the deep path.

---

## 5. Alert event types

### `LLM_QUOTA_EXCEEDED` (platform)

Publisher: gateway (Go).
Source constant: `alert.SourceGateway` (`gateway`).
Severity: `WARNING`.

Fires when a platform-key user (`pro_managed` or `admin`) hits a cap.
Published by:
- `api_handlers.go::preflightLLMQuota` (manual button click block).
- `scheduler.go::preflightUserQuotaBlocked` (auto-cycle block).
- `metering_handler.go::handleReserve` (deep path — via
  `recordBlocked` in `usage.go`; the gateway converts the 429 to the
  same event before responding).

Details payload: `dimension`, `limit`, `used`, `requested`, `resets_at`
(RFC3339), `retry_after` (seconds), `is_admin` (bool), `source`
(`preflight` | `scheduler` | `reserve`).

### `LLM_PROVIDER_QUOTA_EXCEEDED` (BYOK)

Publisher: engine (Python).
Source constant: `engine.shared.alert_publisher.SOURCE_ENGINE` (`engine`).
Severity: `WARNING`.

Fires when a BYOK user's OWN provider returns a quota / rate-limit
error after all retries are exhausted. Gated at the call site
(`service.py::_execute`'s `except Exception as llm_exc` branch) by:
```
not self._config.uses_platform_key
AND classify_llm_failure(exc).code in {CODE_QUOTA_EXCEEDED, CODE_RATE_LIMITED}
```

Details payload: `provider` (`anthropic` | `openai` | `gemini` |
`self_hosted` | `unknown`), `model`, `detail` (provider's raw error
message, truncated to 256 chars), `code` (`quota_exceeded` |
`rate_limited`).

### Wire-shape contract

Both events use the existing `alert.Event` JSON shape:
```
{
  "id":        "20060102150405-<8 hex chars>",
  "source":    "<EventSource>",
  "type":      "<TYPE>",
  "severity":  "<EventSeverity>",
  "timestamp": "<RFC3339Nano UTC>",
  "user_id":   "<string>",
  "message":   "<short user-facing string>",
  "details":   { ... }
}
```
Published on Redis pub/sub channel `etradie:alerts`. The Go-side
`src/alert/redis/transport.go::Transport.subscribeLoop` deserialises
and fans out via the local in-process Hub to the user's WebSocket.

The ID format must match `alert/event.go::generateEventID` (14-digit
timestamp + dash + 8 hex chars) so the gateway's `RecentSince()` can
filter Redis history by score. Both publishers (Go and Python) honour
the same format.

---

## 6. SPA wiring

### Realtime layer

`cotradee/src/features/realtime/types.ts` — both event-type strings
added to `EventType`.

`cotradee/src/features/realtime/eventMap.ts` — TanStack Query
invalidations:

| Event type                    | Keys invalidated              |
|-------------------------------|-------------------------------|
| `LLM_QUOTA_EXCEEDED`          | `['billing']`, `['analysis']` |
| `LLM_PROVIDER_QUOTA_EXCEEDED` | `['analysis']`                |

`cotradee/src/features/realtime/RealtimeProvider.tsx` — dispatches a
window `CustomEvent` per type and suppresses the generic destructive
toast so the modal is the only notification:

| Event type                    | `window.dispatchEvent` name        |
|-------------------------------|------------------------------------|
| `LLM_QUOTA_EXCEEDED`          | `open-llm-quota-modal`             |
| `LLM_PROVIDER_QUOTA_EXCEEDED` | `open-llm-provider-quota-modal`    |

### Axios interceptor (HTTP path)

`cotradee/src/lib/axios.ts` — on HTTP 429 with body
`error_code === "llm_quota_exceeded"`, dispatches the SAME
`open-llm-quota-modal` event with the parsed body as `detail`, and
SUPPRESSES the generic "Limit Reached" toast. Other 429s (cycle-rpm
rate limit, admin handler rate limit, etc.) keep the existing toast.

### Modals

`cotradee/src/features/settings/components/QuotaExhaustedModal.tsx`
and `cotradee/src/features/settings/components/ProviderQuotaModal.tsx`
are mounted once at the App root (`cotradee/src/App.tsx`). They are
entirely event-driven and render `null` until their open event fires.

The platform modal renders a different CTA for admins (link to the
admin quota policy panel in `/settings`) vs. Pro Managed users
("Contact Support"). The BYOK modal renders a provider-specific
dashboard deep-link plus a "Manage Your Keys" link to
`/settings/llm-keys`.

### Admin panel

`cotradee/src/features/admin/components/AdminQuotaPolicyPanel.tsx`,
mounted from `cotradee/src/routes/pages/settings/AdminSystemAiSection.tsx`,
renders only the two enforced tier cards (`pro_managed`, `admin`).
Client-side validation mirrors `billingstore.ValidatePolicy` exactly;
server-side validation remains authoritative.

---

## 7. Admin RBAC + rate limit

Every `/api/v1/admin/quota/policies[/:tier]` endpoint is wrapped by the
standard admin chain:
```
authMiddleware -> auth.RequireAdmin -> csrfMiddleware -> handler
```
at `src/gateway/internal/server/admin_quota_handler.go`. A non-admin
authenticated user receives a clean 403 from `RequireAdmin`.

A per-admin token-bucket rate limit of **60 req/min, burst 30** sits at
the top of every handler to keep a runaway dashboard refetch loop from
scanning the admin endpoints hundreds of times per second. On block
the handler returns 429 with a `Retry-After: 30` header.

The `updated_by` column on every `UpsertPolicy()` row is taken from
the JWT (`auth.ClaimsFromContext`), so an admin cannot impersonate
another admin's edit audit trail.

---

## 8. Operator migration runbook

### What changed in env

The following env-tier knobs were REMOVED from `src/auth/config.go`:

```
TIER_PRO_MANAGED_DAILY_INPUT_TOKENS
TIER_PRO_MANAGED_DAILY_OUTPUT_TOKENS
TIER_PRO_MANAGED_MONTHLY_INPUT_TOKENS
TIER_PRO_MANAGED_MONTHLY_OUTPUT_TOKENS
TIER_PRO_MANAGED_MAX_INPUT_PER_CALL
TIER_PRO_MANAGED_SOFT_CAP_PERCENT
TIER_PRO_MANAGED_ALLOWED_MODELS
LLM_RESERVATION_TTL_SECONDS
```

The following env keys are KEPT (they govern HTTP rate limiting on
`POST /api/v1/cycle/run`, NOT LLM token caps):

```
TIER_FREE_CYCLE_RPM           / TIER_FREE_CYCLE_BURST
TIER_PRO_BYOK_CYCLE_RPM       / TIER_PRO_BYOK_CYCLE_BURST
TIER_PRO_MANAGED_CYCLE_RPM    / TIER_PRO_MANAGED_CYCLE_BURST
```

### Migration steps

**Fresh install / deployment that used env defaults:**
No operator action required. Migration `0028` seeds the four canonical
rows with the SAME numeric values previously encoded as env defaults.
Fresh deploy boots with byte-identical behaviour to the previous
version.

**Deployment that overrode any of the removed env keys (rare case):**

The alembic 0028 seed values are hard-coded. The table cannot be
upserted before migration 0028 runs (the table does not exist). The
migrator runs DURING the image rollout in the engine migrator job.
So the only correct order is: migrate first, then promote your
overrides into the row.

1. **Before rollout.** Read your current `TIER_PRO_MANAGED_*` env
   values from your config store (Vault, env file, k8s secret).
   Compare each value against the alembic 0028 seed below; record
   any deltas:

   | column                       | seed value     |
   |------------------------------|----------------|
   | daily_input_tokens           | 2,000,000      |
   | daily_output_tokens          | 200,000        |
   | monthly_input_tokens         | 20,000,000     |
   | monthly_output_tokens        | 2,000,000      |
   | max_input_tokens_per_call    | 300,000        |
   | soft_cap_percent             | 80             |
   | reservation_ttl_seconds      | 300            |
   | allowed_models               | (empty array)  |

   If every env value matches the seed, no further action is
   needed.

2. **During rollout.** The engine migrator job runs migration 0028
   on image start. The `tier_quota_policies` table is created and
   seeded with the values above. The migrator exits before the
   user-facing pods (gateway, billing, engine API) begin serving
   Reserve calls.

3. **Immediately after migration, before serving user traffic.**
   UPSERT the recorded deltas via either:

   a) The admin dashboard's Tier Quota Policies panel
      (`/settings` -> Admin -> Tier Quota Policies). Admin edits
      apply on the next request after the 30 s `QuotaPolicyStore`
      cache TTL, or instantly on the next request after the
      explicit cache invalidation triggered by Upsert.

   b) A one-off SQL UPDATE against the running database, e.g.:

      ```sql
      UPDATE tier_quota_policies
      SET monthly_input_tokens = 50000000,
          updated_at           = NOW(),
          updated_by           = NULL
      WHERE tier = 'pro_managed';
      ```

      The store's 30 s cache may briefly serve the seeded value
      to the first Reserve calls until the TTL expires; the
      cumulative caps mean this brief stale read cannot let a
      user breach their real cap.

There is NO `seed-quotas-from-env` make target; the env keys are
gone from the code so nothing to seed from. (The previous version
of this doc mentioned one in error.)

### Rollback

The `downgrade` arm of migration `0028` drops the table. A production
rollback would also need to re-introduce the env-tier knobs in
`src/auth/config.go` (revert the relevant commits in this MR). The
downgrade path is intended for local-development rollback only.

---

## 9. End-to-end matrix (verification)

| Scenario                                                | Pre-flight | Deep Reserve | Event              | Modal                 |
|---------------------------------------------------------|------------|--------------|---------------------|------------------------|
| `pro_managed` on platform key, monthly cap OK           | pass       | pass         | none                | none                   |
| `pro_managed` on platform key, monthly cap hit          | block      | n/a          | `LLM_QUOTA_EXCEEDED` (`source=preflight`) | `QuotaExhaustedModal` (Pro Managed CTAs: Use Your Own API Key + Contact Support) |
| `pro_managed` switched to BYOK, provider 429            | n/a        | n/a          | `LLM_PROVIDER_QUOTA_EXCEEDED` | `ProviderQuotaModal` |
| `admin` on platform key, cap hit                        | block      | n/a          | `LLM_QUOTA_EXCEEDED` (`is_admin=true`) | `QuotaExhaustedModal` (Admin CTA: Edit Policy) |
| `admin` switched to BYOK, provider 429                  | n/a        | n/a          | `LLM_PROVIDER_QUOTA_EXCEEDED` | `ProviderQuotaModal` |
| `pro_byok`, provider 429                                | n/a        | n/a          | `LLM_PROVIDER_QUOTA_EXCEEDED` | `ProviderQuotaModal` |
| `free`, provider 429                                    | n/a        | n/a          | `LLM_PROVIDER_QUOTA_EXCEEDED` | `ProviderQuotaModal` |
| `pro_managed` on platform key, daily input cap hit MID-cycle (pre-flight raced) | pass | block | `LLM_QUOTA_EXCEEDED` (`source=reserve`) | `QuotaExhaustedModal` |

In the last row the pre-flight passes because the cumulative counter
was just under cap at SELECT time, but a concurrent reservation from
another session won the `SELECT FOR UPDATE` race and pushed the user
over. The deep `handleReserve` path catches the breach, calls
`recordBlocked` to bump the audit counter, publishes the user-scoped
`LLM_QUOTA_EXCEEDED` event (Audit ref: ADMIN-QUOTA-AUDIT-1) with
`details.source = "reserve"`, and returns the same structured 429
envelope the pre-flight returns. The SPA modal opens identically.
This is the defence-in-depth guarantee.

---

## 10. References

- Migration: `src/engine/shared/db/migrations/versions/0028_tier_quota_policies.py`
- Go store: `src/billing/store/quota_policy.go`
- Go pre-flight: `src/billing/store/usage.go::PreflightLLMQuota`
- Go gateway handler: `src/gateway/internal/server/admin_quota_handler.go`
- Go pre-flight call sites: `src/gateway/internal/server/api_handlers.go::preflightLLMQuota`,
  `src/gateway/internal/pipeline/scheduler.go::preflightUserQuotaBlocked`
- Go alert constants: `src/alert/event.go`
- Python publisher: `src/engine/shared/alert_publisher.py`
- Python call site: `src/engine/processor/service.py::_execute` (BYOK branch)
- SPA realtime: `cotradee/src/features/realtime/{types.ts,eventMap.ts,RealtimeProvider.tsx}`
- SPA axios: `cotradee/src/lib/axios.ts`
- SPA modals: `cotradee/src/features/settings/components/{QuotaExhaustedModal.tsx,ProviderQuotaModal.tsx}`
- SPA admin panel: `cotradee/src/features/admin/components/AdminQuotaPolicyPanel.tsx`
