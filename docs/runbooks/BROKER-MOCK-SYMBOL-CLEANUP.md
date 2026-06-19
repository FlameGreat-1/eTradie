# Broker / Mock / Symbol cleanup — operator runbook

**Status:** shipped to `main`.
**Last updated:** 2026-06-19.
**Related prior runbook:** [`WS-NOTIFICATIONS-INVESTIGATION.md`](WS-NOTIFICATIONS-INVESTIGATION.md).

## TL;DR for the next operator

Three user-facing issues were fixed in one coordinated change series:

1. **Staging header showed `$10,000` balance regardless of broker state.** Root cause: the execution + management services each carried their own mock `broker.Port` implementation, selected at startup via `BROKER_MODE=mock|mt5`. Staging helm pinned `mock`. The mock ignored the connected broker entirely and returned static fixtures. **Fix:** mock package deleted from both services; mt5 bridge is the sole `broker.Port` implementation in both. The Python engine's `/internal/broker/*` surface already resolved the per-user MT4 or MT5 connection per request via `_resolve_user_broker(container, user_id)`, so nothing else changed semantically — the Go services now consistently dispatch every call through that resolver.

2. **MT4 hosted + EA broker connections were rejected with 422 `mt4_not_supported`.** Root cause: three stale code-side guards (engine `broker_connections.py` create + update, engine `factory.py` hosted branch) all cited a false premise — that `ZeroMQ_EA.ex4` was not bundled in the `mt-node` image. The `.ex4` IS committed at `docker/mt-node/ea/ZeroMQ_EA.ex4` and the Dockerfile copies it with SHA verification. The `entrypoint.sh` has a complete MT4 branch. The provisioner already accepts `platform in ('mt4','mt5')`. **Fix:** all three gates removed; the README correction landed in the same commit.

3. **Chart never loaded the correct symbol after a broker connection.** Root cause: `Header.tsx` and `DashboardPage.tsx` each independently resolved the active symbol from URL → `localStorage` → gateway `useSymbols()` (which is operator-seeded with `DEFAULT_SYMBOLS` like `EURUSD`). Brokers that publish symbols under different suffixes (`EURUSDm` on Exness, `EURUSD.x` on some IC brokers) caused the chart to request candles for a symbol the broker does not publish. **Fix:** new shared `useActiveSymbol` hook owns symbol resolution end to end with broker-catalog validation; both `Header.tsx` and `DashboardPage.tsx` migrated to consume it.

## Architectural invariants this change enforces

After this series:

* The execution service has **one** `broker.Port` implementation: `mt5.Bridge` (constructed in `src/execution/cmd/execution/main.go`). The bridge dispatches every call to the engine's `/internal/broker/*` surface, stamping `X-User-Id` from the request context. The engine resolves the per-user MT4 or MT5 broker connection from `broker_connections` per request.
* The management service has **one** `broker.Port` implementation: `broker.NewMT5Broker` (Client + Stream union). Same dispatch contract.
* No `BROKER_MODE` env var. The Go config structs no longer declare `BrokerMode` or `MockBrokerBalance`. The helm charts no longer render `EXECUTION_BROKER_MODE` / `EXECUTION_MOCK_BROKER_BALANCE` / `MANAGEMENT_BROKER_MODE` / `MANAGEMENT_MOCK_BROKER_BALANCE` into the ConfigMap. Operators cannot accidentally re-enable mock by setting an env var.
* `EXECUTION_BROKER_BRIDGE_URL` and `MANAGEMENT_BROKER_BRIDGE_URL` are **always required** at startup (the validation no longer conditions on mode).
* `EXECUTION_ENGINE_INTERNAL_SHARED_SECRET` and `MANAGEMENT_ENGINE_INTERNAL_SHARED_SECRET` are **required unconditionally in `APP_ENV=production` and `APP_ENV=staging`** (≥32 chars), with fall-back to the root `ENGINE_INTERNAL_SHARED_SECRET`. The service refuses to boot otherwise.
* MT4 and MT5 are both first-class on the hosted, EA, and MetaApi connection paths. `platform='mt4'` is selected per `broker_connections` row and applied at mt-node Pod boot via `MT_PLATFORM` rendered by the engine HostedProvisioner.
* The chart's active symbol resolution chain is:
  1. URL `?symbol=<sym>`.
  2. `localStorage['active_symbol']`, **only if present in the broker catalogue** (`useBrokerSymbols`). Stale values from a previous broker connection are cleared on next mount.
  3. Active broker connection's `mt5_symbol` (server-resolved by the hosted provisioner via `GET_ALL_SYMBOLS`).
  4. First instrument in the broker catalogue.
  5. `''` — UI shows `Select Symbol` / the watchlist prompt; the chart is **not** mounted. The chart never falls back to gateway `DEFAULT_SYMBOLS`.

