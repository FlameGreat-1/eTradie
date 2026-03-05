from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class COTReportRow(Base):
    __tablename__ = "cot_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    currency: Mapped[str] = mapped_column(String(5), nullable=False)
    contract_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    non_commercial_long: Mapped[int] = mapped_column(Integer, nullable=False)
    non_commercial_short: Mapped[int] = mapped_column(Integer, nullable=False)
    non_commercial_net: Mapped[int] = mapped_column(Integer, nullable=False)
    commercial_long: Mapped[int] = mapped_column(Integer, nullable=False)
    commercial_short: Mapped[int] = mapped_column(Integer, nullable=False)
    commercial_net: Mapped[int] = mapped_column(Integer, nullable=False)
    open_interest: Mapped[int] = mapped_column(Integer, nullable=False)
    wow_change: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extreme_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("currency", "report_date", name="uq_cot_currency_date"),
        Index("ix_cot_currency_date", "currency", "report_date"),
        Index("ix_cot_report_date", "report_date"),
    )
