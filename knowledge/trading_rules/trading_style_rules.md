---
doc_id: trading_style_rules
doc_type: rulebook
framework: TradingStyle
title: Trading Style and Operational Rules
version: "1.0"
status: active
author: System Owner
effective_date: "2026-03"
updated_at: "2026-03"
source_of_truth: true
---

# TRADING STYLE AND OPERATIONAL RULES

> Defines how the strategy operates — permitted markets, timeframes, setup types, risk management, trade management, holding periods, session constraints, and avoidance conditions. Does not define SMC, SnD, Wyckoff, or macro frameworks — those live in their own documents.

---

## 1. Trading Style Overview

```
RULE_ID: STYLE-001
Title: System Trading Personality
Definition: The system executes structured institutional price action setups only. It is selective, patient, and rule-governed. It does not chase price, trade on impulse, or deviate from documented frameworks.
Implication: Quality over quantity. One high-conviction setup is worth more than ten marginal ones. The system waits for the market to come to it.
```

```
RULE_ID: STYLE-002
Title: Four Permitted Trading Styles
Definition: The system operates in one of four modes. Only one mode is active at any time.

| Style | Holding Period | Priority TFs | Min R:R | Target R:R |
|-------|---------------|-------------|---------|-----------|
| Scalping | Minutes–2 hours | 1D/4H/1H/15M | 1:2 | 1:3 |
| Intraday | Same session | 1W/1D/4H/1H | 1:3 | 1:5 |
| Swing | 2–10 days | 1W/1D/4H/1H | 1:3 | 1:5+ |
| Positional | Weeks–months | 1M/1W/1D | 1:5 | 1:10+ |

Rule: Active style is set on the dashboard before the analysis cycle begins. All rules below apply to the active style only.
```

---

## 2. Permitted Markets

```
RULE_ID: STYLE-MARKET-001
Title: Permitted Instruments
Definition: System trades any instrument selected by the trader from the dashboard. No fixed pair list.

Supported categories:
  FX Majors: EUR/USD · GBP/USD · USD/JPY · AUD/USD · NZD/USD · USD/CAD · USD/CHF
  FX Minors: EUR/GBP · EUR/JPY · GBP/JPY · AUD/JPY · EUR/AUD · GBP/CAD
  Metals: XAU/USD (Gold) · XAG/USD (Silver)
  Indices: US30 · SPX500 · NAS100 · GER40 (where broker liquidity is sufficient)

Implication: Same SMC/SnD/Wyckoff framework applies universally to all instruments.
```

```
RULE_ID: STYLE-MARKET-002
Title: Instrument Liquidity Requirement
Definition: Only trade instruments with sufficient bid-ask spread and volume to support clean institutional price action.
Condition: Spread must not exceed 2x the pair's normal average spread at time of entry.
Action: If spread is elevated at entry time → skip setup regardless of technical quality.
```

```
RULE_ID: STYLE-MARKET-003
Title: Maximum Active Pairs
Definition: Maximum 3 instruments with open trades simultaneously (aligned with portfolio risk rules in master_rulebook.md).
Rule: When at 3 open trades — no new entries regardless of setup quality. Wait for a trade to close first.
```

---

## 3. Timeframe Structure

```
RULE_ID: STYLE-TF-001
Title: Top-Down Timeframe Execution — Mandatory
Definition: Every trade must be analyzed from HTF to LTF in sequence. Never start analysis on the entry timeframe.

Scalping:   1D (bias) → 4H/1H (structure) → 15M/5M (setup) → M1 (entry trigger)
Intraday:   1W/1D (bias) → 4H/1H (setup + confirmation) → 15M/5M (entry trigger)
Swing:      1W/1D (bias + structure) → 4H/1H (setup + OB) → 15M (entry refinement)
Positional: 1M/1W (bias) → 1D (structure + setup) → 4H (entry refinement)

Rule: HTF bias governs direction. LTF governs entry and exit precision. Never trade LTF signals against HTF structure.
```

```
RULE_ID: STYLE-TF-002
Title: Timeframe Confluence Weight
Definition: Signals that appear on multiple timeframes simultaneously carry higher weight.
  Setup visible on 1D + 4H + 1H = maximum conviction (A+ grade candidate)
  Setup visible on 4H + 1H only = standard conviction (A grade candidate)
  Setup visible on 1H only without HTF backing = reduced conviction (B grade or reject)
```

---

## 4. Permitted Setup Types

