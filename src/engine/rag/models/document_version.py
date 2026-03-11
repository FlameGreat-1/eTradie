from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from engine.rag.constants import DocumentStatus
from engine.shared.models.base import TimestampedModel


class DocumentVersion(TimestampedModel):
    document_id: UUID
    version_number: int = Field(ge=1)
    status: DocumentStatus = DocumentStatus.DRAFT
    checksum: str = Field(min_length=1, max_length=128)
    published_at: Optional[datetime] = None
    superseded_at: Optional[datetime] = None
    superseded_by: Optional[UUID] = None
    change_summary: str = Field(default="", max_length=2048)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("checksum")
    @classmethod
    def validate_checksum_hex(cls, v: str) -> str:
        stripped = v.strip().lower()
        if not all(c in "0123456789abcdef" for c in stripped):
            raise ValueError("checksum must be a hex string")
        return stripped
