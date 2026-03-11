from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import Field

from engine.rag.constants import (
    Direction,
    DocumentType,
    Framework,
    RetrievalStrategy,
    SetupFamily,
)
from engine.shared.models.base import FrozenModel, TimestampedModel


class RetrievalFilter(FrozenModel):
    doc_types: frozenset[DocumentType] = Field(default_factory=frozenset)
    frameworks: frozenset[Framework] = Field(default_factory=frozenset)
    setup_families: frozenset[SetupFamily] = Field(default_factory=frozenset)
    directions: frozenset[Direction] = Field(default_factory=frozenset)
    timeframes: frozenset[str] = Field(default_factory=frozenset)
    styles: frozenset[str] = Field(default_factory=frozenset)
    doc_version_ids: frozenset[UUID] = Field(default_factory=frozenset)


class RetrievedChunk(FrozenModel):
    chunk_id: UUID
    document_id: UUID
    doc_type: DocumentType
    content: str
    score: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=0)
    section: Optional[str] = None
    subsection: Optional[str] = None
    metadata: dict[str, str] = Field(default_factory=dict)


class RetrievalResult(TimestampedModel):
    query_text: str
    strategy: RetrievalStrategy
    filters_applied: RetrievalFilter
    chunks: tuple[RetrievedChunk, ...] = Field(default_factory=tuple)
    total_candidates: int = Field(ge=0, default=0)
    score_threshold_used: float = Field(ge=0.0, le=1.0, default=0.25)
