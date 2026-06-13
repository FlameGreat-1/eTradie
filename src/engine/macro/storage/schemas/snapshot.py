from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class MacroSnapshotRow(Base):
    """Durable last-good snapshot of a macro collector's enriched dataset.

    Macro data is global (no user scoping), so there is exactly one live
    row per collector namespace (e.g. 'cot', 'dxy', 'calendar'). The
    scheduler's authoritative writer path persists the collector's final
    ``model_dump(mode="json")`` here on every successful collection; the
    analysis read path rehydrates it on a Redis cache miss so the LLM
    input never silently loses a macro dataset, and the hot path never
    makes an external API call.

    The payload is the exact serialized dataset, so rehydration via the
    collector's ``cache_model`` reproduces the writer's output verbatim.
    """

    __tablename__ = "macro_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    namespace: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("namespace", name="uq_macro_snapshot_namespace"),
        Index("ix_macro_snapshot_namespace", "namespace"),
    )
