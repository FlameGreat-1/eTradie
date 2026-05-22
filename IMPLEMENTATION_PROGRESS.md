# LLM Structured Output Refactor — Progress Tracker

Branch: `feat/llm-structured-output`
Full design and decisions live in `PROBLEM.md` (the conversation log).
This file tracks commit-by-commit progress so the plan survives a chat reset.

---

## Phase 1 — Foundation modules (DONE)

Commit message starts with `feat(processor/llm): foundation`.

- [x] `src/engine/processor/llm/errors.py` — typed LLM failures.
      Classes: `LLMError`, `LLMTruncatedError`, `LLMSchemaViolationError`,
      `LLMSafetyFilterError`, `LLMRateLimitedError`, `LLMTransientError`,
      `LLMStructuredOutputUnsupportedError`. All subclass `ProcessorError`
      so existing `except ProcessorError` paths keep working.

- [x] `src/engine/processor/llm/capabilities.py` —
      per-(provider, model) capability lookup driven by `MODEL_CATALOG.group`.
      No hardcoded model-name string matches anywhere.

- [x] `src/engine/processor/llm/reasoning.py` — `ReasoningBudget` value
      object + `resolve_reasoning_budget()`. One operator knob mapped to
      per-provider native parameter.

- [x] `src/engine/processor/llm/schema_compiler.py` — provider-native
      JSON schema compilation from `AnalysisOutput`. `$ref` inlining,
      `Optional` → `nullable`, OpenAI strict mode pass, Gemini
      `additionalProperties` pruning. Cached per provider.

---

## Phase 2 — Wire structured output into all 4 providers (PENDING)

- [ ] `src/engine/processor/llm/providers/gemini.py`:
      add `response_mime_type='application/json'` + `response_schema=<compiled>`
      + `thinking_config=ThinkingConfig(thinking_budget=N)` (when active)
      to the existing `stream_call`. SSE dashboard feed shape unchanged.

- [ ] `src/engine/processor/llm/providers/anthropic.py`:
      switch `stream_call` decision path to forced tool use
      (`tools=[{name:'emit_analysis', input_schema:<compiled>}]`,
      `tool_choice={type:'tool', name:'emit_analysis'}`). Stream the
      `input_json_delta` deltas as the `reasoning_chunk` SSE frames.
      Add `thinking={type:'enabled', budget_tokens:N}` when active.

- [ ] `src/engine/processor/llm/providers/openai_provider.py`:
      add `response_format={type:'json_schema', json_schema:{name:'AnalysisOutput', schema:<compiled>, strict:true}}`
      and `reasoning_effort=R` (when active, o-series only) to `stream_call`.

- [ ] `src/engine/processor/llm/providers/openai_compatible.py`:
      send `response_format` best-effort. On provider rejection,
      raise `LLMStructuredOutputUnsupportedError` so the service falls
      back to the hardened free-text path.

- [ ] `src/engine/processor/service.py`:
      remove `output_tokens += 1` chunk-counter masquerade.
      Use `usage_metadata` only. Translate provider exceptions to typed
      `LLMError` subclasses.

- [ ] `src/engine/processor/llm/client.py`:
      no signature change required (the schema enforcement happens
      inside each provider's existing `stream_call` so the abstract
      interface stays identical).

---

## Phase 3 — Parser hardening, typed-error routing, reasoning-budget config (PENDING)

- [ ] `src/engine/processor/parsing/response_parser.py`:
      add `_coerce_null_collections` pre-validation pass for the
      fallback path so a self-hosted endpoint that emits
      `"bounds": null` for a `list[float]` field is still accepted.
      Only used when structured output is unavailable.

- [ ] `src/engine/processor/config.py`:
      add `reasoning_budget_tokens: Optional[int]` field. Default `None`.

- [ ] `src/engine/routers/internal.py`:
      map `LLMTruncatedError | LLMSchemaViolationError | LLMSafetyFilterError`
      to a structured 422 (per-symbol analysis-unavailable). Keep generic 500
      for unexpected `Exception`. Preserve current `QuotaExceededError → 429`
      branch.

- [ ] `src/engine/processor/prompts/system_prompt.py`:
      append one-line note below the existing schema block:
      "Output schema is enforced by the LLM provider when supported;
      field semantics above remain authoritative." Schema block itself
      unchanged. The 70-line `_OUTPUT_SCHEMA` constant is preserved.

---

## Phase 4 — Contract tests + MR (PENDING)

- [ ] `tests/processor/llm/schema_compiler.py`:
      compile schema for each provider, validate a round-trip
      `AnalysisOutput → model_dump_json → schema validate` is clean.

- [ ] `tests/processor/llm/capabilities.py`:
      every model in `MODEL_CATALOG` resolves, unknown model returns
      permissive default, thinking-group default reasoning budget is
      applied when operator knob is unset.

- [ ] Open MR `feat/llm-structured-output → main`.

---

## Files explicitly NOT modified (confirmed safe by code reading)

- `src/engine/processor/models/analysis.py` — Pydantic source of truth.
- `src/engine/processor/models/io.py` — `ProcessorInput`/`ProcessorOutput`
  gateway contract.
- `src/engine/processor/mapping/output_mapper.py`, `dashboard_formatter.py`.
- `src/gateway/internal/models/processor.go` and everything downstream
  (Module B / Execution / Management).
- `proto/engine/v1/engine.proto`.
- `src/engine/processor/llm/retry.py` — already correct; only
  classification is tightened in Phase 3 if needed.
