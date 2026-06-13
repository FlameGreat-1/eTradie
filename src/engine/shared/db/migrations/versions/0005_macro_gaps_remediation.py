"""Macro gaps remediation - COT enrichment, inflation type, QE/QT, DXY momentum, commodities.

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -- COT enrichment (Gap 1) --
    op.add_column(
        "cot_reports",
        sa.Column("leveraged_long", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "cot_reports",
        sa.Column("leveraged_short", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "cot_reports",
        sa.Column("leveraged_net", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "cot_reports",
        sa.Column("asset_manager_long", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "cot_reports",
        sa.Column("asset_manager_short", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "cot_reports",
        sa.Column("asset_manager_net", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "cot_reports",
        sa.Column("percentile_rank", sa.Float, nullable=False, server_default="50.0"),
    )
    op.add_column(
        "cot_reports",
        sa.Column("signal_strength", sa.String(20), nullable=False, server_default="NEUTRAL"),
    )
    op.add_column(
        "cot_reports",
        sa.Column("divergence_flag", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_cot_extreme_flag", "cot_reports", ["extreme_flag", "report_date"])

    # -- Inflation type (Gap 5) --
    op.add_column("economic_releases", sa.Column("inflation_type", sa.String(10), nullable=True))
    op.create_index(
        "ix_econ_inflation_type",
        "economic_releases",
        ["inflation_type", "release_time"],
    )

    # -- QE/QT metrics (Gap 7) --
    op.add_column(
        "central_bank_events",
        sa.Column("policy_action", sa.String(10), nullable=False, server_default="NONE"),
    )
    op.add_column(
        "central_bank_events",
        sa.Column("balance_sheet_direction", sa.String(20), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_cb_events_policy_action",
        "central_bank_events",
        ["policy_action", "event_timestamp"],
    )

    # -- Intermarket commodities (Gap 4) --
    op.add_column("intermarket_snapshots", sa.Column("iron_ore", sa.Float, nullable=True))
    op.add_column("intermarket_snapshots", sa.Column("dairy_gdt", sa.Float, nullable=True))
    op.add_column("intermarket_snapshots", sa.Column("copper", sa.Float, nullable=True))
    op.add_column("intermarket_snapshots", sa.Column("natural_gas", sa.Float, nullable=True))

    # -- DXY momentum and divergence (Gap 3) --
    op.add_column(
        "dxy_snapshots",
        sa.Column("momentum", sa.String(15), nullable=False, server_default="FLAT"),
    )
    op.add_column(
        "dxy_snapshots",
        sa.Column(
            "divergence_signals_json",
            postgresql.JSON,
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    # -- DXY --
    op.drop_column("dxy_snapshots", "divergence_signals_json")
    op.drop_column("dxy_snapshots", "momentum")

    # -- Intermarket --
    op.drop_column("intermarket_snapshots", "natural_gas")
    op.drop_column("intermarket_snapshots", "copper")
    op.drop_column("intermarket_snapshots", "dairy_gdt")
    op.drop_column("intermarket_snapshots", "iron_ore")

    # -- Central bank --
    op.drop_index("ix_cb_events_policy_action", table_name="central_bank_events")
    op.drop_column("central_bank_events", "balance_sheet_direction")
    op.drop_column("central_bank_events", "policy_action")

    # -- Economic --
    op.drop_index("ix_econ_inflation_type", table_name="economic_releases")
    op.drop_column("economic_releases", "inflation_type")

    # -- COT --
    op.drop_index("ix_cot_extreme_flag", table_name="cot_reports")
    op.drop_column("cot_reports", "divergence_flag")
    op.drop_column("cot_reports", "signal_strength")
    op.drop_column("cot_reports", "percentile_rank")
    op.drop_column("cot_reports", "asset_manager_net")
    op.drop_column("cot_reports", "asset_manager_short")
    op.drop_column("cot_reports", "asset_manager_long")
    op.drop_column("cot_reports", "leveraged_net")
    op.drop_column("cot_reports", "leveraged_short")
    op.drop_column("cot_reports", "leveraged_long")
