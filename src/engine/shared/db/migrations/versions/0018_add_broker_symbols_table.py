"""Add broker_symbols table.

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "broker_symbols",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("path", sa.String(length=255), nullable=True),
        sa.Column("digits", sa.Integer(), nullable=True),
        sa.Column("point", sa.Float(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_broker_symbols_account_id", "broker_symbols", ["account_id"], unique=False)
    op.create_index("ix_broker_symbols_name", "broker_symbols", ["name"], unique=False)
    op.create_index("ix_broker_symbols_path", "broker_symbols", ["path"], unique=False)
    op.create_index("ix_broker_symbols_provider", "broker_symbols", ["provider"], unique=False)
    op.create_index(
        "ix_broker_symbols_provider_account_name",
        "broker_symbols",
        ["provider", "account_id", "name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("broker_symbols")
