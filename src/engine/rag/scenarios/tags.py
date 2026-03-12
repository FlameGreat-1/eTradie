from __future__ import annotations

from engine.rag.constants import Direction, Framework, ScenarioOutcome, SetupFamily

FRAMEWORK_TAGS: frozenset[str] = frozenset(f.value for f in Framework)
SETUP_FAMILY_TAGS: frozenset[str] = frozenset(f.value for f in SetupFamily)
DIRECTION_TAGS: frozenset[str] = frozenset(d.value for d in Direction)
OUTCOME_TAGS: frozenset[str] = frozenset(o.value for o in ScenarioOutcome)

CONFLUENCE_TAGS: frozenset[str] = frozenset({
    # SMC structure signals
    "bms", "bos", "choch", "sms", "inducement", "liquidity_sweep",
    "order_block", "fair_value_gap", "breaker_block", "mitigation",
    "displacement", "premium", "discount", "equilibrium", "ote",
    "turtle_soup", "amd",
    # SnD structure signals
    "qm", "qml", "qmh", "sr_flip", "rs_flip", "mpl",
    "fakeout", "compression", "marubozu",
    "supply_zone", "demand_zone",
    # Wyckoff phase signals
    "spring", "upthrust", "utad", "sos", "sow", "lps", "lpsy",
    "accumulation", "distribution", "markup", "markdown",
    "reaccumulation", "redistribution",
    "selling_climax", "buying_climax", "automatic_rally", "automatic_reaction",
    # Cross-framework alignment signals
    "dxy_alignment", "dxy_divergence",
    "cot_extreme", "cot_accumulation", "cot_distribution",
    "macro_alignment", "macro_divergence",
    "policy_divergence", "rate_differential",
    # Session signals
    "session_london", "session_new_york", "session_overlap", "session_asia",
    # Fibonacci signals
    "fibonacci_50", "fibonacci_618", "fibonacci_705", "fibonacci_786",
    "fibonacci_optimal",
    # Risk/event signals
    "news_spike", "fomc", "nfp", "cpi", "risk_off", "risk_on",
})

STYLE_TAGS: frozenset[str] = frozenset({
    "scalping", "intraday", "swing", "positional",
})

TIMEFRAME_TAGS: frozenset[str] = frozenset({
    "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN",
    "1M", "1W", "1D", "4H", "1H",
})
