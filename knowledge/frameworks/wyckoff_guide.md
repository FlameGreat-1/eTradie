---
doc_id: wyckoff_guide
doc_type: framework
framework: Wyckoff
title: Wyckoff Market Cycle Guide
version: "1.0"
status: active
author: System Owner
effective_date: "2026-03"
source_of_truth: true
updated_at: "2026-03"
---

# WYCKOFF MARKET CYCLE GUIDE

> Wyckoff is **contextual confirmation** in this system — not a primary entry framework. It strengthens or weakens setup confidence when combined with SMC and SnD signals. Does not contain entry mechanics, risk rules, or confluence scoring.

---

## 1. Framework Overview

Wyckoff methodology describes how large institutional operators (the Composite Operator) engineer price cycles to accumulate and distribute positions against retail traders.

Price does not move randomly — it moves in planned phases driven by institutional order flow:

- **Accumulation** — institutions buy while retail sells into weakness
- **Markup** — price advances; institutions already positioned
- **Distribution** — institutions sell while retail buys into strength
- **Markdown** — price declines; institutions already short or exited

The cycle repeats continuously on all timeframes. Higher timeframe Wyckoff phase defines the macro environment. Lower timeframe sub-cycles form within each phase.

```
RULE_ID: WYCKOFF-OVR-001
Title: Composite Operator Principle
Definition: All price movement is engineered by large operators accumulating or distributing positions. Retail traders provide the liquidity. The Composite Operator absorbs retail buy orders during distribution and retail sell orders during accumulation.
Interpretation: Never trade against the identified phase of the Composite Operator.
```

---

## 2. Wyckoff Market Cycle

```
RULE_ID: WYCKOFF-CYCLE-001
Title: Full Market Cycle
Sequence: Accumulation → Markup → Distribution → Markdown → Accumulation (repeats)
Rule: Every trend has a cause (accumulation/distribution range) and an effect (markup/markdown). The larger the range, the larger the subsequent move.
Timeframe context:
  - 1W/1D = macro cycle phase (highest authority)
  - 4H/1H = intermediate sub-cycle within macro
  - M30/M15 = entry-level sub-cycle
Principle: Always identify the current phase on the highest available timeframe before evaluating a setup.
```

---

## 3. Accumulation Phase

```
RULE_ID: WYCKOFF-ACC-001
Title: Accumulation Phase
Definition: Sideways range where the Composite Operator absorbs sell orders and builds long positions at low prices while retail traders continue selling.
Characteristics:
  - Range-bound structure — no clear HH+HL or LH+LL
  - Repeated tests of support with decreasing selling pressure
  - Volume declining on down moves (supply drying up)
  - Occasional sharp drops that quickly recover (Springs)
  - Price closes in the upper half of the range increasingly
Location: Bottom of a markdown trend — discount pricing
Implication: Bullish setup probability increases. Demand zones forming in this area carry higher weight.
```

---

## 4. Accumulation Events

```
RULE_ID: WYCKOFF-ACC-EVENT-001
Title: PS — Preliminary Support
Definition: First noticeable support after a prolonged decline. Volume increases and spread widens — signals that buying is beginning to absorb selling. Does not end the downtrend alone.
```

```
RULE_ID: WYCKOFF-ACC-EVENT-002
Title: SC — Selling Climax
Definition: Aggressive high-volume panic selling candle(s) that mark the exhaustion of the markdown phase. Wide spread down candle closed off lows — institutions absorbing retail panic.
Signal: Largest volume bar in the decline. Price closes well off the low.
```

```
RULE_ID: WYCKOFF-ACC-EVENT-003
Title: AR — Automatic Rally
Definition: Sharp relief bounce after the SC as selling pressure dries up instantly. Defines the top of the accumulation range. AR high = upper boundary of the range.
```

```
RULE_ID: WYCKOFF-ACC-EVENT-004
Title: ST — Secondary Test
Definition: Price returns to the SC area to test whether supply has been exhausted. Volume and spread must be noticeably lower than the SC — confirms selling pressure diminished.
Failure: If ST shows equal or greater volume than SC — accumulation may not be complete.
```

