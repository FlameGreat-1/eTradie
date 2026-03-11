from __future__ import annotations

from engine.rag.constants import Direction, Framework, ScenarioOutcome, SetupFamily

FRAMEWORK_TAGS: frozenset[str] = frozenset(f.value for f in Framework)
SETUP_FAMILY_TAGS: frozenset[str] = frozenset(f.value for f in SetupFamily)
DIRECTION_TAGS: frozenset[str] = frozenset(d.value for d in Direction)
OUTCOME_TAGS: frozenset[str] = frozenset(o.value for o in ScenarioOutcome)

CONFLUENCE_TAGS: frozenset[str] = frozenset({
    "bms", "choch", "sms", "inducement", "liquidity_sweep",
    "order_block", "fair_value_gap", "breaker_block", "mitigation",
    "qm", "qml", "qmh", "sr_flip", "rs_flip", "mpl",
    "fakeout", "compression", "marubozu", "displacement",
    "spring", "upthrust", "sos", "sow", "lps", "lpsy",
    "dxy_alignment", "cot_extreme", "macro_alignment",
    "session_london", "session_new_york", "session_asia",
    "fibonacci_618", "fibonacci_786", "fibonacci_optimal",
})

STYLE_TAGS: frozenset[str] = frozenset({
    "scalping", "intraday", "swing", "positional",
})

TIMEFRAME_TAGS: frozenset[str] = frozenset({
    "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN",
})
