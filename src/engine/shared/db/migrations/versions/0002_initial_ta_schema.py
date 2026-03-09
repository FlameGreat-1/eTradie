"""Initial TA schema.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-08
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # candles
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "candles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Float, nullable=False),
        sa.Column("high", sa.Float, nullable=False),
        sa.Column("low", sa.Float, nullable=False),
        sa.Column("close", sa.Float, nullable=False),
        sa.Column("volume", sa.Float, nullable=False),
        sa.Column("quote_volume", sa.Float, nullable=True),
        sa.Column("number_of_trades", sa.Integer, nullable=True),
        sa.Column("taker_buy_base_volume", sa.Float, nullable=True),
        sa.Column("taker_buy_quote_volume", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_candles_symbol", "candles", ["symbol"])
    op.create_index("ix_candles_timeframe", "candles", ["timeframe"])
    op.create_index("ix_candles_timestamp", "candles", ["timestamp"])
    op.create_index(
        "ix_candles_symbol_timeframe_timestamp",
        "candles",
        ["symbol", "timeframe", "timestamp"],
        unique=True,
    )
    op.create_index(
        "ix_candles_symbol_timeframe_open_time",
        "candles",
        ["symbol", "timeframe", "open_time"],
    )

    # ──────────────────────────────────────────────────────────────────────
    # technical_snapshots
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "technical_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("swing_highs", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("swing_lows", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("bms_events", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("choch_events", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("sms_events", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("order_blocks", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("fair_value_gaps", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("liquidity_sweeps", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("inducement_events", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("qm_levels", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("sr_flips", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("rs_flips", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("previous_levels", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("mpl_levels", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("fakeout_tests", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("supply_zones", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("demand_zones", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("fibonacci_retracements", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSON, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_snapshots_symbol", "technical_snapshots", ["symbol"])
    op.create_index("ix_snapshots_timeframe", "technical_snapshots", ["timeframe"])
    op.create_index("ix_snapshots_timestamp", "technical_snapshots", ["timestamp"])
    op.create_index(
        "ix_snapshots_symbol_timeframe_timestamp",
        "technical_snapshots",
        ["symbol", "timeframe", "timestamp"],
    )
    op.create_index(
        "ix_snapshots_symbol_timeframe_created_at",
        "technical_snapshots",
        ["symbol", "timeframe", "created_at"],
    )

    # ──────────────────────────────────────────────────────────────────────
    # candidates
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("pattern", sa.String(50), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_price", sa.Float, nullable=False),
        sa.Column("stop_loss", sa.Float, nullable=False),
        sa.Column("take_profit", sa.Float, nullable=False),
        sa.Column("htf_timeframe", sa.String(10), nullable=True),
        sa.Column("ltf_timeframe", sa.String(10), nullable=True),
        sa.Column("is_smc", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_snd", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sms_detected", sa.Boolean, nullable=True),
        sa.Column("sms_price", sa.Float, nullable=True),
        sa.Column("sms_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bms_detected", sa.Boolean, nullable=True),
        sa.Column("bms_price", sa.Float, nullable=True),
        sa.Column("bms_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("choch_detected", sa.Boolean, nullable=True),
        sa.Column("choch_price", sa.Float, nullable=True),
        sa.Column("choch_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("order_block_upper", sa.Float, nullable=True),
        sa.Column("order_block_lower", sa.Float, nullable=True),
        sa.Column("order_block_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("liquidity_swept", sa.Boolean, nullable=True),
        sa.Column("swept_level", sa.Float, nullable=True),
        sa.Column("sweep_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inducement_cleared", sa.Boolean, nullable=True),
        sa.Column("ltf_confirmation", sa.Boolean, nullable=True),
        sa.Column("ltf_confirmation_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("displacement_pips", sa.Float, nullable=True),
        sa.Column("fib_level", sa.String(20), nullable=True),
        sa.Column("session_context", sa.String(50), nullable=True),
        sa.Column("qml_level", sa.Float, nullable=True),
        sa.Column("qml_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("qmh_level", sa.Float, nullable=True),
        sa.Column("qmh_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sr_flip_level", sa.Float, nullable=True),
        sa.Column("rs_flip_level", sa.Float, nullable=True),
        sa.Column("fakeout_count", sa.Integer, nullable=True),
        sa.Column("has_compression", sa.Boolean, nullable=True),
        sa.Column("has_previous_highs", sa.Boolean, nullable=True),
        sa.Column("previous_highs_count", sa.Integer, nullable=True),
        sa.Column("has_previous_lows", sa.Boolean, nullable=True),
        sa.Column("previous_lows_count", sa.Integer, nullable=True),
        sa.Column("has_mpl", sa.Boolean, nullable=True),
        sa.Column("mpl_level", sa.Float, nullable=True),
        sa.Column("metadata", postgresql.JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidation_reason", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_candidates_symbol", "candidates", ["symbol"])
    op.create_index("ix_candidates_timeframe", "candidates", ["timeframe"])
    op.create_index("ix_candidates_pattern", "candidates", ["pattern"])
    op.create_index("ix_candidates_direction", "candidates", ["direction"])
    op.create_index("ix_candidates_timestamp", "candidates", ["timestamp"])
    op.create_index("ix_candidates_is_active", "candidates", ["is_active"])
    op.create_index(
        "ix_candidates_symbol_timeframe_timestamp",
        "candidates",
        ["symbol", "timeframe", "timestamp"],
    )
    op.create_index(
        "ix_candidates_symbol_pattern_direction",
        "candidates",
        ["symbol", "pattern", "direction"],
    )
    op.create_index(
        "ix_candidates_is_active_timestamp",
        "candidates",
        ["is_active", "timestamp"],
    )


def downgrade() -> None:
    op.drop_table("candidates")
    op.drop_table("technical_snapshots")
    op.drop_table("candles")
