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

### F11 (P2) — Stale broker-retry config in execution Helm chart
F9 removed the BrokerRetry* config fields from src/execution config.go, but
the Helm chart still set them in three places: values.yaml,
values-production.yaml, and the configmap (which rendered
EXECUTION_BROKER_RETRY_ATTEMPTS/BASE_MS/CAP_MS env vars). envconfig silently
ignores unknown env vars so this does not break boot, but it is dead,
misleading config implying the broker still retries placement. Removed from
all three files.

### F-MS1 (P0) - Multiple-symbol analysis ran sequentially and never completed
Reported symptom: selecting multiple instruments makes the analysis "keep
running each one over and over and never complete"; RAG + LLM are never
reached. Traced end to end:
  - Gateway TACollector sends ALL symbols in ONE POST to /internal/ta/analyze,
    wrapped in parallelCtx = TA_MACRO_PARALLEL_TIMEOUT_SECONDS (120s default).
  - The engine handler ran `for symbol in body.symbols: await analyze(...)` -
    strictly SEQUENTIAL. N symbols took N x single-symbol time.
  - With real MT5 data (multi-timeframe candle fetch over ZMQ + SMC/SnD
    detection) 4 symbols exceed 120s, so the gateway's TA HTTP call hits the
    parallelCtx deadline.
  - runSingleAttempt sets shouldRetry=true -> RunCycle retries the WHOLE cycle
    (MaxCycleRetries default 1) and re-POSTs all symbols from scratch. Phase 2+
    (RAG/LLM) is never reached. Exactly the reported loop.
  - TA_MAX_CONCURRENT_SYMBOL_ANALYSIS (TAConfig.max_concurrent_symbol_analysis,
    default 4) existed but was NEVER applied at this fan-out.
**Fix:** engine analyzes symbols via asyncio.gather bounded by an
asyncio.Semaphore(max_concurrent_symbol_analysis); per-symbol try/except
preserved; order preserved. Gateway comment corrected.
Consequences (no separate change needed):
  - F-MS2 (timeout premise): the gateway budget-validation comment assumed
    concurrent per-symbol processing; that assumption is now actually true for
    TA, so the 120s budget is correctly sized for the default 4/4 case.
  - F-MS3 (retry amplification): a TA timeout now indicates a genuine broker
    problem rather than structural sequential slowness, so the single cycle
    retry is appropriate and is no longer triggered by normal multi-symbol use.

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
| F10 | fixed 500ms sleep for deal history → poll-with-timeout | P1 | DONE |
| F7 | redundant in-process analysisID dedup | P2 | DONE (removed) |

| F11 | remove stale broker-retry config from execution helm chart | P2 | DONE |
| F12 | expose F5/F6 config knobs (queue, reconcile interval) in charts | P2 | DONE |
| F-MS1 | multi-symbol TA ran sequentially -> never completed; now bounded-concurrent | P0 | DONE |
| F-MS4 | gateway read non-existent SnD candidate zone fields -> OBUpper/OBLower=0, INSTANT fast-path dead | P1 | DONE |

### F-MS4 (P1) — SnD candidate zone fields read by wrong name
In `processSymbol` (`src/gateway/internal/pipeline/orchestrator.go`) the SnD
branch of the candidate-parameter injection read `ob_upper`/`ob_lower` then
fell back to `zone_upper`/`zone_lower`. None of those keys exist on the
`SnDCandidate` model that is `model_dump()`-serialized into the gateway's
candidate dicts (verified in `src/engine/ta/models/candidate.py`): the real
fields are `supply_zone_upper`/`supply_zone_lower` (bearish) and
`demand_zone_upper`/`demand_zone_lower` (bullish). `zone_upper`/`zone_lower`
only exist on `TechnicalCandidate`, which is NOT what reaches the gateway.
Result: `OBUpper`/`OBLower` stayed 0 for every SnD setup, so INSTANT-mode
execution's `tryConfirmAndFire` could not use the ~100ms
`/internal/ta/confirm_ltf` fast-path and fell back to the ~5s full TA
pipeline on every confirmation poll. The SMC branch was already correct
(`order_block_upper`/`order_block_lower` match the model).
**Fix:** read `supply_zone_*` first, `demand_zone_*` otherwise, mirroring the
Python model's `to_technical_candidate()` resolution.