```
RULE_ID: STYLE-SETUP-001
Title: Permitted Setup Origins
Definition: All trades must originate from one or more of the following frameworks:
  - SMC: SH+BMS+RTO · SMS+BMS+RTO · Turtle Soup · AMD cycle
  - SnD: QML + SR/RS Flip + Fakeout patterns (all 14 patterns)
  - Combined: SMC setup inside a valid SnD zone = highest quality
  - Wyckoff: Spring/Upthrust entry within Accumulation/Distribution phase
Rule: Random price movement without structural framework backing = no trade.
```

```
RULE_ID: STYLE-SETUP-002
Title: Minimum Confluence Requirement
Definition: A setup must have a minimum of 3 confluence factors before execution (per master_rulebook.md Section 4).
Single-factor setups are rejected regardless of how clean they appear.
```

```
RULE_ID: STYLE-SETUP-003
Title: HTF Zone Requirement
Definition: Every entry must be inside or at a valid 4H or higher Supply/Demand zone or Order Block.
Entries in the middle of price range without a structural zone = rejected.
```

```
RULE_ID: STYLE-SETUP-004
Title: Trend Alignment Requirement
Definition: Trades must align with HTF BMS direction.
  Counter-trend entries: only permitted with confirmed 1D CHoCH + minimum B grade confluence.
  Full trend entries (HTF aligned): permitted at A/A+/B grade.
```

---

## 5. Risk-to-Reward Requirements

```
RULE_ID: STYLE-RR-001
Title: Minimum R:R by Style

| Style | Minimum R:R | Target R:R | Reject if below |
|-------|------------|-----------|----------------|
| Scalping | 1:2 | 1:3 | 1:2 |
| Intraday | 1:3 | 1:5 | 1:3 |
| Swing | 1:3 | 1:5+ | 1:3 |
| Positional | 1:5 | 1:10+ | 1:5 |

Rule: R:R calculated from entry price to structural SL (denominator) vs entry price to TP3 (numerator). If the zone is valid but price structure does not offer minimum R:R — setup is rejected.
```

```
RULE_ID: STYLE-RR-002
Title: TP Partials Structure
Definition: Profits are taken in structured partial closes — never all-or-nothing.

Scalping:   TP1 = 50% at 1:1.5R · TP2 = 50% at 1:3R (full close)
Intraday:   TP1 = 40% at 1:2R · TP2 = 30% at 1:3R · TP3 = 30% at 1:5R
Swing:      TP1 = 30% at 1:2R · TP2 = 30% at 1:3R · TP3 = 40% at 1:5R+
Positional: TP1 = 25% at 1:3R · TP2 = 25% at 1:5R · TP3 = 50% at 1:10R+

Rule: After TP1 hit → move SL to breakeven immediately. Protect capital before pursuing extended targets.
```

---

## 6. Risk Management Rules

```
RULE_ID: STYLE-RISK-001
Title: Risk Per Trade by Grade
Definition:
  A+ grade setup → 1% of account balance
  A grade setup  → 1% of account balance
  B grade setup  → 0.5% of account balance
  Below B        → No execution
```

```
RULE_ID: STYLE-RISK-002
Title: Position Sizing Formula
Definition: Lot size = (Account Balance × Risk%) ÷ (SL pips × Pip Value)
Rule: Calculate fresh on every trade from current live balance. Never use a static lot size.
Fractional lots are used to achieve precise risk amounts.
```

```
RULE_ID: STYLE-RISK-003
Title: Stop Loss Placement Rules
Definition:
  - SL must be structural — placed beyond the invalidation level of the setup (beyond OB, beyond QML, beyond swing high/low)
  - SL must NEVER be placed on a round number — minimum 3-5 pip offset to avoid stop hunts
  - SL must NEVER be moved against the trade (widened) — only tightened or moved to BE
  - Minimum SL for Turtle Soup setups: 10 pips on LTF (hard minimum)
```

```
RULE_ID: STYLE-RISK-004
Title: Portfolio Risk Limits (Hard Caps)
Definition:
  Max concurrent open trades:    3
  Max trades per correlated group: 1 (take the strongest setup only)
  Daily loss limit:              3% of account → execution locked until next trading day
  Weekly drawdown limit:         5% of account → system paused until Monday
  Monthly drawdown limit:        10% of account → full review required before resumption
  Weekend exposure:              No trades carrying over weekend with SL more than 50 pips from entry (swing/positional styles exempt if SL is at BE)
```

```
RULE_ID: STYLE-RISK-005
Title: Correlated Pair Management
Definition: The following pairs are correlated — only ONE trade permitted across each group simultaneously.

  Group 1 (USD strength): USD/JPY · USD/CAD · USD/CHF (all bullish on DXY up)
  Group 2 (USD weakness): EUR/USD · GBP/USD · AUD/USD · NZD/USD (all bearish on DXY up)
  Group 3 (Risk assets): AUD/USD · NZD/USD · AUD/JPY (all risk-sensitive)
  Group 4 (JPY crosses): USD/JPY · EUR/JPY · GBP/JPY (all affected by JPY flows)
  Group 5 (Gold): XAU/USD (inverse DXY — treat as standalone)

Rule: If two setups from the same group trigger simultaneously — take the higher-grade setup only.
```

