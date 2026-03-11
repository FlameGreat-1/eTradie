from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class AnalysisCitationRow(Base):
    __tablename__ = "rag_analysis_citations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retrieval_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_retrieval_logs.id", ondelete="CASCADE"), nullable=False,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False,
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_document_versions.id", ondelete="SET NULL"), nullable=False,
    )
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    section: Mapped[str | None] = mapped_column(String(256), nullable=True)
    subsection: Mapped[str | None] = mapped_column(String(256), nullable=True)
    rule_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scenario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_rag_acit_retrieval_id", "retrieval_log_id"),
        Index("ix_rag_acit_chunk_id", "chunk_id"),
        Index("ix_rag_acit_document_id", "document_id"),
        Index("ix_rag_acit_doc_type", "doc_type"),
        Index("ix_rag_acit_created_at", "created_at"),
    )
