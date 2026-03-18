
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



Now I can see the critical mismatches. The `QuasiModoLevel` model has fields: `qml_price`, `h_price`, `hh_price`, `h_timestamp`, `hh_timestamp`, `candle_index`. But the `QMDetector` constructs it with: `level`, `h1_price`, `h1_timestamp`, `h2_price`, `h2_timestamp`, `break_candle_index`, `break_timestamp`, `is_valid` - **none of which exist on the model**.

Similarly, the `SRFlipDetector` constructs `SRFlip` with `original_support_level`, `original_support_timestamp`, `breakout_candle_index`, `breakout_price`, `new_resistance_level`, `is_valid` - but the `SRFlip` model has `flip_level`, `flip_level_timestamp`, `breakout_price`, `candle_index`, `previous_role`, `new_role`.

The `MiniPriceLevel` model has `mpl_price` but the `MPLDetector` constructs it with `level`, `is_type1`.

The `SupplyDemandDetector.create_supply_zone()` passes `qml_level`, `qml_timestamp`, `sr_flip_level`, `sr_flip_timestamp`, `is_valid` - but `SupplyZone` model has `candle_index` (required, `ge=0`), `strength`, `tested`, etc. and none of those SnD-specific fields.

These are **model-level mismatches** that need the `zone.py` model and the `structure_event.py` model to be updated to support the fields the detectors actually need. This is a bigger change. The


#### What ORDER.md Says (The Audit)

ORDER.md identifies **one significant issue** and two minor ones:

1. **SIGNIFICANT: SnapshotBuilder doesn't populate structure events** - The orchestrator calls `self.snapshot_builder.build_snapshot(candles=sequence)` with ONLY candles. The SnapshotBuilder accepts BOS, CHOCH, BMS, SMS, OBs, FVGs, sweeps, inducements, etc. as optional parameters, but they're never passed. This means every per-timeframe snapshot has **empty** structure events, liquidity events, and zones. The snapshots persisted to DB and sent to the Gateway/LLM are missing all intermediate structural data.

2. **MINOR: Trend direction fallback is swing-only** - Since BOS/CHOCH lists are always empty (due to issue #1), trend always falls through to the swing-based fallback.

3. **MINOR: No deduplication of candidates across timeframe pairs** - Same pattern could be detected on multiple pairs.

#### Gaps I Confirmed Between TA, Gateway, and Shared

After examining every file end-to-end, here are ALL the gaps:

1. **The core snapshot gap (ORDER.md Issue #1)**: `orchestrator.py` line `snapshot = self.snapshot_builder.build_snapshot(candles=sequence)` passes nothing but candles. The SMC/SnD detectors run separately and produce candidates, but the intermediate structural data (BMS, CHOCH, SMS, OBs, FVGs, sweeps, inducements, QML, MPL, SR/RS flips, supply/demand zones, fibonacci, dealing ranges, equal highs/lows, liquidity grabs, compressions) is never fed back into the snapshots. The `_persist_snapshot` method then serializes all these empty lists to the database, and `_serialize_snapshot` sends empty lists to the Gateway.

2. **Gateway ta_extractor.go reads snapshot fields that are always empty**: The Go gateway's `ta_extractor.go` extracts signals from snapshots (e.g., `trend_direction`), but the snapshot's `total_structure_events`, `total_liquidity_events`, `total_zones` are always 0 because the structural data was never populated.

3. **The SnD detector (`src/engine/ta/snd/detector.py`) needs to be verified** - I identified it exists but haven't read its full content yet. It's referenced by the orchestrator and dependencies.

4. **SMC zones directory** has files (`fvg.py`, `order_block.py`, `breaker.py`, `mitigation.py`) and **SMC builders** (`continuation.py`, `reversal.py`, `amd/candidates.py`) that I identified but haven't read in full yet. Same for **SnD detectors** (`qm.py`, `sr_flip.py`, `rs_flip.py`, `mpl.py`, `fakeouts.py`, `previous_levels.py`, `supply_demand.py`) and **SnD builders** (`qm.py`, `fakeout.py`, `continuation.py`).

5. **Storage repositories and schemas** (`candle.py`, `snapshot.py`, `candidate.py` in both `repositories/` and `schemas/`) need verification to ensure they match the snapshot fields the orchestrator tries to persist.




PLEASE NOTE:  I HAVE ALREADY DONE THIS ONE BELOW BUT YOU HAVE TO VERIFY IT:

#### Step 1: Fix the Orchestrator's Snapshot Building

The core problem: `orchestrator.py` calls `self.snapshot_builder.build_snapshot(candles=sequence)` with ONLY candles. The SMC/SnD detectors run separately and produce candidates, but the intermediate structural data (BMS, CHOCH, SMS, OBs, FVGs, sweeps, inducements, etc.) detected during pattern detection is never fed back into the per-timeframe snapshots. This means every snapshot persisted to DB and sent to the Gateway has empty structure events, empty liquidity events, and empty zones.

The fix requires restructuring the orchestrator to:
1. Run per-timeframe structural detection FIRST (BMS, CHOCH, SMS, sweeps, FVGs, OBs, etc.)
2. Feed those results INTO the snapshot builder
3. THEN run cross-timeframe pattern detection (which uses the same data)

Let me also check one more thing before I start - the `CandleRepository.create()` method references fields (`open_time`, `close_time`, `quote_volume`, `number_of_trades`, `taker_buy_base_volume`, `taker_buy_quote_volume`) that don't exist on the `Candle` model. Let me verify:



SO I THINK WE HAVE UPDATED sr_flip.py, rs_flip.py, structure_event.py, snd/detector.py, orchestrator.py, snd/detector.py