"""Add user_id to broker_connections, llm_connections, analysis_outputs, analysis_audit_logs.

Enables multi-tenant data isolation. Every row is now owned by a specific
user. All repository queries MUST filter by user_id.

Existing rows (created before auth was implemented) are backfilled with
the placeholder value 'system'. After the admin user is seeded by the
Go auth service on first startup, an operator should run:

    UPDATE broker_connections SET user_id = '<admin_user_id>' WHERE user_id = 'system';
    UPDATE llm_connections SET user_id = '<admin_user_id>' WHERE user_id = 'system';
    UPDATE analysis_outputs SET user_id = '<admin_user_id>' WHERE user_id = 'system';
    UPDATE analysis_audit_logs SET user_id = '<admin_user_id>' WHERE user_id = 'system';

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-05
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that need the user_id column.
_TABLES = [
    "broker_connections",
    "llm_connections",
    "analysis_outputs",
    "analysis_audit_logs",
]

# Index name prefix per table for consistent naming.
_INDEX_NAMES = {
    "broker_connections": "ix_bc_user_id",
    "llm_connections": "ix_llm_connections_user_id",
    "analysis_outputs": "ix_ao_user_id",
    "analysis_audit_logs": "ix_aal_user_id",
}


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    for table_name in _TABLES:
        if table_name not in existing_tables:
            # Table doesn't exist yet (shouldn't happen if prior migrations ran).
            continue

        existing_columns = {
            col["name"] for col in inspector.get_columns(table_name)
        }

        if "user_id" in existing_columns:
            # Column already exists (idempotent re-run).
            continue

        # Step 1: Add user_id as NULLABLE first (can't add NOT NULL to
        # a table with existing rows without a default).
        op.add_column(
            table_name,
            sa.Column(
                "user_id",
                sa.String(64),
                nullable=True,
            ),
        )

        # Step 2: Backfill existing rows with 'system' placeholder.
        # This preserves all pre-auth data. The operator should reassign
        # these to the actual admin user ID after first startup.
        op.execute(
            sa.text(
                f"UPDATE {table_name} SET user_id = 'system' WHERE user_id IS NULL"
            )
        )

        # Step 3: Alter column to NOT NULL now that all rows have a value.
        op.alter_column(
            table_name,
            "user_id",
            nullable=False,
        )

        # Step 4: Create index for fast per-user queries.
        index_name = _INDEX_NAMES[table_name]
        existing_indexes = {
            idx["name"] for idx in inspector.get_indexes(table_name)
        }
        if index_name not in existing_indexes:
            op.create_index(index_name, table_name, ["user_id"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    for table_name in _TABLES:
        if table_name not in existing_tables:
            continue

        existing_columns = {
            col["name"] for col in inspector.get_columns(table_name)
        }

        if "user_id" not in existing_columns:
            continue

        # Drop index first.
        index_name = _INDEX_NAMES[table_name]
        existing_indexes = {
            idx["name"] for idx in inspector.get_indexes(table_name)
        }
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name=table_name)

        # Drop column.
        op.drop_column(table_name, "user_id")
