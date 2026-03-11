from __future__ import annotations

from engine.rag.constants import DocumentType, MANDATORY_KNOWLEDGE_GROUPS
from engine.shared.exceptions import RAGKnowledgeBaseError


def enforce_mandatory_assets(
    active_doc_types: set[str],
) -> None:
    missing = MANDATORY_KNOWLEDGE_GROUPS - frozenset(active_doc_types)
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
