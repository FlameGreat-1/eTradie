from __future__ import annotations

from collections import defaultdict

from engine.rag.constants import ConflictResult, DocumentType, METADATA_KEY_DIRECTION, METADATA_KEY_FRAMEWORK
from engine.rag.models.retrieval import RetrievedChunk
from engine.shared.logging import get_logger
from engine.shared.metrics import RAG_CONFLICT_DETECTIONS_TOTAL

logger = get_logger(__name__)

# Document types that are reference material containing both directions
# by design. These should NEVER trigger directional conflicts.
_REFERENCE_DOC_TYPES: frozenset[str] = frozenset({
    DocumentType.MASTER_RULEBOOK,
    DocumentType.TRADING_STYLE_RULES,
    DocumentType.CHART_SCENARIO_LIBRARY,
})


def detect_conflicts(
    chunks: list[RetrievedChunk],
) -> tuple[ConflictResult, list[str]]:
    """Detect genuine directional conflicts across retrieved chunks.

    A conflict exists when chunks from DIFFERENT analytical frameworks
    provide opposing directional signals for the same query context.

    NOT a conflict:
    - A single framework document containing both bullish and bearish
      rules (that is reference material, not a signal)
    - Reference documents (master_rulebook, trading_style_rules,
      chart_scenario_library) containing both directions
    - Chunks without explicit direction metadata
    """
    details: list[str] = []

    framework_directions = _extract_framework_direction_signals(chunks)

    # Only flag conflict when different frameworks disagree
    all_directions: set[str] = set()
    framework_direction_map: dict[str, set[str]] = {}

    for framework, directions in framework_directions.items():
        unique = set(directions)
        # A single framework with both long and short is reference, not conflict
        if len(unique) == 1:
            framework_direction_map[framework] = unique
            all_directions.update(unique)

    # Check if different frameworks point in different directions
    if len(all_directions) > 1 and len(framework_direction_map) > 1:
        conflicting_frameworks: dict[str, str] = {}
        for fw, dirs in framework_direction_map.items():
            for d in dirs:
                conflicting_frameworks[fw] = d

        # Verify it's a genuine cross-framework conflict
        direction_values = set(conflicting_frameworks.values())
        if len(direction_values) > 1:
            conflict_desc = ", ".join(
                f"{fw}={d}" for fw, d in sorted(conflicting_frameworks.items())
            )
            details.append(
                f"Cross-framework directional conflict: {conflict_desc}"
            )

    if details:
        logger.warning(
            "conflict_detected",
            conflicts=len(details),
            details=details,
        )
        RAG_CONFLICT_DETECTIONS_TOTAL.labels(result=ConflictResult.CONFLICT_FOUND).inc()
        return ConflictResult.CONFLICT_FOUND, details

    logger.debug("no_conflicts_detected", chunks=len(chunks))
    RAG_CONFLICT_DETECTIONS_TOTAL.labels(result=ConflictResult.NONE_DETECTED).inc()
    return ConflictResult.NONE_DETECTED, []


def _extract_framework_direction_signals(
    chunks: list[RetrievedChunk],
) -> dict[str, list[str]]:
    """Extract direction signals grouped by framework from chunk metadata.

    Only considers chunks that have explicit direction metadata tags
    (populated during ingest). Skips reference document types that
    naturally contain both directions.
    """
    signals: dict[str, list[str]] = defaultdict(list)

    for chunk in chunks:
        # Skip reference documents that contain both directions by design
        if chunk.doc_type in _REFERENCE_DOC_TYPES:
            continue

        framework = chunk.metadata.get(METADATA_KEY_FRAMEWORK, "")
        direction_raw = chunk.metadata.get(METADATA_KEY_DIRECTION, "")

        if not framework or not direction_raw:
            continue

        # direction_raw may be comma-separated (e.g., "long,short" for
        # mixed chunks). Only use single-direction chunks for conflict
        # detection.
        directions = [d.strip() for d in direction_raw.split(",") if d.strip()]
        if len(directions) == 1:
            signals[framework].append(directions[0])

    return dict(signals)
