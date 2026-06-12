"""Add missing columns to technical_snapshots table.

The ORM schema (SnapshotSchema) defines breaker_blocks, dealing_ranges,
and meta_data columns that were never created in the original migration
(0002). Migration 0006 renamed metadata->meta_data only for RAG tables,
not for technical_snapshots.

This migration:
1. Adds breaker_blocks (JSON, NOT NULL, default '{}')
2. Adds dealing_ranges (JSON, NOT NULL, default '{}')
3. Renames metadata -> meta_data on technical_snapshots

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "technical_snapshots",
        sa.Column("breaker_blocks", postgresql.JSON, nullable=False, server_default="{}"),
    )
    op.add_column(
        "technical_snapshots",
        sa.Column("dealing_ranges", postgresql.JSON, nullable=False, server_default="{}"),
    )
    op.alter_column("technical_snapshots", "metadata", new_column_name="meta_data")


def downgrade() -> None:
    op.alter_column("technical_snapshots", "meta_data", new_column_name="metadata")
    op.drop_column("technical_snapshots", "dealing_ranges")
    op.drop_column("technical_snapshots", "breaker_blocks")
