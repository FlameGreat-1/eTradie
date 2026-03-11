---
doc_id: snd_rulebook
doc_type: framework
framework: SnD
title: Supply and Demand Rulebook
version: "1.0"
status: active
author: System Owner
effective_date: "2026-03"
source_of_truth: true
updated_at: "2026-03"
---

# SUPPLY & DEMAND FRAMEWORK

> Primary retrieval source for all SnD zone identification, validation, entry logic, and invalidation. Does not contain SMC rules, Wyckoff phases, risk rules, or confluence scoring — those belong to their own documents.

---

## 1. Framework Overview

Supply & Demand (SnD) identifies institutional accumulation and distribution zones where large order imbalances caused a strong directional move. Price returns to these zones because unfilled institutional orders remain there.

SnD is used in this system for:
- **Identifying institutional accumulation/distribution areas** (Demand and Supply zones)
- **Identifying high-probability reversal zones** aligned with HTF structure
- **Defining the entry zone** — a range between the SR/RS Flip level and the QML

---

## 2. Supply and Demand Zones

### 2.1 Demand Zone

```
RULE_ID: SND-ZONE-001
Title: Demand Zone
Definition: Price region where institutional buying exceeded selling, causing a strong upward move.
Structure: Drop → Base → Rally
Entry zone: Between RS Flip level (top) and QML (bottom)
Bias: BUY only — must be at Discount price
```

### 2.2 Supply Zone

```
RULE_ID: SND-ZONE-002
Title: Supply Zone
Definition: Price region where institutional selling exceeded buying, causing a strong downward move.
Structure: Rally → Base → Drop
Entry zone: Between SR Flip level (bottom) and QML (top)
Bias: SELL only — must be at Premium price
```

### 2.3 SR Flip (Support-Resistance Flip)

```
RULE_ID: SND-ZONE-003
Title: SR Flip — Support Becomes Resistance
Condition: Single Marubozu candle closes BELOW a previous support level.
Result: That support level flips to resistance — forms the bottom boundary of the Supply zone.
Rule: No Marubozu = no valid SR Flip = no valid Supply zone.
```

### 2.4 RS Flip (Resistance-Support Flip)

```
RULE_ID: SND-ZONE-004
Title: RS Flip — Resistance Becomes Support
Condition: Single Marubozu candle closes ABOVE a previous resistance level.
Result: That resistance level flips to support — forms the top boundary of the Demand zone.
Rule: No Marubozu = no valid RS Flip = no valid Demand zone.
```

### 2.5 QML (Quasi Market Level)

```
RULE_ID: SND-ZONE-005
Title: QML — Quasi Market Level
Definition: The key structural level from which price originally broke — the origin of the QM structure.
QM structure (sells): Higher High → break of prior High level = QML established
QM structure (buys): Lower Low → break of prior Low level = QML established
Role: QML marks the top of the Supply zone (sells) or bottom of the Demand zone (buys).
Filter: If QML sits at the 50% equilibrium midpoint of the dealing range — skip the trade.
```

---

## 3. Base Formation

### 3.1 Valid Base

```
RULE_ID: SND-BASE-001
Title: Valid Base
Definition: Short consolidation area preceding a strong impulse move — where institutional orders were placed.
Requirements:
  - Small candle bodies
  - Limited price range
  - Tight consolidation
  - Precedes strong directional departure
```

### 3.2 MPL (Mini Price Level)

```
RULE_ID: SND-BASE-002
Title: MPL — Mini Price Level
Definition: Small internal engulfing structure that forms near the QML during the HH or LL move — a micro base within the larger zone.
Identification: Small engulfing candle or cluster forming during the impulse — circled on chart.
Role: Adds a secondary confluence level inside the Supply/Demand zone.
Significance: When MPL aligns with QML → zone has double-layered institutional origin.
```

### 3.3 Diamond Fakeout (Fake QM)

```
RULE_ID: SND-BASE-003
Title: Diamond Fakeout
Definition: A structure that looks like a QM but is not — a Fake QM appearing near the end of a long trend.
Role: Exhaustion WARNING only. Not a trade signal. Not a real QML.
Action: Do not trade the Diamond Fakeout as a QM. If already in trade — tighten management.
Appearance: Forms near the end of extended fakeout sequences (R3/R4 / S3/S4 area).
```

---

## 4. Impulse Leg

### 4.1 Valid Impulse Move

```
RULE_ID: SND-IMP-001
Title: Valid Impulse — The Marubozu Non-Negotiable
Definition: A strong directional move away from the base — must be executed by ONE single Marubozu candle.
Requirements:
  - Full candle body
  - No or minimal wicks
  - Single candle only — not a cluster
  - Closes clearly above/below the breakout level
Rule: No Marubozu = no valid breakout = no valid SR/RS Flip = no setup.
This applies to BOTH the initial Clean Breakout AND the Marubozu that breaks the fakeout zone.
```

