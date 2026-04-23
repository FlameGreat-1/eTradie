"""Create sentiment_readings table.

The SentimentReadingRow ORM schema and COTDerivedSentimentProvider
have existed since the macro sentiment collector was built, but
no migration ever created the underlying table.  The retention
pruner's nightly DELETE crashes with UndefinedTableError when it
tries to prune this missing table.

This migration creates the table to match the ORM definition in
engine.macro.storage.schemas.sentiment.SentimentReadingRow.

Revision ID: 0016
Revises: 0015
Create Date: 2026-04-22
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = set(inspector.get_table_names())
    if "sentiment_readings" in existing_tables:
        # Table already exists (e.g. created manually). Nothing to do.
        return

    op.create_table(
        "sentiment_readings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("currency", sa.String(5), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default=""),
        sa.Column("long_percentage", sa.Float, nullable=False, server_default="50.0"),
        sa.Column("short_percentage", sa.Float, nullable=False, server_default="50.0"),
        sa.Column("net_positioning", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("currency", "source", name="uq_sentiment_currency_source"),
    )

    op.create_index("ix_sentiment_currency", "sentiment_readings", ["currency"])
    op.create_index("ix_sentiment_collected_at", "sentiment_readings", ["collected_at"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = set(inspector.get_table_names())
    if "sentiment_readings" not in existing_tables:
        return

    op.drop_index("ix_sentiment_collected_at", table_name="sentiment_readings")
    op.drop_index("ix_sentiment_currency", table_name="sentiment_readings")
    op.drop_table("sentiment_readings")
