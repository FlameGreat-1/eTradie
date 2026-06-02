# Stop-Loss / Take-Profit Accuracy Fix

**MR:** !75 &nbsp;|&nbsp; **Branch:** `fix/structural-invalidation-stop-loss`

Scope: make the stop-loss anchor on the setup's real structural
invalidation level (not the Order Block edge), make the SL buffer and
the TP reward-to-risk floor timeframe-aware, keep the per-style R:R as
a single source of truth, and add an execution-side defensive backstop.
Pure price/candle structure only — no indicators (no ATR).

---

## 1. Root cause (evidence)

Traced from `output/runcycle/Crash 1000 Index_*`:

- Chosen candidate `CRASH 1000 INDEX_CHOCH_BMS_RTO_BEARISH_..._5768.097_30e91c64`.
- Entry (OB midpoint) `5768.097`, SL `5771.0694` -> **2.97 points**, TP3 `5639.895`, reported R:R `43.13`.
- The SL is produced by the **TA candidate builder**, copied verbatim by the LLM (`processor_result.json` `stop_loss.price == 5771.0694`), and accepted verbatim by the parser/validator (no recompute downstream).

Two defects:

1. **SMC SL confined to the OB edge.** `_build_choch_candidate` and the
   SMC builders used `buffer = OB_range * 0.10` then
   `max(structural_sl, ob_edge_sl)` (bearish) / `min(...)` (bullish).
   Because the OB sits between entry and the real invalidation (the
   CHoCH `broken_level`), the clamp always picked the OB-edge term and
   discarded the genuine invalidation level.
2. **Buffers / TP RR too tight and timeframe-blind.** SnD SL used a
   flat `previous_level_tolerance_pips = 3`; SMC/SnD TP used a flat
   `min_take_profit_rr = 1.0` / `risk_reward = 3.0` regardless of
   timeframe or trading style. On synthetics `pip_value = 1.0`, so 3
   "pips" = 3 points.
3. **No execution-side backstop.** A tiny SL inflates lot size in the
   sizing engine (`riskAmount / (slPips * pipValue)`), capped only by
   `MaxLotSize`.

---

## 2. Stop-loss: anchor on real invalidation, timeframe-aware buffer

New shared helper computes the SL beyond the true invalidation level
with a timeframe-scaled structural buffer. The OB edge is used only as
an **inner guard** (SL never inside the zone), never as the anchor.

```
buffer = max(invalidation_candle_range * 0.25, timeframe_floor_pips * pip_value)
SL (short) = invalidation_level + buffer   # guarded to sit beyond OB upper
SL (long)  = invalidation_level - buffer   # guarded to sit beyond OB lower
```

Invalidation level per pattern:

| Pattern | Invalidation anchor |
|---|---|
| SMC CHoCH | `htf_choch.broken_level` |
| SMC continuation (SH+BMS+RTO) | liquidity-sweep extreme (`sweep_low`/`sweep_high`) |
| SMC reversal (SMS+BMS+RTO) | `htf_sms.failed_level` |
| SMC AMD | Asian-range extreme |
| SMC turtle soup | swept extreme (turtle minimum retained as extra floor) |
| SnD QM (QML/QMH) | QM head (`hh_price` / `ll_price`) |
| SnD fakeout-king / continuation | SR/RS flip level |

`TIMEFRAME_SL_FLOOR_PIPS` (pips, converted via `PipSize`): M1 8, M5 12,
M15 18, M30 25, H1 35, H3 55, H4 70, H6 90, H8 110, H12 140, D1 200,
W1 400, MN1 700.

---

## 3. Take-profit: style-driven R-multiple floor, timeframe can only raise it

The TP floor is a reward-to-risk **multiple (R), not pips**. It is
`max(style_floor, timeframe_floor)` and never below the rulebook's
lowest per-style minimum (Scalping 1:2).

- Per-style minimum (rulebook Section 7.3 / STYLE-RR-001): Scalping
  2.0, Intraday 3.0, Swing 3.0, Positional 5.0.
- `TIMEFRAME_MIN_TP_RR`: M1/M5 2.0, M15/M30 2.5, H1/H3 3.0, H4/H6 3.5,
  H8/H12 4.0, D1/W1/MN1 5.0 (each floored at 2.0).
- `resolve_min_tp_rr(timeframe, style)` combines them. The TA layer is
  style-agnostic at build time, so it applies the timeframe floor; the
  processor validator applies the style floor (it has `trading_style`
  but not the candidate timeframe).

