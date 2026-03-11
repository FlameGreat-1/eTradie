---
doc_id: smc_framework
doc_type: framework
framework: SMC
title: Smart Money Concepts Framework
version: "1.0"
status: active
author: System Owner
effective_date: "2026-03"
source_of_truth: true
updated_at: "2026-03"
---

# SMC FRAMEWORK

> Primary retrieval source for SMC structure identification, setup detection, and entry confirmation. Does not contain risk rules, grading rules, or cross-framework rules — those belong to `master_rulebook.md`.

---

## 1. Framework Overview

Smart Money Concepts (SMC) is used for price structure and liquidity analysis, focusing on institutional order flow.

SMC is used in this system for:
- **Structure identification** — determining trend direction and structural context
- **Entry precision** — locating exact entry zones via OBs, FVGs, and liquidity sweeps
- **Liquidity targeting** — identifying where institutional orders are placed and where price is drawn

SMC applies on 4H / 1H for entry precision. 1W / 1D provides directional context. M15/M5/M1 provides entry trigger confirmation.

---

## 2. Market Structure

### 2.1 Bullish Market Structure

```
RULE_ID: SMC-STRUCT-001
Title: Bullish Market Structure
Definition: Price consistently forms higher highs (HH) and higher lows (HL).
Condition: Price breaks above previous swing highs and respects previous swing lows.
Interpretation: Bullish bias. Look for long setups on retracements.
```

### 2.2 Bearish Market Structure

```
RULE_ID: SMC-STRUCT-002
Title: Bearish Market Structure
Definition: Price consistently forms lower highs (LH) and lower lows (LL).
Condition: Price breaks below previous swing lows and respects previous swing highs.
Interpretation: Bearish bias. Look for short setups on retracements.
```

### 2.3 Ranging Market

```
RULE_ID: SMC-STRUCT-003
Title: Ranging Market
Definition: Price forming neither HH+HL nor LH+LL.
Condition: Equal highs and equal lows without structural breaks.
Interpretation: No directional bias. No trade. Wait for structural break.
```

### 2.4 Internal vs External Structure

```
RULE_ID: SMC-STRUCT-004
Title: Internal Structure
Definition: Minor swing highs/lows formed within a larger move. These are inducement targets — price takes them out before reaching the real POI.

RULE_ID: SMC-STRUCT-005
Title: External Structure
Definition: Major swing highs/lows that define the overall trend. Primary BOS/CHoCH reference points.
```

### 2.5 Structure Rules

- `SMC-MS-001` — Cannot assume bearish break until a LOWER HIGH is clearly broken
- `SMC-MS-002` — Cannot assume bullish break until a HIGHER LOW is clearly broken
- `SMC-MS-003` — Liquidity grab = wick that fails to CLOSE beyond level — NOT a structural break
- `SMC-MS-004` — A break = substantial candle CLOSE above or below the level
- `SMC-MS-005` — Never guess trend change — wait for structure to confirm it
- `SMC-MS-006` — Before every entry: confirm where price is coming from AND where it is heading

---

## 3. Break of Structure (BOS)

### 3.1 Bullish BOS

```
RULE_ID: SMC-BOS-001
Title: Bullish Break of Structure
Condition: Price closes above a previous swing high — candle body close, not wick.
Interpretation: Bullish continuation. Demand zones expected to form.
Action: Wait for retracement to OB or OTE — never enter on the BOS candle.
```

### 3.2 Bearish BOS

```
RULE_ID: SMC-BOS-002
Title: Bearish Break of Structure
Condition: Price closes below a previous swing low — candle body close, not wick.
Interpretation: Bearish continuation. Supply zones expected to form.
Action: Wait for retracement to OB or OTE — never enter on the BOS candle.
```

### 3.3 Failure Swing (SMS)

```
RULE_ID: SMC-BOS-003
Title: Failure Swing — SMS (Shift in Market Structure)
Condition (Bearish SMS): Uptrend fails to break last swing high → closes below previous swing low.
Condition (Bullish SMS): Downtrend fails to break last swing low → closes above previous swing high.
Interpretation: Trend exhaustion. Potential reversal.
Requirement: SMS must be confirmed by BMS in the opposite direction before trading reversal.
```

---

## 4. Change of Character (CHoCH)

