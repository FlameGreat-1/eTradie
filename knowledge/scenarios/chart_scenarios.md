---
doc_id: chart_scenario_library
doc_type: scenario_library
framework: MultiFramework
title: Chart Scenario Library
version: "1.0"
status: active
author: System Owner
effective_date: "2026-03"
updated_at: "2026-03"
source_of_truth: true
---

# CHART SCENARIO LIBRARY

> 38 structured reasoning scenarios demonstrating how SMC, SnD, Wyckoff, Macro, DXY, and COT interact across different market conditions. Each scenario is a retrievable reasoning pattern for the processor. Scenarios do not contain risk numbers or trade journals — those belong to master_rulebook.md and trading_style_rules.md.

---

## 1. High Probability Confluence

### SCENARIO_ID: SCN-001
```
Market Context:
GBP/USD in confirmed 1W/1D bearish structure (LH+LL). BOE dovish pivot underway. DXY in bullish trend on 1W.

Framework Signals:
SMC: Bearish BMS on 4H confirmed. Price retracing to Bearish OB at 4H Premium zone.
SnD: Fresh Supply zone formed at same 4H OB origin candle. SR Flip confirmed by Marubozu.
DXY: 1D bullish — rising DXY = GBP/USD bearish pressure.
COT: Non-commercials net short GBP and increasing week-over-week.
Macro: BOE dovish + Fed hawkish = rate differential favoring USD. Policy divergence active.
Wyckoff: 1D showing Distribution Phase C characteristics — UTAD may have formed.

Analysis:
All six frameworks aligned. Price at Premium Supply zone after BMS. Institutional distribution confirmed by COT. Policy divergence provides macro tailwind. Wyckoff distribution context confirms.

Decision: SELL — A+ Grade

Reasoning:
Full six-framework confluence. SMC OB + SnD Supply + DXY bullish + COT short + macro divergence + Wyckoff distribution all pointing to the same setup. Highest conviction scenario in the system. Full 1% risk allocation.
```

---

### SCENARIO_ID: SCN-002
```
Market Context:
AUD/USD sold off sharply over 3 weeks. Price reaches a 4H Demand zone. China PMI beats expectations. RBA holds rates steady with neutral guidance.

Framework Signals:
SMC: SSL swept on 4H (Turtle Soup Long trigger). Bullish BMS on 1H. Bullish OB formed.
SnD: QML + RS Flip + S1/S2 Fakeouts at Demand zone (Pattern 8 baseline). Zone is fresh.
DXY: 4H DXY decelerating — losing bullish momentum. No new highs for 5 days.
COT: Non-commercials extreme net short AUD — 52-week extreme reached.
Macro: China PMI positive = AUD demand. RBA neutral (not hawkish but not cutting).
Wyckoff: 4H Spring potential — price swept lows and closed back above range.

Analysis:
SSL swept and price closed back above → Turtle Soup Long trigger. SnD Demand zone fresh. COT at extreme short (contrarian bullish). DXY momentum fading. China data supportive of AUD. Spring confirmed on 4H.

Decision: BUY — A Grade

Reasoning:
Five frameworks aligned on bullish bias. COT extreme short + Turtle Soup + fresh Demand zone + Wyckoff Spring + DXY momentum loss = high-conviction long. Full 1% risk. Target: next BSL pool above.
```

---

### SCENARIO_ID: SCN-003
```
Market Context:
EUR/USD approaches 4H Supply zone. Fed minutes hawkish. DXY breaks above prior weekly resistance.

Framework Signals:
SMC: SH+BMS+RTO bearish setup. BSL swept above previous week high. Bearish OB at 4H Premium.
SnD: Supply zone at QML + Previous Highs (2 R's clustered) = Type 1 setup (Pattern 3). SR Flip confirmed.
DXY: 1W/1D bullish BOS just confirmed — new demand for USD.
COT: Large speculators increasing net long USD. EUR net shorts building.
Macro: Fed hawkish minutes released. ECB neutral. Rate differential widening in USD favor.

Analysis:
DXY structural BOS confirms broad USD demand. SnD Pattern 3 (90% setup) at same level as SMC Bearish OB. COT institutional flow building in USD. Macro backing confirmed.

Decision: SELL — A+ Grade

Reasoning:
DXY structural BOS = macro structural confirmation. SnD 90% setup (Pattern 3) + SMC SH+BMS+RTO aligned at same zone. COT and macro both support. Premium zone confirmed. Highest conviction sell.
```

---

### SCENARIO_ID: SCN-004
```
Market Context:
XAU/USD (Gold) has been ranging for 6 weeks after a significant downtrend. DXY showing exhaustion.

Framework Signals:
SMC: 4H CHoCH confirmed bullish after Demand zone reaction. BMS higher on 1D.
SnD: QML + RS Flip formed after strong Marubozu break of resistance. Demand zone at Discount.
DXY: 1D bearish CHoCH — DXY trend exhaustion. Bearish momentum building.
COT: Non-commercials net long Gold increasing. Commercial hedgers reducing net shorts.
Wyckoff: Classic Accumulation Phase C — Spring below prior support, successful test, SOS bar confirmed.
Macro: Real yields declining. Fed pivot language appearing in minutes.

Analysis:
Wyckoff Accumulation Spring + SMC CHoCH → BMS + SnD Demand zone + DXY exhaustion + COT accumulation + falling real yields. Six frameworks in full bullish alignment.

Decision: BUY — A+ Grade

Reasoning:
Wyckoff Spring is the anchor event. SMC and SnD confirm structural shift. DXY weakness and declining real yields = Gold dual bullish driver. COT confirms institutional accumulation. Perfect Wyckoff-SMC-SnD convergence.
```

