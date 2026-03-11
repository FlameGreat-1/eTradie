---
doc_id: macro_to_price
doc_type: framework
framework: Macro
title: Macro to Price Translation Guide
version: "1.0"
status: active
author: System Owner
effective_date: "2026-03"
source_of_truth: true
updated_at: "2026-03"
---

# MACRO TO PRICE TRANSLATION GUIDE

> Primary retrieval source when the processor evaluates macro_bias, currency_strength, and risk_environment. Translates macroeconomic data into directional trading bias. Does not contain SMC rules, SnD zones, Wyckoff phases, risk rules, or entry strategies.

---

## 1. Macro Framework Overview

Macroeconomic forces drive large institutional capital flows — the same flows that create the Supply/Demand zones and SMC structure this system trades. Macro sets the directional bias. Technical analysis provides the entry.

**Core principle:**
- Macro → directional bias (weeks to months)
- Technical → setup identification and entry precision (hours to days)
- Never trade technical setups against confirmed macro bias without a structural reason

**Macro output feeds three system variables:**

| Variable | Description |
|----------|-------------|
| `macro_bias` | BULLISH / BEARISH / NEUTRAL per currency |
| `currency_strength` | Relative strength ranking across traded pairs |
| `risk_environment` | RISK-ON / RISK-OFF / NEUTRAL — governs safe-haven vs growth flows |

**Macro hierarchy (strongest to weakest signal):**
1. Central bank policy stance
2. Interest rate decisions and forward guidance
3. Inflation trajectory
4. Employment and growth data
5. COT institutional positioning
6. DXY direction
7. Risk sentiment
8. High-impact event outcomes

---

## 2. Interest Rate Impact

```
RULE_ID: MACRO-RATE-001
Title: Rising Interest Rates Strengthen Currency
Definition: Higher rates increase yield attractiveness → foreign capital inflows → currency demand rises.
Implication: Bullish bias for the currency. Sell pairs where this currency is the quote.
```

```
RULE_ID: MACRO-RATE-002
Title: Falling Interest Rates Weaken Currency
Definition: Lower rates reduce yield attractiveness → capital outflows → currency demand falls.
Implication: Bearish bias for the currency. Buy pairs where this currency is the quote.
```

```
RULE_ID: MACRO-RATE-003
Title: Rate Differentials Drive Pair Bias
Definition: Capital flows from low-yield to high-yield currency. The wider the differential, the stronger the trend.
Implication: Buy high-yield currency vs low-yield currency. Rate differential direction = pair bias direction.
Example: Fed rates rising while ECB holds → USD bullish → EUR/USD bearish.
```

```
RULE_ID: MACRO-RATE-004
Title: Hawkish Policy Stance
Definition: Central bank signals willingness to raise rates or reduce balance sheet (QT) to control inflation.
Implication: Bullish currency bias. Strengthens even before actual rate hike — forward guidance matters.
```

```
RULE_ID: MACRO-RATE-005
Title: Dovish Policy Stance
Definition: Central bank signals willingness to cut rates or expand balance sheet (QE) to stimulate growth.
Implication: Bearish currency bias. Weakens even before actual rate cut.
```

```
RULE_ID: MACRO-RATE-006
Title: Rate Pause / Hold
Definition: Central bank holds rates unchanged with no clear forward guidance shift.
Implication: Neutral. Bias determined by relative comparison to other central banks and inflation trajectory.
```

```
RULE_ID: MACRO-RATE-007
Title: Rate Hike Cycle Peak
Definition: Market begins pricing in end of rate hikes (peak rates) — central bank signals hold or pivot.
Implication: Currency tops out and begins weakening as carry trades unwind. Reversal bias emerging.
```

---

## 3. Inflation Impact

```
RULE_ID: MACRO-INFLATION-001
Title: Rising Inflation Above Target
Definition: CPI/PCE trending above central bank target (typically 2%). Increases probability of rate hikes or prolonged hold.
Implication: Hawkish pressure → currency strengthening bias. Watch for central bank response.
```

```
RULE_ID: MACRO-INFLATION-002
Title: Falling Inflation Toward Target
Definition: CPI/PCE trending down toward or below central bank target.
Implication: Rate cut probability rises → dovish pressure → currency weakening bias.
```

