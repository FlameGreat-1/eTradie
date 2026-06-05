"""SQLAlchemy table definition for broker connection persistence.

Stores user-configured MT5 broker connections with encrypted credentials.
Supports three connection types:
  - 'ea': ZeroMQ EA bridge (LOCAL DEVELOPMENT ONLY - reads single-tenant
    MT5_ZMQ_* env vars; rejected at the router in production/staging)
  - 'metaapi': MetaApi.cloud REST API
  - 'hosted': Per-tenant Wine+Xvfb+MT5 Pod provisioned by HostedProvisioner
    in-cluster; the recommended production path for self-hosted MT5.

Only one connection can be active at a time.
The is_primary flag marks the preferred connection for trading.

Follows the exact same pattern as LLMConnectionRow.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, SmallInteger, String, Text
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

    # -- Connection type: 'ea', 'metaapi', or 'hosted' ------------------------
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

    # -- Hosted (Dockerized MT) credentials ------------------------------------
    # The Docker container ID spawned by the HostedProvisioner for this
    # user's hosted connection. Used to stop/remove the container on
    # deletion and to resolve the container's internal IP for ZeroMQ.
    hosted_container_id: Mapped[Optional[str]] = mapped_column(
        String(100),
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
    # KEK version that wrapped the CURRENT ciphertext in this row's
    # encrypted credential columns (envelope encryption,
    # engine.shared.crypto). NULL means legacy pre-envelope ciphertext
    # / unknown version; it is operational metadata only and is never
    # load-bearing for decryption (the shared cipher decrypts legacy
    # tokens regardless). See migration 0033.
    key_version: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
    )
    # The chart-attach symbol the hosted MT terminal opens on boot.
    # Picked by the provisioner from the first row of the broker_symbols
    # table after BrokerSyncService has synchronously populated the
    # catalog from the broker's live Market Watch. NULL until the first
    # successful catalog sync. The full broker catalog lives in the
    # broker_symbols table; this column carries only the chart pick.
    mt5_symbol: Mapped[Optional[str]] = mapped_column(
        String(50),
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
