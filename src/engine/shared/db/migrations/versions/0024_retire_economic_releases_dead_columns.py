"""Retire economic_releases dead columns.

Revision ID: 0024
Revises: 0023
Create Date: 2026-05-25

Removes currency, indicator, source, forecast, surprise,
surprise_direction, impact and inflation_type from
economic_releases. A repo-wide audit (2026-05) found no live
reader for any of them after the LLM-only EconomicRelease trim:

  - currency and indicator were read only by the Go gateway's
    extractEconomic pipeline, which has been removed.
  - source had no reader anywhere.
  - forecast, surprise, surprise_direction, impact and inflation_type
    were never populated by any provider; defined on the row but
    absent from the Pydantic model.

The unique constraint that enforced (user_id, currency, indicator,
release_time) is replaced with (user_id, indicator_name,
release_time) so dedup remains enforced on the surviving identity
tuple.

Indexes dropped:
  - ix_econ_user_currency_indicator (0013)
  - ix_econ_user_currency_release (0013)
  - ix_econ_user_inflation_type (0013)

Indexes created:
  - ix_econ_user_release_time (user_id, release_time)

The user_id column and its ix_econ_user_id index from migration
0013 are untouched.

Downgrade restores the previous shape with empty values where the
providers never populated data. Surprise enums fall back to
'INLINE' / 'MEDIUM' to satisfy the original NOT NULL defaults.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "economic_releases"

_INDEXES_TO_DROP = [
    "ix_econ_user_currency_indicator",
    "ix_econ_user_currency_release",
    "ix_econ_user_inflation_type",
]

_CONSTRAINT_TO_DROP = "uq_econ_user_currency_indicator_time"
_NEW_CONSTRAINT = "uq_econ_user_indicator_name_time"
_NEW_INDEX = "ix_econ_user_release_time"

_COLUMNS_TO_DROP = [
    "currency",
    "indicator",
    "source",
    "forecast",
    "surprise",
    "surprise_direction",
    "impact",
    "inflation_type",
]


def _existing_indexes(insp, table_name: str) -> set[str]:
    return {idx["name"] for idx in insp.get_indexes(table_name) if idx.get("name")}


def _existing_constraints(insp, table_name: str) -> set[str]:
    return {uc["name"] for uc in insp.get_unique_constraints(table_name) if uc.get("name")}


def _existing_columns(insp, table_name: str) -> set[str]:
    return {col["name"] for col in insp.get_columns(table_name)}


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if _TABLE not in set(insp.get_table_names()):
        return

    # Self-sufficient precondition: 0013 owns user_id, but if for any
    # reason it is missing on entry (stale inspector inside the same
    # transaction, partial prior run, manual schema edit), add it
    # here using the same shape 0013 uses. The migration must not
    # assume upstream state -- it must guarantee its own.
    existing_columns = _existing_columns(insp, _TABLE)
    if "user_id" not in existing_columns:
        op.add_column(
            _TABLE,
            sa.Column(
                "user_id",
                sa.String(64),
                nullable=False,
                server_default="system",
            ),
        )
        insp = inspect(conn)
        existing_indexes = _existing_indexes(insp, _TABLE)
        if "ix_econ_user_id" not in existing_indexes:
            op.create_index("ix_econ_user_id", _TABLE, ["user_id"])
        insp = inspect(conn)

    existing_indexes = _existing_indexes(insp, _TABLE)
    for idx_name in _INDEXES_TO_DROP:
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name=_TABLE)

    existing_constraints = _existing_constraints(insp, _TABLE)
    if _CONSTRAINT_TO_DROP in existing_constraints:
        op.drop_constraint(_CONSTRAINT_TO_DROP, _TABLE, type_="unique")

    insp = inspect(conn)
    existing_constraints = _existing_constraints(insp, _TABLE)
    if _NEW_CONSTRAINT not in existing_constraints:
        op.create_unique_constraint(
            _NEW_CONSTRAINT,
            _TABLE,
            ["user_id", "indicator_name", "release_time"],
        )

    insp = inspect(conn)
    existing_indexes = _existing_indexes(insp, _TABLE)
    if _NEW_INDEX not in existing_indexes:
        op.create_index(_NEW_INDEX, _TABLE, ["user_id", "release_time"])

    insp = inspect(conn)
    existing_columns = _existing_columns(insp, _TABLE)
    for col_name in _COLUMNS_TO_DROP:
        if col_name in existing_columns:
            op.drop_column(_TABLE, col_name)


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if _TABLE not in set(insp.get_table_names()):
        return

    existing_columns = _existing_columns(insp, _TABLE)

    if "currency" not in existing_columns:
        op.add_column(
            _TABLE,
            sa.Column("currency", sa.String(5), nullable=False, server_default=""),
        )
    if "indicator" not in existing_columns:
        op.add_column(
            _TABLE,
            sa.Column("indicator", sa.String(30), nullable=False, server_default=""),
        )
    if "source" not in existing_columns:
        op.add_column(
            _TABLE,
            sa.Column("source", sa.String(50), nullable=False, server_default=""),
        )
    if "forecast" not in existing_columns:
        op.add_column(_TABLE, sa.Column("forecast", sa.Float, nullable=True))
    if "surprise" not in existing_columns:
        op.add_column(_TABLE, sa.Column("surprise", sa.Float, nullable=True))
    if "surprise_direction" not in existing_columns:
        op.add_column(
            _TABLE,
            sa.Column(
                "surprise_direction",
                sa.String(10),
                nullable=False,
                server_default="INLINE",
            ),
        )
    if "impact" not in existing_columns:
        op.add_column(
            _TABLE,
            sa.Column("impact", sa.String(10), nullable=False, server_default="MEDIUM"),
        )
    if "inflation_type" not in existing_columns:
        op.add_column(_TABLE, sa.Column("inflation_type", sa.String(10), nullable=True))

    insp = inspect(conn)
    existing_indexes = _existing_indexes(insp, _TABLE)
    if _NEW_INDEX in existing_indexes:
        op.drop_index(_NEW_INDEX, table_name=_TABLE)

    existing_constraints = _existing_constraints(insp, _TABLE)
    if _NEW_CONSTRAINT in existing_constraints:
        op.drop_constraint(_NEW_CONSTRAINT, _TABLE, type_="unique")

    insp = inspect(conn)
    existing_constraints = _existing_constraints(insp, _TABLE)
    if _CONSTRAINT_TO_DROP not in existing_constraints:
        op.create_unique_constraint(
            _CONSTRAINT_TO_DROP,
            _TABLE,
            ["user_id", "currency", "indicator", "release_time"],
        )

    insp = inspect(conn)
    existing_indexes = _existing_indexes(insp, _TABLE)
    if "ix_econ_user_currency_indicator" not in existing_indexes:
        op.create_index(
            "ix_econ_user_currency_indicator",
            _TABLE,
            ["user_id", "currency", "indicator"],
        )
    if "ix_econ_user_currency_release" not in existing_indexes:
        op.create_index(
            "ix_econ_user_currency_release",
            _TABLE,
            ["user_id", "currency", "release_time"],
        )
    if "ix_econ_user_inflation_type" not in existing_indexes:
        op.create_index(
            "ix_econ_user_inflation_type",
            _TABLE,
            ["inflation_type", "release_time"],
        )