```
RULE_ID: MACRO-INFLATION-003
Title: Unexpected Inflation Spike (Hot Print)
Definition: CPI/PCE prints significantly above forecast.
Implication: Immediate hawkish repricing → sharp currency strength spike → potential liquidity grab entry opportunity on retracement.
```

```
RULE_ID: MACRO-INFLATION-004
Title: Unexpected Inflation Drop (Cold Print)
Definition: CPI/PCE prints significantly below forecast.
Implication: Immediate dovish repricing → sharp currency weakness → potential liquidity grab entry on retracement.
```

```
RULE_ID: MACRO-INFLATION-005
Title: Stagflation Environment
Definition: High inflation + low/negative growth simultaneously. Central bank faces rate dilemma.
Implication: High uncertainty. Currency volatility elevated. Reduce position sizing. Seek clearest setups only.
```

```
RULE_ID: MACRO-INFLATION-006
Title: Core vs Headline Inflation
Definition: Core inflation (ex food/energy) is the primary central bank target metric. Headline is more volatile.
Rule: Weight core CPI/PCE over headline for bias determination. Divergence between core and headline = uncertainty.
```

---

## 4. Central Bank Policy

```
RULE_ID: MACRO-CB-001
Title: Hawkish Central Bank
Definition: Active rate hiking cycle or explicit hawkish forward guidance.
Implication: Strong bullish currency bias. Highest weight macro signal.
```

```
RULE_ID: MACRO-CB-002
Title: Dovish Central Bank
Definition: Active rate cutting cycle or explicit dovish forward guidance / QE expansion.
Implication: Strong bearish currency bias. Highest weight macro signal.
```

```
RULE_ID: MACRO-CB-003
Title: Policy Pivot — Hawkish to Dovish
Definition: Central bank shifts from hiking/hold to cutting — first cut or explicit pivot language.
Implication: Major trend reversal signal for the currency. Bearish bias begins. Highest-impact macro event.
```

```
RULE_ID: MACRO-CB-004
Title: Policy Pivot — Dovish to Hawkish
Definition: Central bank shifts from cutting/hold to hiking — first hike or explicit tightening language.
Implication: Major trend reversal signal. Bullish bias begins. Highest-impact macro event.
```

```
RULE_ID: MACRO-CB-005
Title: Forward Guidance Weight
Definition: Central bank language about future policy direction (dot plots, press conferences, meeting minutes).
Rule: Forward guidance often moves price more than the actual decision. Parse language for hawkish/dovish tilt.
Key signals: "data-dependent", "meeting-by-meeting" = neutral. "Further hikes appropriate" = hawkish. "Cuts coming" = dovish.
```

```
RULE_ID: MACRO-CB-006
Title: Quantitative Tightening (QT)
Definition: Central bank reduces balance sheet by allowing bonds to roll off or actively selling.
Implication: Reduces liquidity in the system → currency bullish, risk assets under pressure.
```

```
RULE_ID: MACRO-CB-007
Title: Quantitative Easing (QE)
Definition: Central bank expands balance sheet by purchasing assets (bonds, MBS).
Implication: Increases liquidity → currency bearish, risk assets supported.
```

```
RULE_ID: MACRO-CB-008
Title: Diverging Central Bank Policy
Definition: One central bank is hawkish while another is dovish simultaneously.
Implication: Strongest possible trend driver for the pair. Bias is clear and persistent. Trade with full conviction in direction of hawkish currency.
Example: Fed hiking + ECB cutting → EUR/USD strongly bearish.
```

---

## 5. US Dollar Index (DXY)

```
RULE_ID: MACRO-DXY-001
Title: Rising DXY — USD Broad Strength
Definition: DXY trending higher on HTF (1W/1D). USD strengthening against basket of major currencies.
Implication:
  USD Base pairs (USD/JPY, USD/CAD, USD/CHF): BULLISH
  USD Quote pairs (EUR/USD, GBP/USD, AUD/USD, NZD/USD): BEARISH
  Gold (XAU/USD): BEARISH (inverse correlation)
```

