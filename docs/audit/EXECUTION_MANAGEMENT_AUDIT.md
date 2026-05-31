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

### F6 (P1) — BurstQueue is implemented and tested but never wired
`src/execution/internal/executor/queue.go` defines a per-user FIFO intake
gate with a global concurrency ceiling and deadlines, with full unit tests in
`queue_test.go`. But no call site constructs it or calls `Enter`: not
`main.go`, not `grpc_server.go`, not `executor.go`, not `http_server.go`. The
only references are the definition and its tests. Backpressure, the global
in-flight cap, and per-user fairness that CHECKLIST Section 3 ("Backpressure
controls", "Queue depth monitoring") calls for are therefore NOT enforced — a
burst of orders hits the broker bridge unbounded.
**Fix:** construct the queue in main.go from config, hold it on
ExecutionServer, and have ExecuteTrade acquire a per-user slot before the
validate/size/execute pipeline and release it after. Overflow/deadline
returns a non-retryable QUEUED/REJECTED response (not a gRPC error, which the
gateway would retry and defeat the backpressure).

### F8 (P0-build) — Execution brokertest package does not compile
`src/execution/brokertest/bridge_test.go` calls `mt5.NewBridge(srv.URL(),
5000)` (2 args) but the current `NewBridge` signature is `(baseURL,
timeoutMs, internalSecret)` (3 args). The package therefore fails to build,
which breaks `go test ./...` for the whole module. Separately, the bridge was
refactored so `stampInternalAuth` requires BOTH a non-empty internal secret
AND a user id in the context; every test passes `context.Background()` with no
identity, so even after fixing the arg count each call would fail with
"missing user id in request context". This is a pre-existing breakage unrelated
to F1-F7 but it blocks CI, so it is fixed here.
**Fix:** add a test-local internal secret and an identity-bearing context
helper, and thread both through every bridge construction + call.

### F7 (P2) — In-process analysisID dedup removed (was dead/redundant)
`grpc_server.go` kept an in-memory `processed` map for analysis_id dedup
(plus its mutex, consts, cleanup goroutine, markProcessed/isDuplicate/
evictExpired, and a Close() method). With the DB-backed idempotency layer
(F1-F3) now correct and keyed on the gateway's idempotency key (which IS the
analysis_id by default), that map was a weaker, single-process,
restart-losing duplicate of the same guard — dead code. Removed in full.
Behavioural note: a duplicate is now surfaced by the executor as
`Accepted:true, Status=DUPLICATE` (returning the prior placement) instead of
the old `Accepted:false` rejection. This is the intended idempotent-retry
semantic and matches the executor's own return.

---

### F9 (P0) — Order-placement HTTP retry is not idempotent at the broker
Traced the full placement path to the metal: executor -> bridge.placeOrder
(HTTP POST) -> engine /internal/broker/place_order -> zmq client.place_order
-> EA ORDER_SEND. Findings, all verified in source:
  - The engine handler reads no idempotency key and does no dedup.
  - The zmq client sends ORDER_SEND with no dedup token.
  - The EA's HandleOrderSend uses a fixed MAGIC_NUMBER and calls OrderSend()
    unconditionally — no client-token or comment-based dedup.
  - bridge.placeOrder wraps the POST in a retry-with-backoff loop and
    isTransient() returns true for "EOF" / "connection reset" / 5xx.
Consequence: if the order reaches the broker and fills but the HTTP RESPONSE
is lost (connection reset after OrderSend), the bridge RETRIES and the EA
places a SECOND order — a duplicate position. The DB idempotency layer
(F1-F3) does NOT cover this: it dedupes ExecuteTrade RPCs, not retries
inside a single placeOrder call. CHECKLIST Section 1 "Network retries are
idempotent" is violated at the broker boundary.
Also: bridge.go declares headerIdempotencyKey = "X-Idempotency-Key" but never
sends it — dead, misleading constant.
**Fix:** order placement must be attempted exactly once — never retried —
because the broker cannot dedupe it. Make placeOrder a single attempt and
remove the now-dead retry machinery (WithRetry, retryConfig, BrokerRetry*
config, headerIdempotencyKey). Transient ambiguity is resolved by the
reconciler, which compares broker truth against engine state. Read calls
are unaffected (they never used the retry loop).

## PROGRESS TRACKER

| ID | Title | Severity | Status |
|----|-------|----------|--------|
| F1 | xmax claim rewrite | P0 | DONE |
| F2 | idempotency-key propagation | P0 | DONE |
| F3 | INSTANT-mode idempotency | P0 | DONE |
| F4 | StatusDuplicate constant | P1 | DONE |
| F5 | management post-boot reconciler supervisor | P1 | DONE |
| F6 | wire BurstQueue into ExecuteTrade | P1 | DONE |
| F8 | execution brokertest compile fix | P0-build | DONE |
| F9 | order placement must not retry (broker not idempotent) | P0 | DONE |
| F7 | redundant in-process analysisID dedup | P2 | DONE (removed) |

Update this table as each fix lands. Each commit references its finding ID.

All five findings landed on branch `audit/execution-management-hardening`.
Next step: open the MR from that branch into `main` and run CI.
