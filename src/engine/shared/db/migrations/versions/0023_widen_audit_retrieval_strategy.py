"""widen_audit_retrieval_strategy

Revision ID: 0023
Revises: 0022
Create Date: 2026-05-24 00:30:00.000000

Widens analysis_audit_logs.retrieval_strategy from VARCHAR(32) to
VARCHAR(128). The column is sourced from the LLM's self-reported
retrieval.strategy_used field, which is free text -- not the short
enum the original migration (0004) assumed. Production traffic has
emitted values up to ~40 chars ("Vector search with metadata
filtering") that trip StringDataRightTruncationError on insert.

No data migration is required: VARCHAR widening is a metadata-only
operation in PostgreSQL when the new length is >= the old length, so
the ALTER COLUMN runs in O(1) and never rewrites the table.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "analysis_audit_logs",
        "retrieval_strategy",
        existing_type=sa.String(length=32),
        type_=sa.String(length=128),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Narrowing requires that no existing row exceeds the new width.
    # Truncate any over-length values before applying the type change
    # so the downgrade does not fail on legitimately-persisted data.
    op.execute("""
        UPDATE analysis_audit_logs
           SET retrieval_strategy = LEFT(retrieval_strategy, 32)
         WHERE retrieval_strategy IS NOT NULL
           AND char_length(retrieval_strategy) > 32;
        """)
    op.alter_column(
        "analysis_audit_logs",
        "retrieval_strategy",
        existing_type=sa.String(length=128),
        type_=sa.String(length=32),
        existing_nullable=True,
    )
