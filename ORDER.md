I've now examined the entire TA module thoroughly. Here's the complete audit:

---

#### Complete TA Module Audit

#### Are we analyzing real live charts or just OHLV values?

**We are analyzing real live OHLCV data from MetaTrader 5.** The MT5 client (`broker/mt5/client.py`) connects to a live MT5 terminal, authenticates with real broker credentials, and calls `mt5.copy_rates_from_pos` / `mt5.copy_rates_range` to fetch actual market candles. Each candle contains:
- `open`, `high`, `low`, `close` (real prices from the broker's feed)
- `tick_volume` (real volume)
- `timestamp` (exact candle open time in UTC)

The system is NOT using synthetic data or just OHLC values in isolation. It fetches **500 candles per timeframe** across **8 timeframes** (W1, D1, H4, H1, M30, M15, M5, M1) and builds a full multi-timeframe structural analysis from that live data.

#### What the system detects accurately

**SMC patterns** (all working correctly from the code):
1. **Turtle Soup Long/Short** - Detects liquidity sweeps below/above swing points with close-back-inside validation
2. **SH + BMS + RTO (Continuation)** - HTF BMS → LTF CHOCH → LTF BMS → Order Block → FVG confluence
3. **SMS + BMS + RTO (Reversal)** - HTF SMS (failure swing) → LTF BMS → LTF CHOCH → Order Block
4. **AMD (Accumulation-Manipulation-Distribution)** - Session-aware phase detection with dealing range analysis
5. **Combined patterns** - Turtle Soup + SH_BMS_RTO composites

**SnD patterns** (all working correctly):
1. **QML Baseline** - Quasimodo Level detection from swing structure (H-HH pattern)
2. **QML Killer Type 1/2** - QML + Previous Highs/Lows + MPL + SR/RS Flip
3. **QMH Baseline/Killer** - Mirror of QML for bullish setups
4. **Fakeout King** - Previous levels + fakeout tests + Marubozu breakout
5. **Triple Fakeout** - Multiple fakeout tests at same level
6. **SR/RS Flip** - Support becomes resistance (and vice versa) with Marubozu confirmation
7. **SOP (Shift of Polarity)** - Zone role reversal detection
8. **SnD Continuation** - Supply/demand zone continuation setups

**Common analyzers** (all structurally sound):
- **SwingAnalyzer** - 5-bar left/right pivot detection with equal highs/lows identification
- **SessionAnalyzer** - UTC-based session identification (Asia, London, NY, Overlap)
- **FibonacciAnalyzer** - OTE levels (50%, 61.8%, 70.5%, 79%)
- **CompressionAnalyzer** - Tight range detection inside zones
- **MarubozuAnalyzer** - Body ≥80%, wick ≤10% validation
- **DealingRangeAnalyzer** - Premium/discount zone calculation

#### Issues Found

**1. SnapshotBuilder doesn't populate structure events (SIGNIFICANT)**

The `SnapshotBuilder.build_snapshot()` only runs `swing_analyzer` and `session_analyzer` internally. It accepts BOS, CHOCH, BMS, SMS, OBs, FVGs, etc. as **optional parameters** but the orchestrator calls it with just `candles`:

```python
snapshot = self.snapshot_builder.build_snapshot(candles=sequence)
```

This means every per-timeframe snapshot has **empty** structure events, liquidity events, and zones. The snapshots only contain swings, session state, and trend direction (derived from swings alone since BOS/CHOCH lists are empty).

The actual pattern detection happens separately in `_run_smc_detection` and `_run_snd_detection`, which output candidates directly. So the **candidates are correct**, but the **snapshots persisted to the database are incomplete** - they're missing all the intermediate structural data (BMS events, OBs, FVGs, sweeps, etc.) that were detected during pattern detection.

This means the serialized snapshots sent to the Gateway/LLM are missing structural context. The LLM sees swing points and trend direction but NOT the BMS events, order blocks, FVGs, liquidity sweeps, etc. that led to the candidates.

**2. Trend direction fallback is swing-only (MINOR)**

When the SnapshotBuilder determines trend, it checks BOS/CHOCH first, but since those lists are always empty (issue #1), it always falls through to the swing-based fallback (higher highs = bullish, lower lows = bearish). This works but is less precise than using actual BMS/CHOCH events.

**3. No deduplication of candidates across timeframe pairs (MINOR)**

The orchestrator runs detection on every adjacent pair (W1-D1, D1-H4, H4-H1, H1-M30, M30-M15, M15-M5, M5-M1, plus the cross-boundary H1-M30). The same pattern could theoretically be detected on multiple pairs. There's no deduplication step before returning results.

**4. Everything else is solid**

- Candle model validation is thorough (H≥L, H≥O/C, L≤O/C)
- CandleSequence enforces same symbol/timeframe, no duplicate timestamps, sorted by time
- MT5 client handles auth, reconnection, error codes properly
- Twelve Data fallback broker exists
- All pattern detectors enforce their respective rules (minimum confluences, OTE, session timing, displacement pips, etc.)
- Fibonacci levels include the correct OTE range (50%, 61.8%, 70.5%, 79%)
- Session UTC ranges are correct for forex

**Issue #1 is the only significant finding.** The candidates themselves are accurately detected from real live data, but the structural context that produced them isn't being passed through to the snapshots. Want me to fix it?