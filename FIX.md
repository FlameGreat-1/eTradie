Excellent question — let me check exactly how the `BrokerRegistry` resolves brokers and whether there's any actual failover wiring:

Viewed registry.py:1-222

Now I can give you the honest, accurate answer. Let me also check how the orchestrator gets its broker:

Searched for "fallback"

Here's the **honest, straight answer** based on exactly what the code shows:

## Twelve Data Is Registered But There's NO Automatic Failover

Looking at the [BrokerRegistry](cci:2://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/ta/broker/registry.py:16:0-189:33) (which I just re-examined), here's what **actually happens**:

### What IS wired up:
1. **Registration** (lines 85-109): If `TAConfig.fallback_broker == "twelve_data"` or `TAConfig.primary_broker == "twelve_data"`, the [TwelveDataClient](cci:2://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/ta/broker/twelve_data/client.py:51:0-584:13) gets created and stored in the [_brokers](cci:1://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/ta/broker/registry.py:84:4-108:86) dict
2. **Manual retrieval** (lines 134-138): Code can call [get_fallback_broker()](cci:1://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/ta/broker/registry.py:136:4-137:62) to get the Twelve Data client by name
3. **Health checks** (lines 140-167): All registered brokers (including Twelve Data) get health-checked via [health_check_all()](cci:1://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/ta/broker/registry.py:139:4-166:22)

### What is NOT wired up:
The [TAOrchestrator](cci:2://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/ta/orchestrator.py:65:0-1432:9) receives a **single `broker_client: BrokerBase`** in its constructor (line 90). It calls `self.broker_client.fetch_candles(...)` — and that's it. There is **no fallback logic** anywhere in the orchestrator:

- **No automatic failover** — if MT5 fails, the orchestrator does NOT automatically try Twelve Data
- **No retry with fallback** — the [_fetch_sequence()](cci:1://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/ta/orchestrator.py:398:4-477:9) method (lines 399-478) tries the broker once, catches the error, and falls back to **stored database candles** — NOT to Twelve Data
- The word `"fallback"` appears **zero times** in [orchestrator.py](cci:7://file://wsl.localhost/Ubuntu-24.04/home/softverse/eTradie/src/engine/ta/orchestrator.py:0:0-0:0)

### So what happens if MT5 is unavailable?
1. The orchestrator tries to fetch candles from the single configured broker → **fails**
2. It falls back to **whatever candles are already stored in the database** from previous successful fetches
3. If the database has enough historical data (≥80% of lookback), analysis proceeds on stale data
4. If the database is empty too → the timeframe is skipped with a `"no_candle_data_available"` warning

**Bottom line:** Twelve Data is **registered in the registry** and **can be retrieved**, but **nothing in the actual analysis pipeline automatically switches to it** when MT5 goes down. It's sitting there ready to be used, but there's no failover orchestration wired up.