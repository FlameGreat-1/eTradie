"""Automatic broker symbol resolution.

Every MT broker publishes its own naming convention for the same
underlying instrument (EURUSD, EURUSDm, EURUSD.r, EURUSD+,
EURUSD.cash, EUR/USD, ...). This module picks the right broker-
actual name for each canonical pair from the broker's live Market
Watch reply (GET_ALL_SYMBOLS via the ZMQ EA). Scoring is generic:
no broker-specific suffix tables, no per-broker branches.
"""
from __future__ import annotations

import re
from typing import Iterable

from engine.shared.logging import get_logger

logger = get_logger(__name__)


CANONICAL_PAIRS: tuple[str, ...] = (
    # Forex majors
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
    "AUDUSD", "NZDUSD", "USDCAD",
    # Forex crosses
    "EURGBP", "EURJPY", "EURCHF", "EURAUD", "EURCAD", "EURNZD",
    "GBPJPY", "GBPCHF", "GBPAUD", "GBPCAD", "GBPNZD",
    "AUDJPY", "AUDCHF", "AUDCAD", "AUDNZD",
    "NZDJPY", "NZDCHF", "NZDCAD",
    "CADJPY", "CADCHF", "CHFJPY",
    # Metals
    "XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD",
    # Indices
    "US30", "US100", "US500", "NAS100", "SPX500", "DJI30",
    "GER40", "UK100", "FRA40", "JPN225", "AUS200",
    # Crypto majors
    "BTCUSD", "ETHUSD", "XRPUSD", "LTCUSD", "BCHUSD",
)

_INDEX_PAIRS: frozenset[str] = frozenset({
    "US30", "US100", "US500", "NAS100", "SPX500", "DJI30",
    "GER40", "UK100", "FRA40", "JPN225", "AUS200",
})

_ASSET_PATH_KEYWORDS: dict[str, tuple[str, ...]] = {
    "forex":   ("forex", "fx", "currencies", "majors", "minors", "crosses"),
    "metals":  ("metal", "metals", "commodit", "gold", "silver"),
    "indices": ("index", "indices", "cash index", "stock index"),
    "crypto":  ("crypto", "cryptocurrenc", "digital"),
}

_DESCRIPTION_DISQUALIFIERS: tuple[str, ...] = (
    "swap-free", "swap free", "islamic", "demo only", "non-trad",
)

_MAX_CANDIDATES_PER_PAIR = 32
_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]")

_DEFAULT_PREFERENCE: tuple[str, ...] = (
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
    "USDCAD", "USDCHF", "NZDUSD", "XAUUSD",
)


def _normalise(name: str) -> str:
    return _NON_ALNUM_RE.sub("", name.upper())


def _asset_class(pair: str) -> str:
    if pair.startswith(("XAU", "XAG", "XPT", "XPD")):
        return "metals"
    if pair.startswith(("BTC", "ETH", "XRP", "LTC", "BCH")):
        return "crypto"
    if pair in _INDEX_PAIRS:
        return "indices"
    return "forex"


def _suffix_length(normalised: str, canonical: str) -> int:
    if normalised == canonical:
        return 0
    if normalised.startswith(canonical):
        return len(normalised) - len(canonical)
    return len(normalised) - len(canonical) + 1


def _score(candidate: dict, canonical: str, asset_class: str, competitors: int) -> int:
    name = str(candidate.get("name", "")).strip()
    if not name:
        return -1
    normalised = _normalise(name)
    if canonical not in normalised:
        return -1

    score = 0
    suffix_len = _suffix_length(normalised, canonical)
    score += 100 if suffix_len == 0 else max(0, 60 - suffix_len * 5)

    path = str(candidate.get("path", "")).lower()
    if any(kw in path for kw in _ASSET_PATH_KEYWORDS.get(asset_class, ())):
        score += 50

    description = str(candidate.get("description", "")).lower()
    if competitors > 1 and any(bad in description for bad in _DESCRIPTION_DISQUALIFIERS):
        score -= 1000

    return score


def _candidates_for(canonical: str, broker_symbols: Iterable[dict]) -> list[dict]:
    matches: list[tuple[int, dict]] = []
    for sym in broker_symbols:
        if not isinstance(sym, dict):
            continue
        name = str(sym.get("name", "")).strip()
        if not name:
            continue
        if canonical in _normalise(name):
            matches.append((len(name), sym))
    matches.sort(key=lambda t: t[0])
    return [sym for _, sym in matches[:_MAX_CANDIDATES_PER_PAIR]]


def resolve_symbol_map(
    broker_symbols: Iterable[dict],
    *,
    canonical_pairs: tuple[str, ...] = CANONICAL_PAIRS,
) -> dict[str, str]:
    """Pick the highest-scoring broker-actual name for each canonical pair.

    Pure: no I/O, no async. broker_symbols is the list returned by
    ZmqClient.get_all_symbols(); each entry must carry 'name' and may
    carry 'description' and 'path'. Canonical pairs the broker does
    not offer are omitted from the result.
    """
    symbols = [s for s in broker_symbols if isinstance(s, dict)]
    if not symbols:
        logger.warning("symbol_resolver_empty_broker_symbol_list")
        return {}

    resolved: dict[str, str] = {}
    for canonical in canonical_pairs:
        candidates = _candidates_for(canonical, symbols)
        if not candidates:
            continue
        asset_class = _asset_class(canonical)
        scored = [(_score(c, canonical, asset_class, len(candidates)), c) for c in candidates]
        scored = [t for t in scored if t[0] >= 0]
        if not scored:
            continue
        scored.sort(key=lambda t: t[0], reverse=True)
        resolved[canonical] = str(scored[0][1].get("name", "")).strip()

    logger.info(
        "symbol_resolver_completed",
        extra={
            "broker_symbol_count": len(symbols),
            "canonical_pair_count": len(canonical_pairs),
            "resolved_count": len(resolved),
        },
    )
    return resolved


def pick_default_symbol(symbol_map: dict[str, str]) -> str:
    """Return the broker-actual name the chart should attach to on first boot.

    Walks _DEFAULT_PREFERENCE in order; falls back to the first entry in
    symbol_map; returns an empty string only when the map is empty.
    """
    if not symbol_map:
        return ""
    for canonical in _DEFAULT_PREFERENCE:
        if canonical in symbol_map:
            return symbol_map[canonical]
    return next(iter(symbol_map.values()))
