

Let me answer each question precisely by examining the actual code.

#### 1. Is `MaxConcurrentSymbols` dead code?

Looking at the Go codebase, `MaxConcurrentSymbols` is defined in `config.go` and validated (must be 1-16), but let me search every file that references it:

- `config.go`: defines and validates it
- `ta_collector.go`: does NOT reference it
- `orchestrator.go`: does NOT reference it
- `container.go`: does NOT reference it

**Yes, it is dead code in the Go gateway.** The old Python `TACollector` used it as `asyncio.Semaphore(self._config.max_concurrent_symbols)` to limit how many symbols were analyzed concurrently. The Go gateway sends all symbols in a single HTTP call to `/internal/ta/analyze` and the Python endpoint processes them sequentially in a `for` loop. The config field serves no purpose.

However, **do not remove it yet.** It's a valid configuration concept that should be wired up. When 8 symbols are selected and each needs a full LLM call (phases 2-6), processing them sequentially is slow. The orchestrator's `executePipeline()` loop should use this config to process symbols with bounded concurrency using goroutines. But that's an enhancement, not a bug fix. For now it's harmless dead config. Removing it would be premature since it should be implemented, not deleted.

#### 2. Do default symbols still work?

Yes. `DefaultSymbols` is NOT related to `MaxConcurrentSymbols`. They are completely separate config fields.

`DefaultSymbols` is used by `symbolstore.Store`:
```go
func NewStore(redis *infra.RedisClient, cfg *config.Config) *Store {
    return &Store{
        redis:          redis,
        defaultSymbols: cfg.DefaultSymbols,  // ← used here
    }
}
```

When `GetActiveSymbols()` finds nothing in Redis (user hasn't selected anything yet), it falls back to `s.copyDefaults()` which returns a copy of `cfg.DefaultSymbols`. This works correctly. The Python `RedisSymbolReader` has the same 8 defaults as a fallback on its side too.

**Default symbols work perfectly.** ✅

#### 3. What happens after `CycleTimeoutSeconds` (300s) is hit?

The exact code in `orchestrator.go` `RunCycle()`:

```go
cycleCtx, cancel := context.WithTimeout(ctx, time.Duration(o.cfg.CycleTimeoutSeconds)*time.Second)
defer cancel()

result, err := o.executePipeline(cycleCtx, tracker, symbols)
if err != nil {
    if cycleCtx.Err() == context.DeadlineExceeded {
        tracker.Fail(
            fmt.Sprintf("Cycle timed out after %ds", o.cfg.CycleTimeoutSeconds),
            "cycle_timeout", true,
        )
        observability.GatewayStageErrors.WithLabelValues("cycle", "timeout").Inc()
        o.log.Error().
            Str("cycle_id", tracker.CycleID()).
            Int("timeout_seconds", o.cfg.CycleTimeoutSeconds).
            Str("phase_reached", tracker.Phase().String()).
            Str("trace_id", tracker.TraceID()).
            Msg("cycle_timed_out")
    }
    outputs = append(outputs, buildErrorOutput(tracker))
    return
}
```

When the timeout fires, here is exactly what happens:

1. **Go's `context.WithTimeout` cancels `cycleCtx`**. This propagates to every in-flight HTTP call because all sub-operations use `cycleCtx` or child contexts derived from it.

2. **If the timeout hits during the TA or Macro HTTP call** (Phase 1): The `EngineHTTPClient.PostJSON()` uses `http.NewRequestWithContext(ctx, ...)` so the HTTP request is cancelled. The Python side receives a broken connection. The Go goroutine returns an error. `executePipeline()` returns the error.

3. **If the timeout hits during the RAG HTTP call** (Phase 3): Same mechanism. The `retrieveRAG()` call uses `ragCtx` which is a child of `cycleCtx`, so it's cancelled.

4. **If the timeout hits during the Processor LLM HTTP call** (Phase 5): Same. The `processor.Process()` call uses `procCtx` which is a child of `cycleCtx`.

5. **If the timeout hits during Guards** (Phase 6): Guards are local Go code (no HTTP), so they complete almost instantly. Unlikely to be the bottleneck.

6. **The tracker records**: `status = TIMED_OUT`, `outcome = PIPELINE_ERROR`, `phase_reached = whatever phase was active when timeout hit`, `error = "Cycle timed out after 300s"`, `error_stage = "cycle_timeout"`.

7. **Metrics are recorded**: `GatewayStageErrors` counter incremented with `stage=cycle, error_type=timeout`. `GatewayCycleDuration` histogram records the elapsed time. `GatewayCycleTotal` counter incremented with `status=TIMED_OUT, outcome=PIPELINE_ERROR`.

8. **A `GatewayOutput` is returned** with the error details. If this was a scheduled cycle, the output is logged and the scheduler moves on. If this was a gRPC `RunCycle` call from the dashboard, the error output is returned to the caller.

9. **Any symbols that were already fully processed before the timeout** are lost. The code does `outputs = append(outputs, buildErrorOutput(tracker))` which replaces whatever partial results existed. So if 3 out of 5 symbols completed successfully but the 4th timed out, all 3 successful results are discarded and only the error output is returned.

10. **The next scheduled cycle runs normally** at the next interval tick. The timeout does not affect future cycles.

**In short: timeout kills the entire cycle, cancels all in-flight HTTP calls, records error metrics, returns an error output, and the system moves on to the next cycle.**



1. SHOULDN'T WE WIRE THE MaxConcurrentSymbols SINCE IT'S BETTER BEST PRACTICE OR IS IT NOT?

2. FOR THE  CycleTimeoutSeconds, SHOULDN'T WE APPLY RETRY AND EXPONENTIAL BACKOFF? BECAUSE IF IT JUST KILLS EVERYTHING AT FIRST ATTEMPT IT MEANS NOTHING WILL BE DONE TILL THE NEXT CYCLE OF ANALYSIS