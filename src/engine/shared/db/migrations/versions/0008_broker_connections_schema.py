"""Broker connections schema.

Creates the broker_connections table for user-configured MT5 broker
connections. Supports two connection types:
  - 'ea' (ZeroMQ): connects to MT5 via ZeroMQ EA on a local PC or VPS
  - 'metaapi': connects to MT5 via MetaApi.cloud REST API

Credentials (API tokens, auth tokens) are stored encrypted using
the same Fernet encryption used for LLM connections.

Only one connection can be active at a time. The is_primary flag
marks the preferred connection for trading operations.

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-25
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "broker_connections",
        # -- Identity ----------------------------------------------------------
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        # -- Connection type: 'ea' or 'metaapi' -------------------------------
        sa.Column(
            "connection_type",
            sa.String(20),
            nullable=False,
        ),
        # -- Display name set by the user (e.g. "VPS EA", "Local PC EA") ------
        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
        ),
        # -- EA (ZeroMQ) credentials -------------------------------------------
        # Host/IP of the machine running MT5 + ZeroMQ EA.
        sa.Column("ea_host", sa.String(255), nullable=True),
        # ZeroMQ REP port on the EA (default 5555).
        sa.Column("ea_port", sa.Integer, nullable=True),
        # Encrypted auth token that must match the EA's AUTH_TOKEN parameter.
        sa.Column("ea_auth_token_encrypted", sa.Text, nullable=True),
        # -- MetaAPI credentials -----------------------------------------------
        # Encrypted MetaApi.cloud API token.
        sa.Column("metaapi_token_encrypted", sa.Text, nullable=True),
        # MetaApi provisioned account ID.
        sa.Column("metaapi_account_id", sa.String(100), nullable=True),
        # -- MT5 account info (common to both types) --------------------------
        # MT5 broker server name (e.g. "ICMarketsSC-Demo").
        sa.Column("mt5_server", sa.String(200), nullable=True),
        # MT5 account login number.
        sa.Column("mt5_login", sa.String(50), nullable=True),
        # -- State flags -------------------------------------------------------
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "is_primary",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        # -- Connection health -------------------------------------------------
        # Last known status: 'connected', 'disconnected', 'error', 'untested'.
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="untested",
        ),
        # Human-readable status message (e.g. error details).
        sa.Column(
            "status_message",
            sa.Text,
            nullable=False,
            server_default="",
        ),
        # Timestamp of the last successful health check.
        sa.Column(
            "last_connected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # -- Timestamps --------------------------------------------------------
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Indexes for common query patterns.
    op.create_index(
        "ix_bc_connection_type",
        "broker_connections",
        ["connection_type"],
    )
    op.create_index(
        "ix_bc_is_active",
        "broker_connections",
        ["is_active"],
    )
    op.create_index(
        "ix_bc_is_primary",
        "broker_connections",
        ["is_primary"],
    )
    op.create_index(
        "ix_bc_status",
        "broker_connections",
        ["status"],
    )
    op.create_index(
        "ix_bc_created_at",
        "broker_connections",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_bc_created_at", table_name="broker_connections")
    op.drop_index("ix_bc_status", table_name="broker_connections")
    op.drop_index("ix_bc_is_primary", table_name="broker_connections")
    op.drop_index("ix_bc_is_active", table_name="broker_connections")
    op.drop_index("ix_bc_connection_type", table_name="broker_connections")
    op.drop_table("broker_connections")
