"""Initial macro schema.

Revision ID: 0001
Revises: None
Create Date: 2026-03-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "central_bank_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("bank", sa.String(10), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("speaker", sa.String(200), nullable=False, server_default=""),
        sa.Column("tone", sa.String(10), nullable=False, server_default="NEUTRAL"),
        sa.Column("tone_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("rate_current", sa.Float, nullable=True),
        sa.Column("rate_previous", sa.Float, nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=False, server_default=""),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cb_events_bank_timestamp", "central_bank_events", ["bank", "event_timestamp"])
    op.create_index("ix_cb_events_event_type", "central_bank_events", ["event_type"])
    op.create_index("ix_cb_events_created_at", "central_bank_events", ["created_at"])

    op.create_table(
        "cot_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("currency", sa.String(5), nullable=False),
        sa.Column("contract_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("non_commercial_long", sa.Integer, nullable=False),
        sa.Column("non_commercial_short", sa.Integer, nullable=False),
        sa.Column("non_commercial_net", sa.Integer, nullable=False),
        sa.Column("commercial_long", sa.Integer, nullable=False),
        sa.Column("commercial_short", sa.Integer, nullable=False),
        sa.Column("commercial_net", sa.Integer, nullable=False),
        sa.Column("open_interest", sa.Integer, nullable=False),
        sa.Column("wow_change", sa.Integer, nullable=False, server_default="0"),
        sa.Column("extreme_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("report_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("currency", "report_date", name="uq_cot_currency_date"),
    )
    op.create_index("ix_cot_currency_date", "cot_reports", ["currency", "report_date"])
    op.create_index("ix_cot_report_date", "cot_reports", ["report_date"])

    op.create_table(
        "economic_releases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("currency", sa.String(5), nullable=False),
        sa.Column("indicator", sa.String(30), nullable=False),
        sa.Column("indicator_name", sa.String(200), nullable=False),
        sa.Column("actual", sa.Float, nullable=True),
        sa.Column("forecast", sa.Float, nullable=True),
        sa.Column("previous", sa.Float, nullable=True),
        sa.Column("surprise", sa.Float, nullable=True),
        sa.Column("surprise_direction", sa.String(10), nullable=False, server_default="INLINE"),
        sa.Column("impact", sa.String(10), nullable=False, server_default="MEDIUM"),
        sa.Column("source", sa.String(50), nullable=False, server_default=""),
        sa.Column("release_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_econ_currency_indicator", "economic_releases", ["currency", "indicator"])
    op.create_index("ix_econ_release_time", "economic_releases", ["release_time"])
    op.create_index("ix_econ_currency_release", "economic_releases", ["currency", "release_time"])

    op.create_table(
        "news_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("headline", sa.String(1000), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False, server_default=""),
        sa.Column("summary", sa.Text, nullable=False, server_default=""),
        sa.Column("currencies", postgresql.ARRAY(sa.String(5)), nullable=False, server_default="{}"),
        sa.Column("sentiment", sa.String(15), nullable=False, server_default="NEUTRAL"),
        sa.Column("impact", sa.String(10), nullable=False, server_default="MEDIUM"),
        sa.Column("dedupe_hash", sa.String(64), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("dedupe_hash", name="uq_news_dedupe_hash"),
    )
    op.create_index("ix_news_published_at", "news_items", ["published_at"])
    op.create_index("ix_news_impact", "news_items", ["impact"])

    op.create_table(
        "calendar_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("event_name", sa.String(300), nullable=False),
        sa.Column("currency", sa.String(5), nullable=False),
        sa.Column("impact", sa.String(10), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual", sa.String(50), nullable=False, server_default=""),
        sa.Column("forecast", sa.String(50), nullable=False, server_default=""),
        sa.Column("previous", sa.String(50), nullable=False, server_default=""),
        sa.Column("source", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cal_currency_time", "calendar_events", ["currency", "event_time"])
    op.create_index("ix_cal_event_time", "calendar_events", ["event_time"])
    op.create_index("ix_cal_impact_time", "calendar_events", ["impact", "event_time"])

    op.create_table(
        "dxy_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("trend_direction", sa.String(10), nullable=False, server_default="SIDEWAYS"),
        sa.Column("key_levels_json", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("bias", sa.String(10), nullable=False, server_default="NEUTRAL"),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_dxy_analyzed_at", "dxy_snapshots", ["analyzed_at"])

    op.create_table(
        "intermarket_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("gold_price", sa.Float, nullable=True),
        sa.Column("silver_price", sa.Float, nullable=True),
        sa.Column("oil_price", sa.Float, nullable=True),
        sa.Column("us2y_yield", sa.Float, nullable=True),
        sa.Column("us10y_yield", sa.Float, nullable=True),
        sa.Column("us30y_yield", sa.Float, nullable=True),
        sa.Column("dxy_value", sa.Float, nullable=True),
        sa.Column("sp500", sa.Float, nullable=True),
        sa.Column("vix", sa.Float, nullable=True),
        sa.Column("correlation_signals_json", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_intermarket_snapshot_at", "intermarket_snapshots", ["snapshot_at"])


def downgrade() -> None:
    op.drop_table("intermarket_snapshots")
    op.drop_table("dxy_snapshots")
    op.drop_table("calendar_events")
    op.drop_table("news_items")
    op.drop_table("economic_releases")
    op.drop_table("cot_reports")
    op.drop_table("central_bank_events")
