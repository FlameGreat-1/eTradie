src/engine/
├── main.py                         # Engine service entrypoint shared by macro, ta, rag, processor.
├── config.py                       # Global engine configuration shared across all modules.
├── dependencies.py                 # Global dependency wiring / DI for the whole engine service.
├── shared/                         # Shared infrastructure: db, cache, http, logging, metrics, scheduler, tracing, etc.
├── macro/                          # Existing macroeconomics module.
├── ta/                             # Technical analysis module (defined below).
├── rag/                            # Later: knowledge-base retrieval module.
└── processor/                      # Later: Module A reasoning/orchestration output to Module B.


src/engine/ta/
├── __init__.py                     # Package marker for TA engine module.
├── config.py                       # TA-specific config only: enabled TA frameworks, broker selection, TA thresholds, symbol/timeframe settings.
├── constants.py                    # TA-specific constants only: timeframe enums, session labels, fib levels, structure/candidate labels.
├── orchestrator.py                 # TA module entrypoint: coordinates broker fetch, snapshot build, SMC/SnD detection, validation, persistence.
│
├── scheduler/
│   ├── __init__.py                 # Package marker for TA scheduling.
│   └── jobs.py                     # TA job definitions only: candle refresh, backfill, broker sync, analysis trigger prep. Uses engine.shared.scheduler.
│
├── broker/
│   ├── __init__.py                 # Package marker for broker/datafeed integration.
│   ├── base.py                     # Abstract broker/feed contract for TA market-data access.
│   ├── registry.py                 # Broker adapter registry/factory resolved from TA/global config.
│   ├── validator.py                # Validation of fetched market data: timestamp continuity, candle completeness, symbol/timeframe integrity.
│   ├── mt5/
│   │   ├── __init__.py             # Package marker for MT5 integration.
│   │   ├── client.py               # MT5 market-data adapter implementation for candles, ticks, spreads, symbol metadata.
│   │   └── config.py               # MT5-specific config mapping layered on top of engine/ta config.
│   ├── twelve_data/
│   │   ├── __init__.py             # Package marker for Twelve Data integration.
│   │   ├── client.py               # Twelve Data adapter for fallback/reference market data retrieval.
│   │   └── config.py               # Twelve Data-specific settings layered on top of TA/global config.
│   └── tradingview/
│       ├── __init__.py             # Package marker for TradingView-related ingestion.
│       ├── webhook/
│       │   ├── __init__.py         # Package marker for TradingView webhook handling.
│       │   └── handler.py          # TradingView webhook receiver/parser for externally pushed chart or alert events.
│       └── config.py               # TradingView webhook/auth/config settings.
│
├── models/
│   ├── __init__.py                 # Package marker for TA domain models.
│   ├── candle.py                   # Core candle/OHLCV domain models and validation helpers.
│   ├── swing.py                    # Swing point models: swing highs/lows, strength, index/window metadata.
│   ├── structure_event.py          # Structure event models: BOS, CHOCH, BMS, SMS, flips, confirmations.
│   ├── liquidity_event.py          # Liquidity event models: sweeps, grabs, inducement clears, pool interactions.
│   ├── zone.py                     # Zone models: OB, FVG, breaker, mitigation, supply, demand, QM-related zones.
│   ├── fibonacci.py                # Premium/discount and retracement models: OTE, equilibrium, dealing-range coordinates.
│   ├── session.py                  # Session models: Asia/London/NY sessions, overlaps, session tags, session-state metadata.
│   ├── candidate.py                # Deterministic candidate output models for SMC/SnD; strict contract consumed later by processor.
│   └── snapshot.py                 # TechnicalSnapshot aggregate model combining candles, swings, structure, liquidity, zones, fib, session context.
│
├── common/
│   ├── __init__.py                 # Package marker for shared TA logic reused by both SMC and SnD.
│   ├── timeframe/
│   │   ├── __init__.py             # Package marker for timeframe utilities.
│   │   └── manager.py              # HTF/LTF coordination helpers: timeframe mapping, synchronization, parent-child lookup.
│   ├── analyzers/
│   │   ├── __init__.py             # Package marker for shared deterministic analyzers.
│   │   ├── candles.py              # Candle primitives: body/wick ratios, displacement, imbalance hints, candle classification.
│   │   ├── swings.py               # Generic swing detection and swing-strength logic shared by all frameworks.
│   │   ├── session.py              # Session classification, boundaries, session-state tagging.
│   │   ├── liquidity.py            # Shared liquidity mapping: BSL/SSL detection, pool clustering, liquidity draw helpers.
│   │   ├── sweeps.py               # Sweep detection logic shared across SMC and SnD.
│   │   ├── fibonacci.py            # Premium/discount, OTE, retracement, dealing-range math shared across frameworks.
│   │   ├── dealing_range.py        # Dealing range construction and equilibrium logic used by both SMC and SnD.
│   │   ├── marubozu.py             # Marubozu detection/classification utility used mainly by SnD validators/builders.
│   │   └── compression.py          # Compression buildup/contraction detection shared across candidate construction.
│   ├── services/
│   │   ├── __init__.py             # Package marker for shared TA services.
│   │   ├── snapshot/
│   │   │   ├── __init__.py         # Package marker for snapshot-building service.
│   │   │   └── builder.py          # Builds normalized TechnicalSnapshot from broker data plus common analyzer outputs.
│   │   └── alignment/
│   │       ├── __init__.py         # Package marker for timeframe alignment service.
│   │       └── service.py          # Cross-timeframe alignment checks: HTF/LTF agreement, directional consistency, zone nesting/context.
│   └── utils/
│       ├── __init__.py             # Package marker for low-level TA utilities.
│       └── price/
│           ├── __init__.py         # Package marker for price utility helpers.
│           └── math.py             # Price math helpers: pip/point conversion, tolerance checks, distance/range calculations, rounding.
│
├── smc/
│   ├── __init__.py                 # Package marker for SMC framework.
│   ├── config.py                   # SMC-specific detection thresholds, feature flags, framework toggles, required primitive settings.
│   ├── detector.py                 # SMC orchestration entrypoint: runs SMC detectors, zone extraction, builders, validators, outputs candidates.
│   ├── detectors/
│   │   ├── __init__.py             # Package marker for SMC primitive detectors.
│   │   ├── bms.py                  # Detects SMC break-in-market-structure events according to codified rules.
│   │   ├── choch.py                # Detects change-of-character events.
│   │   ├── sms.py                  # Detects shift-in-market-structure / internal structure transitions.
│   │   ├── inducement.py           # Detects inducement/liquidity bait conditions preceding intended move.
│   │   ├── amd.py                  # Detects AMD conditions/phases only if fully codified deterministically.
│   │   └── turtle_soup.py          # Detects turtle soup liquidity sweep/reversal conditions deterministically.
│   ├── zones/
│   │   ├── __init__.py             # Package marker for SMC zone extractors.
│   │   ├── order_block.py          # Detects and defines bullish/bearish order block zones.
│   │   ├── fvg.py                  # Detects fair value gaps and manages their range/state.
│   │   ├── breaker.py              # Detects breaker block structures and transitions.
│   │   └── mitigation.py           # Detects mitigation/retest interactions with prior SMC zones.
│   ├── builders/
│   │   ├── __init__.py             # Package marker for SMC candidate builders.
│   │   ├── continuation.py         # Builds continuation-style SMC candidates from detected primitives and valid zones.
│   │   ├── reversal.py             # Builds reversal-style SMC candidates from sweeps, structure shifts, zone retests, LTF conditions.
│   │   └── amd/
│   │       ├── __init__.py         # Package marker for AMD-specific candidate building.
│   │       └── candidates.py       # Builds AMD-related SMC candidates from detected AMD/context events where permitted.
│   └── validators/
│       ├── __init__.py             # Package marker for SMC validation helpers.
│       ├── zone/
│       │   ├── __init__.py         # Package marker for SMC zone validation.
│       │   └── validator.py        # Validates SMC zone quality: freshness, overlap, mitigation state, displacement context, invalidation state.
│       └── ltf/
│           ├── __init__.py         # Package marker for SMC lower-timeframe validation.
│           └── confirmation.py     # Validates LTF confirmation requirements for SMC candidate eligibility.
│
├── snd/
│   ├── __init__.py                 # Package marker for SnD framework.
│   ├── config.py                   # SnD-specific thresholds, zone/fakeout/QM/MPL rules, feature flags, builder toggles.
│   ├── detector.py                 # SnD orchestration entrypoint: runs SnD detectors, builders, validators, outputs candidates.
│   ├── detectors/
│   │   ├── __init__.py             # Package marker for SnD primitive detectors.
│   │   ├── qm.py                   # Detects Quasimodo / QML / QMH structural formations.
│   │   ├── sr_flip.py              # Detects support-to-resistance flip structures.
│   │   ├── rs_flip.py              # Detects resistance-to-support flip structures.
│   │   ├── previous_levels.py      # Detects and aggregates previous highs/lows, repeated touches, clustered reaction levels.
│   │   ├── fakeouts.py             # Detects fakeout/exhaustion sequences around important levels/zones.
│   │   ├── mpl.py                  # Detects MPL-related structures/levels according to your formal rule definitions.
│   │   └── supply_demand.py        # Detects supply/demand zones and their exact boundaries/state.
│   ├── builders/
│   │   ├── __init__.py             # Package marker for SnD candidate builders.
│   │   └── candidates/
│   │       ├── __init__.py         # Package marker for SnD candidate composition.
│   │       ├── fakeout.py          # Builds fakeout-driven SnD candidates from detected levels, marubozu, compression, and zone context.
│   │       ├── qm.py               # Builds QM/QML/QMH-driven SnD candidates.
│   │       └── continuation.py     # Builds continuation-style SnD candidates only where your framework explicitly allows them.
│   └── validators/
│       ├── __init__.py             # Package marker for SnD validation helpers.
│       ├── marubozu/
│       │   ├── __init__.py         # Package marker for SnD marubozu validation.
│       │   └── validator.py        # Validates marubozu quality/eligibility in SnD context.
│       └── ltf/
│           ├── __init__.py         # Package marker for SnD lower-timeframe validation.
│           └── confirmation.py     # Validates LTF confirmation requirements for SnD candidate eligibility.
│
├── storage/
│   ├── __init__.py                 # Package marker for TA persistence layer.
│   ├── repositories/
│   │   ├── __init__.py             # Package marker for TA repositories.
│   │   ├── candle.py               # Repository for candle persistence, cache snapshots, and historical/backfill retrieval.
│   │   ├── snapshot.py             # Repository for persisted TechnicalSnapshot aggregates.
│   │   └── candidate.py            # Repository for persisted deterministic SMC/SnD candidate outputs.
│   └── schemas/
│       ├── __init__.py             # Package marker for TA ORM/database schemas.
│       ├── candle.py               # Database schema/model for candle storage.
│       ├── snapshot.py             # Database schema/model for technical snapshot storage.
│       └── candidate.py            # Database schema/model for deterministic candidate output storage.








