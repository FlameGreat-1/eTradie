from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class ScenarioRow(Base):
    __tablename__ = "rag_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False,
    )
    framework: Mapped[str] = mapped_column(String(32), nullable=False)
    setup_family: Mapped[str] = mapped_column(String(64), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    explanation_text: Mapped[str] = mapped_column(Text, nullable=False)
    image_refs: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="[]")
    confluence_tags: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="[]")
    style_tags: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="[]")
    linked_chunk_ids: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="[]")
    metadata: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_rag_scenarios_document_id", "document_id"),
        Index("ix_rag_scenarios_framework", "framework"),
        Index("ix_rag_scenarios_setup_family", "setup_family"),
        Index("ix_rag_scenarios_direction", "direction"),
        Index("ix_rag_scenarios_outcome", "outcome"),
        Index("ix_rag_scenarios_is_active", "is_active"),
        Index("ix_rag_scenarios_fw_setup_dir", "framework", "setup_family", "direction"),
    )