### 4.2 Fakeout

```
RULE_ID: SND-IMP-002
Title: Fakeout
Definition: A failed breakout attempt at the SR/RS Flip zone — price tests the flipped level but fails to close through it.
Labels: R1/R2/R3/R4 (sells) · S1/S2/S3/S4 (buys)
Role: Each fakeout test confirms the zone is holding. More tests = stronger zone.
Signal: When a Marubozu breaks the fakeout zone → Supply/Demand zone and QML are directly ahead — entry imminent.
```

### 4.3 Compression Inside Fakeout Zone

```
RULE_ID: SND-IMP-003
Title: Compression (CP)
Definition: Small, tight, directional candles converging inside the fakeout zone — higher lows into resistance (sells) or lower highs into support (buys).
Interpretation: Price stalling at zone, collecting orders before Marubozu breakout.
Rule: Compression inside fakeout zone = higher probability that the setup will deliver.
```

---

## 5. Zone Strength Evaluation

### 5.1 Strong Supply Zone

```
RULE_ID: SND-STRENGTH-001
Title: Strong Supply Zone
Condition: Zone produces rapid drop with large bearish Marubozu candle(s).
Indicators of strength:
  - Sharp, fast departure from zone
  - Large candle bodies, minimal wicks
  - Leaves a gap/FVG below
  - First time price is returning (fresh)
Interpretation: High institutional selling present.
```

### 5.2 Strong Demand Zone

```
RULE_ID: SND-STRENGTH-002
Title: Strong Demand Zone
Condition: Zone produces rapid rally with large bullish Marubozu candle(s).
Indicators of strength:
  - Sharp, fast departure from zone
  - Large candle bodies, minimal wicks
  - Leaves a gap/FVG above
  - First time price is returning (fresh)
Interpretation: High institutional buying present.
```

### 5.3 Multiple Fakeout Tests

```
RULE_ID: SND-STRENGTH-003
Title: Multiple Fakeout Tests = Zone Strength
Rule: Repeated tests of the same SR/RS Flip zone (R2, R3, R4 / S2, S3, S4) confirm the trend is intact and zone is holding.
Interpretation: More tests without breaking through = stronger zone = higher probability on entry.
Exception: Diamond Fakeout at end of sequence warns of exhaustion — tighten management.
```

---

## 6. Zone Freshness

### 6.1 Fresh Zone

```
RULE_ID: SND-FRESH-001
Title: Fresh Zone
Definition: Zone that has not been revisited since its original creation.
Interpretation: Highest probability — institutional orders likely still unfilled.
Action: Prioritize fresh zones over tested zones.
```

### 6.2 Tested Zone

```
RULE_ID: SND-FRESH-002
Title: Tested Zone
Definition: Zone that has been visited once since creation — price touched it and respected it.
Interpretation: Reduced but still valid probability. Second touch still tradeable with confluence.
```

### 6.3 Weak / Exhausted Zone

```
RULE_ID: SND-FRESH-003
Title: Weak Zone
Definition: Zone that has been tested multiple times (3+) without producing a strong move.
Interpretation: Institutional orders likely depleted. Zone losing significance.
Action: Treat with reduced confidence. Requires extra confluence to trade.
```

---

## 7. Zone Retest Logic

### 7.1 First Retest

```
RULE_ID: SND-RETEST-001
Title: First Retest
Definition: First return of price to a fresh Supply or Demand zone after its creation.
Interpretation: Highest probability trade opportunity in the SnD system.
Action: Full entry signal if all pattern and confirmation conditions are met.
```

### 7.2 Second Retest

```
RULE_ID: SND-RETEST-002
Title: Second Retest
Definition: Second return to the same zone.
Interpretation: Valid but lower probability than first retest. Zone has been partially mitigated.
Action: Trade only with additional confluence (Fibonacci alignment, Wyckoff support, session timing).
```

### 7.3 Multiple Retests

```
RULE_ID: SND-RETEST-003
Title: Multiple Retests
Condition: Zone tested 3 or more times.
Interpretation: Zone increasingly unreliable — institutional orders being absorbed.
Action: Do not trade. Look for a new zone forming after structural break.
```

---

## 8. Entry Logic

### 8.1 Standard Supply Zone Entry (SELL)

```
RULE_ID: SND-ENTRY-001
Title: Supply Zone Entry
Conditions (ALL required):
  1. Valid QM structure established — QML confirmed on HTF
  2. Single Marubozu breaks Support → SR Flip zone created
  3. Fakeout(s) form at SR Flip zone (R1–R4)
  4. Single Marubozu breaks the fakeout zone
  5. Price rallies into Supply zone (between SR Flip and QML)
  6. Supply zone is at Premium price (50%–100% Fibonacci)
  7. HTF structure is bearish (aligned)
Entry: Inside Supply zone — refined to Decision Point candle on M1/M5
SL: Above QML (top of Supply zone)
Target: Next SSL pool (liquidity draw below)
```

