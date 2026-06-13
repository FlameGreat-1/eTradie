"""Create macro_snapshots durable last-good snapshot table.

Macro collectors deliberately never hit external APIs on the analysis
hot path (latency). On a Redis cache miss the read path falls back to
the database and then to an empty dataset. Previously every collector's
``_read_from_db()`` returned ``None``, so a cache miss silently produced
an EMPTY dataset and the macro section (COT, DXY, intermarket, central
bank, calendar, economic, sentiment) vanished from the LLM input.

macro_snapshots is the durable read-through layer: one row per collector
namespace holding the collector's exact ``model_dump(mode=\"json\")``
output. The scheduler writer upserts it on every successful collection;
the reader rehydrates it on a cache miss so the dataset is always the
last good enriched value, never empty, with no API call.

Revision ID: 0031
Revises: 0030
Create Date: 2026-06-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "macro_snapshots"


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if _TABLE in set(insp.get_table_names()):
        return

    op.create_table(
        _TABLE,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("namespace", sa.String(40), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_unique_constraint(
        "uq_macro_snapshot_namespace",
        _TABLE,
        ["namespace"],
    )
    op.create_index(
        "ix_macro_snapshot_namespace",
        _TABLE,
        ["namespace"],
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if _TABLE not in set(insp.get_table_names()):
        return
    # DROP TABLE removes the unique constraint, its backing index, and
    # the namespace index in one atomic step.
    op.drop_table(_TABLE)