---

### SCENARIO_ID: SCN-005
```
Market Context:
USD/JPY in strong 1W uptrend. BOJ maintaining ultra-dovish policy. Fed holding rates high.

Framework Signals:
SMC: 4H pullback to Bullish OB after BMS higher. FVG present at OB. IDM cleared.
SnD: QML + RS Flip + S1 Fakeout at Demand zone (Pattern 8). Zone at Discount (38% Fibonacci).
DXY: 1W/1D bullish trend intact. No structural weakness visible.
COT: Non-commercials net long USD increasing. JPY net shorts at elevated level.
Macro: US-Japan rate differential at multi-decade high. BOJ no policy change signal.
Wyckoff: Markup phase confirmed. Pullback = Phase D reaccumulation.

Analysis:
US-Japan rate differential is the dominant structural driver. BOJ dovish + Fed hawkish = strongest possible rate differential trade. Technical pullback to Demand zone providing entry.

Decision: BUY — A+ Grade

Reasoning:
Rate differential trade with institutional backing (COT). Wyckoff Markup reaccumulation + SMC OB + SnD Demand at Discount = clean entry on pullback in a macro-driven trend. Highest institutional conviction scenario.
```

---

## 2. Technical Setup Without Macro Confirmation

### SCENARIO_ID: SCN-006
```
Market Context:
GBP/USD forms a bullish structure on 4H/1H. Macro environment is neutral — BOE and Fed both on hold with no clear guidance.

Framework Signals:
SMC: SSL swept on 1H. Bullish BMS confirmed. Bullish OB at 1H Discount zone.
SnD: Fresh Demand zone. RS Flip confirmed. S1 Fakeout formed.
DXY: Sideways — no clear trend on 1D.
COT: Neutral positioning — no extreme or directional shift.
Macro: BOE hold. Fed hold. CPI in line with forecast. No macro catalyst.

Analysis:
Technical setup is valid and clean. SnD + SMC aligned at Demand zone. However, macro provides no directional backing — DXY flat, COT neutral.

Decision: BUY — B Grade

Reasoning:
Valid technical setup but without macro confirmation grade is reduced to B. Risk reduced to 0.5%. R:R must meet minimum 1:3 intraday standard. Trade permitted but with lower conviction — take TP1 quickly, trail the rest.
```

---

### SCENARIO_ID: SCN-007
```
Market Context:
EUR/USD forms bearish structure on 4H. Supply zone visible. Macro is neutral — no clear Fed or ECB driver active.

Framework Signals:
SMC: BSL swept on 4H. Bearish BMS. Bearish OB at Premium.
SnD: Supply zone with SR Flip and R1/R2 Fakeouts. Pattern 1 baseline.
DXY: Neutral — consolidating after prior trend.
COT: Slight net short EUR but not extreme or shifting significantly.
Macro: No active catalyst. Both central banks on hold.

Analysis:
Technical setup valid. SMC + SnD aligned at Supply zone. DXY neutral reduces conviction but does not invalidate. COT slight bearish lean adds minor weight.

Decision: SELL — B Grade

Reasoning:
Clean technical setup without macro tailwind = B grade. 0.5% risk. Monitor closely for DXY directional break — if DXY breaks higher during the trade, upgrade management and let it run.
```

---

### SCENARIO_ID: SCN-008
```
Market Context:
AUD/USD retraces to a 4H Demand zone. Macro is neutral. China data mixed. RBA on hold.

Framework Signals:
SMC: 4H Bullish OB with FVG. IDM cleared on 1H. Bullish CHoCH on 1H.
SnD: Demand zone at Discount. RS Flip confirmed.
DXY: Ranging — no clear directional move.
COT: Non-commercials neutral AUD positioning.
Macro: RBA hold. China PMI mixed — no clear direction.
Wyckoff: No clear phase identified.

Analysis:
Technical setup quality is good but all contextual layers are neutral. AUD commodity link (China) provides no confirmation.

Decision: BUY — B Grade

Reasoning:
Valid technical entry but zero macro backing. B grade only. Must meet 1:3 R:R minimum. Take TP1 early. Do not hold for extended target without macro catalyst developing.
```

---

### SCENARIO_ID: SCN-009
```
Market Context:
EUR/GBP ranging for 3 weeks. No clear macro divergence between ECB and BOE. Price at range support.

Framework Signals:
SMC: Bullish CHoCH on 1H after SSL sweep. No 4H BMS yet.
SnD: Minor Demand zone at range low. Not a 4H zone — visible on 1H only.
DXY: Irrelevant for EUR/GBP cross.
COT: No extreme positioning on either EUR or GBP.
Macro: ECB neutral. BOE neutral. No divergence.

Analysis:
Ranging market with no macro driver. CHoCH only (no BMS). Zone only on 1H (not HTF). No directional conviction.

Decision: NO SETUP

Reasoning:
No HTF BMS confirmation. Zone lacks 4H or higher origin. No macro divergence for a cross pair. Ranging market conditions without structure. Wait for breakout with BMS confirmation before engaging.
```

---

## 3. Conflicting Signals