I need to think bottom-up: primitives → utilities → models → analyzers → detectors → zones → builders → validators → services → orchestrators.

Let me organize them in strict dependency order:

**IMPLEMENTATION ORDER (106 FILES)**

---

**PHASE 1: FOUNDATION & PRIMITIVES (13 files)**

1. `src/engine/ta/__init__.py`
2. `src/engine/ta/constants.py`
3. `src/engine/ta/config.py`
4. `src/engine/ta/common/__init__.py`
5. `src/engine/ta/common/utils/__init__.py`
6. `src/engine/ta/common/utils/price/__init__.py`
7. `src/engine/ta/common/utils/price/math.py`
8. `src/engine/ta/common/timeframe/__init__.py`
9. `src/engine/ta/common/timeframe/manager.py`
10. `src/engine/ta/models/__init__.py`
11. `src/engine/ta/models/candle.py`
12. `src/engine/ta/models/swing.py`
13. `src/engine/ta/models/session.py`

---

**PHASE 2: BROKER LAYER (13 files)**

14. `src/engine/ta/broker/__init__.py`
15. `src/engine/ta/broker/base.py`
16. `src/engine/ta/broker/validator.py`
17. `src/engine/ta/broker/mt5/__init__.py`
18. `src/engine/ta/broker/mt5/config.py`
19. `src/engine/ta/broker/mt5/client.py`
20. `src/engine/ta/broker/twelve_data/__init__.py`
21. `src/engine/ta/broker/twelve_data/config.py`
22. `src/engine/ta/broker/twelve_data/client.py`
23. `src/engine/ta/broker/tradingview/__init__.py`
24. `src/engine/ta/broker/tradingview/config.py`
25. `src/engine/ta/broker/tradingview/webhook/__init__.py`
26. `src/engine/ta/broker/tradingview/webhook/handler.py`
27. `src/engine/ta/broker/registry.py`

