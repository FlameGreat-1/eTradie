from __future__ import annotations

from engine.rag.constants import Direction, Framework, ScenarioOutcome, SetupFamily

_FRAMEWORK_MAP: dict[str, str] = {
    "smart money concepts": Framework.SMC,
    "smart money concept": Framework.SMC,
    "smart money": Framework.SMC,
    "smc": Framework.SMC,
    "supply and demand": Framework.SND,
    "supply & demand": Framework.SND,
    "supply demand": Framework.SND,
    "s&d": Framework.SND,
    "snd": Framework.SND,
    "wyckoff": Framework.WYCKOFF,
    "wyckoff theory": Framework.WYCKOFF,
    "dxy": Framework.DXY,
    "dollar index": Framework.DXY,
    "us dollar index": Framework.DXY,
    "cot": Framework.COT,
    "commitment of traders": Framework.COT,
    "commitments of traders": Framework.COT,
    "macro": Framework.MACRO,
    "macroeconomic": Framework.MACRO,
    "macro to price": Framework.MACRO,
    "style": Framework.STYLE,
    "trading style": Framework.STYLE,
    "trading styles": Framework.STYLE,
}

_SETUP_FAMILY_MAP: dict[str, str] = {
    # SMC setups
    "order block": SetupFamily.ORDER_BLOCK,
    "ob": SetupFamily.ORDER_BLOCK,
    "bullish ob": SetupFamily.ORDER_BLOCK,
    "bearish ob": SetupFamily.ORDER_BLOCK,
    "fair value gap": SetupFamily.FAIR_VALUE_GAP,
    "fvg": SetupFamily.FAIR_VALUE_GAP,
    "bullish fvg": SetupFamily.FAIR_VALUE_GAP,
    "bearish fvg": SetupFamily.FAIR_VALUE_GAP,
    "liquidity sweep": SetupFamily.LIQUIDITY_SWEEP,
    "sweep": SetupFamily.LIQUIDITY_SWEEP,
    "stop hunt": SetupFamily.LIQUIDITY_SWEEP,
    "turtle soup": SetupFamily.TURTLE_SOUP,
    "turtle soup long": SetupFamily.TURTLE_SOUP,
    "turtle soup short": SetupFamily.TURTLE_SOUP,
    "breaker block": SetupFamily.BREAKER_BLOCK,
    "breaker": SetupFamily.BREAKER_BLOCK,
    "amd": SetupFamily.AMD,
    "accumulation manipulation distribution": SetupFamily.AMD,
    "compression": SetupFamily.COMPRESSION,
    # SnD setups
    "supply zone": SetupFamily.SUPPLY_ZONE,
    "supply": SetupFamily.SUPPLY_ZONE,
    "demand zone": SetupFamily.DEMAND_ZONE,
    "demand": SetupFamily.DEMAND_ZONE,
    "qml": SetupFamily.QML,
    "quasimodo": SetupFamily.QML,
    "quasi market level": SetupFamily.QML,
    "qm": SetupFamily.QML,
    "sr flip": SetupFamily.SR_FLIP,
    "support resistance flip": SetupFamily.SR_FLIP,
    "rs flip": SetupFamily.RS_FLIP,
    "resistance support flip": SetupFamily.RS_FLIP,
    "mpl": SetupFamily.QML,
    "mini price level": SetupFamily.QML,
    "fakeout": SetupFamily.SUPPLY_ZONE,
    # Wyckoff setups
    "spring": SetupFamily.SPRING,
    "wyckoff spring": SetupFamily.SPRING,
    "upthrust": SetupFamily.UPTHRUST,
    "utad": SetupFamily.UPTHRUST,
    "upthrust after distribution": SetupFamily.UPTHRUST,
    "accumulation": SetupFamily.ACCUMULATION,
    "wyckoff accumulation": SetupFamily.ACCUMULATION,
    "distribution": SetupFamily.DISTRIBUTION,
    "wyckoff distribution": SetupFamily.DISTRIBUTION,
    "markup": SetupFamily.MARKUP,
    "markup phase": SetupFamily.MARKUP,
    "markdown": SetupFamily.MARKDOWN,
    "markdown phase": SetupFamily.MARKDOWN,
    "re accumulation": SetupFamily.ACCUMULATION,
    "reaccumulation": SetupFamily.ACCUMULATION,
    "re distribution": SetupFamily.DISTRIBUTION,
    "redistribution": SetupFamily.DISTRIBUTION,
}

_DIRECTION_MAP: dict[str, str] = {
    "bullish": Direction.LONG,
    "bull": Direction.LONG,
    "buy": Direction.LONG,
    "long": Direction.LONG,
    "bid": Direction.LONG,
    "demand": Direction.LONG,
    "bearish": Direction.SHORT,
    "bear": Direction.SHORT,
    "sell": Direction.SHORT,
    "short": Direction.SHORT,
    "supply": Direction.SHORT,
    "neutral": Direction.NEUTRAL,
    "flat": Direction.NEUTRAL,
    "no setup": Direction.NEUTRAL,
    "ranging": Direction.NEUTRAL,
}

_OUTCOME_MAP: dict[str, str] = {
    "win": ScenarioOutcome.VALID_WIN,
    "valid_win": ScenarioOutcome.VALID_WIN,
    "valid win": ScenarioOutcome.VALID_WIN,
    "loss": ScenarioOutcome.VALID_LOSS,
    "valid_loss": ScenarioOutcome.VALID_LOSS,
    "valid loss": ScenarioOutcome.VALID_LOSS,
    "failed": ScenarioOutcome.FAILED_SETUP,
    "failed_setup": ScenarioOutcome.FAILED_SETUP,
    "failed setup": ScenarioOutcome.FAILED_SETUP,
    "no setup": ScenarioOutcome.FAILED_SETUP,
    "edge_case": ScenarioOutcome.EDGE_CASE,
    "edge case": ScenarioOutcome.EDGE_CASE,
    "edge": ScenarioOutcome.EDGE_CASE,
}


def resolve_framework(raw: str) -> str | None:
    return _FRAMEWORK_MAP.get(raw.strip().lower())


def resolve_setup_family(raw: str) -> str | None:
    normalized = raw.strip().lower().replace("-", " ").replace("_", " ")
    return _SETUP_FAMILY_MAP.get(normalized)


def resolve_direction(raw: str) -> str | None:
    return _DIRECTION_MAP.get(raw.strip().lower())


def resolve_outcome(raw: str) -> str | None:
    return _OUTCOME_MAP.get(raw.strip().lower())
