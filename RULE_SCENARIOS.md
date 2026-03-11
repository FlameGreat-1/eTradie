
---

# DOCUMENT — `chart_scenarios.md`

Location:

```text
knowledge/scenarios/chart_scenarios.md
```

---

# 1️⃣ METADATA HEADER (REQUIRED)

```md
---
doc_id: chart_scenario_library
doc_type: scenario_library
framework: MultiFramework
title: Chart Scenario Library
version: 1.0
status: active
author: System Owner
effective_date: 2026-03
updated_at: 2026-03
source_of_truth: true
---
```

Required metadata:

```
doc_id
doc_type
framework
title
version
status
author
effective_date
updated_at
source_of_truth
```

---

# 2️⃣ PURPOSE OF THIS DOCUMENT

This document provides **structured market scenarios demonstrating how multiple frameworks interact**.

It helps the AI understand:

```
multi-framework confluence
valid setup conditions
invalid setup conditions
conflicting signals
high probability scenarios
```

The scenarios serve as **reference reasoning patterns**.

---

# 3️⃣ SCENARIO FORMAT (VERY IMPORTANT)

Every scenario must follow **this exact structure**.

```
SCENARIO_ID
Market Context
Framework Signals
Analysis
Decision
Reasoning
```

This format ensures **clean chunking and retrieval**.

---

# 4️⃣ SCENARIO TEMPLATE

Every scenario must use this template:

```md
### SCENARIO_ID: SCN-001

Market Context:
Describe the macro environment and higher timeframe structure.

Framework Signals:
List signals from SMC, SnD, Wyckoff, Macro, DXY, or COT.

Analysis:
Explain how the signals interact.

Decision:
State whether the setup should be taken or rejected.

Reasoning:
Explain the logic behind the decision.
```

---

# 5️⃣ SCENARIO CATEGORY STRUCTURE

Scenarios should be grouped by **market condition type**.

---

# SECTION 1 — HIGH PROBABILITY CONFLUENCE

```md
## 1. High Probability Confluence
```

Example:

```md
### SCENARIO_ID: SCN-001

Market Context:
EURUSD is trending downward on the daily timeframe.
Macro environment favors USD strength due to hawkish Fed policy.

Framework Signals:
SMC: Bearish break of structure on 4H.
SnD: Fresh supply zone formed.
DXY: Strong bullish trend.
COT: Increasing net long USD positioning.

Analysis:
Multiple frameworks indicate USD strength and bearish EURUSD bias.

Decision:
Trade permitted.

Reasoning:
Strong multi-framework confluence increases probability of continuation.
```

---

# SECTION 2 — STRUCTURE WITHOUT MACRO CONFIRMATION

```md
## 2. Technical Structure Without Macro Confirmation
```

Example:

```md
### SCENARIO_ID: SCN-002

Market Context:
EURUSD shows a bullish structure on lower timeframes,
but macro signals remain neutral.

Framework Signals:
SMC: Bullish internal break of structure.
SnD: Demand zone formed.
Macro: Neutral.
DXY: Sideways.

Analysis:
Technical signals exist but macro environment does not provide confirmation.

Decision:
Trade permitted with caution.

Reasoning:
Technical setups can still function in neutral macro environments,
but confidence is reduced.
```

---

# SECTION 3 — CONFLICTING SIGNALS

```md
## 3. Conflicting Signals
```

Example:

```md
### SCENARIO_ID: SCN-003

Market Context:
EURUSD approaching resistance on higher timeframe.

Framework Signals:
SMC: Bullish break of structure.
SnD: Supply zone above.
DXY: Rising strongly.
COT: Neutral.

Analysis:
Technical bullish signal conflicts with strong USD strength.

Decision:
Trade rejected.

Reasoning:
DXY strength increases probability of EURUSD decline.
```

---

# SECTION 4 — FAKEOUT CONDITIONS

```md
## 4. Fakeout Scenarios
```

Example:

```md
### SCENARIO_ID: SCN-004

Market Context:
GBPUSD breaks above resistance but quickly returns into range.

Framework Signals:
SMC: False breakout detected.
SnD: Price returns into supply zone.
DXY: Bullish momentum.

Analysis:
Breakout lacks follow-through and occurs against USD strength.

Decision:
Breakout considered a fakeout.

Reasoning:
Institutional liquidity grab likely occurred before reversal.
```

---

# SECTION 5 — REVERSAL CONDITIONS

```md
## 5. Reversal Scenarios
```

Example:

```md
### SCENARIO_ID: SCN-005

Market Context:
AUDUSD has been declining for several weeks.

Framework Signals:
SMC: Change of character on 4H.
SnD: Demand zone reaction.
COT: Extreme short positioning.
DXY: Losing bullish momentum.

Analysis:
Multiple signals indicate potential reversal.

Decision:
Long trade permitted.

Reasoning:
Extreme positioning and technical structure suggest reversal conditions.
```

---

# SECTION 6 — TREND CONTINUATION

```md
## 6. Trend Continuation Scenarios
```

Example:

```md
### SCENARIO_ID: SCN-006

Market Context:
USDJPY trending strongly upward.

Framework Signals:
SMC: Higher highs and higher lows.
SnD: Demand zone holding.
DXY: Strong bullish trend.
Macro: Rising interest rate differential.

Analysis:
All frameworks support USD strength.

Decision:
Continuation trade permitted.

Reasoning:
Strong alignment across frameworks supports trend continuation.
```

---

# 6️⃣ SCENARIO WRITING RULES

Scenarios must:

```
be realistic
contain multiple frameworks
avoid excessive narrative
remain concise
```

Each scenario should focus on **one reasoning concept**.

---

# 7️⃣ SCENARIO COUNT FOR PRODUCTION

Minimum recommended:

```
20 – 40 scenarios
```

Categories should include:

```
trend continuation
reversal
fakeouts
conflicts
macro overrides
clean confluence
```

---

# 8️⃣ CHUNKING STRUCTURE FOR RAG

Chunks should be generated by:

```
scenario sections
individual scenarios
```

Each scenario becomes a **retrievable reasoning example**.

---

# 9️⃣ WHAT MUST NOT BE INCLUDED

Do not include:

```
detailed trade journals
trade performance statistics
risk management numbers
personal commentary
```

Scenarios must remain **framework-focused**.

---

# VALIDATION CHECKLIST

Before ingestion verify:

```
metadata header exists
scenario IDs included
template structure followed
framework signals listed
decisions clearly defined
```

---

# ROLE IN THE SYSTEM

This document teaches the AI **how to combine frameworks in practice**.

It improves:

```
reasoning quality
conflict resolution
trade filtering
confluence recognition
```

---