---

## 7. Trade Management Rules

```
RULE_ID: STYLE-MGMT-001
Title: Breakeven Rule
Definition: Move SL to entry price (breakeven) immediately after TP1 is hit.
Condition: TP1 must have been hit and partial closed before moving to BE.
Rule: Never move to BE before TP1 — premature BE moves cause unnecessary stop-outs on valid trades.
```

```
RULE_ID: STYLE-MGMT-002
Title: Trailing Stop Rules
Definition: After TP1 hit and SL at BE — begin trailing SL behind structural levels.

Scalping:   Trail behind each 5M swing low (longs) or swing high (shorts)
Intraday:   Trail behind each 1H swing low (longs) or swing high (shorts)
Swing:      Trail behind each 4H swing low (longs) or swing high (shorts)
Positional: Trail behind each 1D swing low (longs) or swing high (shorts)

Rule: Only trail to lock profits — never trail so tight as to exit a valid trend prematurely.
```

```
RULE_ID: STYLE-MGMT-003
Title: SL Adjustment on Structure Break
Definition: If opposing structure forms (4H BOS against trade direction) while in trade:
  Action 1: Tighten SL to most recent swing of the counter-move.
  Action 2: Reduce position by 50% if TP2 not yet hit.
  Action 3: Close fully if 1D BOS confirms against trade.
Rule: Never hold through a confirmed HTF structural invalidation.
```

```
RULE_ID: STYLE-MGMT-004
Title: EOD (End of Day) Protocol — Intraday Style
Definition: All intraday trades must be closed by 16:30 UTC if not already stopped or TP'd.
Exception: If trade is at breakeven or in profit with SL at BE — may hold overnight only if:
  - No high-impact news within 12 hours
  - Swing or positional style is active
  - Weekend is not imminent (Friday after 12:00 UTC = force close)
```

```
RULE_ID: STYLE-MGMT-005
Title: Re-Entry After Stop-Out
Definition: If a valid setup is stopped out and the zone is still intact (SL hit was a liquidity sweep — price did not close beyond the zone):
  - Re-entry is permitted ONCE with HALF the original risk
  - Requires a new LTF confirmation (CHoCH + BMS + RTO) before re-entering
  - Do not re-enter if the zone has been structurally broken
Rule: One re-entry maximum per setup. Never average down on a losing position.
```

```
RULE_ID: STYLE-MGMT-006
Title: Partial Close Management
Definition: After each partial close — recalculate the R:R of the remaining position.
  If remaining risk exceeds the updated target → close more.
  If remaining position has SL at BE or better → let it run to full target.
Rule: Never hold a losing runner. Once SL is at BE — the trade is free to run.
```

---

## 8. Trade Frequency Constraints

```
RULE_ID: STYLE-FREQ-001
Title: Quality Over Quantity
Definition: The system prioritizes high-conviction setups — not trade volume. There is no minimum trade frequency.
Rule: If no valid setup exists — output is NO SETUP. Forced trading is strictly forbidden.
```

```
RULE_ID: STYLE-FREQ-002
Title: Maximum Daily Setups
Definition:
  Scalping:   Max 3 trades per day
  Intraday:   Max 2 trades per day
  Swing:      Max 1 new trade per day
  Positional: Max 1 new trade per week

Rule: After reaching the daily limit — no new trades regardless of setup quality. Reset begins next session.
```

```
RULE_ID: STYLE-FREQ-003
Title: Post-Loss Frequency Reduction
Definition: After 2 consecutive losses in the same session:
  - Stop trading for the remainder of that session
  - Review both setups before the next session
  - Reduce risk by 50% on the next 2 trades after resumption
Rule: Consecutive losses are a signal to pause — not to trade harder to recover.
```

---

## 9. Session Preferences

```
RULE_ID: STYLE-SESSION-001
Title: Active Trading Sessions

| Session | UTC Time | Status | Priority |
|---------|----------|--------|----------|
| London Open | 07:00–10:00 | ENABLED | HIGH |
| London/NY Overlap | 12:00–16:00 | ENABLED | HIGHEST |
| New York Session | 13:00–17:00 | ENABLED | HIGH |
| Asian Session | 00:00–06:00 | DISABLED | — |

Rule: New entries during Asian session = rejected. Monitoring and management of open positions permitted.
```