### 4.1 Bullish CHoCH

```
RULE_ID: SMC-CHOCH-001
Title: Bullish Change of Character
Condition: In bearish structure, price breaks the last lower high — first BOS to the upside.
Interpretation: Earliest signal of potential bullish shift.
Action: NOT a standalone entry. Wait for BMS confirmation → then RTO to Bullish OB.
Sequence: CHoCH → BMS higher confirms → entry on retracement to Bullish OB.
```

### 4.2 Bearish CHoCH

```
RULE_ID: SMC-CHOCH-002
Title: Bearish Change of Character
Condition: In bullish structure, price breaks the last higher low — first BOS to the downside.
Interpretation: Earliest signal of potential bearish shift.
Action: NOT a standalone entry. Wait for BMS confirmation → then RTO to Bearish OB.
Sequence: CHoCH → BMS lower confirms → entry on retracement to Bearish OB.
```

### 4.3 CHoCH on 4H Within HTF Trend

```
RULE_ID: SMC-CHOCH-003
Title: CHoCH as Pullback Exhaustion Signal
Condition: CHoCH occurs on 4H within a 1D bullish or bearish trend.
Interpretation: Retracement is ending — trend resuming. Entry context for continuation trades.
```

---

## 5. Order Blocks (OB)

### 5.1 Bullish Order Block

```
RULE_ID: SMC-OB-001
Title: Bullish Order Block
Definition: The last bearish candle before a strong bullish displacement that caused BMS higher.
Requirements:
  - Must precede bullish displacement
  - Displacement must result in BMS higher
  - Must produce an FVG
  - Must not be previously mitigated
Entry zone: High to low of OB candle. OTE refined entry: 62–79% into OB.
SL: Below OB low.
```

### 5.2 Bearish Order Block

```
RULE_ID: SMC-OB-002
Title: Bearish Order Block
Definition: The last bullish candle before a strong bearish displacement that caused BMS lower.
Requirements:
  - Must precede bearish displacement
  - Displacement must result in BMS lower
  - Must produce an FVG
  - Must not be previously mitigated
Entry zone: High to low of OB candle. OTE refined entry: 62–79% into OB.
SL: Above OB high.
```

### 5.3 Valid OB Criteria

```
RULE_ID: SMC-OB-003
Title: Valid Order Block Criteria
ALL must be true:
  1. Strong impulse departure from OB
  2. Impulse results in BOS or CHoCH
  3. OB has not been previously mitigated
  4. Associated FVG is present
  5. Located at Premium (bearish OB) or Discount (bullish OB)
```

### 5.4 OB Invalidation

```
RULE_ID: SMC-OB-004
Title: Order Block Invalidation
Condition:
  - Bullish OB: price closes below OB low
  - Bearish OB: price closes above OB high
Action: OB invalid. Do not trade. Remove from consideration.
```

### 5.5 Breaker Block

```
RULE_ID: SMC-OB-005
Title: Breaker Block
Definition: A previously valid OB that has been mitigated — price traded through and closed beyond it.
Behavior: On return from the other side → acts as new resistance (former support) or new support (former resistance).
Weight: Lower than fresh OBs. Requires additional confluence to qualify as entry.
```

### 5.6 The 7 Rules of a Tradeable OB

An OB must satisfy ALL seven:

| # | Rule |
|---|------|
| 1 | Sponsors a BOS or CHoCH |
| 2 | Has associated FVG / imbalance |
| 3 | Has liquidity or inducement present |
| 4 | Takes out an opposing OB |
| 5 | Located at Premium (sells) or Discount (buys) |
| 6 | Has FVG and OB in subsequent timeframe (BPR — FVG within FVG, OB within OB) |
| 7 | HTF OB selected and refined to LTF for entry |

---

## 6. Fair Value Gaps (FVG)

### 6.1 Bullish FVG

```
RULE_ID: SMC-FVG-001
Title: Bullish Fair Value Gap
Definition: 3-candle pattern where the low of candle 3 is above the high of candle 1.
Condition: Wick of candle 1 does not overlap with wick of candle 3.
Interpretation: Inefficient price delivery (more buyers than sellers). Price will return to fill.
Strongest when: Within or adjacent to a Bullish OB on the same timeframe.
```

