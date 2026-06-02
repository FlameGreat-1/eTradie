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
- [ ] **Step 1** – Envoy: dedicated no-retry, long-timeout route for the
      non-idempotent analysis POSTs (`/api/v1/cycle/run`,
      `/api/analysis/rerun`); raise catch-all route timeout/per-try above
      worst-case cycle; drop `cancelled` from local `retry_on`. Both
      local and production configs.
- [ ] **Step 2** – Gateway HTTP server: align `WriteTimeout` with the
      real cycle budget so a long analysis response is not killed by the
      server write deadline.
- [ ] **Step 3** – Engine idempotency: honour `X-Idempotency-Key` on
      `/internal/processor/process` with a short-TTL Redis dedupe so a
      duplicate processor call returns the first result instead of
      re-billing the LLM. Gateway adapter forwards the key.
- [ ] **Step 4** – Gateway cancellation propagation: `RunCycle` /
      `processSymbol` honour the inbound request context so an abandoned
      connection cancels the LLM call.

## Notes

- All timeout changes are kept coherent end-to-end: Envoy route timeout
  ≥ gateway `WriteTimeout` ≥ `CycleTimeoutSeconds` + margin.
- No behavioural change to the analysis logic itself; only the
  transport/idempotency/cancellation layers are corrected.
