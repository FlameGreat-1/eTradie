"""Add user_id to RAG tables.

Migration 0011 added user_id for multi-tenant isolation to
broker_connections, llm_connections, analysis_outputs, and
analysis_audit_logs — but missed rag_retrieval_logs and
rag_analysis_citations.

The SQLAlchemy models already declare user_id, so every INSERT
fails with: UndefinedColumnError: column "user_id" of relation...

This migration adds the missing columns using the same idempotent
pattern as 0011.

Revision ID: 0026
Revises: 0025
Create Date: 2026-05-26
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = [
    ("rag_retrieval_logs", "ix_rag_retlog_user_id"),
    ("rag_analysis_citations", "ix_rag_acit_user_id"),
]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    for table_name, index_name in _TABLES:
        if table_name not in existing_tables:
            continue

        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}

        if "user_id" in existing_columns:
            # Already present (idempotent re-run).
            continue

        # Step 1: Add as NULLABLE so existing rows don't block.
        op.add_column(
            table_name,
            sa.Column("user_id", sa.String(64), nullable=True),
        )

        # Step 2: Backfill existing rows with empty string (matches model default).
        op.execute(sa.text(f"UPDATE {table_name} SET user_id = '' WHERE user_id IS NULL"))  # nosec B608

        # Step 3: Flip to NOT NULL.
        op.alter_column(table_name, "user_id", nullable=False)

        # Step 4: Create index.
        existing_indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
        if index_name not in existing_indexes:
            op.create_index(index_name, table_name, ["user_id"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    for table_name, index_name in _TABLES:
        if table_name not in existing_tables:
            continue

        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}

        if "user_id" not in existing_columns:
            continue

        existing_indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name=table_name)

        op.drop_column(table_name, "user_id")
