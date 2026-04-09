

#### Problem

The `app_client` fixture boots the full FastAPI app (including loading the 250MB sentence_transformers model at ~22s per load) once per test function. 28 API integration tests = 28 app boots = ~10 minutes of wasted model loading.

#### Optimization

Upgrade `pytest-asyncio` from `0.25.3` to `0.26+` which supports `loop_scope="session"` directly on the fixture decorator:

```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def app_client() -> AsyncGenerator[AsyncClient, None]:
```

Then make `seeded_client` a `yield` fixture that deletes its seed rows after each test to prevent data leaks across the shared app instance.

No changes to `pyproject.toml` needed. No manual `event_loop` fixture needed. The newer `pytest-asyncio` handles it cleanly.







**The current system uses polling (request/response), not streaming.** Every single data fetch is a REQ/REP (request/reply) pattern:

#### Historical Candles (TA Analysis)
**Polling.** The `scheduler_jobs.py` runs `_candle_refresh()` on a timer interval (based on the smallest HTF timeframe, typically every 60 minutes). Each call sends a `CANDLES` command via ZMQ REQ/REP to the EA, which calls `CopyRates()` and returns the data. This is a one-shot request, not a stream.

#### Tick Prices (Execution Watcher)
**Polling.** The Go `watcher/manager.go` polls tick prices on a configurable interval (`EXECUTION_WATCHER_POLL_INTERVAL_MS=500`, so every 500ms). Each poll sends an HTTP GET to `/internal/broker/tick_price`, which calls `ZmqClient.get_tick_price()`, which sends a `TICK_PRICE` REQ/REP command to the EA, which calls `SymbolInfoTick()`.

#### Tick Prices (Trade Management)
**Polling.** The Go `monitoring/worker.go` polls tick prices on a configurable interval (`tickPollMs`) per open trade. Same chain: HTTP GET -> Python bridge -> ZMQ REQ/REP -> EA `SymbolInfoTick()`.

#### Why this matters

The ZeroMQ REQ/REP pattern means every tick price requires a full round trip: Go -> HTTP -> Python -> ZMQ -> EA -> ZMQ -> Python -> HTTP -> Go. Over a network (Linux machine to VPS), each round trip adds latency from the TCP connection.

**Quote streaming (ZMQ PUB/SUB)** would be different: the EA would continuously push tick updates to subscribers without being asked. This eliminates the request overhead and gives you every tick as it happens, not just the ones you poll for. You'd never miss a tick between polls.

**For your system specifically**, the polling approach works because:
- TA analysis doesn't need every tick, just periodic candle snapshots
- The Execution watcher polls at 500ms which is fast enough for zone entry detection
- The Management worker polls at its configured interval for SL/TP monitoring

**But** if you want faster execution (detecting zone entries within milliseconds instead of 500ms) or more accurate trade management (catching exact SL/TP levels instead of polling), streaming would be the upgrade path. That would require adding a ZMQ PUB socket to the EA alongside the existing REP socket, and a SUB client on the Python side.









MACRO GAPS THAT NEEDS TO BE ADDRESSED:

Indicator breadth for non-US: TE covered PMI, retail sales, trade balance, consumer confidence, housing, manufacturing for all 8 currencies. OECD currently covers GDP, CPI, Core CPI, unemployment. Missing: PMI, retail sales, trade balance, PPI for non-US.

US Treasury yields (2Y, 10Y, 30Y): TE fetched these from /markets/bond. TwelveData does not include them in the current _SYMBOLS map. These are critical for the risk assessment (yield curve inversion detection in assess_risk_environment).
Iron Ore: AUD correlation proxy. Niche but was available.
Dairy GDT: NZD correlation proxy. Niche and TE rarely found it anyway.

The sentiment collector now produces zero SentimentReading objects. The risk assessment still works because it reads from intermarket cache. But any downstream code that expects sentiments list to have data will get an empty list.



---

## TA DATABASE STORAGE BLOAT — FUTURE OPTIMIZATION

### The Problem

With TA kept user-scoped (which is correct because different brokers produce different OHLCV candles due to liquidity providers, spreads, and timezone shifts), storage grows linearly with users:

- 1,000 users × 5 pairs × 4 cycles/hour × 24 hours = **~480,000 new DB rows/day**
- Tables affected: `candles`, `technical_snapshots`, `candidates`

### Why Streaming Alone Doesn't Fix It

The storage bloat comes from **persisting snapshots and candle rows**, not from how candles are acquired. Whether you poll 500 candles every 15 minutes or stream them one-by-one 24/7, you still end up with the same volume of candle data in the database. Streaming is actually *more* granular (writing on every single candle close), so it would write MORE rows, not fewer.

### The Real Solution: Hybrid Compute-on-Demand Architecture

| Current (Poll + Store) | Optimal (Stream + Compute-in-Memory) |
|------------------------|--------------------------------------|
| Fetch 500 candles → Write all to DB | Stream candle closes → Hold in memory (ring buffer) |
| Run TA on DB-stored candles | Run TA on in-memory candles |
| Write snapshot to DB | **Don't persist snapshot at all** — pass directly to Processor |
| ~480,000 rows/day | Near-zero DB writes for candles/snapshots |

The key insight: **TA snapshots and raw candles are ephemeral compute artifacts, not permanent records.** Nobody needs a Fair Value Gap snapshot from 3 days ago. The only things worth persisting permanently are:
- The **Processor's final analysis output** (the trade decision) — already stored user-scoped in `analysis_outputs`.
- The **Audit trail** — already stored in `analysis_audit_logs`.

### Implementation Steps (Future)

1. **Stream** candle closes into an in-memory ring buffer (e.g., last 500 candles per symbol per timeframe per user).
2. **Compute** TA entirely in memory — no DB reads or writes for candles/snapshots.
3. **Pass** the result directly to the Processor pipeline.
4. **Only persist** the final trade decision and audit log (which we already do).
5. **Result:** Daily DB writes drop from ~480,000 rows to ~5,000–10,000 rows (analysis records only). A **98% reduction**.

### Prerequisite Changes

- Refactor `TAOrchestrator._fetch_sequence()` to read from an in-memory candle store instead of Postgres.
- Build a candle streaming service (ZMQ PUB/SUB from EA → Python ring buffer).
- Add a per-user in-memory candle manager that maintains the ring buffers.

### Short-Term Mitigation (Before Streaming)

Add an aggressive **data pruning cron job** that permanently deletes:
- `candles` rows older than 7 days
- `technical_snapshots` rows older than 7 days
- `candidates` rows where `is_active = false` and older than 14 days

This keeps the DB lean without requiring the full streaming refactor.
