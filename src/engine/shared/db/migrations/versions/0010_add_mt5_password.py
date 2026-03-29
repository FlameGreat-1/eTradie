"""Add mt5_password_encrypted to broker_connections.

Adds encrypted storage for the user's MT5 trading password so that
MetaAPI can re-provision (re-deploy) the cloud connection if needed.

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    table_name = "broker_connections"

    # Only add if the table exists and column is missing.
    if table_name in inspector.get_table_names():
        existing_columns = {
            col["name"] for col in inspector.get_columns(table_name)
        }

        if "mt5_password_encrypted" not in existing_columns:
            op.add_column(
                table_name,
                sa.Column(
                    "mt5_password_encrypted",
                    sa.Text,
                    nullable=True,
                ),
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    table_name = "broker_connections"

    if table_name in inspector.get_table_names():
        existing_columns = {
            col["name"] for col in inspector.get_columns(table_name)
        }

        if "mt5_password_encrypted" in existing_columns:
            op.drop_column(table_name, "mt5_password_encrypted")