```
RULE_ID: MACRO-DXY-002
Title: Falling DXY — USD Broad Weakness
Definition: DXY trending lower on HTF (1W/1D). USD weakening against basket.
Implication:
  USD Base pairs: BEARISH
  USD Quote pairs: BULLISH
  Gold (XAU/USD): BULLISH
```

```
RULE_ID: MACRO-DXY-003
Title: DXY at Key HTF Level (Supply/Demand / Structure)
Definition: DXY reaching a major HTF Supply zone, Demand zone, or structural resistance/support.
Implication: Potential DXY reversal → anticipate reversal in all USD pairs. Do not enter USD pairs until DXY reaction is confirmed.
```

```
RULE_ID: MACRO-DXY-004
Title: DXY Divergence
Definition: DXY trending in one direction but a specific USD pair is moving opposite to expectation.
Implication: Divergence signals a pair-specific fundamental driver overriding DXY. Investigate pair-specific macro. Reduce confidence in DXY-derived bias for that pair.
```

```
RULE_ID: MACRO-DXY-005
Title: DXY Correlation by Pair Type
Definition: Correlation strength varies by pair.

| Pair Type | DXY Correlation | Weight |
|-----------|----------------|--------|
| EUR/USD | Strong inverse | HIGH |
| GBP/USD | Strong inverse | HIGH |
| USD/JPY | Strong positive | HIGH |
| AUD/USD | Moderate inverse | MEDIUM |
| NZD/USD | Moderate inverse | MEDIUM |
| USD/CAD | Moderate positive | MEDIUM |
| USD/CHF | Moderate positive | MEDIUM |
| XAU/USD | Strong inverse | HIGH |
| Non-USD crosses | Global risk context | INFORMATIONAL |
```

---

## 6. Commitment of Traders (COT)

```
RULE_ID: MACRO-COT-001
Title: Extreme Net Long — Large Speculators
Definition: Non-commercial (large speculator) net long position reaches historically extreme level.
Implication: Contrarian bearish signal. Market is overcrowded long. Reversal risk elevated.
Rule: Extreme long + HTF Supply zone + SMC bearish setup = highest conviction short.
```

```
RULE_ID: MACRO-COT-002
Title: Extreme Net Short — Large Speculators
Definition: Non-commercial net short position reaches historically extreme level.
Implication: Contrarian bullish signal. Market is overcrowded short. Reversal risk elevated.
Rule: Extreme short + HTF Demand zone + SMC bullish setup = highest conviction long.
```

```
RULE_ID: MACRO-COT-003
Title: COT Positioning Shift (Week-over-Week)
Definition: Significant change in net positioning from one COT report to the next.
Implication:
  Net longs increasing → institutions building long exposure → bullish bias strengthening.
  Net shorts increasing → institutions building short exposure → bearish bias strengthening.
  Rapid shift in direction → trend change potentially beginning.
```

```
RULE_ID: MACRO-COT-004
Title: Commercial vs Non-Commercial Divergence
Definition: Commercials (hedgers) and non-commercials (speculators) positioned opposite to each other.
Implication: Commercials are typically "smart money." When commercials are heavily net long while speculators are net short → bullish. Reverse for bearish.
```

```
RULE_ID: MACRO-COT-005
Title: COT as Confluence — Not Standalone
Rule: COT data is a +1 confluence factor only. It does not generate entries on its own.
COT extreme + technical setup at key zone = high probability trade.
COT alone = no action.
```

---

## 7. Global Risk Sentiment

```
RULE_ID: MACRO-RISK-001
Title: Risk-Off Environment
Definition: Investors reduce exposure to risk assets and move capital into safe havens due to uncertainty, fear, or crisis.
Triggers: Geopolitical conflict, financial crisis, recession fears, surprise negative data.
Implication:
  Safe havens strengthen: USD · JPY · CHF · Gold (XAU)
  Risk assets weaken: AUD · NZD · CAD · Equities · Commodity currencies
```

```
RULE_ID: MACRO-RISK-002
Title: Risk-On Environment
Definition: Investors increase exposure to higher-yielding and growth-sensitive assets.
Triggers: Strong economic data, central bank easing, geopolitical stability, positive earnings.
Implication:
  Risk currencies strengthen: AUD · NZD · CAD · Emerging Market currencies
  Safe havens weaken: JPY · CHF · Gold (in some phases)
  USD direction depends on whether US growth is outperforming or underperforming globally.
```