### 6.2 Bearish FVG

```
RULE_ID: SMC-FVG-002
Title: Bearish Fair Value Gap
Definition: 3-candle pattern where the high of candle 3 is below the low of candle 1.
Condition: Wick of candle 1 does not overlap with wick of candle 3.
Interpretation: Inefficient price delivery (more sellers than buyers). Price will return to fill.
Strongest when: Within or adjacent to a Bearish OB on the same timeframe.
```

### 6.3 FVG Mitigation

```
RULE_ID: SMC-FVG-003
Title: FVG Mitigation
Condition: Price trades back to the 50% level of the FVG.
Interpretation: FVG mitigated. Reduced significance as entry target after mitigation.
Note: FVG within FVG on subsequent timeframe = extra confluence before mitigation.
```

### 6.4 FVG Invalidation

```
RULE_ID: SMC-FVG-004
Title: FVG Invalidation
Condition: Price closes a full candle body through and beyond the entire FVG range.
Action: FVG invalid. Remove from consideration.
Note: OB without associated FVG is significantly weaker — treat with reduced confidence.
```

---

## 7. Liquidity Concepts

### 7.1 Buy-Side Liquidity (BSL)

```
RULE_ID: SMC-LIQ-001
Title: Buy-Side Liquidity
Definition: Stop-loss orders of sell positions resting ABOVE swing highs.
Locations: PMH · PWH · PDH · HOD · Old Highs · Equal Highs
Behavior: BSL swept → market reverses DOWN. Banks used BSL to place sell orders.
```

### 7.2 Sell-Side Liquidity (SSL)

```
RULE_ID: SMC-LIQ-002
Title: Sell-Side Liquidity
Definition: Stop-loss orders of buy positions resting BELOW swing lows.
Locations: PML · PWL · PDL · LOD · Old Lows · Equal Lows
Behavior: SSL swept → market reverses UP. Banks used SSL to place buy orders.
```

### 7.3 Liquidity Sweep

```
RULE_ID: SMC-LIQ-003
Title: Liquidity Sweep / Stop Hunt
Definition: Price temporarily exceeds a key swing high/low to activate stops before reversing sharply.
Valid condition: Price rejects AND closes back inside the range. Wick without close-back = not confirmed.
BSL sweep + close back below → bearish reversal.
SSL sweep + close back above → bullish reversal.
Highest quality: Sweeps into 4H OBs or 1D FVGs.
```

### 7.4 Inducement (IDM)

```
RULE_ID: SMC-LIQ-004
Title: Inducement
Definition: Engineered false move to trap traders into premature entry at the wrong level.
Locations: Internal swing highs/lows — minor structure inside a larger move.
Behavior: Price ALWAYS takes out IDM before moving to the real POI.
Rule: Never enter at inducement. Wait for IDM swept → then enter at real OB/POI.
```

### 7.5 Equal Highs / Equal Lows

```
RULE_ID: SMC-LIQ-005
Title: Equal Highs and Equal Lows
Equal Highs = BSL resting above → prime SH target before selling.
Equal Lows = SSL resting below → prime SH target before buying.
Rule: When equal highs/lows visible — expect sweep of that level before the real move.
```

### 7.6 Compression Liquidity

```
RULE_ID: SMC-LIQ-006
Title: Compression Liquidity
Definition: Small, messy, slow-moving candles in a tight range moving directionally (up or down).
NOT consolidation (consolidation = equal highs/lows). Compression is directional.
Behavior: Price collecting pending orders. Compression spike ends → sell-off or buy-off. Mostly trend continuation.
```

### 7.7 Liquidity Cycle

```
RULE_ID: SMC-LIQ-007
Title: Price Runs From Liquidity to Liquidity
Rule: Price runs from liquidity to liquidity on every timeframe without exception.
BSL cleared → price reverses seeking SSL.
SSL cleared → price reverses seeking BSL.
Action: Execute after liquidity grab. Target = next BSL or SSL pool.
```

---

## 8. Displacement

### 8.1 Bullish Displacement

```
RULE_ID: SMC-DISP-001
Title: Bullish Displacement
Definition: Strong impulsive bullish move — large candle bodies, minimal wicks, minimal retracement — indicating heavy institutional buying.
Requirements:
  - Large full-bodied candles
  - Leaves FVG behind
  - Results in BOS higher
Interpretation: Institutional participation confirmed. OB formed at origin of move.
```