## File inventory (what changed and why)

### Go — execution service

| File | Action | Why |
|---|---|---|
| `src/execution/internal/broker/mock/broker.go` | DELETED | Mock `broker.Port` implementation (static $10k account). Replaced by the mt5 bridge as the sole implementation. |
| `src/execution/internal/state/state_test.go` | REWRITTEN | Replaced the deleted `mockbroker` import with a local `fakeBroker` scoped to the state package's internal test file. Behaviour preserved bit-for-bit. Pattern matches the pre-existing `reconciler_test.go::fakeBroker`. |
| `src/execution/cmd/execution/main.go` | EDITED | Dropped mockbroker import + `BROKER_MODE` branch. Always constructs `mt5.NewBridge`. Dropped `cfg.IsMT5Mode()` guard from preload-positions; preload now keys solely on `cfg.PreloadPositionsOnStart`. |
| `src/execution/internal/config/config.go` | EDITED | Removed `BrokerMode`, `MockBrokerBalance`, `IsMT5Mode()`. `BrokerBridgeURL` + `EngineInternalSecret` required unconditionally in prod-like; ≥32-char policy unchanged. |

### Go — management service

| File | Action | Why |
|---|---|---|
| `src/management/internal/broker/mock/broker.go` | DELETED | Same rationale as execution. |
| `src/management/internal/monitoring/manager_test.go` | REWRITTEN | Replaced `mockbroker` with a local `fakeBroker` implementing `broker.Port` (9 methods including `WatchPositions`) plus the test helpers `SetTickPrice` + `AddPosition` that the deleted mock exposed. |
| `src/management/internal/takeprofit/executor_test.go` | REWRITTEN | Independent local `fakeBroker` (Go test-internal types cannot be shared across packages). Mirrors the monitoring fake. |
| `src/management/cmd/management/main.go` | EDITED | Dropped mock import + `IsMT5Mode()` branch. Always constructs `broker.NewMT5Broker`. |
| `src/management/internal/config/config.go` | EDITED | Removed `BrokerMode`, `MockBrokerBalance`, `IsMT5Mode()`. Same unconditional bridge URL + engine secret policy as execution. |

### Helm charts

| File | Action | Why |
|---|---|---|
| `helm/execution/templates/configmap.yaml` | EDITED | Removed `EXECUTION_BROKER_MODE` and `EXECUTION_MOCK_BROKER_BALANCE` env keys. |
| `helm/execution/values.yaml` | EDITED | Removed `brokerMode` + `mockBrokerBalance`. Documented the single-bridge architecture. |
| `helm/execution/values-staging.yaml` | EDITED | Removed `brokerMode: "mock"`. |
| `helm/execution/values-production.yaml` | EDITED | Removed `brokerMode: "mt5"`. |
| `helm/management/templates/configmap.yaml` | EDITED | Removed `MANAGEMENT_BROKER_MODE` and `MANAGEMENT_MOCK_BROKER_BALANCE` env keys. |
| `helm/management/values.yaml` | EDITED | Removed `brokerMode` + `mockBrokerBalance`. |
| `helm/management/values-staging.yaml` | EDITED | Removed `brokerMode: "mock"`. |
| `helm/management/values-production.yaml` | EDITED | Removed `brokerMode: "mt5"`. |

### Engine — MT4 unblock

| File | Action | Why |
|---|---|---|
| `src/engine/routers/broker_connections.py` | EDITED | Removed the `422 mt4_not_supported` gate from BOTH the create and update routes. The premise (`.ex4` not bundled) was false. |
| `src/engine/ta/broker/mt5/factory.py` | EDITED | Removed the hosted-branch `ConfigurationError` that rejected `row.platform == 'mt4'`. The factory accepts mt4 hosted rows; the ZmqClient + per-tenant Service DNS work identically for either platform. |
| `docker/mt-node/ea/README.md` | REWRITTEN | Corrected the stale claim that `ZeroMQ_EA.ex4` is absent. Both `.ex4` and `.ex5` are committed to the repository and bundled into the `mt-node` image. |

