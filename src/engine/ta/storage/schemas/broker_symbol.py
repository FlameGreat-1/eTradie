from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class BrokerSymbolSchema(Base):
    """
    Persistent registry for broker symbols.

    Stores full metadata including the MT5 path for categorization.
    Synchronized from the broker (MetaAPI/ZMQ) in the background.
    """

    __tablename__ = "broker_symbols"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # We scope symbols by provider to avoid collisions if multiple brokers are used.
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # The account ID is important because different accounts have different symbols.
    account_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    path: Mapped[str] = mapped_column(String(255), nullable=True, index=True)

    digits: Mapped[int] = mapped_column(Integer, nullable=True)
    point: Mapped[float] = mapped_column(Float, nullable=True)

    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index(
            "ix_broker_symbols_provider_account_name",
            "provider",
            "account_id",
            "name",
            unique=True,
        ),
    )
