from __future__ import annotations

from uuid import UUID

from pydantic import Field, field_validator

from engine.shared.models.base import TimestampedModel


class EmbeddingRecord(TimestampedModel):
    chunk_id: UUID
    provider: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=128)
    dimensions: int = Field(ge=64, le=4096)
    content_hash: str = Field(min_length=1, max_length=128)
    vector_hash: str = Field(min_length=1, max_length=128)

    @field_validator("content_hash", "vector_hash")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        stripped = v.strip().lower()
        if not all(c in "0123456789abcdef" for c in stripped):
            raise ValueError("hash must be a hex string")
        return stripped