The TP selectors still target a **real structural liquidity level**
(swing high/low); the floor only filters out targets too close to
clear the minimum R:R.

---

## 4. Single source of truth for per-style R:R

`engine/shared/risk.py` holds the canonical `MIN_RR_*`,
`STYLE_MIN_TP_RR`, `style_min_tp_rr`, `LOWEST_STYLE_MIN_RR`.

- `engine.ta.common.utils.price.stop_loss` imports them (re-exported
  for TA callers).
- `engine.processor.constants` re-exports `MIN_RR_*` from shared (no
  duplicate numbers).
- `engine.processor.parsing.validators._validate_rr_ratio` derives the
  per-style minimum from shared. **No processor -> TA cross-import.**

---

## 5. Execution-side minimum-stop-distance backstop (Go, Module B)

New validator check rejects a sub-floor SL **before** position sizing
(validator runs at gRPC Step 2; sizing is Step 3).

- Reject when `|entry - SL| / PipSize < MinStopPipsForTimeframe(LTFTimeframe)`.
- `MinStopPipsByTimeframe` mirrors the TA `TIMEFRAME_SL_FLOOR_PIPS`
  values (separate Go definition; the execution service cannot import
  the Python helper). `DefaultMinStopPips = 35` for unknown timeframe.
- Uses broker `InstrumentInfo.PipSize` for per-instrument conversion.
- **Fail-open** on a broker data gap (missing/invalid `PipSize`) — the
  sizing engine independently rejects an invalid `PipSize` one step
  later. A zero/negative SL distance is rejected outright.
- No broker `stops_level` field exists on `InstrumentInfo`, so the
  guard uses a structural pips floor (the unit the sizing engine
  already uses).

---

## 6. Files touched

**New**

- `src/engine/shared/risk.py` — canonical per-style R:R map + helpers.
- `src/engine/ta/common/utils/price/stop_loss.py` — shared SL geometry
  + timeframe SL floor + TP R-multiple resolver.
- `docs/audit/STOP_LOSS_TAKE_PROFIT_FIX.md` — this document.

**SMC (Python)**

- `src/engine/ta/smc/detector.py` — CHoCH SL anchored on
  `broken_level`; CHoCH TP uses `resolve_min_tp_rr`.
- `src/engine/ta/smc/builders/continuation.py` — SL via shared helper;
  TP selectors take a timeframe-resolved R-multiple.
- `src/engine/ta/smc/builders/reversal.py` — SMS SL via shared helper;
  turtle-soup SL via shared helper (turtle min retained as floor); TP
  selectors timeframe-resolved.
- `src/engine/ta/smc/builders/amd/candidates.py` — AMD SL via shared
  helper; TP selectors timeframe-resolved.

**SnD (Python)**

- `src/engine/ta/snd/builders/levels.py` — `compute_trade_levels`
  gains `timeframe`; SL buffer floored by timeframe; TP `risk_reward`
  resolved from timeframe when not supplied.
- `src/engine/ta/snd/builders/candidates/qm.py` — pass `timeframe`
  (4 call sites).
- `src/engine/ta/snd/builders/candidates/fakeout.py` — pass `timeframe`
  (2 call sites).
- `src/engine/ta/snd/builders/candidates/continuation.py` — pass
  `timeframe` (2 call sites).

**Processor (Python)**

- `src/engine/processor/constants.py` — re-export `MIN_RR_*` from
  `engine.shared.risk`.
- `src/engine/processor/parsing/validators.py` — `_validate_rr_ratio`
  uses `engine.shared.risk.style_min_tp_rr`.

**Execution (Go, Module B)**

- `src/execution/internal/constants/constants.go` —
  `CheckMinStopDistance = 14`, `MinStopPipsByTimeframe`,
  `DefaultMinStopPips`, `MinStopPipsForTimeframe`.
- `src/execution/internal/validator/checks.go` —
  `check14MinStopDistance`.
- `src/execution/internal/validator/validator.go` — register the
  check; comment updated to checks 4-14.

---

## 7. Notes / follow-up

- This is an accuracy fix at the SL/TP source plus a defensive
  backstop (defence in depth); it relocates/widens the stop
  structurally and does not add rejection gates that would invalidate
  otherwise-valid setups.
- The floor tables (`TIMEFRAME_SL_FLOOR_PIPS`, `TIMEFRAME_MIN_TP_RR`,
  `MinStopPipsByTimeframe`) should be validated against historical
  setups (per `MR-VER-002`) before live use and could be made
  operator-tunable via config/settings.