---

**PHASE 3: DOMAIN MODELS (6 files)**

28. `src/engine/ta/models/fibonacci.py`
29. `src/engine/ta/models/structure_event.py`
30. `src/engine/ta/models/liquidity_event.py`
31. `src/engine/ta/models/zone.py`
32. `src/engine/ta/models/candidate.py`
33. `src/engine/ta/models/snapshot.py`

---

**PHASE 4: COMMON ANALYZERS (10 files)**

34. `src/engine/ta/common/analyzers/__init__.py`
35. `src/engine/ta/common/analyzers/candles.py`
36. `src/engine/ta/common/analyzers/swings.py`
37. `src/engine/ta/common/analyzers/session.py`
38. `src/engine/ta/common/analyzers/marubozu.py`
39. `src/engine/ta/common/analyzers/liquidity.py`
40. `src/engine/ta/common/analyzers/sweeps.py`
41. `src/engine/ta/common/analyzers/fibonacci.py`
42. `src/engine/ta/common/analyzers/dealing_range.py`
43. `src/engine/ta/common/analyzers/compression.py`

---

**PHASE 5: COMMON SERVICES (6 files)**

44. `src/engine/ta/common/services/__init__.py`
45. `src/engine/ta/common/services/snapshot/__init__.py`
46. `src/engine/ta/common/services/snapshot/builder.py`
47. `src/engine/ta/common/services/alignment/__init__.py`
48. `src/engine/ta/common/services/alignment/service.py`

