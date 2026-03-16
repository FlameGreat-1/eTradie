

I have examined Part 3 thoroughly from beginning to end.

#### What Needs Updating

**`rerun_analysis`** - Step 3 (RAG retrieval) calls `retrieve_context()` with only `symbol` and `trace_id`. It does NOT pass any of the enriched macro signal flags. This is a dashboard rerun endpoint that bypasses the Go gateway, so it needs to derive these flags from the TA and macro results it already has in-hand (Steps 1 and 2). Currently it's a bare-bones RAG call with no context about what macro/TA data is available.

#### What Does NOT Need Changes

- **`get_available_models`** - Processor config endpoint, no macro changes
- **`get_processor_config`** - Processor config endpoint, no macro changes
- **`update_processor_config`** - Processor config hot-swap, no macro changes
- **`metrics_app` mount** - Fine
- **`return app`** - Fine

#### Summary of ALL Changes Needed Across All 3 Parts

1. **`InternalRAGRequest`** (Part 1) - Add new fields: `has_qe_qt`, `has_stagflation`, `has_cot_extremes`, `has_tff_data`, `has_core_inflation`, `has_safe_haven_elevated`, `has_commodity_currencies_weak`, `dxy_momentum`, `risk_environment`
2. **`internal_rag_retrieve`** (Part 2) - Pass the new fields through to `retrieve_context()`
3. **`rerun_analysis`** (Part 3) - Step 3 RAG call needs to derive and pass the enriched macro flags from the TA/macro results collected in Steps 1 and 2

That's 3 precise locations. Everything else in the 3 parts stays exactly as-is.

Waiting for your permission.




Yes, exactly 3 locations:

1. **`InternalRAGRequest` class** - add the new fields to the Pydantic schema
2. **`internal_rag_retrieve` function** - pass those new fields to `retrieve_context()`
3. **`rerun_analysis` function** - derive the enriched flags from TA/macro results and pass them to `retrieve_context()`

Everything else in the entire `main.py` stays untouched.