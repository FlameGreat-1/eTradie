from __future__ import annotations

from engine.rag.constants import (
    METADATA_KEY_DIRECTION,
    METADATA_KEY_DOC_TYPE,
    METADATA_KEY_FRAMEWORK,
    METADATA_KEY_SCENARIO_OUTCOME,
    METADATA_KEY_SETUP_FAMILY,
    METADATA_KEY_STYLE,
    METADATA_KEY_TIMEFRAMES,
)


def build_where_filter(
    *,
    doc_types: list[str] | None = None,
    frameworks: list[str] | None = None,
    setup_families: list[str] | None = None,
    directions: list[str] | None = None,
    timeframes: list[str] | None = None,
    styles: list[str] | None = None,
    scenario_outcomes: list[str] | None = None,
) -> dict | None:
    """Build a ChromaDB where filter from retrieval parameters.

    Uses $eq/$in for single-value metadata fields (doc_type, framework,
    scenario_outcome) and $contains for multi-value comma-separated
    fields (direction, setup_family, timeframes, style) to ensure
    partial matching works correctly.

    Example: A chunk with metadata direction="long,short" will match
    a filter for direction="long" via $contains.
    """
    conditions: list[dict] = []

    # Single-value fields: use exact matching ($eq / $in)
    if doc_types and len(doc_types) == 1:
        conditions.append({METADATA_KEY_DOC_TYPE: {"$eq": doc_types[0]}})
    elif doc_types:
        conditions.append({METADATA_KEY_DOC_TYPE: {"$in": doc_types}})

    if frameworks and len(frameworks) == 1:
        conditions.append({METADATA_KEY_FRAMEWORK: {"$eq": frameworks[0]}})
    elif frameworks:
        conditions.append({METADATA_KEY_FRAMEWORK: {"$in": frameworks}})

    if scenario_outcomes and len(scenario_outcomes) == 1:
        conditions.append({METADATA_KEY_SCENARIO_OUTCOME: {"$eq": scenario_outcomes[0]}})
    elif scenario_outcomes:
        conditions.append({METADATA_KEY_SCENARIO_OUTCOME: {"$in": scenario_outcomes}})

    # Multi-value fields (comma-separated): use $contains for substring matching
    # When multiple values are requested, use $or to match any of them
    if directions:
        if len(directions) == 1:
            conditions.append({METADATA_KEY_DIRECTION: {"$contains": directions[0]}})
        else:
            conditions.append({"$or": [
                {METADATA_KEY_DIRECTION: {"$contains": d}} for d in directions
            ]})

    if setup_families:
        if len(setup_families) == 1:
            conditions.append({METADATA_KEY_SETUP_FAMILY: {"$contains": setup_families[0]}})
        else:
            conditions.append({"$or": [
                {METADATA_KEY_SETUP_FAMILY: {"$contains": sf}} for sf in setup_families
            ]})

    if timeframes:
        if len(timeframes) == 1:
            conditions.append({METADATA_KEY_TIMEFRAMES: {"$contains": timeframes[0]}})
        else:
            conditions.append({"$or": [
                {METADATA_KEY_TIMEFRAMES: {"$contains": tf}} for tf in timeframes
            ]})

    if styles:
        if len(styles) == 1:
            conditions.append({METADATA_KEY_STYLE: {"$contains": styles[0]}})
        else:
            conditions.append({"$or": [
                {METADATA_KEY_STYLE: {"$contains": s}} for s in styles
            ]})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}