```
RULE_ID: WYCKOFF-ACC-EVENT-005
Title: Spring
Definition: A deliberate price sweep below the accumulation range low to trigger retail stop losses and absorb final sell orders before markup. The Spring is the engineered liquidity grab — equivalent to SSL sweep in SMC.
Types:
  - Type 1 Spring: Deep break below range — strong bearish close
  - Type 2 Spring: Moderate break — quick recovery
  - Type 3 Spring (No Spring): Shallow wick — rarely breaks support
Highest probability: Type 2 — moderate sweep with strong bullish recovery close
Signal: Spring + low volume on the sweep + strong close back inside range = accumulation complete.
```

```
RULE_ID: WYCKOFF-ACC-EVENT-006
Title: Test of Spring
Definition: After the Spring, price returns to test the Spring low with significantly reduced volume. Confirms supply is exhausted. Low volume test = institutions absorbing — markup imminent.
Rule: Test must show lower volume than the Spring. High volume test = Spring may fail — wait.
```

```
RULE_ID: WYCKOFF-ACC-EVENT-007
Title: SOS — Sign of Strength
Definition: Strong bullish advance on increased volume breaking above the AR high. Confirms institutional buying is in control and markup phase is beginning.
```

```
RULE_ID: WYCKOFF-ACC-EVENT-008
Title: LPS — Last Point of Support
Definition: Retracement after SOS on low volume — price finds support above the Spring. This is the final entry opportunity before full markup. Equivalent to RTO to Bullish OB in SMC.
```

---

## 5. Markup Phase

```
RULE_ID: WYCKOFF-MARKUP-001
Title: Markup Phase
Definition: Sustained bullish trend following completion of accumulation. The Composite Operator is fully positioned long and price advances with minimal resistance.
Characteristics:
  - Clear HH + HL structure
  - Impulsive moves on increased volume
  - Shallow pullbacks on reduced volume (LPS forming)
  - Pullbacks find support at former resistance (RS Flip / OB zones)
  - Volatility increases on up moves, decreases on retracements
Implication: Only long setups. SnD Demand zones and SMC Bullish OBs on pullbacks carry highest probability. Short setups invalid unless 1D CHoCH confirmed.
```

```
RULE_ID: WYCKOFF-MARKUP-002
Title: Re-accumulation Within Markup
Definition: Temporary sideways consolidation mid-trend before continuation. Smaller version of accumulation — institutions adding to longs before next leg up.
Identification: Tight range forming after an impulsive advance. Spring may occur within range. Low volume during range = healthy re-accumulation.
Implication: Continuation trade — buy Demand zones at range lows.
```

---

## 6. Distribution Phase

```
RULE_ID: WYCKOFF-DIST-001
Title: Distribution Phase
Definition: Sideways range at high prices where the Composite Operator sells long positions and builds short positions while retail traders buy into perceived strength.
Characteristics:
  - Range-bound after extended markup
  - Repeated tests of resistance with decreasing buying pressure
  - Volume increasing on up moves but price not advancing (supply overwhelming demand)
  - Occasional sharp spikes above range that quickly reverse (Upthrusts)
  - Price closes in the lower half of the range increasingly
Location: Top of a markup trend — premium pricing
Implication: Bearish setup probability increases. Supply zones forming in this area carry higher weight.
```

---

## 7. Distribution Events

```
RULE_ID: WYCKOFF-DIST-EVENT-001
Title: PSY — Preliminary Supply
Definition: First noticeable resistance after a prolonged advance. Volume increases and spread widens on up move — signals that selling is beginning to absorb buying. Does not end the uptrend alone.
```

```
RULE_ID: WYCKOFF-DIST-EVENT-002
Title: BC — Buying Climax
Definition: Aggressive high-volume euphoric buying candle(s) marking the exhaustion of the markup phase. Wide spread up candle closed off highs — institutions distributing into retail buying.
Signal: Largest volume bar in the advance. Price closes well off the high.
```