### SCENARIO_ID: SCN-010
```
Market Context:
EUR/USD shows bullish structure on 4H/1H. However, Fed signals continued hawkishness and DXY is in a strong uptrend.

Framework Signals:
SMC: Bullish BMS on 4H. Bullish OB forming.
SnD: Demand zone at 4H Discount.
DXY: 1W/1D bullish trend — strong USD demand confirmed.
COT: Non-commercials increasing net long USD. EUR net shorts building.
Macro: Fed hawkish. ECB neutral. Rate differential widening against EUR.

Analysis:
4H technical structure is bullish but the 1W macro and DXY environment are strongly bearish for EUR/USD. The 4H bullish structure is a retracement within the larger bearish macro trend.

Decision: NO SETUP — Wait for macro-aligned sell

Reasoning:
4H bullish move is a pullback inside a macro downtrend. Do not buy into a macro headwind. Wait for price to reach a Premium Supply zone on 4H/1H and look for bearish SMC/SnD setup aligned with DXY and macro direction.
```

---

### SCENARIO_ID: SCN-011
```
Market Context:
GBP/USD shows bearish structure on 4H. But BOE surprises with hawkish speech. DXY losing momentum.

Framework Signals:
SMC: Bearish BMS on 4H. Bearish OB at Premium.
SnD: Supply zone formed at 4H Premium.
DXY: Momentum losing — smaller candles, wicks rejecting highs on 1D.
COT: Slight net short GBP but not extreme.
Macro: BOE unexpected hawkish shift — GBP-specific bullish catalyst emerging.

Analysis:
Technical bearish setup conflicts with a pair-specific hawkish macro development. BOE hawkish shift can override DXY-derived bearish bias for GBP/USD.

Decision: NO SETUP — Macro override active

Reasoning:
BOE hawkish surprise is a pair-specific driver that temporarily overrides DXY influence (per DXY-PAIR-002). Technical bearish setup is downgraded — macro conflict reduces conviction below threshold. Wait for new structure after BOE event is priced in.
```

---

### SCENARIO_ID: SCN-012
```
Market Context:
EUR/USD approaching 4H Demand zone. DXY is in a strong bullish trend. Trader sees a potential long setup.

Framework Signals:
SMC: SSL swept on 1H. Bullish CHoCH on 1H. No 4H BMS yet.
SnD: Demand zone at Discount. Fresh zone.
DXY: 1W/1D strongly bullish — consistent HH+HL structure.
COT: USD net longs increasing. EUR net shorts increasing.
Macro: Fed hawkish. ECB dovish. Policy divergence fully active.

Analysis:
DXY strength and macro divergence are strongly bearish for EUR/USD. The 1H SSL sweep and CHoCH are inducement-level moves within the larger macro downtrend — not reversal signals.

Decision: NO SETUP — DXY and macro conflict overrides

Reasoning:
CHoCH without 4H BMS is insufficient against strong macro headwind. DXY bullish trend + policy divergence = EUR/USD bearish. The "bullish" move to the Demand zone is likely a retracement before continuation lower. Look for Supply zone short on the retracement.
```

---

### SCENARIO_ID: SCN-013
```
Market Context:
AUD/USD technical structure is bearish on 4H. But COT shows non-commercials at extreme net short AUD — 52-week extreme.

Framework Signals:
SMC: Bearish BMS on 4H. Price retesting Bearish OB.
SnD: Supply zone at Premium. Fresh.
DXY: Mildly bullish on 1D.
COT: AUD non-commercials at 52-week extreme net short — maximum crowding.
Macro: RBA neutral. China data mixed.

Analysis:
Technical setup is valid bearish but COT positioning is at extreme contrarian bullish level. Overcrowded trade. Risk of short squeeze. COT extreme downgrades the short.

Decision: SELL — B Grade with reduced size and early TP

Reasoning:
Technical setup valid but COT extreme warns of reversal risk. Per COT-TECH-003 — downgrade one grade. Execute with 0.5% risk only. Target TP1 aggressively. Do not hold for extended target into overcrowded position territory.
```

---

### SCENARIO_ID: SCN-014
```
Market Context:
USD/CAD at a key 4H zone. DXY mildly bullish. But crude oil (WTI) is surging — CAD petrocurrency tailwind.

Framework Signals:
SMC: Bullish OB at 4H Discount. BMS higher on 1H.
SnD: Demand zone at 4H Discount. Fresh RS Flip.
DXY: Mild bullish on 1D — no strong momentum.
COT: USD slightly net long. CAD neutral.
Macro: WTI crude oil +4% — strong CAD-positive driver. CAD strengthening independently.

Analysis:
SMC and SnD support long USD/CAD. But surging crude oil provides a counter-driver strengthening CAD. Per DXY-PAIR-007 — rising oil = CAD strengthens = USD/CAD bearish pressure overriding mild DXY bullishness.

Decision: NO SETUP — Commodity counter-driver too strong

Reasoning:
Mixed signals: technical long setup vs. macro CAD strength from oil. Mild DXY cannot overcome a 4% crude oil surge. Wait for oil to stabilize or reverse before re-engaging with USD/CAD long setup.
```

---

## 4. Fakeout Conditions

