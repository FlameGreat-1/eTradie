# Dynamic Timeframe Lookback & Output Optimization

The current technical analysis orchestration retrieves a static number of candles (500) for all timeframes, pushing gigabytes of irrelevant historic swings, zones, and events to the LLM processor. This plan details the implementation of an adaptive sliding scale for candle fetches and caps the number of output structures sent to the LLM.

## User Review Required

> [!CAUTION]
> Please review the proposed **Sliding Scale Constraints** below to ensure the periods align with your trading strategy. If you prefer different values, let me know!

## Proposed Changes

### 1. Adaptive Candle Lookback (Sliding Scale)
Instead of forcing 500 periods across the board, `src/engine/ta/orchestrator.py` will dynamically assign the `lookback_periods` parameter depending on the timeframe.

Proposed limits:
- **W1 (Weekly) / MN1**: `30` periods (approx. ~7 months of history for Weekly charts)
- **D1 (Daily)**: `60` periods (~3 trading months)
- **H4 (4-Hour)**: `150` periods (~25 trading days)
- **H1 (1-Hour)**: `300` periods (~12 trading days)
- **M30 limits & below**: `500` periods (to retain enough candles for intraday structure)

#### [MODIFY] `src/engine/ta/orchestrator.py`
- Update `_fetch_sequence` calls in the `analyze` function to utilize a new internal map resolving timeframe-specific lookbacks, ignoring the static global configuration size.
- Refactor loops to pull the exact calculated lookback per timeframe limit.

### 2. Output Event Truncation
Even with the sliding scale, passing historical structure events (like a CHoCH that happened 3 months ago) litters the LLM's context.

We will modify the serialization logic to enforce truncation:
- **Swings:** Keep only the **last 10** `swing_highs` and `swing_lows`.
- **Market Structure (BMS, CHoCH, SMS):** Keep only the **last 5** structural events per array. 
- **Zones (Order Blocks, Breakers, FVGs, SnD):** Filter out mitigated/filled ones, or strictly limit it to the **last 5** recent zones.
- **Liquidity (Sweeps, Equal Highs/Lows):** Keep only the **last 10**.

#### [MODIFY] `src/engine/ta/orchestrator.py`
- Modify the `_serialize_*` methods (e.g., `_serialize_swing_highs`, `_serialize_bms_events`) to apply Python array slicing (e.g., `[-10:]`). This ensures we only output the *most recent* data to `ta_analysis.json` and the LLM.

## Open Questions

- Does the proposed lookback schedule (30 for W1, 60 for D1, 150 for H4, etc.) fit your vision?
- Should we completely discard mitigated Order Blocks and Filled FVGs from the LLM prompt, or keep the most recent ones just in case?

## Verification Plan

### Automated Tests
- Trigger an MT5 local engine analysis using `/internal/processor/process` or RAG test endpoints.
- Check the output token limits on LLM logs.

### Manual Verification
- Review the generated `ta_analysis.json` in the `/output/` directory on a fresh run to confirm the file size is reduced from 4.8MB down to a few kilobytes.
