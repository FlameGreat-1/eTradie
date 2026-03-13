PLEASE NOTE: THIS IS JUST THE QUESTION I ASKED IN THE PREVIOUS SESSION WHICH IS WHY WE ARE DECIDING TO IMPLEMENT THE GATEWAY:


NOW EXAMINE THE OUTPUT.md THOROUGHLY FROM THE BEGINNING TO THE END.
NOW IF THAT'S EXACTLY THE OUTPUT OF THE TA+MACRO, WHAT EXACTLY WOULD THE RAG USE AND SEARCH AND WHAT EXACTLY WOULD THE RAG RETURN?
   
---

## AUDIT: What the RAG Would Use, Search, and Return Given This Exact TA+Macro Output

#### What the TA Output Contains (the signals)

The TA output for EURUSD H4 gives us:

**SMCCandidate:**
- `symbol`: EURUSD
- `pattern`: break_of_structure (with BMS detected, SMS detected)
- `direction`: BEARISH (implied from trend_direction in snapshot)
- `timeframe`: H4, HTF: D1
- `order_block`: 1.0945-1.0975
- `fvg`: 1.0980-1.1010
- `liquidity_swept`: true at 1.0880
- `inducement_cleared`: true
- `fib_level`: 0.618
- `session_context`: Asian
- `displacement_pips`: 120.5

**SnDCandidate:**
- `pattern`: supply_test (with QML, SR Flip, MPL, fakeout, compression)
- `direction`: BEARISH
- `supply_zone`: 1.0955-1.0975
- `previous_highs_count`: 3
- `fib_level`: 0.382

**TechnicalSnapshot:**
- `trend_direction`: BEARISH
- BOS events, BMS events confirmed
- Supply zones and demand zones identified

#### What the Macro Output Contains (the environment)

- **Fed**: Rate cut -25bps, dovish tone → USD BEARISH (MACRO-RATE-002, MACRO-CB-002)
- **ECB**: Lagarde hawkish speech → EUR BULLISH (MACRO-CB-001)
- **BOE**: Neutral MPC minutes
- **BOJ**: Dovish forward guidance, holding rates
- **CPI**: 3.2 actual vs 3.4 forecast = cold print → USD BEARISH (MACRO-INFLATION-004)
- **DXY**: 104.75 (value only, no trend structure in this output)
- **COT**: EUR non-commercial net +70,000 (net long EUR), GBP net -35,000 (net short GBP)
- **Calendar**: NFP tomorrow (HIGH impact within 24 hours), ECB rate decision in 8 days
- **News**: "Fed Cuts Rates" = HIGH impact bearish USD, "UK Employment Disappoints" = bearish GBP
- **Sentiment**: USD 62.5% long (retail crowded long USD)

---

#### THE PROBLEM: What the RAG Orchestrator Actually Receives

Looking at the `RAGOrchestrator.retrieve_context()` method signature:

```python
async def retrieve_context(
    self,
    query_text: str,          # ← What is this?
    *,
    strategy: str | None,
    framework: str | None,
    setup_family: str | None,
    direction: str | None,
    timeframe: str | None,
    style: str | None,
    trace_id: str | None,
)
```

**There is NO caller.** The RAG orchestrator exposes `retrieve_context()` but **nothing in the codebase calls it with the TA+Macro output**. The `Container.build_rag()` creates the `RAGOrchestrator` but it's never wired to the TA orchestrator or macro collectors. There is no component that:

1. Takes the `SMCCandidate` + `SnDCandidate` + `TechnicalSnapshot` from TA
2. Takes the `CentralBankDataSet` + `COTDataSet` + `EconomicDataSet` + `MarketDataSet` + `NewsDataSet` + `CalendarDataSet` from Macro
3. Translates them into the `query_text`, `framework`, `setup_family`, `direction`, `timeframe`, `style` parameters that `RAGOrchestrator.retrieve_context()` needs
4. Calls the RAG
5. Receives the `ContextBundle` back
6. Feeds it to the Processor LLM

**This is the missing bridge between TA+Macro and RAG.** Per ALIGNMENT.md, this is exactly the pipeline:

```
TA Output + Macro Output → RAG Retrieval (conditional on outputs) → Context Assembly → Processor LLM
```

#### What the RAG SHOULD Use to Search (Given This Output)

For this specific EURUSD example, the RAG query should be constructed from the TA+Macro outputs as:

