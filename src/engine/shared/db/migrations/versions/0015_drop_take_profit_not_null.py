from __future__ import annotations

from typing import Any

"""Drop NOT NULL constraint on candidates.take_profit.

The CandidateSchema ORM declares take_profit as nullable and
SMCCandidate.take_profit is typed Optional[float] at the pydantic
layer, but the production Postgres column was created with NOT NULL
in migration 0002 and no later migration dropped that constraint.

When a builder correctly emits a null take_profit (e.g. no swing
clears the R:R floor), the INSERT hits NotNullViolationError and
SQLAlchemy aborts the session, which rolls back the entire
candidate batch via PendingRollbackError.  See NOTE.md for the
full stack trace.

This migration aligns the DB with the ORM by dropping the NOT NULL
constraint.  It is idempotent: the upgrade checks the current
nullability before issuing ALTER COLUMN so re-running on an already
migrated DB is a no-op.  The downgrade restores NOT NULL but will
fail (correctly) if any null rows exist; operators who need to
downgrade must first either backfill or delete null-TP candidates.

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-17
"""


from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = set(inspector.get_table_names())
    if "candidates" not in existing_tables:
        return

    take_profit_col = _get_column(inspector, "candidates", "take_profit")
    if take_profit_col is None:
        # Column doesn't exist -- nothing to do.  Should not happen on
        # a healthy schema but we don't want the migration to crash.
        return

    # Only issue the ALTER when the column is currently NOT NULL.
    # This makes the migration safe to re-run.
    if take_profit_col.get("nullable") is False:
        op.alter_column(
            "candidates",
            "take_profit",
            existing_type=sa.Float(),
            nullable=True,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = set(inspector.get_table_names())
    if "candidates" not in existing_tables:
        return

    take_profit_col = _get_column(inspector, "candidates", "take_profit")
    if take_profit_col is None:
        return

    # Only re-apply NOT NULL when the column is currently nullable.
    # Postgres will raise a CheckViolation here if any rows have
    # take_profit IS NULL; that is the correct failure mode and
    # signals the downgrader to clean up first.
    if take_profit_col.get("nullable") is True:
        op.alter_column(
            "candidates",
            "take_profit",
            existing_type=sa.Float(),
            nullable=False,
        )


def _get_column(inspector, table_name: str, column_name: str) -> dict[str, Any] | None:
    """Return the column info dict for a named column, or None if absent."""
    for col in inspector.get_columns(table_name):
        if col["name"] == column_name:
            return col
    return None