```
RULE_ID: MACRO-RISK-003
Title: Safe Haven Flows — JPY
Definition: JPY strengthens sharply during risk-off due to yen carry trade unwinding.
Implication: Risk-off → JPY strength → USD/JPY bearish, EUR/JPY bearish, GBP/JPY bearish.
Note: JPY carry trade (borrow JPY, buy high-yield assets) unwinds rapidly during risk-off = violent JPY appreciation.
```

```
RULE_ID: MACRO-RISK-004
Title: Safe Haven Flows — Gold (XAU/USD)
Definition: Gold strengthens during risk-off AND during USD weakness periods.
Dual driver: (1) Risk-off safe haven demand. (2) Inverse USD correlation.
Implication:
  Risk-off + falling DXY → strongest bullish Gold bias.
  Risk-on + rising DXY → bearish Gold bias.
  Risk-off + rising DXY → Gold may be capped (competing forces).
```

```
RULE_ID: MACRO-RISK-005
Title: Commodity Currency Sensitivity
Definition: AUD, NZD, CAD are commodity-linked currencies — their value correlates with commodity prices and global growth expectations.
AUD/NZD: Iron ore, coal, agricultural prices + China growth proxy.
CAD: Crude oil price correlation.
Implication: Risk-on + rising commodities → bullish AUD/NZD/CAD. Risk-off + falling commodities → bearish.
```

---

## 8. High-Impact Macro Events

```
RULE_ID: MACRO-EVENT-001
Title: FOMC Decision and Press Conference
Tier: EXTREME — highest market-moving event.
Behavior: Volatility spike on release → initial direction often reverses (stop hunt) → real direction established within 30–60 minutes post-release.
Rule: No new entries 30 minutes before or after FOMC. Watch for liquidity grab post-release as entry opportunity.
```

```
RULE_ID: MACRO-EVENT-002
Title: CPI (Consumer Price Index)
Tier: VERY HIGH.
Behavior: Hot print (above forecast) → currency spikes UP → often retraces after initial spike.
Cold print (below forecast) → currency drops → often retraces.
Rule: Initial move is frequently a stop hunt. Wait for close and retracement to zone for entry.
```

```
RULE_ID: MACRO-EVENT-003
Title: NFP (Non-Farm Payrolls)
Tier: VERY HIGH — USD-specific.
Behavior: Strong NFP → USD bullish spike. Weak NFP → USD bearish spike. Revision of prior month can flip initial reaction.
Rule: No entries 30 minutes before or after. Initial spike is frequently a liquidity grab.
```

```
RULE_ID: MACRO-EVENT-004
Title: GDP (Gross Domestic Product)
Tier: HIGH.
Behavior: Strong GDP → growth optimism → hawkish central bank expectations → currency bullish.
Weak GDP → recession fears → dovish expectations → currency bearish.
```

```
RULE_ID: MACRO-EVENT-005
Title: Central Bank Speeches and Press Conferences
Tier: HIGH — can override recent data.
Behavior: Hawkish language → immediate currency strength. Dovish language → immediate weakness.
Key speakers: Fed Chair, ECB President, BOE Governor, BOJ Governor.
Rule: Parse for explicit policy signals. "Data dependent" = neutral. Named rate path = act on it.
```

```
RULE_ID: MACRO-EVENT-006
Title: PMI (Purchasing Managers Index)
Tier: MEDIUM-HIGH.
Above 50 = expansion → currency supportive. Below 50 = contraction → currency negative.
Flash PMI (preliminary) moves price more than final revision.
```

```
RULE_ID: MACRO-EVENT-007
Title: Retail Sales
Tier: MEDIUM.
Definition: Measures consumer spending. Strong retail sales → growth → hawkish pressure. Weak → dovish pressure.
```

```
RULE_ID: MACRO-EVENT-008
Title: News Spike as Liquidity Grab
Definition: Major news event spikes price sharply → takes out resting stops (BSL or SSL) → reverses in true direction.
Implication: This is an institutional stop hunt using the news as catalyst. The reversal after the spike is the real move.
Rule: If news spike sweeps a key level AND closes back inside → this is a valid SMC/SnD entry trigger. Treat as Turtle Soup / SH confirmation.
```

