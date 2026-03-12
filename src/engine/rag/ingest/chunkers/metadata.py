from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from engine.rag.constants import (
    DocumentType,
    METADATA_KEY_CHUNK_HASH,
    METADATA_KEY_CHUNK_INDEX,
    METADATA_KEY_DIRECTION,
    METADATA_KEY_DOC_ID,
    METADATA_KEY_DOC_TYPE,
    METADATA_KEY_DOC_VERSION,
    METADATA_KEY_FRAMEWORK,
    METADATA_KEY_RULE_IDS,
    METADATA_KEY_SECTION,
    METADATA_KEY_SETUP_FAMILY,
    METADATA_KEY_SOURCE_PATH,
    METADATA_KEY_SUBSECTION,
    METADATA_KEY_TIMEFRAMES,
    METADATA_KEY_UPDATED_AT,
)
from engine.rag.ingest.chunkers.base import RawChunk

_RULE_ID_RE = re.compile(
    r"\b([A-Z][A-Z0-9_]+-[A-Z]+-\d{3}|[A-Z]+-[A-Z]+-\d{3}|[A-Z]+-\d{3})"
    r"|\bRULE_ID:\s*([A-Z][A-Z0-9_-]+\d{3})\b",
)

_DIRECTION_PATTERNS: dict[str, str] = {
    r"\bbullish\b": "long",
    r"\bbearish\b": "short",
    r"\bBUY\b": "long",
    r"\bSELL\b": "short",
    r"\bLONG\b": "long",
    r"\bSHORT\b": "short",
}

_TIMEFRAME_RE = re.compile(
    r"\b(1M|1W|1D|4H|1H|M30|M15|M5|M1|H4|H1|D1|W1|MN)\b"
)

_SETUP_FAMILY_PATTERNS: dict[str, str] = {
    r"\border block\b": "order_block",
    r"\bOB\b": "order_block",
    r"\bfair value gap\b": "fair_value_gap",
    r"\bFVG\b": "fair_value_gap",
    r"\bliquidity sweep\b": "liquidity_sweep",
    r"\bstop hunt\b": "liquidity_sweep",
    r"\bturtle soup\b": "liquidity_sweep",
    r"\bbreaker block\b": "breaker_block",
    r"\bsupply zone\b": "supply_zone",
    r"\bSupply Zone\b": "supply_zone",
    r"\bdemand zone\b": "demand_zone",
    r"\bDemand Zone\b": "demand_zone",
    r"\bspring\b": "spring",
    r"\bSpring\b": "spring",
    r"\bupthrust\b": "upthrust",
    r"\bUpthrust\b": "upthrust",
    r"\bUTAD\b": "upthrust",
    r"\baccumulation\b": "accumulation",
    r"\bAccumulation\b": "accumulation",
    r"\bdistribution\b": "distribution",
    r"\bDistribution\b": "distribution",
    r"\bmarkup\b": "markup",
    r"\bMarkup\b": "markup",
    r"\bmarkdown\b": "markdown",
    r"\bMarkdown\b": "markdown",
    r"\bQML\b": "qml",
    r"\bquasimodo\b": "qml",
    r"\bSR Flip\b": "sr_flip",
    r"\bRS Flip\b": "rs_flip",
    r"\bAMD\b": "amd",
    r"\bcompression\b": "compression",
}

_DOC_TYPE_TO_FRAMEWORK: dict[str, str] = {
    DocumentType.SMC_FRAMEWORK: "smc",
    DocumentType.SND_RULEBOOK: "snd",
    DocumentType.WYCKOFF_GUIDE: "wyckoff",
    DocumentType.DXY_FRAMEWORK: "dxy",
    DocumentType.COT_INTERPRETATION_GUIDE: "cot",
    DocumentType.MACRO_TO_PRICE_GUIDE: "macro",
    DocumentType.TRADING_STYLE_RULES: "style",
    DocumentType.MASTER_RULEBOOK: "global",
    DocumentType.CHART_SCENARIO_LIBRARY: "multi",
}