| N1 | news lockout bypassed for delayed activation (INSTANT watcher + LIMIT TTL) | P0 | IN PROGRESS |
| N2 | news guard ignores event currency -> over-blocks unrelated pairs | P1 | IN PROGRESS |
| N3 | news guard fails-open silently when calendar data absent | P2 | IN PROGRESS |
| N4 | is247Market duplicated across gateway + execution | P2 | IN PROGRESS |

## NEWS PROTECTION (N1-N4) DESIGN + STEP PLAN

Problem (verified): MR-REJECT-001 only runs at gateway decision time. But
LIMIT orders rest at the broker for the full style TTL (Swing ~3d, Positional
~7d per LimitTTLCandlesByStyle) and INSTANT watchers poll for up to the same
window (WatcherTimeoutMinutesByStyle). So a setup that passes the 30-min gate
at decision time can fill / fire directly into a high-impact event. The
execution-side check4NewsLockout is a wired no-op. The gateway guard also
ignores event currency (over-blocks) and fails open silently on missing
calendar data. Gateway uses flat 30m; execution constants intend style-aware
30m/45m (NewsLockoutMinutesNormal/Scalping) but never use them.

Design: single currency-aware, style-aware, fail-CLOSED news evaluator in the
gateway routing package = the one source of truth, reused at (a) decision
time, (b) INSTANT fire time via RunConfirmationPulseWithParams, (c) LIMIT/
placement time via a new gateway RPC CheckNewsWindow that execution calls.

DESIGN DECISION (verified constraint): proto .pb.go is generated by `make
proto-gen` (protoc) and committed. protoc cannot be run in this environment and
hand-editing generated descriptor bytes is unsafe. Therefore the entire fix is
implemented WITHOUT any proto change. This is also the cleaner design: the
calendar lives in the gateway, so all enforcement is gateway-side and no new
cross-service field/RPC is needed.

  - N1 INSTANT: enforced inside gateway RunConfirmationPulseWithParams (the
    watcher already calls ConfirmSetup on every fire attempt). If news-locked,
    return Confirmed=false; the watcher keeps polling and never fires into
    news. Fire-time uses the WIDER (scalping, 45m) window unconditionally:
    being more conservative at the irreversible market-order moment is correct
    and needs no trading-style field on the wire.
  - N1 LIMIT: enforced at PLACEMENT time in the gateway router executeTrade,
    BEFORE the order is sent to execution. A LIMIT order rests for its style
    TTL, so the gateway refuses placement when a relevant HIGH-impact event
    falls within (lockout + order max lifetime). This guarantees no resting
    LIMIT order can exist across a news event. Calendar already present at the
    router; no proto change.
  - check4NewsLockout (execution): stays a documented no-op BUT its comment is
    corrected to state that BOTH decision-time and placement-time news gating
    are owned by the gateway (which has the calendar) and INSTANT fire-time is
    gated via ConfirmSetup. This is now accurate and not a hidden gap.

Revised step plan (each = one commit):
  S1 [done] docs plan + tracker.
  S2 [done] news.go evaluator (currency+style aware, fail-closed flag, 247).
  S3 [done] decision-time guard rewired + symbol threaded + 247 consolidated.
  S4 orchestrator RunConfirmationPulseWithParams: INSTANT fire-time news gate
     (uses MacroCollector + 45m window). The router must hand the orchestrator
     a way to read the cached calendar -> use o.macroCollector.Collect.
  S5 router executeTrade: LIMIT placement-time news gate (lockout + TTL window)
     using ProcessorOutput.ExecutionMode + TradingStyle. Needs order-lifetime
     minutes helper keyed by style (mirror of WatcherTimeoutMinutesByStyle /
     LimitTTLCandlesByStyle, expressed in gateway constants).
  S6 execution check4NewsLockout: correct the misleading comment to reflect the
     real (now-complete) ownership; keep as pass() no-op (calendar lives in GW).
  S7 update tracker -> DONE; final consistency pass incl exports.go comment.

VERIFIED CONSTRAINT (calendar horizon): the calendar source is an RSS feed
(InvestingRSSCalendarProvider) whose lookahead horizon is NOT controlled by us
and is typically only ~24-48h. Therefore a one-shot "placement + full TTL
window" check at LIMIT placement CANNOT reliably see events 3-7 days out for
Swing/Positional TTLs. Honest consequence: LIMIT news protection must be
RE-EVALUATED over the order lifetime (the watcher runLimitTTL ticks every 1m
and the calendar refreshes each macro cycle), not only at placement.