### SCENARIO_ID: SCN-015
```
Market Context:
GBP/USD has equal highs sitting above at 1.2850. Price approaches the level during London Open.

Framework Signals:
SMC: BSL visible at equal highs. Price approaches slowly with compression.
SnD: SR Flip level sitting just below 1.2850 from prior breakdown.
DXY: 1D bearish trend — DXY losing ground.
COT: GBP net shorts reducing — speculators covering.
AMD: London Open active — manipulation phase expected.

Analysis:
Equal highs = prime BSL target. London Open AMD context — manipulation phase upward expected before Distribution reversal. Compression building below equal highs.

Decision: Wait for BSL sweep → then SELL on SH+BMS+RTO

Reasoning:
Do not sell before the sweep. Equal highs MUST be taken first (SMC-R-001). Wait for single bearish candle to close back below 1.2850 after sweep → then look for Bearish OB on 15M → SELL. This is a textbook Turtle Soup Short + SH+BMS+RTO setup (SMC-SELL-005).
```

---

### SCENARIO_ID: SCN-016
```
Market Context:
EUR/USD has been ranging between 1.0800 and 1.0950 for 2 weeks. Price breaks above 1.0950 with a strong candle but immediately pulls back into range.

Framework Signals:
SMC: Apparent bullish BOS above range. But candle that broke out has a large wick — no full body close above.
SnD: Supply zone sitting just above 1.0950. Prior SR Flip level.
DXY: 1D bullish — no sign of DXY weakness.
COT: USD net longs stable. No EUR accumulation visible.
Macro: No catalyst for EUR strength. Fed hawkish.

Analysis:
Break above range lacked a full body Marubozu close — per SND-IMP-001 and SMC-MS-004, a wick is a liquidity grab NOT a break. Price returned into range = false breakout.

Decision: SELL — BSL sweep above range confirmed false breakout

Reasoning:
No Marubozu body close above 1.0950 = no valid SR Flip = no valid bullish BOS (SMC-MS-003/004). BSL grab above range = distribution signal. DXY bullish supports sell. Look for Bearish OB on 4H for sell entry re-entering the range toward 1.0800.
```

---

### SCENARIO_ID: SCN-017
```
Market Context:
USD/JPY approaching a key 4H Demand zone after a pullback. Price dips below the zone low by 15 pips then immediately recovers.

Framework Signals:
SMC: SSL swept below Demand zone (Turtle Soup Long potential). Single bullish candle closes back above zone.
SnD: QML + RS Flip. Demand zone origin. Dip below = fakeout of zone low.
DXY: 1D bullish trend intact.
COT: JPY net shorts at extreme — contrarian JPY strength risk noted but US-Japan rate differential dominant.
Macro: US-Japan rate differential wide. BOJ no change.

Analysis:
Price dipped below zone low to sweep SSL sitting below equal lows — classic stop hunt. Single bullish candle close back above zone confirms the sweep is complete. Turtle Soup Long trigger.

Decision: BUY — A Grade

Reasoning:
SSL swept + close back inside = confirmed Turtle Soup Long (SMC-BUY-001). Zone not invalidated — price closed back above. Rate differential macro backing. DXY bullish. 10 pip minimum SL below sweep low. Target BSL pool above.
```

---

### SCENARIO_ID: SCN-018
```
Market Context:
AUD/USD at a 4H Demand zone. Price touches zone, forms a small bullish reaction, then breaks below with a bearish Marubozu close.

Framework Signals:
SMC: Bullish CHoCH formed initially. Then price breaks below Bullish OB with full body close — OB invalidated (SMC-INV-001).
SnD: QML breached — Demand zone invalidated (SND-INV-002). Bearish Marubozu confirmed the breakdown.
DXY: 1D bullish momentum accelerating.
COT: AUD net shorts increasing week-over-week.
Macro: China data disappointing. RBA dovish language emerging.

Analysis:
Initial reaction at Demand zone failed. Bearish Marubozu closed below QML = Demand zone fully invalidated. Not a fakeout — a genuine structural breakdown.

Decision: NO SETUP (Zone Failed) — Monitor for new Supply zone short

Reasoning:
OB invalidated per SMC-INV-001. Zone invalidated per SND-INV-002. Do not re-enter long. The failed Demand zone is now a Breaker Block (SMC-OB-005) — future price return to this level is a short opportunity, not a long.
```

---

### SCENARIO_ID: SCN-019
```
Market Context:
GBP/JPY at a 4H Supply zone. Price touches zone briefly then pushes sharply higher through the zone with a full-body Marubozu close above.

Framework Signals:
SMC: Price closes above Bearish OB — OB invalidated (SMC-INV-001). Bullish BMS confirmed.
SnD: Supply zone QML breached by Marubozu close = zone invalidated (SND-INV-001).
DXY: Irrelevant for GBP/JPY cross.
COT: GBP net long increasing. JPY weakness persistent.
Macro: BOE unexpectedly hawkish. BOJ ultra-dovish. Strong divergence favoring GBP/JPY bullish.

Analysis:
Failed Supply zone = zone invalidated. Marubozu close above = genuine bullish BOS. BOE hawkish + BOJ dovish = macro driver for GBP/JPY strength. Supply zone is now a Breaker Block.

Decision: BUY on retest of invalidated Supply zone as new Support

Reasoning:
Supply zone became Breaker Block (SMC-OB-005). Per RS Flip logic — former resistance is new support. Look for bullish Demand zone on retest of the prior Supply zone. Macro divergence provides sustained directional backing.
```

---

## 5. Reversal Scenarios

