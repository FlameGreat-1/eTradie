# LLM Structured Output Refactor — Progress Tracker

Branch: `feat/llm-structured-output`
Full design and decisions live in `PROBLEM.md` (the conversation log).

---

## Phase 1 — Foundation modules (DONE)

- [x] `src/engine/processor/llm/errors.py` — typed LLM failures.
      Classes: `LLMError`, `LLMTruncatedError`, `LLMSchemaViolationError`,
      `LLMSafetyFilterError`, `LLMRateLimitedError`, `LLMTransientError`,
      `LLMStructuredOutputUnsupportedError`. All subclass `ProcessorError`.

- [x] `src/engine/processor/llm/capabilities.py` — per-(provider, model)
      capability lookup driven by `MODEL_CATALOG.group`.

- [x] `src/engine/processor/llm/reasoning.py` — `ReasoningBudget` +
      `resolve_reasoning_budget()`.

- [x] `src/engine/processor/llm/schema_compiler.py` — provider-native
      JSON schema compilation from `AnalysisOutput`. Cached per provider.

---

## Phase 2 — Wire structured output into all 4 providers (DONE)

- [x] `src/engine/processor/llm/providers/gemini.py` —
      `response_mime_type` + `response_schema` + `thinking_config`.
- [x] `src/engine/processor/llm/providers/openai_provider.py` —
      `response_format={type:'json_schema', strict:true}` + `reasoning_effort`.
- [x] `src/engine/processor/llm/providers/anthropic.py` — forced
      tool-use + `thinking={enabled, budget_tokens}`.
- [x] `src/engine/processor/llm/providers/openai_compatible.py` —
      best-effort `response_format` with latched fallback probe.
- [x] `src/engine/processor/service.py` — removed chunk-counter token
      masquerade; usage_metadata is now the only token source.

---

## Phase 3 — Parser hardening, typed-error routing, reasoning-budget config, prompt note (DONE)

- [x] `src/engine/processor/parsing/response_parser.py` —
      `_coerce_null_collections` pre-validation pass for the fallback
      path (None -> [] on the AnalysisOutput list fields).
- [x] `src/engine/processor/config.py` —
      `reasoning_budget_tokens: Optional[int]` operator knob.
- [x] `src/engine/routers/internal.py` — `LLMTruncatedError |
      LLMSchemaViolationError | LLMSafetyFilterError |
      LLMRateLimitedError` -> 422 per-symbol; `ProcessorInsufficientDataError`
      -> 400; preserved `QuotaExceededError` -> 429; everything else -> 500.
- [x] `src/engine/processor/prompts/system_prompt.py` — single-line note
      above the schema block. Schema block itself untouched.

---

## Phase 4 — Open MR (DONE)

- [x] Open MR `feat/llm-structured-output -> main`.

---

## Files explicitly NOT modified (verified safe by code reading)

- `src/engine/processor/models/analysis.py` — Pydantic source of truth.
- `src/engine/processor/models/io.py` — `ProcessorInput`/`ProcessorOutput`
  gateway contract.
- `src/engine/processor/mapping/output_mapper.py`, `dashboard_formatter.py`.
- `src/gateway/internal/models/processor.go` and everything downstream
  (Module B / Execution / Management).
- `proto/engine/v1/engine.proto`.
- `src/engine/processor/llm/client.py` — abstract interface unchanged.
- `src/engine/processor/llm/factory.py` — construction unchanged.
- `src/engine/processor/llm/retry.py` — already correct.

## What stays exactly the same end-to-end

- The system prompt text (every word). Only a single informational line
  added above the embedded schema block.
- The dashboard SSE feed (`status` / `reasoning_chunk` / `final`).
- One LLM call per analysis (no extra calls, no double cost).
- The Pydantic `AnalysisOutput` model and every field on it.
- The Go `ProcessorOutput` contract and the proto.
- Module B, Execution, Management.
