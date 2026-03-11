from __future__ import annotations

from collections import defaultdict

from engine.rag.constants import ConflictResult
from engine.rag.models.retrieval import RetrievedChunk
from engine.shared.logging import get_logger
from engine.shared.metrics import RAG_CONFLICT_DETECTIONS_TOTAL

logger = get_logger(__name__)

_DIRECTION_KEYWORDS: dict[str, str] = {
    "bullish": "long",
    "long": "long",
    "buy": "long",
    "bearish": "short",
    "short": "short",
    "sell": "short",
}


def detect_conflicts(
    chunks: list[RetrievedChunk],
) -> tuple[ConflictResult, list[str]]:
    details: list[str] = []

    direction_signals = _extract_direction_signals(chunks)

    for key, directions in direction_signals.items():
        unique_directions = set(directions)
        if len(unique_directions) > 1:
            details.append(
                f"Conflicting directions for {key}: "
                f"{', '.join(sorted(unique_directions))} "
                f"(from {len(directions)} chunks)"
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


def _extract_direction_signals(
    chunks: list[RetrievedChunk],
) -> dict[str, list[str]]:
    signals: dict[str, list[str]] = defaultdict(list)

    for chunk in chunks:
        if not chunk.section:
            continue

        content_lower = chunk.content.lower()
        section_key = chunk.section.strip().lower()

        for keyword, direction in _DIRECTION_KEYWORDS.items():
            if keyword in content_lower:
                signals[section_key].append(direction)
                break

    return dict(signals)