| Parameter | Value | Derived From |
|---|---|---|
| `query_text` | `"EURUSD bearish BOS supply zone H4 USD dovish Fed rate cut ECB hawkish liquidity sweep order block FVG"` | Structured concatenation of TA pattern + macro signals |
| `framework` | `"smc"` | Primary candidate is SMCCandidate with BOS pattern |
| `setup_family` | `"order_block"` or `"supply_zone"` | OB detected in SMC, supply zone in SnD |
| `direction` | `"short"` | Both candidates BEARISH |
| `timeframe` | `"H4"` | Candidate timeframe |
| `style` | From active dashboard setting (not in output) | External input |

#### What the RAG SHOULD Return

Given the above query, the 4-bucket hybrid strategy should return:

**Bucket 1 - Rules (master_rulebook + trading_style_rules):**
- MR-REJECT-001 (news proximity - NFP tomorrow within 24hrs)
- MR-REJECT-002 (Asian session - session_context is "Asian")
- Section 4 confluence scoring table
- Section 6 risk management rules
- STYLE-AVOID-001 (news blackout windows)
- STYLE-SESSION-001 (session restrictions)

**Bucket 2 - Framework (SMC + SnD):**
- SMC-BOS-002 (Bearish BOS rules)
- SMC-OB-002 (Bearish Order Block)
- SMC-OB-003 (Valid OB criteria)
- SMC-FVG-002 (Bearish FVG)
- SMC-LIQ-003 (Liquidity sweep confirmation)
- SMC-ENTRY-001 (Standard SMC entry conditions)
- SND-ZONE-002 (Supply Zone definition)
- SND-ZONE-003 (SR Flip rules)
- SND-ZONE-005 (QML rules)
- SND-ENTRY-001 (Supply zone entry conditions)

**Bucket 3 - Macro/Cross-framework (DXY + COT + Macro):**
- MACRO-RATE-002 (Falling rates weaken currency - Fed cut)
- MACRO-CB-002 (Dovish central bank - Fed)
- MACRO-CB-008 (Diverging policy - Fed dovish + ECB hawkish)
- MACRO-INFLATION-004 (Cold CPI print)
- MACRO-EVENT-003 (NFP tomorrow - proximity warning)
- DXY-TREND rules (DXY value provided but no trend structure)
- COT-SHIFT-001 (EUR non-commercials net long +70k)

**Bucket 4 - Scenarios:**
- SCN-003 (EUR/USD Supply zone + Fed hawkish + DXY BOS - closest match but inverted macro)
- SCN-027 (EUR/USD bearish trend continuation at Supply zone)
- SCN-035 (Fed dovish surprise - directly matches this output)
- SCN-010 or SCN-012 (Conflicting signals scenarios - TA bearish but macro now USD bearish)

#### THE CRITICAL FINDING

**This specific output reveals a CONFLICT that the RAG must surface:**

The TA says BEARISH EURUSD (BOS lower, supply zone, order block short). But the Macro says the Fed just CUT rates (dovish) and CPI missed (cold print) = **USD BEARISH = EUR/USD BULLISH**. ECB is hawkish = EUR BULLISH. This is a **direct macro-vs-technical conflict**.

Per the knowledge base rules:
- `MACRO-LIMIT-003`: Technical without macro alignment = reduced grade (maximum B)
- `MACRO-BIAS-006`: Counter-macro technical setup requires 1D CHoCH + COT shift + minimum NEUTRAL macro
- `MR-REJECT-006`: Counter-trend without 1D ChoCH = NO SETUP
- SCN-010, SCN-011, SCN-012: All show NO SETUP when technical conflicts with macro

The RAG MUST retrieve these conflict/rejection rules so the LLM correctly outputs **NO SETUP** or at best **B grade with 0.5% risk** for this scenario.

Additionally, `MR-REJECT-001` applies because NFP is tomorrow (within 30 minutes is the hard rule, but the calendar shows it's within 24 hours - the system should flag this as EVENT RISK).

And `MR-REJECT-002` applies because `session_context` is "Asian" - no entries during Asian session.

**The RAG must return these rejection rules. If it doesn't, the LLM might approve a trade that violates 3 hard rejection rules simultaneously.**

---

That is exactly what the RAG would use, search, and return given this OUTPUT.md. The critical gap is that **there is no query builder component** that translates the structured TA+Macro outputs into the RAG orchestrator's parameters. That bridge needs to be built.
