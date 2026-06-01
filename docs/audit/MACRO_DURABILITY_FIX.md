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

## Additional verified root cause (scheduler vs cache TTL)

Scheduler intervals (engine/macro/scheduler_jobs.py + main.py) bind to
`refresh()` and are LONG: COT/sentiment 604800s (7d), intermarket 86400s
(1d), dxy 14400s (4h). The Redis `cache_ttl` is far shorter. So between
scheduler runs the request-path `collect()` almost always cache-misses ->
old `_read_from_db` returned None -> empty dataset. The durable snapshot
bridges this gap: the scheduler writes it on each (infrequent) refresh and
every miss in between serves it.

Second half: the lifespan startup warmup called `collect()` (read-through),
so on a COLD start it warmed NOTHING real (no cache, no snapshot) and the
first true fetch waited for the scheduler interval. Fixed in S7 by warming
with `refresh()`.

## Step plan (each = one commit)

- [x] S0  Tracker (this file).
- [x] S1  macro_snapshots schema + register + migration 0031.
- [x] S2  MacroSnapshotRepository (get_payload / upsert_payload).
- [x] S3  BaseCollector: _persist_snapshot() + generic snapshot-backed
          _read_from_db(); persist on collect() + refresh() success;
          datetime/UTC import fix.
- [x] S4  Removed all 7 stub _read_from_db overrides (inherit base).
- [x] S5  Fixed cot _empty_dataset() (was reports=/sources= -> valid
          COTDataSet()); audited all 7 empties (valid).
- [x] S6  DI: collectors already receive self._db; no change needed
          (verified in dependencies.py _build_collectors).
- [x] S7  Startup warmup switched collect() -> refresh() so a fresh
          deploy fetches + persists snapshot at boot.
- [x] S8  Tests: tests/macro/collectors/test_read_through_durability.py
          (cache-miss-serves-snapshot, dict path, cold-start-empty,
          refresh-persists, cot _empty_dataset valid). asyncio_mode=auto.
- [ ] S9  Final consistency pass + open MR; verify diffs; tracker -> DONE.

## Progress marker

COMPLETED: S0-S8.
NEXT: S9 (open MR, verify all diffs landed, run engine test + alembic).

## S9 verification checklist (must confirm before marking DONE)
- macro_snapshots migration 0031 chains from 0030 (latest) -> yes.
- collectors construct with self._db already (no DI change) -> yes.
- scheduler refresh() persists snapshot via base success path -> yes.
- startup warmup uses refresh() not collect() -> yes (S7).
- all 7 _read_from_db stubs removed -> yes (S4).
- cot _empty_dataset valid COTDataSet -> yes (S5).
- base.py imports datetime/UTC and MacroSnapshotRepository -> yes (S3).
- gateway side (MacroResult.COT -> buildMacroSection 'cot' -> extractCOT
  'latest_positions') unchanged and already correct -> yes.

Key files changed:
  - src/engine/macro/storage/schemas/snapshot.py (new)
  - src/engine/macro/storage/schemas/__init__.py (register)
  - src/engine/shared/db/migrations/versions/0031_macro_snapshots.py (new)
  - src/engine/macro/storage/repositories/snapshot/snapshot.py (new)
  - src/engine/macro/collectors/base.py (persist + read-through + imports)
  - src/engine/macro/collectors/{cot,dxy,intermarket,calendar,
    economic_data,sentiment,central_bank}/collector.py (drop stub)
  - src/engine/main.py (warmup refresh)