### 8.2 Standard Demand Zone Entry (BUY)

```
RULE_ID: SND-ENTRY-002
Title: Demand Zone Entry
Conditions (ALL required):
  1. Valid QM structure established — QML confirmed on HTF
  2. Single Marubozu breaks Resistance → RS Flip zone created
  3. Fakeout(s) form at RS Flip zone (S1–S4)
  4. Single Marubozu breaks the fakeout zone
  5. Price drops into Demand zone (between RS Flip and QML)
  6. Demand zone is at Discount price (0%–50% Fibonacci)
  7. HTF structure is bullish (aligned)
Entry: Inside Demand zone — refined to Decision Point candle on M1/M5
SL: Below QML (bottom of Demand zone)
Target: Next BSL pool (liquidity draw above)
```

### 8.3 Sell Patterns

| ID | Pattern | Key Feature |
|----|---------|-------------|
| SND-SELL-001 | QML + SR Flip + Fakeout (Baseline) | Standard QM → SR Flip → Fakeout → SELL at Supply |
| SND-SELL-002 | QML + MPL + SR Flip + Fakeout | MPL forms near QML → adds internal confluence |
| SND-SELL-003 | QML + Prev Highs + MPL + SR Flip + Fakeout T1 | 90% Setup — Prev Highs at QML + MPL engulfing |
| SND-SELL-004 | QML + Prev Highs + SR Flip + Fakeout T2 | Same as T1 — MPL breaks cleanly (no engulf) |
| SND-SELL-005 | QML + Triple Fakeout | 3 layers of resistance → Diamond → SELL — highest confluence |
| SND-SELL-006 | Fakeout King | Prev Highs LOWER than QML + MPL above SR Flip |
| SND-SELL-007 | Prev Highs + Supply + Fakeout (S.O.P) | 3-step SOP: Prev Highs → Fakeouts → Marubozu → SELL |

### 8.4 Buy Patterns

| ID | Pattern | Key Feature |
|----|---------|-------------|
| SND-BUY-001 | QML + RS Flip + Fakeout (Baseline) | Standard QM → RS Flip → Fakeout → BUY at Demand |
| SND-BUY-002 | QML + MPL + RS Flip + Fakeout | MPL forms near QML → adds internal confluence |
| SND-BUY-003 | QML + Prev Lows + MPL + RS Flip + Fakeout T1 | 90% Setup — Prev Lows at QML + MPL engulfing |
| SND-BUY-004 | QML + Prev Lows + RS Flip + Fakeout T2 | Same as T1 — MPL breaks cleanly (no engulf) |
| SND-BUY-005 | QML + Triple Fakeout Buy | 3 layers of support → Diamond → BUY — highest confluence |
| SND-BUY-006 | Fakeout King Buy | Prev Lows HIGHER than QML + MPL below RS Flip |
| SND-BUY-007 | Prev Lows + Demand + Fakeout (S.O.P Buy) | 3-step SOP: Prev Lows → Fakeouts → Marubozu → BUY |

### 8.5 Pattern Ranking

| Rank | Pattern | Reason |
|------|---------|--------|
| 1 | Triple Fakeout (SELL-005/BUY-005) | 3 separate confluence layers at same QML |
| 2 | Prev Highs/Lows + QML T1 (SELL-003/BUY-003) | 90% Killer Setup — Prev Highs/Lows at QML |
| 3 | Fakeout King (SELL-006/BUY-006) | Prev Highs/Lows separate from QML |
| 4 | QML + MPL (SELL-002/BUY-002) | MPL adds internal zone confluence |
| 5 | QML + SR/RS Flip Baseline (SELL-001/BUY-001) | Minimum standard requirement |

### 8.6 LTF Entry Confirmation (M15/M5/M1)

After full pattern confirmed on HTF (H4/H1) and SR/RS Flip + fakeout confirmed on mid-TF (M30/H1) — drop to LTF and wait for ALL:

| # | Confirmation | Condition |
|---|-------------|-----------|
| 1 | Compression at zone | Small, tight directional candles inside SR/RS Flip zone. Confirms stalling and order collection. |
| 2 | Marubozu breaks fakeout | Single Marubozu breaks through fakeout zone. Supply/Demand zone directly ahead. Be ready. |
| 3 | Decision Point candle | Exact candle on M15/M5/M1 where price makes final rejection at SR/RS Flip level. Closes = entry trigger. |
| 4 | Fibonacci alignment (optional) | 50% · 61.8% · 70.5% · 79% aligning with zone = 90% probability boost. Only valid on existing zone. |

