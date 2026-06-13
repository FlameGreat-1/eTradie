from typing import Any
"""SQLAlchemy table definitions for processor persistence.

Defines analysis_outputs and analysis_audit_logs tables.
Follows the same pattern as TA and RAG schemas.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ProcessorBase(DeclarativeBase):
    pass


class AnalysisOutputRow(ProcessorBase):
    """Persisted analysis output from every processor invocation."""

    __tablename__ = "analysis_outputs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # -- Owner (multi-tenant isolation) ----------------------------------------
    # References auth_users.id managed by the Go auth service.
    # Every query MUST filter by user_id to enforce data ownership.
    user_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    analysis_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )
    pair: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    setup_grade: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    confluence_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    proceed_to_module_b: Mapped[str] = mapped_column(String(5), nullable=False)
    rr_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_price_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_price_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp1_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp2_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp3_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    trading_style: Mapped[str] = mapped_column(String(20), nullable=False, server_default="")
    session: Mapped[str] = mapped_column(String(30), nullable=False, server_default="")
    llm_provider: Mapped[str] = mapped_column(String(20), nullable=False, server_default="", index=True)
    llm_model: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True, server_default="success")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    raw_output: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class AnalysisAuditLogRow(ProcessorBase):
    """Audit trail for every processor invocation."""

    __tablename__ = "analysis_audit_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # -- Owner (multi-tenant isolation) ----------------------------------------
    user_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    analysis_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    pair: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Retrieval context
    retrieval_query_summary: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    # Sourced from the LLM's self-report (analysis.audit.retrieval.
    # strategy_used). Free text in practice -- e.g. Gemini emits
    # "Vector search with metadata filtering" -- not the short enum
    # the original 32-char width assumed. Widened to 128 in
    # migration 0023; the repository writer additionally truncates
    # defensively against future models that might exceed even this.
    retrieval_strategy: Mapped[str | None] = mapped_column(String(128), nullable=True)
    retrieval_chunks_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    retrieval_coverage: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    retrieval_coverage_details: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    retrieval_conflicts: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    retrieval_conflict_details: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    # LLM call reference
    llm_model: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
    llm_prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
    llm_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    llm_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    llm_duration_ms: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")

    # Response
    llm_response: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, server_default="{}")

    # Citations
    citations: Mapped[list[Any]] = mapped_column(JSON, nullable=False, server_default="[]")

    # Final decision
    final_direction: Mapped[str] = mapped_column(String(20), nullable=False, server_default="")
    final_grade: Mapped[str] = mapped_column(String(10), nullable=False, server_default="")
    final_confidence: Mapped[str] = mapped_column(String(20), nullable=False, server_default="")
    final_proceed: Mapped[str] = mapped_column(String(5), nullable=False, server_default="")

    # Validation
    validation_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    validation_errors: Mapped[list[Any]] = mapped_column(JSON, nullable=False, server_default="[]")

    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