```
RULE_ID: WYCKOFF-DIST-EVENT-003
Title: AR — Automatic Reaction
Definition: Sharp sell-off after the BC as buying pressure dries up. Defines the bottom of the distribution range. AR low = lower boundary of the range.
```

```
RULE_ID: WYCKOFF-DIST-EVENT-004
Title: ST — Secondary Test
Definition: Price returns to the BC area to test whether demand has been exhausted. Volume and spread must be noticeably lower than the BC — confirms buying pressure diminished.
Failure: If ST shows equal or greater volume to BC — distribution may not be complete.
```

```
RULE_ID: WYCKOFF-DIST-EVENT-005
Title: Upthrust (UT)
Definition: A deliberate price spike above the distribution range high to trigger retail buy stops and absorb final buy orders before markdown. The Upthrust is the engineered liquidity grab — equivalent to BSL sweep in SMC.
Signal: Upthrust + high volume on spike + bearish close back inside range = distribution progressing.
```

```
RULE_ID: WYCKOFF-DIST-EVENT-006
Title: UTAD — Upthrust After Distribution
Definition: A final, more decisive Upthrust that occurs after the range has been established — often the last trap before markdown. Larger and more convincing than the initial UT.
Signal: UTAD on diminishing volume relative to the BC = strongest distribution signal. Equivalent to terminal BSL sweep in SMC combined with Bearish OB formation.
```

```
RULE_ID: WYCKOFF-DIST-EVENT-007
Title: SOW — Sign of Weakness
Definition: Strong bearish decline on increased volume breaking below the AR low. Confirms institutional selling in control and markdown phase is beginning.
```

```
RULE_ID: WYCKOFF-DIST-EVENT-008
Title: LPSY — Last Point of Supply
Definition: Weak rally after SOW on low volume — price finds resistance below the Upthrust. Final distribution opportunity before full markdown. Equivalent to RTO to Bearish OB in SMC.
```

---

## 8. Markdown Phase

```
RULE_ID: WYCKOFF-MARKDOWN-001
Title: Markdown Phase
Definition: Sustained bearish trend following completion of distribution. The Composite Operator is fully positioned short and price declines with minimal support.
Characteristics:
  - Clear LH + LL structure
  - Impulsive moves lower on increased volume
  - Shallow rallies on reduced volume (LPSY forming)
  - Rallies find resistance at former support (SR Flip / Bearish OB zones)
  - Volatility increases on down moves, decreases on rallies
Implication: Only short setups. SnD Supply zones and SMC Bearish OBs on rallies carry highest probability. Long setups invalid unless 1D CHoCH confirmed.
```

```
RULE_ID: WYCKOFF-MARKDOWN-002
Title: Re-distribution Within Markdown
Definition: Temporary sideways consolidation mid-trend before continuation lower. Smaller version of distribution — institutions adding to shorts before next leg down.
Identification: Tight range forming after an impulsive decline. Upthrust may occur within range. Low volume during range = healthy re-distribution.
Implication: Continuation trade — sell Supply zones at range highs.
```

---

## 9. Phase Identification

```
RULE_ID: WYCKOFF-PHASE-001
Title: Accumulation Identification
Conditions:
  - Range-bound market at bottom of prior markdown
  - Repeated support tests with declining volume
  - At least one Spring visible (sweep below range low with recovery)
  - SOS break above AR high
  - Price at Discount pricing (0%–50% Fibonacci range)
Action: Treat bullish SnD and SMC setups as higher probability.
```

```
RULE_ID: WYCKOFF-PHASE-002
Title: Distribution Identification
Conditions:
  - Range-bound market at top of prior markup
  - Repeated resistance tests with declining momentum
  - At least one Upthrust visible (spike above range high with rejection)
  - SOW break below AR low
  - Price at Premium pricing (50%–100% Fibonacci range)
Action: Treat bearish SnD and SMC setups as higher probability.
```