---

## 9. Zone Invalidation

### 9.1 Supply Zone Invalidation

```
RULE_ID: SND-INV-001
Title: Supply Zone Invalidation
Condition: Price closes a full candle body ABOVE the QML (top of Supply zone).
Action: Zone invalid. Setup cancelled. Do not enter or hold short.
```

### 9.2 Demand Zone Invalidation

```
RULE_ID: SND-INV-002
Title: Demand Zone Invalidation
Condition: Price closes a full candle body BELOW the QML (bottom of Demand zone).
Action: Zone invalid. Setup cancelled. Do not enter or hold long.
```

### 9.3 SR/RS Flip Invalidation

```
RULE_ID: SND-INV-003
Title: SR/RS Flip Level Invalidation
Condition: Price closes a candle body through and beyond the SR/RS Flip level in the wrong direction.
Action: Flip is broken — zone boundary invalid. Re-evaluate structure from scratch.
```

### 9.4 QML at Equilibrium — Skip Rule

```
RULE_ID: SND-INV-004
Title: QML at Equilibrium — Skip Trade
Condition: QML is located at the 50% midpoint of the dealing range (equilibrium).
Action: Skip the trade entirely. Do not enter. Equilibrium zones carry insufficient edge.
```

---

## 10. Zone Quality Filters

### 10.1 Premium / Discount Filter (Mandatory)

```
RULE_ID: SND-FILTER-001
Title: Premium / Discount Mandatory Filter
Rule: Every Supply or Demand zone must be located at Premium (sells) or Discount (buys).

Fibonacci mapping (swing high to low for sells / swing low to high for buys):
  0%–50%   = DISCOUNT (Demand zones / buys only)
  50%      = EQUILIBRIUM (skip all trades)
  50%–100% = PREMIUM (Supply zones / sells only)
  OTE      = 61% · 70.5% · 79% (highest probability within zone)

Any zone at equilibrium = skip. No exceptions.
```

### 10.2 Dealing Range Filter

```
RULE_ID: SND-FILTER-002
Title: Dealing Range Filter
Definition: Confined trading region between two structural points. All zone trades governed by position within range.
Rules:
  - SELL only at Premium range extreme
  - BUY only at Discount range extreme
  - Focus left-hand side of chart to identify liquidity sources
  - Execute ONLY after liquidity sweep at range extremes
  - OB + FVG + BOS/CHoCH left at zone = extra confluence
  - Price cycles: BSL → SSL → BSL → SSL — always target next liquidity draw for TP
```

### 10.3 Previous Highs/Lows Filter

```
RULE_ID: SND-FILTER-003
Title: Previous Highs/Lows Cluster Requirement
Rule: Previous Highs (sell) or Previous Lows (buy) must be a MINIMUM of 2 clustered touches at the same level.
Single touch does not qualify.
These are also called Previous Fakeouts.
Normally sit at the same QML level — when they do, zone strength multiplies significantly.
```

### 10.4 Trend Alignment Filter

```
RULE_ID: SND-FILTER-004
Title: Trend Alignment Filter
Rule: Supply zones are only traded when HTF structure is bearish (LH+LL). Demand zones are only traded when HTF structure is bullish (HH+HL).
Counter-trend SnD zones require 1D CHoCH confirmation — otherwise skip.
```

### 10.5 Fibonacci Confluence Filter

```
RULE_ID: SND-FILTER-005
Title: Fibonacci Confluence — 90% Probability Add-On
Rule: Draw Fibonacci from most recent swing Low to High (sells) or High to Low (buys).
If 50% · 61.8% · 70.5% · 79% aligns exactly with the Supply/Demand zone (QML / MPL / SR Flip) = 90% probability setup.
Fibonacci alone is meaningless — only counts when landing precisely on an already valid zone.
```

---

## 11. Market Structure Rules

- `SND-MS-001` — Cannot assume bearish structure break until a LOWER HIGH is clearly broken
- `SND-MS-002` — Cannot assume bullish structure break until a HIGHER LOW is clearly broken
- `SND-MS-003` — Liquidity grab = wick fails to close substantially beyond level — NOT a valid SR/RS Flip
- `SND-MS-004` — A real break = single Marubozu candle closing clearly above/below the level
- `SND-MS-005` — No HH+HL and no LH+LL = ranging market — no directional bias — no trade
- `SND-MS-006` — Always ask: Where is price coming from? Where is it heading to?
- `SND-MS-007` — Price runs from liquidity to liquidity. BSL cleared → seek SSL. SSL cleared → seek BSL. Always target next liquidity draw for TP.

---

*Supply & Demand Framework | Version 1.0 | 2026-03 | Proprietary*