### SCENARIO_ID: SCN-020
```
Market Context:
EUR/USD has been in a downtrend for 8 weeks. Price forms a CHoCH on 4H then a full BMS higher on 1D.

Framework Signals:
SMC: 4H CHoCH → 1D BMS confirmed. Bullish OB formed at origin of 1D BMS move.
SnD: QML + RS Flip formed. New Demand zone at Discount (28% Fibonacci).
DXY: 1D bearish CHoCH — DXY losing bullish structure. Momentum decelerating.
COT: Non-commercials EUR net shorts at 52-week extreme — beginning to reduce.
Macro: Fed pivot language appearing. ECB holding rates steady — no further cuts.

Analysis:
Reversal sequence: 4H CHoCH → 1D BMS → OB formed → DXY structural deterioration → COT unwinding → macro shift in Fed language. Full reversal stack.

Decision: BUY — A Grade

Reasoning:
1D BMS is the key signal — not CHoCH alone. DXY CHoCH + COT unwinding + Fed pivot language = macro beginning to support EUR. Entry on retracement to Bullish OB at Discount. Target BSL clusters above.
```

---

### SCENARIO_ID: SCN-021
```
Market Context:
XAU/USD has been in a 3-month downtrend. Price makes a new low below prior swing low, then recovers sharply. Classic Wyckoff Spring pattern developing.

Framework Signals:
SMC: SSL swept below prior swing low — Turtle Soup Long trigger. Single bullish candle closes back above prior low.
SnD: Demand zone origin from prior major high volume node. RS Flip forming.
DXY: Showing exhaustion at 20-year high. Bearish CHoCH developing on 1W.
COT: Gold non-commercials at extreme net short. Commercial hedgers heavily net long.
Wyckoff: Phase C Spring confirmed — price swept below support (PS/SC level), volume spike on the low, then SOS bar up.
Macro: Real yields peaking. Fed dot plots shifting dovish.

Analysis:
Wyckoff Spring + SSL sweep + COT extreme short + DXY exhaustion + real yields peaking = textbook gold bottom scenario. All frameworks simultaneously confirming accumulation complete.

Decision: BUY — A+ Grade

Reasoning:
Wyckoff Spring is the anchor. SMC Turtle Soup confirms the liquidity sweep. COT commercial accumulation (COT-CONTRA-003) + extreme speculator short = maximum divergence signal. Real yield peak = Gold fundamental inflection. Highest conviction gold reversal scenario.
```

---

### SCENARIO_ID: SCN-022
```
Market Context:
GBP/USD has been rallying for 12 weeks. Price reaches a major 1W Supply zone. COT shows extreme net long GBP. DXY at key 1W Demand zone.

Framework Signals:
SMC: BSL swept above 2-year high. Bearish OB forming on 4H after sweep and close back below.
SnD: Triple Fakeout Supply zone (Pattern 5) forming at 1W Supply origin. Previous Highs cluster. R1/R2/R3 fakeouts present.
DXY: 1W Demand zone. DXY Spring potential. Bullish CHoCH on 1D.
COT: GBP non-commercials at 52-week extreme net long. Sentiment exhaustion signal.
Wyckoff: 1W showing Distribution UTAD characteristics. Phase C completed.
Macro: BOE beginning to signal rate cuts. Fed holding high.

Analysis:
Wyckoff Distribution UTAD + SnD Triple Fakeout (highest confluence sell pattern) + SMC BSL sweep + DXY at Demand + COT extreme long + BOE dovish pivot = complete distribution reversal stack.

Decision: SELL — A+ Grade

Reasoning:
SnD Pattern 5 (Triple Fakeout = highest confluence sell) combined with Wyckoff UTAD = institutional distribution confirmed. COT sentiment exhaustion (COT-CONTRA-002). DXY Spring = USD reversal adds macro backing. Full 1% risk. Trail aggressively — this is a trend reversal with multi-week potential.
```

---

### SCENARIO_ID: SCN-023
```
Market Context:
NZD/USD at extreme COT short positioning. 52-week extreme reached. Price at a 4H Demand zone.

Framework Signals:
SMC: SSL swept on 4H. 1H CHoCH forming. Bullish OB on 1H.
SnD: Fresh Demand zone at Discount. Pattern 8 (QML + RS Flip + S1 Fakeout).
DXY: Mild bearish momentum — 1D losing structure.
COT: NZD non-commercials at 52-week extreme net short. Commercials net long.
Macro: RBNZ on hold. No active negative catalyst.

Analysis:
COT extreme short with commercial accumulation (COT-CONTRA-003) = contrarian bullish setup. Technical confirmation present. DXY mild weakness adds directional support.

Decision: BUY — A Grade

Reasoning:
COT extreme short at key Demand zone = highest contrarian confluence (COT-EXTREME-002 + COT-CONTRA-003). Technical confirmation through SMC SSL sweep + CHoCH. Trade with COT as primary context, SMC/SnD as timing mechanism. Take TP1 quickly given contrarian nature — let runners trail.
```

---

