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
    + release_time) plus audit timestamps. Older columns (currency,
    indicator, source, forecast, surprise, surprise_direction,
    impact, inflation_type) were retired by migration 0024 after a
    repo-wide audit found no live readers.

    Like every other macro table this row is GLOBAL - the upstream
    providers (FRED, OECD) are public market-data sources and the
    collector runs in the scheduler with no user context. The
    user_id column briefly added by migration 0013 was removed by
    migration 0025 along with the tenant-scoped unique constraint
    it required; this model now declares the global identity tuple
    (indicator_name, release_time) the collector has always used.
    """

    __tablename__ = "economic_releases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
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
            "indicator_name",
            "release_time",
            name="uq_econ_indicator_name_time",
        ),
        Index("ix_econ_release_time", "release_time"),
    )
