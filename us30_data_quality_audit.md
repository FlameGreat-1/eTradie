# US30 TA Data Quality Audit — Root Cause Analysis

**Date:** 2026-04-15  
**Symbol:** US30_x10m  
**Question:** Is the LLM receiving bad data, or is it misinterpreting good data?

---

## Verdict: **~70% Data Quality Issue / ~30% LLM Interpretation Issue**

The TA engine is producing **incomplete and one-sided D1 structural data**, which then causes the LLM to overstate the bearish case. The LLM's reasoning is actually logically sound *given what it was fed* — the problem is upstream.

---

## D1 Snapshot Data Audit (THE CORE PROBLEM)

### 🔴 Critical Finding: D1 Structural Data is Catastrophically Sparse

| Metric | D1 | H4 | M30 | M15 |
|--------|----|----|-----|-----|
| Candle Count | 52 | 109 | 363 | 538 |
| Swing Highs Detected | **1** | 5 | 12 | 12 |
| Swing Lows Detected | **2** | 7 | 12 | 12 |
| Bullish BMS | **0** | 3 | 0 | 0 |
| Bearish BMS | 1 | 1 | 5 | 5 |
| Bullish CHoCH | **0** | 1 | 0 | 0 |
| Bearish CHoCH | 1 | 1 | 5 | 5 |
| SMS Events | **0** | 2 | 5 | 5 |
| RS Flips (R→S) | **0** | 4 | 5 | varies |
| Supply Zones | **0** | 0 | 5 | varies |
| Demand Zones | **0** | 0 | 5 | varies |
| Total Structure Events | **3** | **12** | **82** | varies |

> [!CAUTION]
> **The D1 has only 3 total structural events across 52 candles.** Compare this to H4 with 12 events across 109 candles, and M30 with 82 events across 363 candles. The D1 is producing almost NO structural data.

### Problem #1: Only 1 Swing High Detected on D1

The system found **only 1 swing high on D1** — at 49,867.4 (Feb 26, strength 9).

Looking at the D1 chart, during the **recovery phase** (Mar 29 → Apr 15), price rallied from 44,846 to 48,742. That's a **3,896 point rally over ~12 daily candles**. This massive impulsive move SHOULD have produced at least 1-2 intermediate swing highs on D1 (e.g., the ~46,800 area where price consolidated before pushing higher).

**But the system detected ZERO swing highs during the entire April recovery.**

This means the swing detection algorithm's strength threshold is too aggressive for D1. It's filtering out intermediate pivots that are structurally significant.

### Problem #2: ZERO Bullish Structure Detected on D1

Because swing highs are missing from the recovery, the entire bullish side of the D1 story is invisible:

- **0 bullish BMS** — Price broke above multiple intermediate D1 levels during the recovery, but since those levels weren't registered as swing highs, no BMS could be detected.
- **0 bullish CHoCH** — Same reason. No swing highs to break = no change of character detected.
- **0 SMS events** — No failure swings detected despite the clear failure to make a new low.
- **0 RS flips** — The SR_flip at 46,331.3 (Support→Resistance) was detected on March 27. But when price subsequently rallied BACK above 46,331.3 (around April 8-9), the corresponding RS_flip (Resistance→Support) was **NOT detected**. This is a critical miss.
- **0 demand zones** — Despite the massive bullish demand that drove price from 44,846 to 48,742, zero demand zones were identified on D1.

### Problem #3: The D1 Bearish Order Block at 46,401–46,767 is Listed as Unmitigated

The system shows a bearish D1 OB at [46,401.9 – 46,767.2] from March 15, marked as `"mitigated": false`.

**But price has ALREADY traded through this zone multiple times during the recovery** — the H4 chart clearly shows price passing through the 46,400–46,800 zone on the way up. This OB should be marked as mitigated.

### Problem #4: The D1 Fibonacci Data is Provided But Incomplete

The system correctly computed the D1 fib retracement from 49,867 to 44,846, with `is_bullish: true` and range_size 5,021. But it doesn't provide the current retracement percentage or which fib level price is at. The LLM has to compute this itself, and it apparently didn't weigh this heavily enough.

---

## What the LLM Actually Received (Summary)

The LLM got a D1 snapshot that said:

| Category | Data |
|----------|------|
| Trend | BEARISH |
| Bearish evidence | 1 BMS, 1 CHoCH, 1 SR→flip, 1 bearish OB |
| Bullish evidence | **NOTHING** |
| Swing structure | 1 high, 2 lows (all from weeks ago) |
| Recovery evidence | **NONE** — no bullish BMS, CHoCH, RS-flip, demand zones |