### 8.2 Bearish Displacement

```
RULE_ID: SMC-DISP-002
Title: Bearish Displacement
Definition: Strong impulsive bearish move — large candle bodies, minimal wicks, minimal retracement — indicating heavy institutional selling.
Requirements:
  - Large full-bodied candles
  - Leaves FVG behind
  - Results in BOS lower
Interpretation: Institutional participation confirmed. OB formed at origin of move.
```

### 8.3 Displacement Validity Rule

```
RULE_ID: SMC-DISP-003
Title: Displacement Validity
Rule: An OB is only valid when its associated move qualifies as displacement.
Weak departure (small candles, overlapping wicks, no FVG) = OB is not valid.
Strong displacement = institutional sponsorship confirmed.
```

---

## 9. Mitigation

### 9.1 Order Block Mitigation

```
RULE_ID: SMC-MIT-001
Title: Order Block Mitigation
Definition: Price returning to an OB after creation — institutions adding to or exiting positions at origin.
Condition: Price retraces into OB zone after initial displacement.
Entry: First return to unmitigated OB = highest probability entry.
Invalidation: Price closes full candle body beyond OB → mitigated → invalid.
```

### 9.2 FVG Mitigation

```
RULE_ID: SMC-MIT-002
Title: FVG Mitigation
Definition: Price filling the imbalance left by displacement.
Condition: Price trades back to 50% level of FVG.
Behavior: Price always seeks to fill FVGs before continuing in trend direction.
Note: Partially filled FVG retains some relevance. Fully filled FVG loses significance.
```

### 9.3 Premium / Discount / Dealing Range

```
RULE_ID: SMC-MIT-003
Title: Premium, Discount and Dealing Range
Definition: Confined trading region between two structural points. All mitigation and entry decisions governed by Premium/Discount position.
Rule: SELL only at Premium. BUY only at Discount. No trades at equilibrium (50%).

Fibonacci mapping (draw from swing high to low for sells / low to high for buys):
  0%–50%   = DISCOUNT (buy zone)
  50%      = EQUILIBRIUM (no entries)
  50%–100% = PREMIUM (sell zone)
  OTE      = 61% · 70.5% · 79% (highest probability entry)

Price cycles inside range: Premium → Discount → BSL → SSL → repeat.
Execute ONLY after liquidity sweep at range extremes. OB + FVG + BOS/CHoCH = high-confidence entry.
```

---

## 10. Entry Logic

### 10.1 Standard Entry Setup

```
RULE_ID: SMC-ENTRY-001
Title: Standard SMC Entry
Conditions (ALL required):
  1. HTF bias aligned — 1W + 1D BOS/CHoCH in trade direction
  2. Liquidity sweep confirmed — BSL (shorts) or SSL (longs) — closed back inside range
  3. CHoCH on entry TF (4H or 1H) — first reversal signal
  4. BMS confirms reversal direction
  5. Price returns to valid OB (meets SMC-OB-003)
  6. OB has associated FVG
  7. OB at Premium (shorts) or Discount (longs)
Entry: OB zone — refined to OTE (62–79%)
SL: Beyond OB invalidation level
Target: Next BSL or SSL pool
```

### 10.2 Sell Patterns

| ID | Pattern | Trigger Sequence |
|----|---------|-----------------|
| SMC-SELL-001 | Turtle Soup Short | BSL raids 5–20+ pips above → bearish close back below → SELL → min 10 pip SL |
| SMC-SELL-002 | SH + BMS + RTO | BSL taken → BMS lower → retrace to Bearish OB → SELL → SL above OB |
| SMC-SELL-003 | SMS + BMS + RTO | Uptrend SMS → BMS lower → retrace to Bearish OB → SELL → SL above OB |
| SMC-SELL-004 | Bearish AMD | Asian range → London/NY UP above BSL → reverses DOWN → SELL on Distribution |
| SMC-SELL-005 | TS + SH + BMS + RTO | BSL raided + BMS lower simultaneously → retrace to Bearish OB → SELL |

### 10.3 Buy Patterns

