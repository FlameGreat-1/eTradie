from __future__ import annotations

from engine.rag.constants import Direction, Framework, SetupFamily

_FRAMEWORK_MAP: dict[str, str] = {
    "smart money concepts": Framework.SMC,
    "smart money": Framework.SMC,
    "smc": Framework.SMC,
    "supply and demand": Framework.SND,
    "supply & demand": Framework.SND,
    "s&d": Framework.SND,
    "snd": Framework.SND,
    "wyckoff": Framework.WYCKOFF,
    "dxy": Framework.DXY,
    "dollar index": Framework.DXY,
    "cot": Framework.COT,
    "commitments of traders": Framework.COT,
    "macro": Framework.MACRO,
    "style": Framework.STYLE,
    "trading style": Framework.STYLE,
}

_SETUP_FAMILY_MAP: dict[str, str] = {
    "order block": SetupFamily.ORDER_BLOCK,
    "ob": SetupFamily.ORDER_BLOCK,
    "fair value gap": SetupFamily.FAIR_VALUE_GAP,
    "fvg": SetupFamily.FAIR_VALUE_GAP,
    "liquidity sweep": SetupFamily.LIQUIDITY_SWEEP,
    "sweep": SetupFamily.LIQUIDITY_SWEEP,
    "breaker block": SetupFamily.BREAKER_BLOCK,
    "breaker": SetupFamily.BREAKER_BLOCK,
    "supply zone": SetupFamily.SUPPLY_ZONE,
    "supply": SetupFamily.SUPPLY_ZONE,
    "demand zone": SetupFamily.DEMAND_ZONE,
    "demand": SetupFamily.DEMAND_ZONE,
    "spring": SetupFamily.SPRING,
    "upthrust": SetupFamily.UPTHRUST,
    "accumulation": SetupFamily.ACCUMULATION,
    "distribution": SetupFamily.DISTRIBUTION,
    "markup": SetupFamily.MARKUP,
    "markdown": SetupFamily.MARKDOWN,
}

_DIRECTION_MAP: dict[str, str] = {
    "bullish": Direction.LONG,
    "bull": Direction.LONG,
    "buy": Direction.LONG,
    "long": Direction.LONG,
    "bearish": Direction.SHORT,
    "bear": Direction.SHORT,
    "sell": Direction.SHORT,
    "short": Direction.SHORT,
    "neutral": Direction.NEUTRAL,
    "flat": Direction.NEUTRAL,
}


def resolve_framework(raw: str) -> str | None:
    return _FRAMEWORK_MAP.get(raw.strip().lower())


def resolve_setup_family(raw: str) -> str | None:
    normalized = raw.strip().lower().replace("-", " ").replace("_", " ")
    return _SETUP_FAMILY_MAP.get(normalized)


def resolve_direction(raw: str) -> str | None:
    return _DIRECTION_MAP.get(raw.strip().lower())
