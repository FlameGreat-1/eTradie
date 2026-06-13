"""Add user_id to all 7 macro tables for multi-tenant data isolation.

Completes multi-tenant scoping for the macro engine. Migrations 0011
and 0012 added user_id to processor/TA tables. This migration covers
all 7 macro storage tables:

  - calendar_events
  - central_bank_events
  - cot_reports
  - dxy_snapshots
  - economic_releases
  - intermarket_snapshots
  - news_items

Every row is now owned by a specific user. All repository queries
MUST filter by user_id. All cache keys MUST include user_id.

Note: Application is in development with no existing data.
Tables are empty so user_id is added as NOT NULL directly
with no backfill needed.

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# All 7 macro tables that need user_id.
_TABLES = [
    "calendar_events",
    "central_bank_events",
    "cot_reports",
    "dxy_snapshots",
    "economic_releases",
    "intermarket_snapshots",
    "news_items",
]

# Simple user_id index per table.
_USER_ID_INDEXES = {
    "calendar_events": "ix_cal_user_id",
    "central_bank_events": "ix_cb_events_user_id",
    "cot_reports": "ix_cot_user_id",
    "dxy_snapshots": "ix_dxy_user_id",
    "economic_releases": "ix_econ_user_id",
    "intermarket_snapshots": "ix_intermarket_user_id",
    "news_items": "ix_news_user_id",
}

# Old indexes to drop (created in 0001 and 0005 without user_id).
_OLD_INDEXES_TO_DROP = [
    ("calendar_events", "ix_cal_currency_time"),
    ("calendar_events", "ix_cal_event_time"),
    ("calendar_events", "ix_cal_impact_time"),
    ("central_bank_events", "ix_cb_events_bank_timestamp"),
    ("central_bank_events", "ix_cb_events_event_type"),
    ("central_bank_events", "ix_cb_events_created_at"),
    ("central_bank_events", "ix_cb_events_policy_action"),
    ("cot_reports", "ix_cot_currency_date"),
    ("cot_reports", "ix_cot_report_date"),
    ("cot_reports", "ix_cot_extreme_flag"),
    ("dxy_snapshots", "ix_dxy_analyzed_at"),
    ("economic_releases", "ix_econ_currency_indicator"),
    ("economic_releases", "ix_econ_release_time"),
    ("economic_releases", "ix_econ_currency_release"),
    ("economic_releases", "ix_econ_inflation_type"),
    ("intermarket_snapshots", "ix_intermarket_snapshot_at"),
    ("news_items", "ix_news_published_at"),
    ("news_items", "ix_news_impact"),
]

# New indexes with user_id prefix.
_NEW_INDEXES = [
    (
        "calendar_events",
        "ix_cal_user_currency_time",
        ["user_id", "currency", "event_time"],
        False,
    ),
    ("calendar_events", "ix_cal_user_event_time", ["user_id", "event_time"], False),
    (
        "calendar_events",
        "ix_cal_user_impact_time",
        ["user_id", "impact", "event_time"],
        False,
    ),
    (
        "central_bank_events",
        "ix_cb_events_user_bank_timestamp",
        ["user_id", "bank", "event_timestamp"],
        False,
    ),
    (
        "central_bank_events",
        "ix_cb_events_user_event_type",
        ["user_id", "event_type"],
        False,
    ),
    (
        "central_bank_events",
        "ix_cb_events_user_created_at",
        ["user_id", "created_at"],
        False,
    ),
    (
        "central_bank_events",
        "ix_cb_events_user_policy_action",
        ["user_id", "policy_action", "event_timestamp"],
        False,
    ),
    (
        "cot_reports",
        "ix_cot_user_currency_date",
        ["user_id", "currency", "report_date"],
        False,
    ),
    ("cot_reports", "ix_cot_user_report_date", ["user_id", "report_date"], False),
    (
        "cot_reports",
        "ix_cot_user_extreme_flag",
        ["user_id", "extreme_flag", "report_date"],
        False,
    ),
    ("dxy_snapshots", "ix_dxy_user_analyzed_at", ["user_id", "analyzed_at"], False),
    (
        "economic_releases",
        "ix_econ_user_currency_indicator",
        ["user_id", "currency", "indicator"],
        False,
    ),
    (
        "economic_releases",
        "ix_econ_user_release_time",
        ["user_id", "release_time"],
        False,
    ),
    (
        "economic_releases",
        "ix_econ_user_currency_release",
        ["user_id", "currency", "release_time"],
        False,
    ),
    (
        "economic_releases",
        "ix_econ_user_inflation_type",
        ["user_id", "inflation_type", "release_time"],
        False,
    ),
    (
        "intermarket_snapshots",
        "ix_intermarket_user_snapshot_at",
        ["user_id", "snapshot_at"],
        False,
    ),
    ("news_items", "ix_news_user_published_at", ["user_id", "published_at"], False),
    ("news_items", "ix_news_user_impact", ["user_id", "impact"], False),
]

# Old unique constraints to drop.
_OLD_CONSTRAINTS_TO_DROP = [
    ("cot_reports", "uq_cot_currency_date"),
    ("news_items", "uq_news_dedupe_hash"),
]

# New unique constraints with user_id.
_NEW_CONSTRAINTS = [
    (
        "calendar_events",
        "uq_cal_user_event",
        ["user_id", "event_name", "currency", "event_time"],
    ),
    (
        "central_bank_events",
        "uq_cb_user_bank_title_ts",
        ["user_id", "bank", "title", "event_timestamp"],
    ),
    (
        "cot_reports",
        "uq_cot_user_currency_date",
        ["user_id", "currency", "report_date"],
    ),
    (
        "economic_releases",
        "uq_econ_user_currency_indicator_time",
        ["user_id", "currency", "indicator", "release_time"],
    ),
    ("news_items", "uq_news_user_dedupe_hash", ["user_id", "dedupe_hash"]),
]


def _get_existing_indexes(insp, table_name: str) -> set[str]:
    return {idx["name"] for idx in insp.get_indexes(table_name) if idx.get("name")}


def _get_existing_constraints(insp, table_name: str) -> set[str]:
    return {uc["name"] for uc in insp.get_unique_constraints(table_name) if uc.get("name")}


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    existing_tables = set(insp.get_table_names())

    # Phase 1: Add user_id column (NOT NULL directly - tables are empty).
    for table_name in _TABLES:
        if table_name not in existing_tables:
            continue

        existing_columns = {col["name"] for col in insp.get_columns(table_name)}
        if "user_id" in existing_columns:
            continue

        op.add_column(
            table_name,
            sa.Column("user_id", sa.String(64), nullable=False, server_default="system"),
        )

        index_name = _USER_ID_INDEXES[table_name]
        existing_indexes = _get_existing_indexes(insp, table_name)
        if index_name not in existing_indexes:
            op.create_index(index_name, table_name, ["user_id"])

    # Refresh inspector after schema changes.
    insp = inspect(conn)

    # Phase 2: Drop old indexes (without user_id).
    for table_name, index_name in _OLD_INDEXES_TO_DROP:
        if table_name not in existing_tables:
            continue
        existing_indexes = _get_existing_indexes(insp, table_name)
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name=table_name)

    # Phase 3: Drop old unique constraints (without user_id).
    for table_name, constraint_name in _OLD_CONSTRAINTS_TO_DROP:
        if table_name not in existing_tables:
            continue
        existing_constraints = _get_existing_constraints(insp, table_name)
        if constraint_name in existing_constraints:
            op.drop_constraint(constraint_name, table_name, type_="unique")

    # Refresh inspector after drops.
    insp = inspect(conn)

    # Phase 4: Create new unique constraints (with user_id).
    for table_name, constraint_name, columns in _NEW_CONSTRAINTS:
        if table_name not in existing_tables:
            continue
        existing_constraints = _get_existing_constraints(insp, table_name)
        if constraint_name not in existing_constraints:
            op.create_unique_constraint(constraint_name, table_name, columns)

    # Phase 5: Create new indexes (with user_id).
    for table_name, index_name, columns, unique in _NEW_INDEXES:
        if table_name not in existing_tables:
            continue
        existing_indexes = _get_existing_indexes(insp, table_name)
        if index_name not in existing_indexes:
            op.create_index(index_name, table_name, columns, unique=unique)


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    existing_tables = set(insp.get_table_names())

    # Phase 1: Drop new indexes.
    for table_name, index_name, _columns, _unique in _NEW_INDEXES:
        if table_name not in existing_tables:
            continue
        existing_indexes = _get_existing_indexes(insp, table_name)
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name=table_name)

    # Phase 2: Drop new unique constraints.
    for table_name, constraint_name, _columns in _NEW_CONSTRAINTS:
        if table_name not in existing_tables:
            continue
        existing_constraints = _get_existing_constraints(insp, table_name)
        if constraint_name in existing_constraints:
            op.drop_constraint(constraint_name, table_name, type_="unique")

    # Phase 3: Restore old unique constraints.
    _OLD_CONSTRAINTS_RESTORE = [
        ("cot_reports", "uq_cot_currency_date", ["currency", "report_date"]),
        ("news_items", "uq_news_dedupe_hash", ["dedupe_hash"]),
    ]
    for table_name, constraint_name, columns in _OLD_CONSTRAINTS_RESTORE:
        if table_name not in existing_tables:
            continue
        op.create_unique_constraint(constraint_name, table_name, columns)

    # Phase 4: Restore old indexes.
    _OLD_INDEXES_RESTORE = [
        ("calendar_events", "ix_cal_currency_time", ["currency", "event_time"]),
        ("calendar_events", "ix_cal_event_time", ["event_time"]),
        ("calendar_events", "ix_cal_impact_time", ["impact", "event_time"]),
        (
            "central_bank_events",
            "ix_cb_events_bank_timestamp",
            ["bank", "event_timestamp"],
        ),
        ("central_bank_events", "ix_cb_events_event_type", ["event_type"]),
        ("central_bank_events", "ix_cb_events_created_at", ["created_at"]),
        (
            "central_bank_events",
            "ix_cb_events_policy_action",
            ["policy_action", "event_timestamp"],
        ),
        ("cot_reports", "ix_cot_currency_date", ["currency", "report_date"]),
        ("cot_reports", "ix_cot_report_date", ["report_date"]),
        ("cot_reports", "ix_cot_extreme_flag", ["extreme_flag", "report_date"]),
        ("dxy_snapshots", "ix_dxy_analyzed_at", ["analyzed_at"]),
        ("economic_releases", "ix_econ_currency_indicator", ["currency", "indicator"]),
        ("economic_releases", "ix_econ_release_time", ["release_time"]),
        ("economic_releases", "ix_econ_currency_release", ["currency", "release_time"]),
        (
            "economic_releases",
            "ix_econ_inflation_type",
            ["inflation_type", "release_time"],
        ),
        ("intermarket_snapshots", "ix_intermarket_snapshot_at", ["snapshot_at"]),
        ("news_items", "ix_news_published_at", ["published_at"]),
        ("news_items", "ix_news_impact", ["impact"]),
    ]
    for table_name, index_name, columns in _OLD_INDEXES_RESTORE:
        if table_name not in existing_tables:
            continue
        existing_indexes = _get_existing_indexes(insp, table_name)
        if index_name not in existing_indexes:
            op.create_index(index_name, table_name, columns)

    # Phase 5: Drop user_id columns and their indexes.
    for table_name in _TABLES:
        if table_name not in existing_tables:
            continue

        existing_columns = {col["name"] for col in insp.get_columns(table_name)}
        if "user_id" not in existing_columns:
            continue

        index_name = _USER_ID_INDEXES[table_name]
        existing_indexes = _get_existing_indexes(insp, table_name)
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name=table_name)

        op.drop_column(table_name, "user_id")
