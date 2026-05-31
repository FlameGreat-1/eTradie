# Execution + Management Production-Readiness Audit

Scope: end-to-end trace of the trade execution and management lifecycle
(`src/gateway`, `src/execution`, `src/management`) against `CHECKLIST.md`.
Every finding below was verified by reading the actual source on `main`, not
assumed. Fixes are landed in small, reviewable commits on branch
`audit/execution-management-hardening`.

---

## Severity legend

- **P0** Correctness / money-loss / silent data divergence. Fix immediately.
- **P1** Reliability / production-breaking under load or failure.
- **P2** Consistency / dead code / hygiene. No runtime harm but must be clean.

---

## FINDINGS

### F1 (P0) — Order idempotency claim is non-functional (`RETURNING xmax`)
`src/execution/internal/store/idempotency.go` `TryClaim` runs
`INSERT ... ON CONFLICT DO NOTHING RETURNING xmax` and scans `xmax` into a Go
`string`. `xmax` is a Postgres system column of type `xid`; pgx v5 has no
text/string decoder path that makes scanning `xid` into `*string` safe and
deterministic, and the whole `RETURNING xmax` trick is a fragile way to detect
"did the INSERT happen". The robust, idiomatic detection is to `RETURNING` a
real column from the table and rely on pgx `ErrNoRows` to mean "conflict
fired". As written, the happy-path claim can error out, causing the executor
to log `idempotency_claim_failed_falling_through` and place the order WITHOUT
idempotency protection. CHECKLIST Section 1 ("Same order cannot execute
twice") is therefore not actually enforced.
**Fix:** rewrite `TryClaim` to `RETURNING order_id` (a guaranteed-non-null,
real column) and branch on `pgx.ErrNoRows`.

### F2 (P0) — Idempotency key is never propagated from the gateway
The gateway stamps `x-idempotency-key` into outgoing gRPC metadata
(`src/gateway/internal/infra/execution_grpc.go`), and `models.Order` documents
an `IdempotencyKey` field, but:
- `src/auth/middleware.go` `UnaryAuthInterceptor` never reads
  `x-idempotency-key`.
- `src/execution/internal/server/grpc_server.go` `ExecuteTrade` never reads it
  and never stamps `order.IdempotencyKey`.
So `Executor.placeLimit` always falls back to `order.OrderID`, which
`builder.generateOrderID` regenerates randomly on EVERY call. A retried RPC
(the gateway retries on `Unavailable`/`DeadlineExceeded`/`Internal`) produces a
brand-new OrderID, so the DB claim key never matches a prior attempt and the
duplicate is NOT detected. The two idempotency windows the comments claim to
unify are in fact disjoint.
**Fix:** read `x-idempotency-key` from incoming gRPC metadata in the execution
gRPC server and stamp it onto `order.IdempotencyKey` before `executor.Execute`.

### F3 (P0) — INSTANT-mode orders have no idempotency at all
`Executor.handleInstant` arms a watcher without ever touching the idempotency
store. A duplicate `ExecuteTrade` for the same setup in INSTANT mode arms TWO
watchers (different random `WatcherID`), each of which can independently fire a
market order ⇒ double position. The gRPC server's in-memory `analysisID`
dedup is best-effort, single-process, and lost on restart; it is not a
substitute. CHECKLIST Section 1 "Retry logic cannot create duplicate
positions" is violated for INSTANT mode.
**Fix:** claim idempotency in `handleInstant` too, keyed on
`(UserID, IdempotencyKey)`, short-circuiting duplicate arming.

### F4 (P1) — `DUPLICATE` order status is a magic string
`executor.go` returns `constants.OrderStatus("DUPLICATE")` inline instead of a
declared constant. Inconsistent with every other status and invisible to any
exhaustiveness check.
**Fix:** add `StatusDuplicate` to `constants` and use it.

### F5 (P1) — Management runs no reconciler/monitoring for users who appear
after startup
`src/management/cmd/management/main.go` only starts a `StateReconciler`
(startup sync + position watcher) for users returned by `ListActiveUsers` at
boot. A user who registers a broker AFTER startup gets reconciliation ONLY if
they route a fresh `RegisterFilledTrade` through gRPC. Orphaned/manually-opened
positions for such users are never imported, and external closes are never
detected, until the next process restart. CHECKLIST Management Section 1
("Continuous Reconciliation", "self-healing") is not met for the post-boot
cohort.
**Fix:** `monitoring.ReconcilerSupervisor` runs one StateReconciler per
active user, re-evaluating the active-user set every
`MANAGEMENT_RECONCILE_INTERVAL_SECS` (default 60s). It starts reconcilers
for newly-active users, stops them for deactivated users, seeds the
cold-start tick-cache identity once, and is drained on shutdown.
Supporting changes: `TickCache.HasServiceIdentity()` and the new
`ReconcileIntervalSecs` management config field.

---

## PROGRESS TRACKER

| ID | Title | Severity | Status |
|----|-------|----------|--------|
| F1 | xmax claim rewrite | P0 | DONE |
| F2 | idempotency-key propagation | P0 | DONE |
| F3 | INSTANT-mode idempotency | P0 | DONE |
| F4 | StatusDuplicate constant | P1 | DONE |
| F5 | management post-boot reconciler supervisor | P1 | DONE |

Update this table as each fix lands. Each commit references its finding ID.

All five findings landed on branch `audit/execution-management-hardening`.
Next step: open the MR from that branch into `main` and run CI.
