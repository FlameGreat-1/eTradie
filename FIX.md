

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


