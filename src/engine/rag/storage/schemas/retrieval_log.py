from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class RetrievalLogRow(Base):
    __tablename__ = "rag_retrieval_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    filters_applied: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    total_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunks_returned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    coverage_result: Mapped[str] = mapped_column(String(20), nullable=False, default="insufficient")
    conflict_result: Mapped[str] = mapped_column(String(20), nullable=False, default="none_detected")
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_rag_retlog_strategy", "strategy"),
        Index("ix_rag_retlog_coverage", "coverage_result"),
        Index("ix_rag_retlog_created_at", "created_at"),
        Index("ix_rag_retlog_trace_id", "trace_id"),
    )
