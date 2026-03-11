from __future__ import annotations

from uuid import UUID

from engine.rag.constants import ConflictResult, CoverageResult, RetrievalStrategy
from engine.rag.models.citation import Citation
from engine.rag.models.context_bundle import ContextBundle
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.models.scenario import Scenario


def assemble_context_bundle(
    *,
    strategy: RetrievalStrategy,
    chunks: list[RetrievedChunk],
    citations: list[Citation],
    scenarios: list[Scenario],
    coverage_result: CoverageResult,
    conflict_result: ConflictResult,
    coverage_gaps: list[str] | None = None,
    conflict_details: list[str] | None = None,
    total_candidates: int = 0,
) -> ContextBundle:
    return ContextBundle(
        strategy_used=strategy,
        retrieved_chunks=tuple(chunks),
        citations=tuple(citations),
        matched_scenarios=tuple(scenarios),
        coverage_result=coverage_result,
        conflict_result=conflict_result,
        coverage_gaps=tuple(coverage_gaps or []),
        conflict_details=tuple(conflict_details or []),
        total_chunks_considered=total_candidates,
        total_chunks_returned=len(chunks),
    )
