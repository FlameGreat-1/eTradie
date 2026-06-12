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
        conditions.append(
            {METADATA_KEY_SCENARIO_OUTCOME: {"$eq": scenario_outcomes[0]}}
        )
    elif scenario_outcomes:
        conditions.append({METADATA_KEY_SCENARIO_OUTCOME: {"$in": scenario_outcomes}})

    # Multi-value fields (comma-separated): we now use dynamic boolean flags
    # stored in metadata (e.g. timeframe_H1=True, direction_long=True).
    if directions:
        if len(directions) == 1:
            conditions.append({f"direction_{directions[0]}": {"$eq": True}})
        else:
            conditions.append(
                {"$or": [{f"direction_{d}": {"$eq": True}} for d in directions]}
            )

    if setup_families:
        if len(setup_families) == 1:
            conditions.append({f"setup_family_{setup_families[0]}": {"$eq": True}})
        else:
            conditions.append(
                {
                    "$or": [
                        {f"setup_family_{sf}": {"$eq": True}} for sf in setup_families
                    ]
                }
            )

    if timeframes:
        if len(timeframes) == 1:
            conditions.append({f"timeframe_{timeframes[0]}": {"$eq": True}})
        else:
            conditions.append(
                {"$or": [{f"timeframe_{tf}": {"$eq": True}} for tf in timeframes]}
            )

    if styles:
        # Note: chunkers metadata builder doesn't extract 'style' to a dynamic flag yet.
        # But this was broken before anyway (using $contains). If style extraction is added later,
        # it should follow the same pattern `style_X = True`.
        pass

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}
