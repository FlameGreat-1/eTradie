# Macro Read-Through Durability Fix — Progress Tracker

## Problem (verified, not assumed)

The analysis hot path calls `cot_collector.collect()` (and the other six
collectors) WITHOUT `force_refresh`. `BaseCollector.collect()` deliberately
refuses to hit external APIs on the request path (correct: avoids latency).
On a Redis cache miss it falls back to `_read_from_db()` and then to
`_empty_dataset()`.

VERIFIED defect: EVERY collector's `_read_from_db()` is a stub returning
`None`:
  - cot/collector.py
  - dxy/collector.py
  - intermarket/collector.py
  - central_bank/collector.py
  - calendar/collector.py
  - economic_data/collector.py
  - sentiment/collector.py

So any request-path cache miss (cold cache after deploy/restart, or after
the 600s `cache_ttl` lapses before the scheduler re-warms) returns an EMPTY
dataset. Consequence:
  - COT disappears from the LLM input (`latest_positions=[]` -> extractCOT
    produces nothing). This is the user-reported regression.
  - The SAME failure mode silently degrades DXY, intermarket, central_bank,
    calendar (which the news-protection guard depends on!), economic, and
    sentiment.

Secondary defect: `cot/collector.py::_empty_dataset()` constructs
`COTDataSet(reports=[], sources=[], ...)` — neither field exists on
`COTDataSet`. Pydantic config is `extra='ignore'` (verified in
shared/models/base.py: FrozenModel has no `extra='forbid'`), so it does NOT
raise; it silently produces an empty dataset with the wrong kwargs. Still
wrong/misleading and must be corrected.

## Design (best practice, no API on hot path)

Writer/reader separation (CQRS):
  - WRITER = scheduler via `refresh()` -> `_do_collect()`: fetch APIs,
    enrich, persist, warm Redis. Latency irrelevant (background).
  - READER = analysis cycle via `collect()`: cache -> durable snapshot ->
    empty. No API calls.

The reader must always land on the LAST-GOOD enriched dataset, never empty.
Chosen mechanism: a durable "last-good snapshot" of each collector's final
`model_dump(mode='json')`, persisted by `_do_collect` and rehydrated by
`_read_from_db` through `cache_model`. This returns the BYTE-IDENTICAL
enriched dataset the writer produced (no per-collector SQL reassembly =
no drift, no DB/logic mix-up), survives Redis flush + restart, and is a
single indexed read (blazing fast).

## Step plan (each = one commit)

- [x] S0  Tracker (this file).
- [ ] S1  macro_snapshot schema (SQLAlchemy table) + Alembic migration.
- [ ] S2  MacroSnapshotRepository (get_latest_json / upsert_json by namespace).
- [ ] S3  BaseCollector: inject snapshot repo; add _persist_snapshot() +
          generic _read_from_db() default that rehydrates via cache_model;
          call _persist_snapshot() in the success path.
- [ ] S4  Wire snapshot persistence into each _do_collect (or centralise in
          base) for all 7 collectors; remove the 7 stub _read_from_db.
- [ ] S5  Fix cot _empty_dataset() (valid fields) + audit all 7 empties.
- [ ] S6  Container/DI: pass the snapshot repo/db into collectors.
- [ ] S7  Eager cache warm on engine startup (one refresh per collector)
          so the first post-deploy cycle never hits a cold cache.
- [ ] S8  Tests: request-path miss returns last-good snapshot (not empty)
          for COT + one market-data collector + calendar.
- [ ] S9  Final consistency pass; update this tracker -> DONE.

## Progress marker

COMPLETED: S0.
NEXT: S1 (schema + migration).
