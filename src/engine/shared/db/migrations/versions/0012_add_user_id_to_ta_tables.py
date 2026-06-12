"""Add user_id to candles, technical_snapshots, candidates.

Completes multi-tenant data isolation for the TA engine. Migration 0011
added user_id to broker_connections, llm_connections, analysis_outputs,
and analysis_audit_logs. This migration covers the three TA storage
tables that were missed.

Every row is now owned by a specific user. All repository queries
MUST filter by user_id.

Existing rows are backfilled with 'system' placeholder. After the
admin user is seeded, run:

    UPDATE candles SET user_id = '<admin_user_id>' WHERE user_id = 'system';
    UPDATE technical_snapshots SET user_id = '<admin_user_id>' WHERE user_id = 'system';
    UPDATE candidates SET user_id = '<admin_user_id>' WHERE user_id = 'system';

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = [
    "candles",
    "technical_snapshots",
    "candidates",
]

_INDEX_NAMES = {
    "candles": "ix_candles_user_id",
    "technical_snapshots": "ix_snapshots_user_id",
    "candidates": "ix_candidates_user_id",
}


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    for table_name in _TABLES:
        if table_name not in existing_tables:
            continue

        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}

        if "user_id" in existing_columns:
            # Column already exists (idempotent re-run).
            continue

        # Step 1: Add user_id as NULLABLE first.
        op.add_column(
            table_name,
            sa.Column(
                "user_id",
                sa.String(64),
                nullable=True,
            ),
        )

        # Step 2: Backfill existing rows with 'system' placeholder.
        op.execute(sa.text(f"UPDATE {table_name} SET user_id = 'system' WHERE user_id IS NULL"))

        # Step 3: Alter column to NOT NULL.
        op.alter_column(
            table_name,
            "user_id",
            nullable=False,
        )

        # Step 4: Create index for fast per-user queries.
        index_name = _INDEX_NAMES[table_name]
        existing_indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
        if index_name not in existing_indexes:
            op.create_index(index_name, table_name, ["user_id"])

    # Step 5: Update the candles unique constraint to include user_id.
    # The old constraint (symbol, timeframe, timestamp) would cause
    # conflicts when different users store candles for the same symbol.
    # The new constraint is (user_id, symbol, timeframe, timestamp).
    if "candles" in existing_tables:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("candles")}

        # Drop old unique constraint.
        if "ix_candles_symbol_timeframe_timestamp" in existing_indexes:
            op.drop_index(
                "ix_candles_symbol_timeframe_timestamp",
                table_name="candles",
            )

        # Create new unique constraint with user_id.
        new_idx = "ix_candles_user_symbol_timeframe_timestamp"
        if new_idx not in existing_indexes:
            op.create_index(
                new_idx,
                "candles",
                ["user_id", "symbol", "timeframe", "timestamp"],
                unique=True,
            )

    # Step 6: Add user_id to snapshot composite indexes.
    if "technical_snapshots" in existing_tables:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("technical_snapshots")}

        # Drop old indexes and recreate with user_id.
        old_new_pairs = [
            (
                "ix_snapshots_symbol_timeframe_timestamp",
                "ix_snapshots_user_symbol_timeframe_timestamp",
                ["user_id", "symbol", "timeframe", "timestamp"],
            ),
            (
                "ix_snapshots_symbol_timeframe_created_at",
                "ix_snapshots_user_symbol_timeframe_created_at",
                ["user_id", "symbol", "timeframe", "created_at"],
            ),
        ]
        for old_name, new_name, columns in old_new_pairs:
            if old_name in existing_indexes:
                op.drop_index(old_name, table_name="technical_snapshots")
            if new_name not in existing_indexes:
                op.create_index(new_name, "technical_snapshots", columns)

    # Step 7: Add user_id to candidate composite indexes.
    if "candidates" in existing_tables:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("candidates")}

        old_new_pairs = [
            (
                "ix_candidates_symbol_timeframe_timestamp",
                "ix_candidates_user_symbol_timeframe_timestamp",
                ["user_id", "symbol", "timeframe", "timestamp"],
            ),
            (
                "ix_candidates_symbol_pattern_direction",
                "ix_candidates_user_symbol_pattern_direction",
                ["user_id", "symbol", "pattern", "direction"],
            ),
            (
                "ix_candidates_is_active_timestamp",
                "ix_candidates_user_is_active_timestamp",
                ["user_id", "is_active", "timestamp"],
            ),
        ]
        for old_name, new_name, columns in old_new_pairs:
            if old_name in existing_indexes:
                op.drop_index(old_name, table_name="candidates")
            if new_name not in existing_indexes:
                op.create_index(new_name, "candidates", columns)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # Restore candidate indexes.
    if "candidates" in existing_tables:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("candidates")}
        restore_pairs = [
            (
                "ix_candidates_user_symbol_timeframe_timestamp",
                "ix_candidates_symbol_timeframe_timestamp",
                ["symbol", "timeframe", "timestamp"],
            ),
            (
                "ix_candidates_user_symbol_pattern_direction",
                "ix_candidates_symbol_pattern_direction",
                ["symbol", "pattern", "direction"],
            ),
            (
                "ix_candidates_user_is_active_timestamp",
                "ix_candidates_is_active_timestamp",
                ["is_active", "timestamp"],
            ),
        ]
        for new_name, old_name, columns in restore_pairs:
            if new_name in existing_indexes:
                op.drop_index(new_name, table_name="candidates")
            op.create_index(old_name, "candidates", columns)

    # Restore snapshot indexes.
    if "technical_snapshots" in existing_tables:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("technical_snapshots")}
        restore_pairs = [
            (
                "ix_snapshots_user_symbol_timeframe_timestamp",
                "ix_snapshots_symbol_timeframe_timestamp",
                ["symbol", "timeframe", "timestamp"],
            ),
            (
                "ix_snapshots_user_symbol_timeframe_created_at",
                "ix_snapshots_symbol_timeframe_created_at",
                ["symbol", "timeframe", "created_at"],
            ),
        ]
        for new_name, old_name, columns in restore_pairs:
            if new_name in existing_indexes:
                op.drop_index(new_name, table_name="technical_snapshots")
            op.create_index(old_name, "technical_snapshots", columns)

    # Restore candles unique constraint.
    if "candles" in existing_tables:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("candles")}
        if "ix_candles_user_symbol_timeframe_timestamp" in existing_indexes:
            op.drop_index(
                "ix_candles_user_symbol_timeframe_timestamp",
                table_name="candles",
            )
        op.create_index(
            "ix_candles_symbol_timeframe_timestamp",
            "candles",
            ["symbol", "timeframe", "timestamp"],
            unique=True,
        )

    # Drop user_id columns and indexes.
    for table_name in _TABLES:
        if table_name not in existing_tables:
            continue

        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
        if "user_id" not in existing_columns:
            continue

        index_name = _INDEX_NAMES[table_name]
        existing_indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name=table_name)

        op.drop_column(table_name, "user_id")
