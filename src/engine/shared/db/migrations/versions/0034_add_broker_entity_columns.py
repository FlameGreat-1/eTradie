"""Add broker_id and broker_entity_id to broker_connections.

Revision ID: 0034
Revises: 0033
Create Date: 2026-06-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    table_names = set(insp.get_table_names())

    if "broker_connections" not in table_names:
        return

    existing = {c["name"] for c in insp.get_columns("broker_connections")}

    if "broker_id" not in existing:
        op.add_column(
            "broker_connections",
            sa.Column("broker_id", sa.String(length=50), nullable=True),
        )

    if "broker_entity_id" not in existing:
        op.add_column(
            "broker_connections",
            sa.Column("broker_entity_id", sa.String(length=100), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    table_names = set(insp.get_table_names())

    if "broker_connections" not in table_names:
        return

    existing = {c["name"] for c in insp.get_columns("broker_connections")}

    if "broker_entity_id" in existing:
        op.drop_column("broker_connections", "broker_entity_id")

    if "broker_id" in existing:
        op.drop_column("broker_connections", "broker_id")
