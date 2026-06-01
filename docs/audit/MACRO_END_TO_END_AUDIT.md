# Macro subsystem end-to-end audit

Scope: every file in the macro path, both engine (Python) and gateway (Go),
read directly (not from memory): 8 providers, 7 collectors + base, all
collector/provider models, central_bank schema + repository, macro_snapshots
schema + repository, provider registry, base provider, startup/lifespan,
engine `/internal/macro/collect`, gateway MacroCollector + macro_extractor +
builder + query_text + assembler + MacroResult model, processor prompt builder.

## Verdict

The core path is structurally sound and correctly wired end to end:

```
providers -> collectors (read-through cache + single-flight + durable snapshot)
  -> engine /internal/macro/collect (model_dump)
  -> gateway MacroCollector (Redis-cached opaque maps)
  -> ExtractMacroSignals (RAG flags) + buildMacroSection (full opaque payload)
  -> RAG query (query_text + flags) -> processor build_user_message -> LLM
```

Verified correct and intentionally left unchanged:
- All 7 collectors write cache + persist durable snapshot; valid `_empty_dataset`.
- `refresh()` (writer) drives scheduler + startup warmup; `collect()` (reader)
  never hits an external API on the hot path (cache -> snapshot -> empty).
- Rate data drives `HasRateChange` -> `HasRateDecision` -> `rule_first` RAG
  strategy and the `"{bank} rate {direction}"` query term: actionable, not just
  present.
- Gateway forwards the full `central_bank` map (incl. the multi-year
  `rate_decisions` history) to the LLM untouched.

## Findings and remediations

### A. Intermarket `correlation_signals` was DB-only (MEDIUM) — FIXED
`IntermarketCollector._compute_correlation_signals` produced yield-curve
slope/inversion, VIX regime, and iron-ore (AUD) / dairy (NZD) proxy signals and
persisted them to `intermarket_snapshots.correlation_signals_json`, but the
`MarketDataSet` dataset carried only raw snapshots, so they never reached the
cache, snapshot, gateway, or LLM. Added `MarketDataSet.correlation_signals`
and populated it in the collector; it now flows to the LLM via the opaque
`intermarket` map. (Gateway `extractIntermarket` already derives yield-curve
inversion from raw yields for RAG, so it was intentionally NOT duplicated.)

### B. ProviderRegistry was dead infrastructure (MEDIUM) — FIXED
Every provider was `register()`ed but nothing called `get`/`get_by_category`/
`health_check_all`/`disable`/`enable`, so the `ACTIVE_PROVIDERS` gauge was never
updated and operators had no provider-health visibility. Added
`GET /health/providers` (mirrors `/health/rag`) which calls
`registry.health_check_all()` — returning per-provider status and, as a side
effect, refreshing the `ACTIVE_PROVIDERS` gauge per category. Registry is now
live; analysis path unchanged.

### C. `rate_change_bps` dropped on the DB path (LOW) — FIXED
`RateDecision.rate_change_bps` reached the LLM via the cached dataset but had
no column on `central_bank_events`, so the collector dropped it when persisting.
Added the nullable `rate_change_bps` column (migration 0032, idempotent like
0031), mapped it on the ORM row, and wrote it in the collector upsert. Existing
rows backfill NULL (unknown) which is correct.

### D. central_bank_events dedup key uses empty `title` for rate decisions (LOW) — DOCUMENTED, NOT CHANGED
Unique key is `(bank, title, event_timestamp)` and `RateDecision.title` is `""`.
Safe in practice: different banks never collide (bank differs); same bank's
decisions have distinct `decision_date`s; RSS events always carry a non-empty
title. Changing the constraint requires a migration that risks live data for no
real-world collision, so it is deliberately left as-is. Re-evaluate only if a
future title-less, same-timestamp, same-bank event type is added.

### E. Naming overlap `has_rate_decision` vs `rate_decisions` (LOW) — DOCUMENTED, NOT CHANGED
`has_rate_decision` (gateway calendar flag) = "a rate decision is scheduled in
the event-risk window"; `rate_decisions` (central_bank) = "the actual rate data".
Different concepts, similar names; both correct. No code change — renaming the
RAG flag would churn the proto/RAG contract for zero behavioural gain.
