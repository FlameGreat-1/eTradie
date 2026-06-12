"""Add rate_change_bps to central_bank_events.

RateDecision (the macro central-bank rate model) carries rate_change_bps,
and it reaches the LLM via the cached dataset, but the central_bank_events
table had no column for it, so the collector dropped it on the DB
persistence path. This adds the nullable column so the persisted row
matches the model and the historical table can answer the bps change of
each decision. Existing rows backfill as NULL (unknown change), which is
correct -- they predate rate-decision data.

Revision ID: 0032
Revises: 0031
Create Date: 2026-06-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "central_bank_events"
_COLUMN = "rate_change_bps"


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if _TABLE not in set(insp.get_table_names()):
        return
    existing = {c["name"] for c in insp.get_columns(_TABLE)}
    if _COLUMN in existing:
        return
    op.add_column(
        _TABLE,
        sa.Column(_COLUMN, sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if _TABLE not in set(insp.get_table_names()):
        return
    existing = {c["name"] for c in insp.get_columns(_TABLE)}
    if _COLUMN not in existing:
        return
    op.drop_column(_TABLE, _COLUMN)