### SPA — symbol default fix

| File | Action | Why |
|---|---|---|
| `cotradee/src/features/chart/hooks/useActiveSymbol.ts` | CREATED | New shared hook owning chart symbol resolution end to end. Composes `useBrokerSymbols` + `useActiveBrokerConnection` + URL + `localStorage`. Exports `ACTIVE_SYMBOL_STORAGE_KEY`. |
| `cotradee/src/components/layout/Header.tsx` | EDITED | Migrated to `useActiveSymbol`. Drop the duplicated `persistedSymbol` state machine. Timeframe handling unchanged. |
| `cotradee/src/routes/pages/DashboardPage.tsx` | EDITED | Migrated to `useActiveSymbol`. Removed the `useSymbols`-driven auto-select (which fell back to gateway `DEFAULT_SYMBOLS`). |

### Misc

| File | Action | Why |
|---|---|---|
| `.env.example` | EDITED | Removed `EXECUTION_BROKER_MODE` + `EXECUTION_MOCK_BROKER_BALANCE` keys so a fresh `.env` copy stays aligned with the Go config. Management section was already clean. |

## Operational preconditions for the deploy to succeed

These are owned by the operator and **cannot** be automated from the repo edits:

1. **The deployed `mt-node` image must contain `/opt/ea/ZeroMQ_EA.ex4`.** The `.ex4` is committed and the Dockerfile copies it, but whether the live image tag was built after the `.ex4` was added is opaque to the repo. **Rebuild + repush the `mt-node` image** and bump `helm/engine/values.yaml::config.mtNode.image` to the new digest BEFORE any user creates a `platform='mt4'` hosted connection. Without this, an MT4 hosted Pod will start successfully but the EA copy step in `entrypoint.sh` will fall through to the `WARN` branch (no `.ex4` in `/opt/ea/`) and the watcher will time out on `ZMQ PING` during the provisioner's readiness gate.

2. **`EXECUTION_ENGINE_INTERNAL_SHARED_SECRET` (≥32 chars) must be present in staging Vault** (`etradie/services/execution/staging`) AND in production Vault (`etradie/services/execution/production`). Same for `MANAGEMENT_ENGINE_INTERNAL_SHARED_SECRET`. The unconditional validation will fail the pod boot otherwise. The fall-back chain reads the root `ENGINE_INTERNAL_SHARED_SECRET` from the same Vault path if the prefixed key is unset, so a single shared secret is usually sufficient.

3. **A user must provision a real broker connection in staging** (demo or live) before reloading the dashboard. Until then `/api/execution/account` returns 503 (engine: "No broker connection configured") and the header shows `---`. This is the intended, honest behaviour — no more fake $10,000.

## Failure-mode triage tree

### Symptom A: dashboard header shows `---` everywhere

This is the **expected** state when the user has not provisioned a broker connection. Verify:

```bash
kubectl -n etradie-system exec deploy/etradie-engine -- sh -c \
  "curl -sS -H 'X-Internal-Auth: $ENGINE_INTERNAL_SHARED_SECRET' \
        -H 'X-User-Id: <USER_ID>' \
        http://localhost:8000/internal/broker/account_info"
# Expect: {"balance":0,"equity":0,"margin":0,"margin_free":0,"currency":"USD"}
#         (the engine's no-broker skeleton response)
```

If the user **has** provisioned a connection and still sees `---`, jump to **Symptom C**.

### Symptom B: dashboard header shows fake `$10,000` (regression)

Seeing the mock value again means a regression. Check:

```bash
# 1. Verify the deployed execution image actually has the new code.
kubectl -n etradie-system get pods -l app.kubernetes.io/name=etradie-execution \
  -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}'

# 2. Verify the env var is not silently re-set to mock.
kubectl -n etradie-system exec deploy/etradie-execution -- env | grep -i broker
# EXECUTION_BROKER_MODE should NOT appear at all. EXECUTION_BROKER_BRIDGE_URL must be set.
```

### Symptom C: balance + equity show `0` for a user with a provisioned broker

