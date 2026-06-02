# Duplicate LLM-call / repeated analysis-cycle fix

## Summary

A single `POST /api/v1/cycle/run` (the dashboard "Run Analysis" button)
results in **multiple full analysis cycles**, each making its own LLM
call, for one user click. The TA + Macro + RAG collection runs once
(served from cache on the repeats); only the processor/LLM phase
repeats, which is why the Thinking Terminal visibly streams a response,
clears, and re-streams. This wastes LLM tokens and quota.

## Verified evidence

Gateway logs for one click showed **two** `dashboard_run_cycle_triggered`
events and **two** `cycle_finished` events with **distinct trace_ids**,
both `attempt: 1`, `will_retry: false`:

- Cycle 1 (`f970f8c4...`): full TA (~56s) + LLM, `TRADE_APPROVED`,
  total ~139s.
- Cycle 2 (`0516d529...`): fired ~64ms after cycle 1 finished, TA+macro
  from cache, processor LLM -> Gemini 429 quota exhausted ->
  `PIPELINE_ERROR`.

The browser issued **one** request that stayed pending until everything
(including the repeat) finished, then showed a single 200.

`attempt: 1` on both cycles rules out the gateway cycle-retry loop
(`runSingleAttempt`). Three distinct prompt-dump directories with three
trace_ids rule out the engine's in-process `retry_llm_call` (which
retries inside one `process()` call and dumps the prompt only once).
The duplication is therefore **repeated top-level `process()` calls**
driven from above the gateway handler.

## Root causes (all addressed)

1. **Envoy route timeout + retry** (`src/envoy/config/local/envoy-local.yaml`,
   `src/envoy/config/production/envoy-production.yaml`): the catch-all
   route to `gateway_cluster` uses `timeout: 30s` and
   `per_try_timeout: 10s` with `num_retries: 2`/`3`. A ~139s cycle blows
   the per-try budget on every attempt, so Envoy abandons and **replays
   the same POST upstream** while the gateway keeps running the orphaned
   cycle. Local `retry_on` even includes `cancelled`. (Envoy runs only
   under `docker compose --profile edge` locally, but is always in path
   in production.)

2. **Gateway `http.Server` write deadline** (`src/gateway/internal/server/http_server.go`):
   `WriteTimeout: 120s` is below `CycleTimeoutSeconds` (450s) and below
   the observed 139s cycle, so the HTTP response is killed mid-flight
   even with no proxy in the path.

3. **No idempotency on the processor endpoint** (`src/engine/routers/internal.py`,
   `src/gateway/internal/infra/processor_http.go`): the gateway mints an
   `X-Idempotency-Key` per call but the engine never reads it, so a
   duplicate `/internal/processor/process` re-bills the LLM.

4. **No client-cancellation propagation** (`src/gateway/internal/pipeline/orchestrator.go`):
   an abandoned request orphans a full LLM run instead of stopping.

## Remediation steps & status

- [x] **Step 0** – Tracking doc (this file).
- [x] **Step 1** – Envoy: dedicated no-retry, long-timeout route for the
      non-idempotent analysis POSTs (`/api/v1/cycle/run`,
      `/api/analysis/rerun`); raise catch-all route timeout/per-try above
      worst-case cycle; drop `cancelled` from local `retry_on`. Both
      local and production configs. (commit: envoy no-retry analysis POSTs)
- [x] **Step 2** – Gateway HTTP server: `WriteTimeout: 0` (duration
      bounded by the orchestrator per-cycle context instead) +
      `ReadHeaderTimeout: 10s` slow-loris guard, so a long analysis
      response is not killed by the server write deadline.
      (commit: gateway WriteTimeout)