---

## 9. Macro Bias Generation

```
RULE_ID: MACRO-BIAS-001
Title: Strong Bullish Currency Bias
Conditions (majority present):
  - Central bank in active hiking cycle or hawkish stance
  - Inflation above target and sticky
  - Economy outperforming (strong GDP, NFP, PMI)
  - Rate differential favorable vs counterpart
  - DXY trending up (if USD)
  - COT non-commercials net long and increasing
  - Risk-on environment (if risk currency)
Result: BULLISH bias. Full weight on long setups.
```

```
RULE_ID: MACRO-BIAS-002
Title: Strong Bearish Currency Bias
Conditions (majority present):
  - Central bank in active cutting cycle or dovish stance
  - Inflation falling below target
  - Economy underperforming (weak GDP, NFP, PMI)
  - Rate differential unfavorable vs counterpart
  - DXY trending down (if USD)
  - COT non-commercials net short and increasing
  - Risk-off environment (if risk currency)
Result: BEARISH bias. Full weight on short setups.
```

```
RULE_ID: MACRO-BIAS-003
Title: Neutral / Mixed Bias
Conditions: Macro signals conflicting — some hawkish, some dovish. No clear dominant theme.
Result: NEUTRAL. Reduce position sizing. Only take A+ technical setups. Avoid low-confluence entries.
```

```
RULE_ID: MACRO-BIAS-004
Title: Relative Currency Strength Ranking
Rule: Always rank both currencies in a pair. The bias of the pair = strong currency vs weak currency.
  Strong bias (hawkish, hot data, risk-on if applicable) → expect appreciation
  Weak bias (dovish, cold data, risk-off if applicable) → expect depreciation
Example: USD strong + EUR weak → EUR/USD bearish. GBP strong + JPY weak → GBP/JPY bullish.
```

```
RULE_ID: MACRO-BIAS-005
Title: Macro Bias Timeframe Scope
Rule:
  Weekly/Monthly macro bias → governs 1W and 1D directional context
  Current cycle position → governs 4H/1H setup direction filter
  Macro does NOT dictate M15/M5/M1 entries — that is technical confirmation
```

```
RULE_ID: MACRO-BIAS-006
Title: Macro Confirmation Required for Counter-Trend
Rule: If a technical setup is counter to the macro bias, it requires:
  - 1D CHoCH confirmed
  - COT shift beginning (non-commercials reducing position)
  - At minimum a NEUTRAL macro read
  Without these → skip counter-macro technical setups entirely.
```

---

## 10. Macro Limitations

```
RULE_ID: MACRO-LIMIT-001
Title: Macro Operates on Higher Timeframes
Rule: Macro bias is relevant on 1W and 1D. Intraday moves frequently contradict macro direction.
Do not use macro bias to filter 1H or lower timeframe retracements within a larger trend.
```

```
RULE_ID: MACRO-LIMIT-002
Title: Price May Temporarily Move Against Macro Bias
Rule: Pullbacks against the macro trend are normal and expected — they create the technical entry zones this system trades.
A retracement to a Supply/Demand zone within a macro trend is NOT a macro reversal.
```

```
RULE_ID: MACRO-LIMIT-003
Title: Technical Confirmation Required Always
Rule: Macro bias alone never generates a trade. A valid SMC or SnD technical setup must align with macro bias before executing.
Macro without technical = no entry.
Technical without macro alignment = reduced grade (maximum B, reduced risk).
```

```
RULE_ID: MACRO-LIMIT-004
Title: Macro Data Lag
Rule: COT data is released weekly with a 3-day lag. Macro reports reflect past conditions. Price often prices in expectations before actual data release.
Implication: Monitor central bank language and forward guidance — these lead macro data.
```

```
RULE_ID: MACRO-LIMIT-005
Title: Black Swan Events Override Macro Bias
Rule: Unexpected geopolitical events, financial crises, or systemic shocks can override established macro bias immediately.
Action: During black swan conditions — reduce all exposure. Wait for new macro narrative to establish before re-engaging.
```

---

*Macro to Price Translation Guide | Version 1.0 | 2026-03 | Proprietary*