---

**PHASE 6: SMC FRAMEWORK (24 files)**

49. `src/engine/ta/smc/__init__.py`
50. `src/engine/ta/smc/config.py`
51. `src/engine/ta/smc/detectors/__init__.py`
52. `src/engine/ta/smc/detectors/bms.py`
53. `src/engine/ta/smc/detectors/choch.py`
54. `src/engine/ta/smc/detectors/sms.py`
55. `src/engine/ta/smc/detectors/inducement.py`
56. `src/engine/ta/smc/detectors/turtle_soup.py`
57. `src/engine/ta/smc/detectors/amd.py`
58. `src/engine/ta/smc/zones/__init__.py`
59. `src/engine/ta/smc/zones/fvg.py`
60. `src/engine/ta/smc/zones/order_block.py`
61. `src/engine/ta/smc/zones/breaker.py`
62. `src/engine/ta/smc/zones/mitigation.py`
63. `src/engine/ta/smc/validators/__init__.py`
64. `src/engine/ta/smc/validators/zone/__init__.py`
65. `src/engine/ta/smc/validators/zone/validator.py`
66. `src/engine/ta/smc/validators/ltf/__init__.py`
67. `src/engine/ta/smc/validators/ltf/confirmation.py`
68. `src/engine/ta/smc/builders/__init__.py`
69. `src/engine/ta/smc/builders/continuation.py`
70. `src/engine/ta/smc/builders/reversal.py`
71. `src/engine/ta/smc/builders/amd/__init__.py`
72. `src/engine/ta/smc/builders/amd/candidates.py`
73. `src/engine/ta/smc/detector.py`

---

**PHASE 7: SND FRAMEWORK (24 files)**

74. `src/engine/ta/snd/__init__.py`
75. `src/engine/ta/snd/config.py`
76. `src/engine/ta/snd/detectors/__init__.py`
77. `src/engine/ta/snd/detectors/qm.py`
78. `src/engine/ta/snd/detectors/sr_flip.py`
79. `src/engine/ta/snd/detectors/rs_flip.py`
80. `src/engine/ta/snd/detectors/previous_levels.py`
81. `src/engine/ta/snd/detectors/mpl.py`
82. `src/engine/ta/snd/detectors/fakeouts.py`
83. `src/engine/ta/snd/detectors/supply_demand.py`
84. `src/engine/ta/snd/validators/__init__.py`
85. `src/engine/ta/snd/validators/marubozu/__init__.py`
86. `src/engine/ta/snd/validators/marubozu/validator.py`
87. `src/engine/ta/snd/validators/ltf/__init__.py`
88. `src/engine/ta/snd/validators/ltf/confirmation.py`
89. `src/engine/ta/snd/builders/__init__.py`
90. `src/engine/ta/snd/builders/candidates/__init__.py`
91. `src/engine/ta/snd/builders/candidates/fakeout.py`
92. `src/engine/ta/snd/builders/candidates/qm.py`
93. `src/engine/ta/snd/builders/candidates/continuation.py`
94. `src/engine/ta/snd/detector.py`

---

**PHASE 8: STORAGE LAYER (9 files)**

95. `src/engine/ta/storage/__init__.py`
96. `src/engine/ta/storage/schemas/__init__.py`
97. `src/engine/ta/storage/schemas/candle.py`
98. `src/engine/ta/storage/schemas/snapshot.py`
99. `src/engine/ta/storage/schemas/candidate.py`
100. `src/engine/ta/storage/repositories/__init__.py`
101. `src/engine/ta/storage/repositories/candle.py`
102. `src/engine/ta/storage/repositories/snapshot.py`
103. `src/engine/ta/storage/repositories/candidate.py`

---

**PHASE 9: ORCHESTRATION & SCHEDULING (4 files)**

104. `src/engine/ta/scheduler/__init__.py`
105. `src/engine/ta/scheduler/jobs.py`
106. `src/engine/ta/orchestrator.py`

---

**Total: 106 files in 9 phases**