- [x] **Step 3** – Engine idempotency. COMPLETE:
      - Wired into `service.py` via `_execute_guarded` (thin wrapper;
        `_execute` unchanged). check_cached -> acquire (single-flight)
        -> run `_execute` + store_result + release-in-finally; duplicate
        path awaits the owner's result or raises
        `LLMDuplicateSuppressedError`. Guard skipped when cache/user_id
        absent. (commit: wire idempotency guard)
      Scaffolding (earlier commits):
      - `src/engine/processor/idempotency.py` (single-flight + result
        cache, keyed on sha256(user_id:symbol:prompt_hash), fail-open).
      - `LLMDuplicateSuppressedError` in `llm/errors.py`.
      - 409 `llm_duplicate_suppressed` mapping in `routers/internal.py`.
      REMAINING (wiring into `service.py::_execute`):
        1. Imports: `ProcessorIdempotency`, `compute_digest`,
           `LLMDuplicateSuppressedError`.
        2. After `prompt_hash = compute_prompt_hash(...)` (and the
           prompt dump): if `self._cache` is set, build the guard,
           `digest = compute_digest(user_id=..., symbol=..., prompt_hash=...)`.
           - `cached = await guard.check_cached(digest, trace_id=...)`;
             if not None -> `return cached` (skip LLM entirely).
           - `handle = await guard.acquire(digest, trace_id=...)`.
             If `handle is None` (duplicate): `owner_result =
             await guard.await_result(digest, trace_id=...)`; if not
             None `return owner_result`, else raise
             `LLMDuplicateSuppressedError(...)`.
        3. Wrap the post-acquire body (metering -> LLM -> parse -> map)
           in `try/finally`; in `finally` call `await guard.release(
           handle, trace_id=...)` when `handle` is not None. This MUST
           release on every exit (success, truncation raise, parse
           raise, BYOK quota raise) so the single-flight lock never
           blocks a legitimate retry for the lock TTL.
        4. Immediately before `return processor_output` (success path,
           status SUCCESS or NO_SETUP), call
           `await guard.store_result(digest, processor_output,
           trace_id=...)`. NEVER store on an error path.
        NOTE: the safe way to add the try/finally without a fragile
        400-line string edit is to extract the metering->map core of
        `_execute` into a private `_run_pipeline(...)` helper and have
        `_execute` call it inside the guard's try/finally. Implement via
        a full, verified rewrite of `_execute` + new helper, not blind
        partial edits.
        The gateway already mints `X-Idempotency-Key` per call
        (`engine_http.go`); no gateway change is required for Step 3
        because the dedupe key is derived server-side from the prompt,
        which is strictly stronger (covers distinct-cycle duplicates,
        not just same-request replays).
- [x] **Step 4** – Gateway cancellation propagation. COMPLETE:
      Context already propagated end-to-end (handleRunCycle ->
      RunCycle -> executePipeline -> processSymbol -> processor.Process
      -> engine PostJSONNoRetry via http.NewRequestWithContext). Added a
      parent-cancellation branch in `runSingleAttempt`: when `ctx.Err()`
      is set (client/proxy disconnected) the cycle stops with no retry
      and no spurious CYCLE_FAILED alert, distinct from the cycle's own
      DeadlineExceeded (still retryable). (commit: stop cleanly on
      client cancellation)

## Current branch state (fix/duplicate-llm-cycle-calls)

Shipped and verified:
  - Step 0: tracking doc.
  - Step 1: Envoy local + production — no-retry long-timeout routes for
    `/api/v1/cycle/run` and `/api/analysis/rerun`; hardened catch-all.
  - Step 2: gateway `http.Server` WriteTimeout 0 + ReadHeaderTimeout 10s.
  - Step 3 scaffolding: `idempotency.py`, `LLMDuplicateSuppressedError`,
    router 409 mapping.

Not yet wired (do next, in order):
  - Step 3 wiring into `service.py::_execute` per the exact plan above.
    Implement by extracting the metering->LLM->parse->map core into a
    new `_run_pipeline(...)` and calling it from `_execute` inside the
    idempotency guard's try/finally. Verify the full method compiles
    and preserves every existing raise path (BYOK quota, truncation,
    parse) before committing. Do NOT in-place-wrap with a 380-line
    re-indent.
  - Step 4: gateway cancellation propagation verification/fix.

## Notes

- All timeout changes are kept coherent end-to-end: Envoy route timeout
  ≥ gateway `WriteTimeout` ≥ `CycleTimeoutSeconds` + margin.
- No behavioural change to the analysis logic itself; only the
  transport/idempotency/cancellation layers are corrected.
