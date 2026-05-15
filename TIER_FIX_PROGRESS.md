# Tier-Gating + Broker-Stats Hardening — Progress

Live tracker for the fix that addresses three production issues raised
from the dashboard:

1. **Spurious "Upgrade Required" pop-up.** Connecting / deleting a
   broker connection and creating an LLM connection trigger an
   "Action restricted by your subscription tier" toast. None of these
   endpoints are tier-gated server-side. The toast originates from the
   global axios interceptor in `cotradee/src/lib/axios.ts`, which
   treats EVERY 403 from a non-allowlisted path as a tier restriction.
   A 403 here is almost always a CSRF / cookie issue, not a tier
   denial. The fix tightens the interceptor to require an explicit
   structured signal (`error_code: "tier_required"`) from the server.

2. **Admins are subscription-gated.** The SPA renders the upgrade
   banner and limits for any user whose `tier === "free"`, but admins
   bypass tier checks on the backend already. The SPA must mirror
   that: admins never see the Upgrade modal, the "Upgrade to Pro"
   banner, or the plan-limits panel. The billing service still
   exposes the canonical subscription record so a future admin who
   ALSO carries a paid tier sees it under Settings → Subscription.

3. **Header values (Balance, Equity, Margin, …) all show `---`.**
   The execution service's MT5 bridge calls `POST/GET /internal/broker/*`
   on the engine, but those endpoints require:
     - `X-Internal-Auth` shared-secret header (constant-time compared
       against `ENGINE_INTERNAL_SHARED_SECRET`), AND
     - `X-User-Id` so the engine can resolve the right per-user broker.
   The bridge currently forwards only the user's Bearer token, which
   the engine's `verify_internal_auth` dependency rejects with 401.
   Result: every call to `GetAccountInfo` / `GetPositions` /
   `GetPendingOrders` 401s, the execution HTTP handler returns 503,
   and the header reads empty.

## Files in scope

### Backend (Phase 1 — wire-level broker bridge fix)
- `src/execution/internal/config/config.go` — add `EngineInternalSecret`.
- `src/execution/internal/broker/mt5/bridge.go` — stamp `X-Internal-Auth`
  + `X-User-Id` on every internal call; the Bearer token is no longer
  needed because the engine route is shared-secret-gated.
- `src/execution/cmd/execution/main.go` — pass the secret into
  `mt5.NewBridge`.

### Backend (Phase 2 — structured tier-denial responses)
- `src/gateway/internal/server/api_handlers.go` — 403 payload gains
  `error_code: "tier_required"`, `required_tier`, `feature`.
- `src/gateway/internal/routing/router.go` — same structured shape for
  the execution-blocked-for-free-tier path.

### Frontend (Phase 3 — interceptor + admin bypass)
- `cotradee/src/lib/axios.ts` — only show the upgrade toast when the
  server's 403 carries `error_code === "tier_required"`.
- `cotradee/src/features/settings/components/UpgradeModal.tsx` — refuse
  to open for admins (admins emit a debug log and silently dismiss).
- `cotradee/src/components/layout/Header.tsx` — no behavioural change
  to broker-stats (the bridge fix above is enough); admin still sees
  full stats panel.
- `cotradee/src/routes/pages/settings/BillingSection.tsx` — render an
  "Admin (unrestricted)" surface for admins instead of the free-tier
  upgrade prompt.
- `cotradee/src/features/auth/index.ts` — export an
  `isTierUnrestricted(user)` helper so every gating site uses one
  source of truth.

## Status

| Batch | Files | Status |
|-------|-------|--------|
| 1 | execution config + bridge + main | ⏳ in progress |
| 2 | gateway api_handlers + router    | pending |
| 3 | axios + UpgradeModal + Billing + auth | pending |

This file will be removed after merge.