### SCENARIO_ID: SCN-024
```
Market Context:
DXY has been in a 6-month uptrend. Now shows: exhaustion candles on 1W, failure to make new high for 3 weeks, bearish CHoCH forming on 1D.

Framework Signals:
SMC: EUR/USD shows 4H CHoCH then BMS higher. Bullish OB at 4H Discount.
SnD: Demand zone forming from 4H origin. RS Flip with Marubozu.
DXY: 1D bearish CHoCH. Momentum exhaustion (DXY-MOM-003). Failed to break prior high.
COT: USD non-commercials reducing net longs — distribution phase (COT-TREND-003).
Macro: Fed pause language emerging. Inflation trending down toward target.

Analysis:
DXY trend exhaustion is the macro anchor. Fed pause + declining inflation = policy shift beginning. EUR/USD technical reversal confirmed by CHoCH + BMS. COT USD distribution confirms smart money exit.

Decision: BUY EUR/USD — A Grade

Reasoning:
DXY structural deterioration (DXY-MOM-003 + DXY-STRUCT-003) = USD trend ending. EUR/USD BMS confirms bullish reversal technically. COT USD distribution = institutional exit from USD longs. Macro pivot narrative beginning. Trade reversal with trailing management.
```

---

## 6. Trend Continuation

### SCENARIO_ID: SCN-025
```
Market Context:
USD/JPY in confirmed 1W uptrend. Pulls back to a 4H Bullish OB after a 1H BMS higher. Rate differential remains wide.

Framework Signals:
SMC: 4H Bullish OB with FVG. IDM cleared on 1H. Compression forming at OB.
SnD: QML + RS Flip. Demand zone at Discount (62% Fibonacci = OTE alignment).
DXY: 1D pullback to 4H Demand — same macro retracement context.
COT: USD net longs steady. No distribution.
Wyckoff: Markup Phase D reaccumulation.
Macro: Rate differential dominant driver unchanged.

Analysis:
Textbook pullback continuation in a macro trend. OTE Fibonacci alignment at Demand zone (SnD Rule 9 + SMC-R-004 = 90% probability trigger). Wyckoff Phase D reaccumulation confirms trend continuation.

Decision: BUY — A+ Grade

Reasoning:
Fibonacci OTE (62%) aligning exactly with SMC OB + SnD Demand zone = 90% probability add-on. Macro unchanged. Wyckoff Markup Phase D = institutional re-accumulation on pullback. Full 1% risk. Target: next BSL cluster above.
```

---

### SCENARIO_ID: SCN-026
```
Market Context:
GBP/USD is in a confirmed 1D uptrend (HH+HL). Price pulls back to a 4H Demand zone after BMS higher.

Framework Signals:
SMC: 4H Bullish OB. SSL swept below on 15M (inducement cleared). 15M BMS higher.
SnD: Demand zone. RS Flip level. Fakeout S1 formed and broken by Marubozu.
DXY: 1D pullback within 1W neutral — no strong DXY headwind.
COT: GBP net longs building week-over-week. Trend accumulation.
Macro: BOE neutral. No active headwind.

Analysis:
Clean trend continuation. All LTF confirmations met (SMC Section 11 Entry Confirmation checklist complete). COT accumulation confirms institutions building longs.

Decision: BUY — A Grade

Reasoning:
Full LTF confirmation checklist satisfied: liquidity taken (SSL swept) → CHoCH on 15M → BMS → RTO to OB → IDM cleared → London session timing. COT accumulation adds conviction. Standard 1% risk.
```

---

### SCENARIO_ID: SCN-027
```
Market Context:
EUR/USD in confirmed 1D/1W downtrend. Pulls back to a 4H Supply zone after a 4H BMS lower.

Framework Signals:
SMC: 4H Bearish OB. BSL swept above on 15M (inducement cleared). 15M BMS lower.
SnD: Supply zone. SR Flip level. R1 Fakeout forming at zone with compression.
DXY: 1D uptrend intact — pulling back to 4H Demand simultaneously.
COT: EUR net shorts building. USD net longs stable.
Macro: ECB dovish signaling. Fed holding high.

Analysis:
Mirror of SCN-026. Bearish trend continuation. DXY pullback to Demand = DXY about to rally = EUR/USD about to fall. Both moving in sync. LTF entry checklist satisfiable.

Decision: SELL — A Grade

Reasoning:
DXY and EUR/USD inverse correlation aligned at same structural inflection. Supply zone SR Flip + compression forming. ECB dovish + Fed hold = macro continues to support. Full LTF confirmation expected. 1% risk.
```

---

### SCENARIO_ID: SCN-028
```
Market Context:
GBP/USD breaks a major 1D resistance level with a strong Marubozu candle. Pulls back to retest the broken level.

Framework Signals:
SMC: Bullish BOS on 1D. RS Flip created. Price retesting former resistance as support. Bullish OB at the breakout origin.
SnD: Break and retest = RS Flip with Marubozu (SND-ZONE-004). Demand zone at the retested level.
DXY: 1D structure weakening. DXY BMS lower forming.
COT: GBP net longs increasing.
Macro: BOE hawkish surprise. GBP-specific bullish driver.

Analysis:
Classic break and retest structure. 1D BOS + RS Flip is the highest-quality SnD zone creation event. Retest of the level as support = first retest (SND-RETEST-001) = highest probability entry.

Decision: BUY — A+ Grade

Reasoning:
1D BOS with Marubozu = valid RS Flip. First retest of the level = maximum freshness. DXY weakening adds USD weakness tailwind. BOE hawkish driver = GBP-specific strength. COT building. Textbook institutional break and retest continuation.
```

---