```
RULE_ID: STYLE-SESSION-002
Title: Best Entry Windows (AMD Context)
Definition: The highest-probability entry windows within each session:
  London: 07:00–09:00 UTC — Accumulation/Manipulation phase. Watch for BSL/SSL sweep before 09:00.
  NY Open: 13:00–14:30 UTC — Secondary manipulation phase. Frequently reverses or extends London move.
  London/NY Overlap: 12:00–16:00 UTC — Distribution phase. Highest volume, cleanest moves.
Rule: Entries outside these windows require an explicit HTF key level retest as justification.
```

```
RULE_ID: STYLE-SESSION-003
Title: Day-of-Week Constraints
Definition:
  Monday before 07:00 UTC: No entries — gap risk, positioning not established
  Friday after 12:00 UTC: No new intraday/scalp entries — position squaring begins
  Friday after 14:00 UTC: No new swing entries — weekend gap risk
  Sunday open: Monitor for gaps — no entries until London session confirms direction
```

---

## 10. Conditions to Avoid

```
RULE_ID: STYLE-AVOID-001
Title: High-Impact News Blackout
Definition: No new entries within the following windows around high-impact news:
  Scalping:   45 minutes before and after
  Intraday:   30 minutes before and after
  Swing:      15 minutes before — hold through if SL is structural and beyond spike range

Key events: FOMC · CPI · NFP · GDP · Central Bank rate decisions · Flash PMI
Rule: News spike that sweeps liquidity and reverses = potential entry after the news window clears.
```

```
RULE_ID: STYLE-AVOID-002
Title: Ambiguous Market Structure
Definition: Do not trade when HTF market structure is unclear — no definitive HH+HL or LH+LL pattern. Price ranging without directional bias.
Action: Wait for structural break (BOS) before engaging. Ranging = no trade.
```

```
RULE_ID: STYLE-AVOID-003
Title: Overlapping Correlated Positions
Definition: Do not hold two trades from the same correlated group simultaneously (see STYLE-RISK-005).
Action: If second signal triggers — skip it regardless of grade.
```

```
RULE_ID: STYLE-AVOID-004
Title: Spread Spike Avoidance
Definition: Do not enter when current spread exceeds 2x the pair's normal average (1.5x for scalping).
Typical conditions: Asian session open, major news release, illiquid market hours, broker issues.
Action: Wait for spread to normalize before executing.
```

```
RULE_ID: STYLE-AVOID-005
Title: Equilibrium Entry Avoidance
Definition: Do not enter trades where the entry zone sits at the 50% midpoint (equilibrium) of the dealing range.
Rule: Supply/Demand zone at equilibrium = skip. QML at equilibrium = skip. No entries at 50%.
```

```
RULE_ID: STYLE-AVOID-006
Title: Revenge Trading
Definition: Trading to recover a loss by immediately entering a new position without waiting for a valid setup.
Rule: After a loss — mandatory minimum 15-minute pause before next analysis cycle. After daily limit hit — session ends regardless of perceived opportunities.
```

---

## 11. Strategy Consistency

```
RULE_ID: STYLE-CONSISTENCY-001
Title: Framework Consistency — No Deviation
Definition: The system executes only rules defined in this document and the referenced framework documents. Discretionary overrides based on "feel" or unstructured observation are prohibited.
Implication: Consistency over a large sample size produces edge. Deviation destroys expectancy.
```

```
RULE_ID: STYLE-CONSISTENCY-002
Title: Process Consistency — Same Cycle Every Time
Definition: Every analysis cycle follows the same sequence without exception:
  1. DXY assessment (USD pairs only)
  2. Macro bias check (interest rates, COT, risk sentiment)
  3. 1W/1D structural analysis
  4. 4H/1H setup identification
  5. Confluence scoring (master_rulebook.md Section 4)
  6. Grade assignment
  7. Entry zone, SL, TP1/TP2/TP3 calculation
  8. R:R validation
  9. Module B execution instruction (YES/NO)
Rule: Skipping steps is not permitted. If any step cannot be completed → NO SETUP.
```

```
RULE_ID: STYLE-CONSISTENCY-003
Title: Post-Trade Review Mandatory
Definition: Every closed trade must be journaled (per master_rulebook.md Section 7) before the next trade is eligible.
Rule: Unreviewed trades are a sign of undisciplined execution. The system learns from every outcome.
```

```
RULE_ID: STYLE-CONSISTENCY-004
Title: Rule Amendment Process
Definition: No rule in this document may be amended during an active trading session. All amendments follow the versioning protocol in master_rulebook.md Section 9.
Rule: Rules can only be changed between sessions, after review, and with version increment. Never mid-session.
```

---

*Trading Style and Operational Rules | Version 1.0 | 2026-03 | Proprietary*
