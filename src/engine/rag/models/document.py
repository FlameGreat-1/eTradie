from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from engine.rag.constants import DocumentStatus, DocumentType, SourceFormat
from engine.shared.models.base import TimestampedModel


class Document(TimestampedModel):
    doc_type: DocumentType
    title: str = Field(min_length=1, max_length=512)
    source_path: str = Field(min_length=1, max_length=1024)
    source_format: SourceFormat
    status: DocumentStatus = DocumentStatus.DRAFT
    checksum: str = Field(min_length=1, max_length=128)
    active_version_id: Optional[UUID] = None
    framework_tags: frozenset[str] = Field(default_factory=frozenset)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def validate_title_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        return stripped

    @field_validator("checksum")
    @classmethod
    def validate_checksum_hex(cls, v: str) -> str:
        stripped = v.strip().lower()
        if not all(c in "0123456789abcdef" for c in stripped):
            raise ValueError("checksum must be a hex string")
        return stripped