**The LLM had no choice but to conclude D1 is firmly bearish.** It literally had zero counter-evidence in the D1 snapshot.

---

## H4 Data Quality (GOOD — Contrast with D1)

The H4 snapshot is dramatically richer and correctly captures the bullish recovery:

- **3 bullish BMS events** — Breaking above 46,864, 46,854, and 48,361 ✅
- **1 bullish CHoCH** — At 46,854 on Apr 8 ✅
- **1 bullish SMS (failure swing)** — At 44,846, reversed to 45,659 ✅
- **3 bullish OBs** — Correctly mapped ✅
- **4 RS-flips** — Previous resistance flipping to support ✅
- **1 bullish breaker block** ✅

The H4 data correctly tells the story of a bullish recovery. The gap between D1 data quality and H4 data quality is where the analysis falls apart.

---

## LLM Interpretation Issues (Secondary)

Even with the flawed data, the LLM made some interpretation errors:

1. **Failed to flag the D1-H4 conflict more strongly.** D1=BEARISH + H4=BULLISH (with MULTIPLE bullish BMS) is a major red flag. The LLM acknowledged it but dismissed H4 as "counter-trend retracement." With 3 bullish BMS on H4, that's not a correction — that's a confirmed trend.

2. **Dealing range data was available.** The D1 dealing range shows equilibrium at 47,384. Current price at ~48,420 is deep in premium. The LLM used this to support the short, which is correct — BUT it should have questioned whether the impulsive move into premium suggests trend reversal, not just "premium for shorting."

3. **Overconfident grading.** Even with one-sided data, 0.85 confidence / Grade A for a trade fighting a confirmed H4 bullish trend is objectively too high. The LLM should have downgraded when it saw the H4 conflict.

4. **11.7:1 RR is fantasy.** Targeting 47,440 (TP3) means expecting 1,200 points of downside against active H4 bullish structure. This shows the LLM isn't properly stress-testing its targets against the H4 backdrop.

---

## Root Causes in the TA Engine

### 1. Swing Detection Algorithm — Strength Threshold Too High on HTF

The swing detection appears to require very high "strength" scores on D1, filtering out intermediate pivots that are structurally meaningful. With only 52 candles, D1 candles represent larger moves — intermediate swings during a recovery might have strength 4-6, which gets filtered out.

**Impact:** No intermediate swing highs → no bullish BMS/CHoCH detected → one-sided structural picture.

### 2. SR/RS Flip Detection — Missing Recovery-Phase Flips

The SR_flip at 46,331.3 (Support→Resistance on Mar 27) was detected. But the subsequent break back above this level (around April 8-9 when price was rallying) should have produced an RS_flip — and didn't.

**Impact:** The LLM sees 46,331 as resistance (supporting bearish view) when price is actually 2,000+ points above it.

### 3. OB Mitigation Tracking — Not Updating Properly

The D1 bearish OB at 46,401–46,767 is marked as unmitigated despite price clearly trading through it during the H4 bullish rally.

**Impact:** The LLM may interpret this as a live bearish zone when it's already been consumed.

### 4. No "Recovery Strength" or "Retracement Depth" Metric

The engine provides the Fibonacci range but doesn't compute WHERE current price sits within it. Adding a `current_retracement_pct` field (e.g., 77.6%) would give the LLM critical context about how deep the recovery has gone.

---

## Recommendations (Priority Order)

1. **Lower the swing detection strength threshold for D1/W1** — Or use an adaptive threshold based on candle count. D1 with 52 candles should find 3-5 swing highs minimum.

2. **Ensure BMS/CHoCH detection runs on ALL detected swings** — Currently it appears to only fire when high-strength swings are broken. Lower-strength breaks matter for context.

3. **Fix RS_flip detection to track when price reclaims broken levels** — If an SR_flip is created (Support→Resistance), and price subsequently breaks back above that level, an RS_flip should be created.

4. **Fix OB mitigation tracking** — Cross-reference OB zones against subsequent candle highs/lows to properly mark mitigated zones.

5. **Add `current_retracement_pct` to the Fibonacci data** — Let the LLM know price is at 77.6% retracement without having to compute it.

6. **Add a "structural conflict" warning to `ta_metadata.json`** — When adjacent pairs (D1/H4) show opposite strong structures, flag it explicitly so the LLM can't dismiss it.
