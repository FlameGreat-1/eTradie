"""SQLAlchemy table definition for broker connection persistence.

Stores user-configured MT5 broker connections with encrypted credentials.
Supports two connection types:
  - 'ea': ZeroMQ EA bridge (local PC or cloud VPS)
  - 'metaapi': MetaApi.cloud REST API

Only one connection can be active at a time.
The is_primary flag marks the preferred connection for trading.

Follows the exact same pattern as LLMConnectionRow.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.processor.storage.schemas.processor_schema import ProcessorBase


class BrokerConnectionRow(ProcessorBase):
    """Persisted broker connection configured by the user."""

    __tablename__ = "broker_connections"

    # -- Identity --------------------------------------------------------------
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

    # -- Connection type: 'ea' or 'metaapi' -----------------------------------
    connection_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    # -- Platform: 'mt4' or 'mt5' ---------------------------------------------
    platform: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default="mt5",
    )

    # -- Display name (e.g. "VPS EA - ICMarkets", "Local PC Backup") ----------
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # -- EA (ZeroMQ) credentials -----------------------------------------------
    ea_host: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    ea_port: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    ea_auth_token_encrypted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # -- MetaAPI credentials ---------------------------------------------------
    # NOTE: There is intentionally no per-row MetaAPI token column. The
    # platform-level developer token lives in the MT5_METAAPI_TOKEN env
    # var and is fetched from there at request time by the broker
    # factory. Each user only stores the cloud account_id provisioned
    # by MetaApiProvisioner from their MT5 broker credentials.
    metaapi_account_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    metaapi_region: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # -- MT5 account info (common to both types) ------------------------------
    mt5_server: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    mt5_login: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    mt5_password_encrypted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # -- State flags -----------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        index=True,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        index=True,
    )

    # -- Connection health -----------------------------------------------------
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="untested",
        index=True,
    )
    status_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="",
    )
    last_connected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -- Timestamps ------------------------------------------------------------
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
