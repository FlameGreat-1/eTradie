from __future__ import annotations

from engine.rag.constants import MANDATORY_KNOWLEDGE_GROUPS, DocumentType
from engine.shared.exceptions import RAGKnowledgeBaseError


def _to_known_doc_types(active_doc_types: set[str]) -> frozenset[DocumentType]:
    """Coerce stored doc-type strings to DocumentType, skipping unknowns.

    An out-of-enum value (legacy or mistyped doc_type persisted on a
    document row) cannot satisfy any mandatory group, so dropping it
    here lets it surface as a missing mandatory asset below rather than
    raising an unhandled ValueError inside enforce_mandatory_assets.
    """
    known: set[DocumentType] = set()
    for dt in active_doc_types:
        try:
            known.add(DocumentType(dt))
        except ValueError:
            continue
    return frozenset(known)


def enforce_mandatory_assets(
    active_doc_types: set[str],
) -> None:
    missing = MANDATORY_KNOWLEDGE_GROUPS - _to_known_doc_types(active_doc_types)
    if missing:
        raise RAGKnowledgeBaseError(
            f"Missing mandatory knowledge assets: {sorted(missing)}",
            details={"missing": sorted(missing)},
        )


def enforce_version_requirements(
    doc_type: str,
    *,
    has_active_version: bool,
) -> None:
    if doc_type in MANDATORY_KNOWLEDGE_GROUPS and not has_active_version:
        raise RAGKnowledgeBaseError(
            f"Mandatory asset {doc_type} has no active version",
            details={"doc_type": doc_type},
        )


def enforce_scenario_minimum(
    scenario_count: int,
    *,
    minimum: int = 20,
) -> None:
    if scenario_count < minimum:
        raise RAGKnowledgeBaseError(
            f"Insufficient scenarios: {scenario_count} < {minimum} required",
            details={"count": scenario_count, "required": minimum},
        )