def attach_metadata(
    chunks: tuple[RawChunk, ...],
    *,
    doc_id: UUID,
    doc_type: str,
    doc_version: int,
    source_path: str,
) -> tuple[RawChunk, ...]:
    now_iso = datetime.now(UTC).isoformat()
    enriched: list[RawChunk] = []

    for chunk in chunks:
        meta = dict(chunk.metadata)

        # Core identity metadata
        meta[METADATA_KEY_DOC_ID] = str(doc_id)
        meta[METADATA_KEY_DOC_TYPE] = doc_type
        meta[METADATA_KEY_DOC_VERSION] = str(doc_version)
        meta[METADATA_KEY_CHUNK_INDEX] = str(chunk.chunk_index)
        meta[METADATA_KEY_CHUNK_HASH] = chunk.content_hash
        meta[METADATA_KEY_SOURCE_PATH] = source_path
        meta[METADATA_KEY_UPDATED_AT] = now_iso

        if chunk.section:
            meta[METADATA_KEY_SECTION] = chunk.section
        if chunk.subsection:
            meta[METADATA_KEY_SUBSECTION] = chunk.subsection

        # Framework metadata derived from doc_type
        framework = _DOC_TYPE_TO_FRAMEWORK.get(doc_type, "")
        if framework:
            meta[METADATA_KEY_FRAMEWORK] = framework

        # Extract rule IDs from chunk content
        rule_ids = _extract_rule_ids(chunk.content)
        if rule_ids:
            meta[METADATA_KEY_RULE_IDS] = ",".join(sorted(rule_ids))

        # Extract direction signals from chunk content
        directions = _extract_directions(chunk.content)
        if directions:
            meta[METADATA_KEY_DIRECTION] = ",".join(sorted(directions))

        # Extract setup families from chunk content
        setup_families = _extract_setup_families(chunk.content)
        if setup_families:
            meta[METADATA_KEY_SETUP_FAMILY] = ",".join(sorted(setup_families))

        # Extract timeframes from chunk content
        timeframes = _extract_timeframes(chunk.content)
        if timeframes:
            meta[METADATA_KEY_TIMEFRAMES] = ",".join(sorted(timeframes))

        enriched.append(RawChunk(
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            section=chunk.section,
            subsection=chunk.subsection,
            hierarchy_level=chunk.hierarchy_level,
            parent_chunk_index=chunk.parent_chunk_index,
            metadata=meta,
        ))

    return tuple(enriched)


def _extract_rule_ids(content: str) -> set[str]:
    """Extract all RULE_ID references from chunk content.

    Matches patterns like: SMC-BOS-001, MR-REJECT-005, STYLE-RISK-001,
    SND-ZONE-003, WYCKOFF-ACC-EVENT-005, DXY-TREND-001, COT-EXTREME-001,
    MACRO-RATE-001, etc.
    """
    ids: set[str] = set()
    for match in _RULE_ID_RE.finditer(content):
        rule_id = match.group(1) or match.group(2)
        if rule_id:
            ids.add(rule_id.strip())
    return ids


def _extract_directions(content: str) -> set[str]:
    """Extract directional signals from chunk content.

    Only extracts when the chunk has a clear directional focus.
    Returns empty set for chunks that discuss both directions equally
    (e.g., framework overview sections).
    """
    long_count = 0
    short_count = 0

    for pattern, direction in _DIRECTION_PATTERNS.items():
        matches = len(re.findall(pattern, content, re.IGNORECASE))
        if direction == "long":
            long_count += matches
        else:
            short_count += matches

    # Only tag direction if there is a clear dominant signal
    # If both directions are present roughly equally, this is a
    # reference/overview chunk - don't tag it directionally
    total = long_count + short_count
    if total == 0:
        return set()

    directions: set[str] = set()
    long_ratio = long_count / total if total > 0 else 0
    short_ratio = short_count / total if total > 0 else 0

    if long_ratio >= 0.7:
        directions.add("long")
    elif short_ratio >= 0.7:
        directions.add("short")
    # If neither dominates (mixed chunk), tag both so it can be
    # retrieved for either direction query
    elif total >= 2:
        directions.add("long")
        directions.add("short")

    return directions


def _extract_setup_families(content: str) -> set[str]:
    """Extract setup family tags from chunk content."""
    families: set[str] = set()
    for pattern, family in _SETUP_FAMILY_PATTERNS.items():
        if re.search(pattern, content):
            families.add(family)
    return families


def _extract_timeframes(content: str) -> set[str]:
    """Extract timeframe references from chunk content."""
    return set(_TIMEFRAME_RE.findall(content))
