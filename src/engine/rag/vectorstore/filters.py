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
    conditions: list[dict] = []

    if doc_types and len(doc_types) == 1:
        conditions.append({METADATA_KEY_DOC_TYPE: {"$eq": doc_types[0]}})
    elif doc_types:
        conditions.append({METADATA_KEY_DOC_TYPE: {"$in": doc_types}})

    if frameworks and len(frameworks) == 1:
        conditions.append({METADATA_KEY_FRAMEWORK: {"$eq": frameworks[0]}})
    elif frameworks:
        conditions.append({METADATA_KEY_FRAMEWORK: {"$in": frameworks}})

    if setup_families and len(setup_families) == 1:
        conditions.append({METADATA_KEY_SETUP_FAMILY: {"$eq": setup_families[0]}})
    elif setup_families:
        conditions.append({METADATA_KEY_SETUP_FAMILY: {"$in": setup_families}})

    if directions and len(directions) == 1:
        conditions.append({METADATA_KEY_DIRECTION: {"$eq": directions[0]}})
    elif directions:
        conditions.append({METADATA_KEY_DIRECTION: {"$in": directions}})

    if timeframes and len(timeframes) == 1:
        conditions.append({METADATA_KEY_TIMEFRAMES: {"$eq": timeframes[0]}})
    elif timeframes:
        conditions.append({METADATA_KEY_TIMEFRAMES: {"$in": timeframes}})

    if styles and len(styles) == 1:
        conditions.append({METADATA_KEY_STYLE: {"$eq": styles[0]}})
    elif styles:
        conditions.append({METADATA_KEY_STYLE: {"$in": styles}})

    if scenario_outcomes and len(scenario_outcomes) == 1:
        conditions.append({METADATA_KEY_SCENARIO_OUTCOME: {"$eq": scenario_outcomes[0]}})
    elif scenario_outcomes:
        conditions.append({METADATA_KEY_SCENARIO_OUTCOME: {"$in": scenario_outcomes}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}