| ID | Pattern | Trigger Sequence |
|----|---------|-----------------|
| SMC-BUY-001 | Turtle Soup Long | SSL raids 5–20+ pips below → bullish close back above → BUY → min 10 pip SL |
| SMC-BUY-002 | SH + BMS + RTO | SSL taken → BMS higher → retrace to Bullish OB → BUY → SL below OB |
| SMC-BUY-003 | SMS + BMS + RTO | Downtrend SMS → BMS higher → retrace to Bullish OB → BUY → SL below OB |
| SMC-BUY-004 | Bullish AMD | Asian range → London/NY DOWN below SSL → reverses UP → BUY on Distribution |
| SMC-BUY-005 | TS + SH + BMS + RTO | SSL raided + BMS higher simultaneously → retrace to Bullish OB → BUY |

### 10.4 Pattern Ranking

| Rank | Pattern | Reason |
|------|---------|--------|
| 1 | TS + SH + BMS + RTO (SELL-005/BUY-005) | Both setups confirm simultaneously |
| 2 | AMD + SH + BMS + RTO (SELL-004/BUY-004) | Session + liquidity + structure aligned |
| 3 | SH + BMS + RTO (SELL-002/BUY-002) | Core flagship setup |
| 4 | SMS + BMS + RTO (SELL-003/BUY-003) | Reversal confirmation |
| 5 | Turtle Soup standalone (SELL-001/BUY-001) | Baseline — needs session confluence |

### 10.5 Confluence Combinations

| Combination | Type |
|-------------|------|
| BOS + FVG + IDM + RTO | Continuation |
| SMS + CHoCH + IDM + FVG + RTO | Reversal |
| OB + BOS + FVG + IDM | Directional continuation |
| TS + SH + BMS + RTO | Sweep + structure |
| AMD + SH + BMS + RTO + Session | Full AMD cycle |

### 10.6 LTF Entry Confirmation (M15/M5/M1)

After full pattern confirmed on HTF and mid-TF — drop to LTF and wait for ALL:

| # | Confirmation | Condition |
|---|-------------|-----------|
| 1 | Liquidity Taken | SH complete — swept BSL/SSL and CLOSED back inside range. Wick only = not confirmed. |
| 2 | CHoCH on LTF | First order flow shift on M15/M5. Earliest reversal signal. |
| 3 | BMS Confirmed | Full BMS on LTF confirming direction. Do not enter on CHoCH alone. |
| 4 | RTO to LTF OB | OB must have FVG. OB at Premium (sells) or Discount (buys). SL beyond OB. |
| 5 | Session Timing | London Open or NY Open. Outside windows = wait unless clear HTF level retested. |
| 6 | IDM Cleared | Internal inducement swept. If not cleared — price will take it out first — wait. |

---

## 11. Setup Invalidation

### 11.1 OB Invalidation

```
RULE_ID: SMC-INV-001
Title: Order Block Invalidation
Condition:
  - Long: candle closes below Bullish OB low
  - Short: candle closes above Bearish OB high
Action: Setup invalid. Do not enter or close existing. Log as structural invalidation.
```

### 11.2 Structural Invalidation

```
RULE_ID: SMC-INV-002
Title: Structural Invalidation
Condition: 4H BOS confirmed in opposite direction while in trade.
Action: Tighten SL to most recent 4H swing. Prepare for exit.
```

### 11.3 HTF Thesis Invalidation

```
RULE_ID: SMC-INV-003
Title: HTF Thesis Invalidation
Condition: 1D candle closes beyond the SL invalidation zone.
Action: Close trade immediately. Log as structural invalidation.
```

### 11.4 Sweep Failure Invalidation

```
RULE_ID: SMC-INV-004
Title: Liquidity Sweep Failure
Condition: Price sweeps liquidity level but fails to close back inside range — continues in sweep direction.
Interpretation: Sweep was a genuine breakout, not a stop hunt.
Action: No entry. Setup invalid. Remove from consideration.
```

### 11.5 Mitigated OB Invalidation

```
RULE_ID: SMC-INV-005
Title: Mitigated OB
Condition: Price has already traded through and closed beyond the OB body on a prior visit.
Action: OB is mitigated — invalid as entry. Do not trade mitigated OBs.
```

---

*SMC Framework | Version 1.0 | 2026-03 | Proprietary*
