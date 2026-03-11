from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from engine.rag.constants import DocumentType, EmbeddingStatus
from engine.shared.models.base import TimestampedModel


class Chunk(TimestampedModel):
    document_id: UUID
    document_version_id: UUID
    doc_type: DocumentType
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    content_hash: str = Field(min_length=1, max_length=128)
    token_count: int = Field(ge=1)
    embedding_status: EmbeddingStatus = EmbeddingStatus.PENDING
    section: Optional[str] = None
    subsection: Optional[str] = None
    parent_chunk_id: Optional[UUID] = None
    hierarchy_level: int = Field(default=0, ge=0, le=10)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("content_hash")
    @classmethod
    def validate_hash_hex(cls, v: str) -> str:
        stripped = v.strip().lower()
        if not all(c in "0123456789abcdef" for c in stripped):
            raise ValueError("content_hash must be a hex string")
        return stripped