The engine's failover cache returns the empty skeleton when the broker call fails. Check:

```bash
kubectl -n etradie-system logs deploy/etradie-engine --tail=200 \
  | grep -E 'broker_account_info_failed|_resolve_user_broker|no_broker'

USER_ID=<the user id>
kubectl -n etradie-system get pods -l "etradie.user-id=$USER_ID"
```

### Symptom D: `POST /api/broker/connections` with `platform='mt4'` returns 422

A 422 with `code: mt4_not_supported` means the deployed engine image predates the merge. Bump the engine image and redeploy.

### Symptom E: MT4 hosted Pod boots but the EA never connects

The Pod logs will show `entrypoint.sh` emitting the WARN: `EA binary not found at /opt/ea/ZeroMQ_EA.ex4`. The deployed `mt-node` image was built BEFORE `.ex4` was committed. Operational precondition #1 above is the fix.

### Symptom F: chart never loads, candle requests 404

The chart is requesting a symbol the broker does not publish. Debug:

```javascript
// In the browser DevTools console:
localStorage.getItem('active_symbol')
// If this is set to a symbol the active broker does not publish,
// the hook will clear it on the next mount once the catalogue
// loads. Manual fix: localStorage.removeItem('active_symbol') and reload.
```

## Rollback recipe

If the change series needs to be reverted entirely, revert the commits in reverse order:

```bash
# The commits in the series (latest first). Use `git log --oneline` on
# main to recover the exact SHAs in your environment.
#
# Commit 9: management mt5 bridge sole; helm cleanup
# Commit 8: management mock removal + test migration
# Commit 7: .env.example cleanup
# Commit 6: DashboardPage useActiveSymbol migration
# Commit 5: useActiveSymbol hook + Header migration
# Commit 4: MT4 unblock (engine + README)
# Commit 3: execution helm cleanup
# Commit 2: execution main.go + config.go cleanup
# Commit 1: execution mock removal + state_test migration

git revert <sha-of-commit-9>
git revert <sha-of-commit-8>
# ...continue in reverse order...
git revert <sha-of-commit-1>
```

Rolling back commit 1 alone leaves the build broken (main.go imports a deleted package). Roll back commits 1 + 2 together to restore execution to the prior state. Same for management with commits 8 + 9. The SPA commits (5 + 6) and the MT4 unblock (commit 4) are independently revertable.

## What this runbook does NOT cover

* The token-refresh / 15-minute access-token expiry behaviour observed during the related WS investigation. See [`WS-NOTIFICATIONS-INVESTIGATION.md`](WS-NOTIFICATIONS-INVESTIGATION.md).
* The Cloudflare zone-level WebSockets toggle and the related Terraform drift. Same upstream runbook.
* The `mt-node` image build process itself. See `docker/mt-node/README.md` and the `Makefile.platform` build targets.
* The engine's `_resolve_user_broker` failover semantics (Stale-While-Revalidate cache). See `src/engine/routers/broker_bridge.py`.

## Verification matrix (post-deploy)

```bash
# 1. Both services boot with no mock references in their startup log.
kubectl -n etradie-system logs deploy/etradie-execution --tail=20 \
  | grep -iE 'mock|broker_mt5_bridge_configured'
kubectl -n etradie-system logs deploy/etradie-management --tail=20 \
  | grep -iE 'mock|broker_mt5_bridge_configured'
# Expect: broker_mt5_bridge_configured present, NO broker_mock_configured.

# 2. Both configmaps no longer carry BROKER_MODE or MOCK_BROKER_BALANCE.
kubectl -n etradie-system get configmap -l app.kubernetes.io/component=config -o yaml \
  | grep -iE 'broker_mode|mock_broker'
# Expect: empty output.

# 3. Provision a demo broker connection, wait for status='ready', then
#    confirm the header balance flips from '---' to real account data
#    within one 5-second poll cycle.

# 4. Provision a platform='mt4' hosted connection. The create POST must
#    return 200 (not 422). The mt-node Pod must reach Ready within 5
#    minutes. The EA must authenticate (ZMQ PING returns ok).

# 5. With a broker connection that publishes EURUSDm (or any non-vanilla
#    suffix), the chart must auto-select that exact symbol — NOT EURUSD.
#    Verify in DevTools -> Application -> Local Storage -> 'active_symbol'.
```
