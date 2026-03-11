from __future__ import annotations

from pydantic import Field

from engine.rag.constants import ConflictResult, CoverageResult, RetrievalStrategy
from engine.rag.models.citation import Citation
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.models.scenario import Scenario
from engine.shared.models.base import TimestampedModel


class ContextBundle(TimestampedModel):
    strategy_used: RetrievalStrategy
    retrieved_chunks: tuple[RetrievedChunk, ...] = Field(default_factory=tuple)
    citations: tuple[Citation, ...] = Field(default_factory=tuple)
    matched_scenarios: tuple[Scenario, ...] = Field(default_factory=tuple)
    coverage_result: CoverageResult = CoverageResult.INSUFFICIENT
    conflict_result: ConflictResult = ConflictResult.NONE_DETECTED
    coverage_gaps: tuple[str, ...] = Field(default_factory=tuple)
    conflict_details: tuple[str, ...] = Field(default_factory=tuple)
    total_chunks_considered: int = Field(ge=0, default=0)
    total_chunks_returned: int = Field(ge=0, default=0)