```
RULE_ID: WYCKOFF-PHASE-003
Title: Markup Identification
Conditions:
  - Clear HH + HL structure on 1D or 4H
  - Impulsive advances on volume, shallow pullbacks on low volume
  - Price consistently closing upper half of daily range
  - Pullbacks holding above key SnD Demand zones
Action: Long bias only. Re-accumulation ranges are continuation entry opportunities.
```

```
RULE_ID: WYCKOFF-PHASE-004
Title: Markdown Identification
Conditions:
  - Clear LH + LL structure on 1D or 4H
  - Impulsive declines on volume, shallow rallies on low volume
  - Price consistently closing lower half of daily range
  - Rallies rejected at key SnD Supply zones
Action: Short bias only. Re-distribution ranges are continuation entry opportunities.
```

```
RULE_ID: WYCKOFF-PHASE-005
Title: Ambiguous Phase — No Bias
Condition: Cannot clearly identify accumulation, distribution, markup, or markdown on HTF.
Action: No Wyckoff phase bonus applied to confluence. System proceeds on SMC + SnD signals alone.
```

---

## 10. Trading Interpretation

```
RULE_ID: WYCKOFF-TRADING-001
Title: Accumulation Bias
Phase: Accumulation (Spring visible / SOS confirmed)
Interpretation: Bullish setups have higher probability. Spring = equivalent to SSL sweep + Bullish OB formation in SMC. Add +1 Wyckoff confluence to bullish setups inside Demand zones.
Action: Prioritize long setups at Discount zones. Avoid shorts unless strong structural reason.
```

```
RULE_ID: WYCKOFF-TRADING-002
Title: Markup Bias
Phase: Markup (HH+HL confirmed on 1D/4H)
Interpretation: Trend continuation setups have highest probability. Pullbacks to LPS / Demand zones = entry. Re-accumulation ranges = continuation opportunity.
Action: Long only. SnD Demand zones + SMC Bullish OBs on low-volume retracements = highest probability entries.
```

```
RULE_ID: WYCKOFF-TRADING-003
Title: Distribution Bias
Phase: Distribution (Upthrust visible / SOW confirmed)
Interpretation: Bearish setups have higher probability. Upthrust/UTAD = equivalent to BSL sweep + Bearish OB formation in SMC. Add +1 Wyckoff confluence to bearish setups inside Supply zones.
Action: Prioritize short setups at Premium zones. Avoid longs unless strong structural reason.
```

```
RULE_ID: WYCKOFF-TRADING-004
Title: Markdown Bias
Phase: Markdown (LH+LL confirmed on 1D/4H)
Interpretation: Trend continuation setups have highest probability. Rallies to LPSY / Supply zones = entry. Re-distribution ranges = continuation opportunity.
Action: Short only. SnD Supply zones + SMC Bearish OBs on low-volume rallies = highest probability entries.
```

```
RULE_ID: WYCKOFF-TRADING-005
Title: Spring and Upthrust — SMC Alignment
Spring aligns with: SSL sweep → Bullish OB → SH+BMS+RTO (BUY-002) or Turtle Soup Long (BUY-001)
Upthrust/UTAD aligns with: BSL sweep → Bearish OB → SH+BMS+RTO (SELL-002) or Turtle Soup Short (SELL-001)
Rule: When a Spring or Upthrust/UTAD aligns with a valid SMC setup AND a fresh SnD zone — Wyckoff phase confirmation adds maximum confluence weight.
```

```
RULE_ID: WYCKOFF-TRADING-006
Title: Wyckoff Phase — Confluence Weight
Wyckoff phase aligned with trade direction = +1 to confluence score (per master_rulebook.md)
Wyckoff phase opposed to trade direction = treat as caution flag — reduce position size or skip
Wyckoff phase ambiguous = neutral — no bonus, no penalty
```

---

*Wyckoff Market Cycle Guide | Version 1.0 | 2026-03 | Proprietary*