### SCENARIO_ID: SCN-029
```
Market Context:
XAU/USD (Gold) in a confirmed 1W uptrend. DXY falling. Real yields declining. Geopolitical tensions elevated.

Framework Signals:
SMC: 4H Bullish OB after 4H BMS higher. FVG present. IDM cleared.
SnD: Demand zone at Discount (OTE 70.5% Fibonacci alignment). Fresh zone.
DXY: 1W bearish trend. 1D BMS lower confirmed.
COT: Gold non-commercials increasing net longs. No extreme yet.
Wyckoff: Markup phase — Phase D continuation.
Macro: Real yields declining + DXY bearish + risk-off geopolitical = Gold dual-driver bullish.

Analysis:
Gold trend continuation with full macro backing. Fibonacci OTE at Demand zone = 90% probability add-on. Wyckoff Markup Phase D reaccumulation.

Decision: BUY — A+ Grade

Reasoning:
Gold dual macro driver (DXY bearish + real yields declining) + geopolitical safe-haven demand + Wyckoff Phase D + SMC OB + Fibonacci OTE at SnD Demand = maximum institutional expansion scenario.
```

---

## 7. Range Market Conditions

### SCENARIO_ID: SCN-030
```
Market Context:
EUR/USD ranging between 1.0750 and 1.0950 for 4 weeks. Price approaches range support (1.0750) from above.

Framework Signals:
SMC: SSL pool sitting below 1.0750 (equal lows). SMC-LIQ-005 — expect sweep before buy.
SnD: Demand zone at 1.0750 from prior range low reaction.
DXY: Ranging — no directional trend.
COT: Neutral. No extreme positioning.
Macro: Both Fed and ECB on hold. No catalyst.

Analysis:
Range support reaction possible but SSL sitting below range low must be swept first. Do not buy at range support before the sweep.

Decision: Wait for SSL sweep below 1.0750 → then BUY

Reasoning:
Equal lows = SSL target (SMC-LIQ-005). Per SMC-R-001 — liquidity must be taken before reversal entry. If price sweeps below 1.0750 and closes back above → Turtle Soup Long trigger + range support confirmation. Buy on close back inside range. If no sweep — no entry.
```

---

### SCENARIO_ID: SCN-031
```
Market Context:
GBP/USD ranging between 1.2600 and 1.2800. Price approaches range resistance (1.2800).

Framework Signals:
SMC: BSL pool sitting above 1.2800 (equal highs). Expect sweep before sell.
SnD: Supply zone at 1.2800 from prior range high reaction.
DXY: Ranging — no clear trend.
COT: Neutral.
AMD: London Open approaching — manipulation phase may target BSL above 1.2800.

Analysis:
Same logic as SCN-030 but inverted. Do not sell at range resistance before the BSL sweep.

Decision: Wait for BSL sweep above 1.2800 → then SELL

Reasoning:
Equal highs above 1.2800 = BSL target. AMD London manipulation likely to push above range resistance to grab BSL before reversing into Distribution. Wait for single bearish candle to close back below 1.2800 after sweep → Turtle Soup Short + Supply zone = SELL.
```

---

### SCENARIO_ID: SCN-032
```
Market Context:
USD/CAD ranging. Price breaks below range support but oil prices spike sharply. Price immediately recovers back into range.

Framework Signals:
SMC: SSL swept below range (wick only — no full body close below). Price closes back inside range.
SnD: RS Flip not created — no Marubozu body close below support.
DXY: Mild bullish.
Macro: WTI oil +3% — CAD strengthens → USD/CAD sold even as DXY rose.

Analysis:
Wick below range = liquidity grab (SMC-MS-003/004). No Marubozu body close = no valid SR/RS Flip (SND-IMP-001). Oil spike provided the CAD-bullish catalyst that forced the stop hunt. Price back inside range = false breakdown confirmed.

Decision: BUY at range low — B Grade (neutral macro environment for USD/CAD)

Reasoning:
False breakdown confirmed (wick only, no body close). Turtle Soup Long trigger valid. But oil spike creates ongoing CAD-strength headwind. B grade only. Small size. Take TP1 quickly at range midpoint.
```

---

### SCENARIO_ID: SCN-033
```
Market Context:
EUR/USD ranging. Price sweeps to the middle of the range and stalls. No clear HTF setup visible.

Framework Signals:
SMC: No BMS. No clear OB. Price at equilibrium of range.
SnD: No valid Supply or Demand zone at current price. Equilibrium = no entry (SND-INV-004).
DXY: Neutral.
COT: Neutral.
Macro: Neutral.

Analysis:
Price at equilibrium inside a range. No structural zone. No liquidity event. No framework signal.

Decision: NO SETUP

Reasoning:
Equilibrium trading is prohibited across all frameworks (SMC-MIT-003, SND-FILTER-001, SND-INV-004). No OB, no Supply/Demand zone, no liquidity sweep. Wait for price to reach range extreme — then look for liquidity sweep + confirmation before entering.
```

---

## 8. Macro-Driven Scenarios

### SCENARIO_ID: SCN-034
```
Market Context:
Fed delivers a hawkish FOMC — raises rates 25bps and signals two more hikes. DXY spikes immediately. EUR/USD drops sharply.

Framework Signals:
SMC: EUR/USD bearish BMS on 4H post-FOMC. Bearish OB at retracement level.
SnD: Supply zone at prior SR Flip above current price — retest opportunity.
DXY: 1D bullish BOS on FOMC reaction candle.
COT: USD net longs expected to increase in next report.
Macro: Fed hawkish 3-hike path. ECB holding. Rate differential widening sharply.

Analysis:
FOMC event created a new macro regime shift. DXY BOS = structural confirmation of USD demand. EUR/USD bearish BMS = technical confirmation. Retracement to Supply zone = entry opportunity.

Decision: SELL on retracement to Supply zone — A Grade

Reasoning:
Post-FOMC macro regime = strongest USD bullish catalyst. Per MACRO-EVENT-001 — initial spike often produces a retracement before resuming. Wait for retracement to 4H Bearish OB at Premium zone. Do not chase the initial move. Enter on the retest.
```

