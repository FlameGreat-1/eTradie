from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import Field

from engine.rag.constants import DocumentType
from engine.shared.models.base import FrozenModel


class Citation(FrozenModel):
    chunk_id: UUID
    document_id: UUID
    document_version_id: UUID
    doc_type: DocumentType
    section: Optional[str] = None
    subsection: Optional[str] = None
    scenario_id: Optional[UUID] = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    excerpt: str = Field(default="", max_length=2048)
