from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class EconomicReleaseRow(Base):
    """Persisted economic release.

    Mirrors the slimmed EconomicRelease Pydantic model: only the
    fields the LLM actually reads (indicator_name + actual + previous
    + release_time) plus the multi-tenant user_id scope and audit
    timestamps. Older columns (currency, indicator, source, forecast,
    surprise, surprise_direction, impact, inflation_type) were retired
    by migration 0024 after a repo-wide audit found no live readers.
    """

    __tablename__ = "economic_releases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    indicator_name: Mapped[str] = mapped_column(String(200), nullable=False)
    actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous: Mapped[float | None] = mapped_column(Float, nullable=True)
    release_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "indicator_name",
            "release_time",
            name="uq_econ_user_indicator_name_time",
        ),
        Index("ix_econ_user_id", "user_id"),
        Index("ix_econ_user_release_time", "user_id", "release_time"),
    )
