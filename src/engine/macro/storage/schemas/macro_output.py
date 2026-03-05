from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class MacroBiasOutputRow(Base):
    __tablename__ = "macro_bias_outputs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    currency: Mapped[str] = mapped_column(String(5), nullable=False)
    bias: Mapped[str] = mapped_column(String(10), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_chain_json: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    dxy_bias: Mapped[str] = mapped_column(String(10), nullable=False, default="NEUTRAL")
    cot_signal_json: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    event_risks_json: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    data_snapshot_ids_json: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    rules_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_macro_output_run_id", "run_id"),
        Index("ix_macro_output_currency", "currency"),
        Index("ix_macro_output_created_at", "created_at"),
        Index("ix_macro_output_run_currency", "run_id", "currency"),
    )
