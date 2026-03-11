from __future__ import annotations

from uuid import UUID

from engine.rag.models.citation import Citation
from engine.rag.models.retrieval import RetrievedChunk


def build_citations(
    chunks: list[RetrievedChunk],
    *,
    version_map: dict[UUID, UUID],
) -> list[Citation]:
    citations: list[Citation] = []
    for chunk in chunks:
        doc_version_id = version_map.get(chunk.document_id)
        if doc_version_id is None:
            continue

        scenario_id: UUID | None = None
        raw_scenario = chunk.metadata.get("scenario_id")
        if raw_scenario:
            try:
                scenario_id = UUID(raw_scenario)
            except ValueError:
                pass

        excerpt = chunk.content[:2048] if chunk.content else ""

        citations.append(Citation(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            document_version_id=doc_version_id,
            doc_type=chunk.doc_type,
            section=chunk.section,
            subsection=chunk.subsection,
            scenario_id=scenario_id,
            relevance_score=chunk.score,
            excerpt=excerpt,
        ))

    return citations