That lifetime re-check requires execution -> gateway to ask "news imminent?",
which needs a proto change (new RPC or field). protoc cannot be run here and
hand-editing generated descriptor bytes is unsafe -> DO NOT fake it.

SPLIT DECISION:
  - N1 INSTANT: fully closeable now with NO proto change (gateway ConfirmSetup
    fire-time gate). PROCEED.
  - N2, N3, N4: fully closeable now with NO proto change. PROCEED (S2/S3 done
    + a placement-time best-effort LIMIT gate that is correct within the RSS
    horizon and strictly better than today).
  - N1 LIMIT lifetime re-check: needs proto. Two correct options for the user:
      (a) add gateway RPC CheckNewsWindow + regenerate via `make proto-gen`
          (best, full coverage); OR
      (b) cap LIMIT TTL so a resting order never outlives the calendar horizon
          AND re-check at placement each macro cycle (no proto, but reduces
          max TTL for Swing/Positional LIMIT orders).
  Awaiting user choice for the LIMIT lifetime piece; everything else proceeds.

DECISION UPDATE: user confirmed they CAN run `make proto-gen`. So N1-LIMIT is
closed PROPERLY with a dedicated gateway RPC (full lifetime coverage), not the
within-horizon placement compromise. Only hand-written .proto files are edited
here; generated .pb.go / _grpc.pb.go are regenerated by the user via
`make proto-gen` AFTER these commits. Generated files are NOT hand-edited.

New RPC: gateway.v1 GatewayService.CheckNewsWindow(CheckNewsWindowRequest)
  returns (CheckNewsWindowResponse).
  Request:  symbol, trading_style, trace_id.
  Response: locked (bool), data_available (bool), reason, event_name,
            currency, minutes_until (double).

Wiring:
  - Gateway handler: read calendar via macroCollector (cached), call
    routing.EvaluateNewsWindow with the style-aware window; auth-protected
    like other gateway RPCs.
  - Execution GatewayPort gains CheckNewsWindow; GatewayGRPCClient implements
    it over the new stub.
  - Watcher runLimitTTL: on each 1-min tick, call CheckNewsWindow; if locked,
    cancel the resting broker order (ReasonNewsLockout) and stop. This closes
    the LIMIT lifetime gap regardless of the RSS calendar horizon, because the
    event enters the lockout window as time advances and the macro cache
    refreshes each cycle.
  - check4NewsLockout: STAYS a no-op (calendar lives in the gateway). A LIMIT
    trade reaching execution has already passed the gateway decision-time news
    guard (checkHighImpactEventProximity, currency-aware + fail-closed, fixed
    in S3); re-checking the SAME instant inside execution would be redundant
    (forbidden). Its comment is corrected to state the real, now-complete
    ownership: decision-time guard (gateway) + INSTANT fire-time gate
    (ConfirmSetup) + LIMIT lifetime gate (watcher -> CheckNewsWindow). No
    calendar dependency leaks into execution; the only new execution wiring is
    the watcher's GatewayPort.CheckNewsWindow call.

Revised step plan from here:
  S5 proto: gateway.proto add CheckNewsWindow rpc + request/response messages.
  S6 gateway grpc_server.go: implement CheckNewsWindow handler.
  S7 execution watcher GatewayPort + GatewayGRPCClient: CheckNewsWindow method.
  S8 watcher runLimitTTL: cancel resting order on news lockout (N1 LIMIT).
  S9 execution validator check4NewsLockout: correct the misleading comment to
     reflect the now-complete ownership (no code change; stays pass()).
  S10 final pass: exports.go comment, tracker -> DONE, document the required
     `make proto-gen` regeneration step + build expectations.

Progress marker: COMPLETED S1-S6 (S5 proto CheckNewsWindow; S6 orchestrator
CheckNewsWindow + gateway gRPC handler). NEXT: S7 (execution GatewayPort +
GatewayGRPCClient CheckNewsWindow method).

Pending cleanup for S11: querybuilder/exports.go header comment still says its
consumer is routing/guards.go (checkNewsProximity); the real consumer is now
routing/news.go (EvaluateNewsWindow). Update the comment, do not change code.

Update this table as each fix lands. Each commit references its finding ID.

All five findings landed on branch `audit/execution-management-hardening`.
Next step: open the MR from that branch into `main` and run CI.