---

### SCENARIO_ID: SCN-035
```
Market Context:
Fed delivers dovish surprise — pauses hikes and signals cuts coming. DXY drops sharply. EUR/USD rallies.

Framework Signals:
SMC: EUR/USD bullish BMS on 4H. Bullish OB forming on retracement.
SnD: Demand zone at prior RS Flip. Retracement entry available.
DXY: 1D bearish BOS. DXY below prior support.
COT: USD net longs starting to reduce. EUR net shorts covering.
Macro: Fed dovish pivot = USD bearish macro regime shift. ECB still holding.

Analysis:
Fed pivot is the most powerful macro event for USD weakness. DXY BOS lower = structural confirmation. EUR/USD BMS higher = technical confirmation.

Decision: BUY on retracement to Demand zone — A Grade

Reasoning:
Per MACRO-CB-003 — policy pivot is a major trend reversal signal. Do not chase initial EUR/USD spike. Wait for retracement to 4H Bullish OB at Discount zone. Per MACRO-EVENT-001 — initial spike retraces before resuming. Enter on the first retest of the new Demand zone.
```

---

### SCENARIO_ID: SCN-036
```
Market Context:
NFP releases. USD spikes sharply higher for 20 pips taking BSL above equal highs. Then immediately reverses and closes 25 pips lower — below the pre-NFP level.

Framework Signals:
SMC: BSL swept above equal highs during news spike. Price closed back sharply below → Turtle Soup Short trigger (SMC-SELL-001). Bearish BMS forming on 15M.
SnD: Supply zone above current price — SR Flip from prior breakdown.
DXY: NFP spike on DXY also — wick above prior high, closed below → DXY BSL sweep.
Macro: NFP beat forecast slightly but wage growth missed — mixed signal. Market repriced dovish post-initial spike.

Analysis:
NFP used as liquidity grab catalyst (MACRO-EVENT-008 — news spike = stop hunt). BSL swept above equal highs → price closed back below = Turtle Soup Short confirmed. DXY also showing same sweep pattern.

Decision: SELL — A Grade (post news window)

Reasoning:
Per MACRO-EVENT-003 — NFP initial spike frequently a liquidity grab. BSL sweep + close back below = institutional distribution using the news as catalyst. Turtle Soup Short trigger active. Enter after 30-minute news window clears with 15M confirmation. Target SSL pool below.
```

---

### SCENARIO_ID: SCN-037
```
Market Context:
ECB turns dovish (cuts rates) while Fed holds high. EUR/USD in structural downtrend. Policy divergence fully active.

Framework Signals:
SMC: Bearish BMS on 1D. Bearish OB on 4H pullback. BSL swept, price reversing.
SnD: Supply zone forming at SR Flip. Pattern 3 (90% setup — Previous Highs + QML + MPL).
DXY: 1W/1D bullish trend.
COT: EUR net shorts increasing. USD net longs increasing.
Macro: Fed-ECB rate differential at maximum — MACRO-CB-008 (policy divergence) = strongest possible trend driver. ECB cutting + Fed holding = EUR/USD bearish for months.
Wyckoff: 1D Distribution Phase confirmed.

Analysis:
Policy divergence is the macro anchor — the single strongest medium-term trend driver (MACRO-CB-008). All frameworks aligned. SnD Pattern 3 (90% setup) provides the technical entry. Wyckoff distribution confirms.

Decision: SELL — A+ Grade

Reasoning:
Policy divergence = sustained macro trend driver. SnD 90% setup (Pattern 3) + SMC bearish OB + Wyckoff distribution + COT EUR short building + DXY bullish = complete institutional sell stack. Positional trade candidate. Trail aggressively after TP2.
```

---

### SCENARIO_ID: SCN-038
```
Market Context:
Sudden risk-off shock — major geopolitical event announced. Equity markets drop sharply. JPY and CHF surging. AUD/USD collapsing.

Framework Signals:
SMC: AUD/USD massive bearish BMS on 1H. No clean OB — impulsive move.
SnD: No fresh Supply zone to trade — move has already happened aggressively.
DXY: Spiking up (risk-off safe haven + USD demand).
COT: Pre-event positioning unknown — event occurred mid-week.
Macro: MACRO-RISK-001 (risk-off) active. MACRO-RISK-003 (JPY carry unwind) active. AUD = risk currency collapsing.
AMD: Manipulation/Distribution phase compressed into single move.

Analysis:
Black swan / risk-off event. Initial impulsive move happened without a tradeable entry structure. No Supply zone to retest. Chasing the move is prohibited.

Decision: NO SETUP — Wait for structure

Reasoning:
Per MACRO-LIMIT-005 — black swan events override all frameworks temporarily. Do not chase impulsive moves without a structural zone. Wait for: (1) DXY to find a structural zone, (2) AUD/USD to retrace to a fresh Supply zone or Bearish OB on 4H, (3) risk sentiment to stabilize enough for AMD structure to reform. Re-engage only when clean SMC/SnD setup forms at a new zone.
```

---

*Chart Scenario Library | Version 1.0 | 2026-03 | Proprietary*
