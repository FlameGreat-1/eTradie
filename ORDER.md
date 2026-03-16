I've now read every single file in the gateway codebase (34 files). Here is the complete audit:

---

#### FULL GATEWAY AUDIT REPORT

**Files audited: 34** (cmd/1, collectors/2, config/1, constants/1, container/1, context/1, infra/4, models/6, observability/3, pipeline/3, ports/2, querybuilder/5, routing/2, server/2, symbolstore/1)

---

#### Issue 1: `scheduler.go` uses `math/rand` without seeding (LOW)

`scheduler.go` imports `math/rand` and calls `rand.Int63n()` for jitter. In Go < 1.20, `math/rand` defaults to seed 0, producing identical jitter across instances. In Go 1.20+ (this project uses 1.23), `math/rand` auto-seeds from the runtime, so this is actually fine. **No action needed** for Go 1.23.

---

#### Issue 2: `constants.go` - `PhaseCollectingTA`, `PhaseCollectingMacro` are unused (LOW)

`PhaseCollectingTA` and `PhaseCollectingMacro` are defined but never referenced. The orchestrator uses `PhaseCollectParallel` instead (since TA and Macro are collected in parallel). These are dead constants.

Also: `StageQueryBuilder`, `StageContextAssembly`, `StageGuardEvaluation`, `StageDecisionRouting` are defined but never used in any `GatewayStageErrors.WithLabelValues()` call. Only `StageTACollector`, `StageMacroCollector`, `StageRAGRetrieval`, and `StageProcessorLLM` are actually used.

Also: `StatusSkipped` is defined but never used anywhere.

Also: `GatewayCycleJobID`, `GatewayHealthJobID` are defined but never referenced.

Also: `TAResultCacheKeyPrefix`, `MacroResultCacheKeyPrefix` are defined but never referenced (no caching of TA/Macro results is implemented).

---

#### Issue 3: `engine_http.go` - `min()` function shadows Go 1.21+ builtin (LOW)

The file defines a local `min(a, b int) int` function. Go 1.21+ has a builtin `min()`. Since this project uses Go 1.23, the local function shadows the builtin. It compiles fine but is redundant.

---

#### Issue 4: `GatewayOutput` doesn't include `ExecutionResult` (MEDIUM)

In `router.go`, `RouteResult` has `ExecutionResult map[string]interface{}`. But `models/cycle.go` `GatewayOutput` does NOT have an `ExecutionResult` field. In `orchestrator.go` `processSymbol()`, the `GatewayOutput` is built from `routeResult` but the `ExecutionResult` is silently dropped:

```go
return &models.GatewayOutput{
    // ... no ExecutionResult field
}
```

This means the gRPC `RunCycle` response never includes the execution result (order_id, lot_size, status, etc.). The dashboard calling `RunCycle` cannot see whether the trade was actually placed or what order ID was assigned. The execution result is lost.

---

#### Issue 5: `observability/tracing.go` - `StartSpan`, `SetSpanError`, `ShutdownTracing` are unused (LOW)

These exported functions are defined but never called anywhere in the gateway codebase. The tracing is initialized in `main.go` via `InitTracing()` and the `otelgrpc.NewServerHandler()` in `grpc_server.go` handles span creation automatically. The manual span helpers are dead code.

---

#### Issue 6: `models/ta.go` - `SuccessfulSymbols()` is unused (LOW)

The method is defined on `TAResult` but never called anywhere. `HasCandidates()` is used instead.

---

#### Issue 7: `models/guard.go` - `IsApproved()` is unused (LOW)

The method is defined on `GuardEvaluationResult` but never called. The router checks `guardResult.OverallVerdict == constants.VerdictReject` directly.

---

#### Priority Summary

| Priority | Issue | Description |
|---|---|---|
| **MEDIUM** | #4 | `GatewayOutput` drops `ExecutionResult` - dashboard can't see order placement results |
| **LOW** | #2 | Dead constants: `PhaseCollectingTA`, `PhaseCollectingMacro`, `StatusSkipped`, 4 unused stages, 2 unused job IDs, 2 unused cache prefixes |
| **LOW** | #3 | Local `min()` shadows Go 1.23 builtin |
| **LOW** | #5 | Unused tracing helpers: `StartSpan`, `SetSpanError`, `ShutdownTracing` |
| **LOW** | #6 | Unused `SuccessfulSymbols()` method |
| **LOW** | #7 | Unused `IsApproved()` method |
| **INFO** | #1 | `math/rand` without explicit seed (fine in Go 1.23) |

---

**Issue #4 is the only one that affects correctness.** When the gateway routes a trade to Module B and gets back the execution result (accepted, order_id, lot_size, etc.), that result is currently lost because `GatewayOutput` has no field for it. The gRPC `RunCycle` response to the dashboard is missing the most important piece of information: what happened with the trade.
