"""SQLAlchemy table definition for LLM connection persistence.

Stores user-configured LLM provider connections with API keys.
Only one connection can be active at a time.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.processor.storage.schemas.processor_schema import ProcessorBase


class LLMConnectionRow(ProcessorBase):
    """Persisted LLM provider connection configured by the user."""

    __tablename__ = "llm_connections"

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

    provider: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    api_key_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    base_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    temperature: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
    )
    max_output_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="16384",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        index=True,
    )
    label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        server_default="",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
