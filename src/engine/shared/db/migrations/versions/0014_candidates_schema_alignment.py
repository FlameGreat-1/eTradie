"""Align candidates table with CandidateSchema ORM model.

The candidates table was created in migration 0002 with a column set that
no longer matches the current CandidateSchema ORM model. The ORM was
refactored to use explicit per-field columns (e.g. qml_detected, qml_price,
qml_timestamp) instead of the original shorthand columns (e.g. qml_level).

This migration:
1. Adds all columns the ORM expects that are missing from the DB.
2. Renames metadata -> meta_data (consistent with 0006/0007 pattern).
3. Drops obsolete columns that no longer exist in the ORM.

Fixes: column "fvg_upper" of relation "candidates" does not exist

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-13
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = set(inspector.get_table_names())
    if "candidates" not in existing_tables:
        return

    existing_columns = {
        col["name"] for col in inspector.get_columns("candidates")
    }

    # ── 1. Add missing columns ──────────────────────────────────────────

    # SMC: FVG columns
    _add_if_missing(existing_columns, "fvg_upper", sa.Float, nullable=True)
    _add_if_missing(existing_columns, "fvg_lower", sa.Float, nullable=True)
    _add_if_missing(
        existing_columns, "fvg_timestamp",
        sa.DateTime(timezone=True), nullable=True,
    )

    # SMC: inducement_level (was missing from 0002)
    _add_if_missing(existing_columns, "inducement_level", sa.Float, nullable=True)

    # SnD: QML – add qml_detected and qml_price (qml_timestamp already exists)
    _add_if_missing(existing_columns, "qml_detected", sa.Boolean, nullable=True)
    _add_if_missing(existing_columns, "qml_price", sa.Float, nullable=True)

    # SnD: SR flip – full set
    _add_if_missing(existing_columns, "sr_flip_detected", sa.Boolean, nullable=True)
    _add_if_missing(existing_columns, "sr_flip_price", sa.Float, nullable=True)
    _add_if_missing(
        existing_columns, "sr_flip_timestamp",
        sa.DateTime(timezone=True), nullable=True,
    )

    # SnD: RS flip – full set
    _add_if_missing(existing_columns, "rs_flip_detected", sa.Boolean, nullable=True)
    _add_if_missing(existing_columns, "rs_flip_price", sa.Float, nullable=True)
    _add_if_missing(
        existing_columns, "rs_flip_timestamp",
        sa.DateTime(timezone=True), nullable=True,
    )

    # SnD: MPL – full set
    _add_if_missing(existing_columns, "mpl_detected", sa.Boolean, nullable=True)
    _add_if_missing(existing_columns, "mpl_price", sa.Float, nullable=True)
    _add_if_missing(
        existing_columns, "mpl_timestamp",
        sa.DateTime(timezone=True), nullable=True,
    )

    # SnD: Supply zone
    _add_if_missing(existing_columns, "supply_zone_upper", sa.Float, nullable=True)
    _add_if_missing(existing_columns, "supply_zone_lower", sa.Float, nullable=True)
    _add_if_missing(
        existing_columns, "supply_zone_timestamp",
        sa.DateTime(timezone=True), nullable=True,
    )

    # SnD: Demand zone
    _add_if_missing(existing_columns, "demand_zone_upper", sa.Float, nullable=True)
    _add_if_missing(existing_columns, "demand_zone_lower", sa.Float, nullable=True)
    _add_if_missing(
        existing_columns, "demand_zone_timestamp",
        sa.DateTime(timezone=True), nullable=True,
    )

    # SnD: Fakeout – full set
    _add_if_missing(existing_columns, "fakeout_detected", sa.Boolean, nullable=True)
    _add_if_missing(existing_columns, "fakeout_level", sa.Float, nullable=True)
    _add_if_missing(
        existing_columns, "fakeout_timestamp",
        sa.DateTime(timezone=True), nullable=True,
    )

    # SnD: Marubozu
    _add_if_missing(existing_columns, "marubozu_detected", sa.Boolean, nullable=True)
    _add_if_missing(
        existing_columns, "marubozu_timestamp",
        sa.DateTime(timezone=True), nullable=True,
    )

    # SnD: Compression
    _add_if_missing(existing_columns, "compression_detected", sa.Boolean, nullable=True)
    _add_if_missing(existing_columns, "compression_candle_count", sa.Integer, nullable=True)

    # SnD: Sweep timestamp (SMC liquidity_swept exists, but sweep_timestamp may be missing)
    _add_if_missing(
        existing_columns, "sweep_timestamp",
        sa.DateTime(timezone=True), nullable=True,
    )

    # ── 2. Rename metadata -> meta_data ─────────────────────────────────
    if "metadata" in existing_columns and "meta_data" not in existing_columns:
        op.alter_column("candidates", "metadata", new_column_name="meta_data")

    # ── 3. Drop obsolete columns ────────────────────────────────────────
    # These existed in migration 0002 but are not in the current ORM.
    # Re-read columns after adds/renames above.
    existing_columns_after = {
        col["name"] for col in inspector.get_columns("candidates")
    }

    obsolete_columns = [
        "qml_level",       # replaced by qml_detected + qml_price
        "qmh_level",       # removed entirely
        "qmh_timestamp",   # removed entirely
        "sr_flip_level",   # replaced by sr_flip_detected/price/timestamp
        "rs_flip_level",   # replaced by rs_flip_detected/price/timestamp
        "fakeout_count",   # replaced by fakeout_detected/level/timestamp
        "has_compression", # replaced by compression_detected/candle_count
        "has_previous_highs",  # removed (previous_highs_count suffices)
        "has_previous_lows",   # removed (previous_lows_count suffices)
        "has_mpl",         # replaced by mpl_detected
        "mpl_level",       # replaced by mpl_price
    ]

    for col_name in obsolete_columns:
        if col_name in existing_columns_after:
            op.drop_column("candidates", col_name)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = set(inspector.get_table_names())
    if "candidates" not in existing_tables:
        return

    existing_columns = {
        col["name"] for col in inspector.get_columns("candidates")
    }

    # ── Restore obsolete columns ────────────────────────────────────────
    _add_if_missing(existing_columns, "qml_level", sa.Float, nullable=True)
    _add_if_missing(
        existing_columns, "qmh_level", sa.Float, nullable=True,
    )
    _add_if_missing(
        existing_columns, "qmh_timestamp",
        sa.DateTime(timezone=True), nullable=True,
    )
    _add_if_missing(existing_columns, "sr_flip_level", sa.Float, nullable=True)
    _add_if_missing(existing_columns, "rs_flip_level", sa.Float, nullable=True)
    _add_if_missing(existing_columns, "fakeout_count", sa.Integer, nullable=True)
    _add_if_missing(existing_columns, "has_compression", sa.Boolean, nullable=True)
    _add_if_missing(existing_columns, "has_previous_highs", sa.Boolean, nullable=True)
    _add_if_missing(existing_columns, "has_previous_lows", sa.Boolean, nullable=True)
    _add_if_missing(existing_columns, "has_mpl", sa.Boolean, nullable=True)
    _add_if_missing(existing_columns, "mpl_level", sa.Float, nullable=True)

    # ── Rename meta_data -> metadata ────────────────────────────────────
    existing_columns_after = {
        col["name"] for col in inspector.get_columns("candidates")
    }
    if "meta_data" in existing_columns_after and "metadata" not in existing_columns_after:
        op.alter_column("candidates", "meta_data", new_column_name="metadata")

    # ── Drop columns added in upgrade ───────────────────────────────────
    existing_columns_final = {
        col["name"] for col in inspector.get_columns("candidates")
    }

    new_columns = [
        "fvg_upper", "fvg_lower", "fvg_timestamp",
        "inducement_level",
        "qml_detected", "qml_price",
        "sr_flip_detected", "sr_flip_price", "sr_flip_timestamp",
        "rs_flip_detected", "rs_flip_price", "rs_flip_timestamp",
        "mpl_detected", "mpl_price", "mpl_timestamp",
        "supply_zone_upper", "supply_zone_lower", "supply_zone_timestamp",
        "demand_zone_upper", "demand_zone_lower", "demand_zone_timestamp",
        "fakeout_detected", "fakeout_level", "fakeout_timestamp",
        "marubozu_detected", "marubozu_timestamp",
        "compression_detected", "compression_candle_count",
    ]

    for col_name in new_columns:
        if col_name in existing_columns_final:
            op.drop_column("candidates", col_name)


def _add_if_missing(
    existing: set[str],
    column_name: str,
    column_type,
    *,
    nullable: bool = True,
) -> None:
    """Add a column to the candidates table only if it doesn't already exist."""
    if column_name not in existing:
        op.add_column(
            "candidates",
            sa.Column(column_name, column_type, nullable=nullable),
        )
