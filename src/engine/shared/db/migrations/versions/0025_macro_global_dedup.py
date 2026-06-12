"""Restore global dedup on macro tables, drop accidental multi-tenancy.

Macro data (central-bank RSS, economic calendar, COT reports, DXY,
intermarket commodities and yields, economic releases) is inherently
global - the providers are public market-data sources, the
collectors are run by the scheduler with no user context, and the
BaseCollector contract is explicit:

    \"Every collector is global: no user_id is required.\"

Migration 0013 nonetheless added a user_id column and tenant-scoped
unique constraints to the six global macro tables under the
incorrect assumption that every persisted row was user-owned. The
ORM models continued to declare the original global unique
constraints (with the single exception of economic_releases, which
migration 0024 updated). At runtime this drift surfaces as

    asyncpg.exceptions.InvalidColumnReferenceError: there is no
    unique or exclusion constraint matching the ON CONFLICT
    specification

the instant any collector runs bulk_upsert() with its (global)
index_elements.

This migration restores the original global design across the macro
subsystem in a single transactional step:

  1. For each macro table, drop the user_id-prefixed unique
     constraint added by 0013 (or 0024 for economic_releases) and
     create the global constraint declared by the ORM model.
  2. Create the missing global unique constraints on dxy_snapshots
     and intermarket_snapshots. The ORM models have always declared
     these, but no prior migration ever installed them in Postgres,
     so any upsert path against those tables was latently broken.
  3. Drop every user_id column and the user_id-prefixed indexes that
     0013 attached to the six macro tables. No reader filters by
     user_id (verified across repositories and the retention
     pruner); every existing row carries the sentinel value
     'system'; the column adds nothing but schema noise and a
     misleading invariant.
  4. Drop the news_items table. The macro news collector was removed
     before this branch was cut (see
     engine/macro/scheduler_jobs.py register_macro_jobs docstring),
     no ORM model imports it, and no live code reads or writes it.

Every DDL step is guarded by an inspector check so the migration is
idempotent on a partially-applied database. downgrade() reinstates
0013's tenant-scoped shape verbatim (including news_items) so the
Alembic history remains reversible.

Revision ID: 0025
Revises: 0024
Create Date: 2026-05-25
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Constraint and index inventory ─────────────────────────────────────
#
# Each entry describes one macro table:
#   tenant_uq   : the tenant-scoped unique constraint added by 0013/0024.
#                 Empty string when the table never got one (dxy,
#                 intermarket).
#   global_uq   : the (name, columns) tuple of the global unique
#                 constraint declared by the ORM model.
#   tenant_ix   : tenant-scoped indexes added by 0013 that are dropped
#                 here. The corresponding global indexes were already
#                 dropped by 0013 itself, so they are recreated below.
#   global_ix   : (name, columns) tuples for the global indexes that
#                 must exist after this migration. Matches the ORM.
#
# Maintaining the inventory as data keeps upgrade() and downgrade()
# symmetric and makes future schema audits trivial: every entry is in
# one place.

_MACRO_TABLES: list[dict] = [
    {
        "table": "calendar_events",
        "tenant_uq": "uq_cal_user_event",
        "global_uq": (
            "uq_cal_event",
            ["event_name", "currency", "event_time"],
        ),
        "tenant_ix": [
            "ix_cal_user_currency_time",
            "ix_cal_user_event_time",
            "ix_cal_user_impact_time",
            "ix_cal_user_id",
        ],
        "global_ix": [
            ("ix_cal_currency_time", ["currency", "event_time"]),
            ("ix_cal_event_time", ["event_time"]),
            ("ix_cal_impact_time", ["impact", "event_time"]),
        ],
    },
    {
        "table": "central_bank_events",
        "tenant_uq": "uq_cb_user_bank_title_ts",
        "global_uq": (
            "uq_cb_bank_title_ts",
            ["bank", "title", "event_timestamp"],
        ),
        "tenant_ix": [
            "ix_cb_events_user_bank_timestamp",
            "ix_cb_events_user_event_type",
            "ix_cb_events_user_created_at",
            "ix_cb_events_user_policy_action",
            "ix_cb_events_user_id",
        ],
        "global_ix": [
            ("ix_cb_events_bank_timestamp", ["bank", "event_timestamp"]),
            ("ix_cb_events_event_type", ["event_type"]),
            ("ix_cb_events_created_at", ["created_at"]),
            (
                "ix_cb_events_policy_action",
                ["policy_action", "event_timestamp"],
            ),
        ],
    },
    {
        "table": "cot_reports",
        "tenant_uq": "uq_cot_user_currency_date",
        "global_uq": (
            "uq_cot_currency_date",
            ["currency", "report_date"],
        ),
        "tenant_ix": [
            "ix_cot_user_currency_date",
            "ix_cot_user_report_date",
            "ix_cot_user_extreme_flag",
            "ix_cot_user_id",
        ],
        "global_ix": [
            ("ix_cot_currency_date", ["currency", "report_date"]),
            ("ix_cot_report_date", ["report_date"]),
            ("ix_cot_extreme_flag", ["extreme_flag", "report_date"]),
        ],
    },
    {
        "table": "economic_releases",
        "tenant_uq": "uq_econ_user_indicator_name_time",
        "global_uq": (
            "uq_econ_indicator_name_time",
            ["indicator_name", "release_time"],
        ),
        "tenant_ix": [
            "ix_econ_user_release_time",
            "ix_econ_user_id",
        ],
        "global_ix": [
            ("ix_econ_release_time", ["release_time"]),
        ],
    },
    {
        "table": "dxy_snapshots",
        # 0001 created this table without a unique constraint; the
        # ORM has declared uq_dxy_analyzed_at since well before this
        # migration. We create the missing global constraint here.
        "tenant_uq": "",
        "global_uq": ("uq_dxy_analyzed_at", ["analyzed_at"]),
        "tenant_ix": [
            "ix_dxy_user_analyzed_at",
            "ix_dxy_user_id",
        ],
        "global_ix": [
            ("ix_dxy_analyzed_at", ["analyzed_at"]),
        ],
    },
    {
        "table": "intermarket_snapshots",
        # Same situation as dxy_snapshots: missing in 0001, declared
        # by the ORM, created here.
        "tenant_uq": "",
        "global_uq": (
            "uq_intermarket_snapshot_at",
            ["snapshot_at"],
        ),
        "tenant_ix": [
            "ix_intermarket_user_snapshot_at",
            "ix_intermarket_user_id",
        ],
        "global_ix": [
            ("ix_intermarket_snapshot_at", ["snapshot_at"]),
        ],
    },
]

_DEAD_TABLE = "news_items"


# ── Inspector helpers ──────────────────────────────────────────────────
#
# Each helper takes a fresh Inspector reference so callers can refresh
# state cheaply between DDL steps. The cost of re-introspecting one
# table after each operation is negligible compared to the safety of
# never operating on a stale view of the schema mid-migration.


def _existing_indexes(insp, table_name: str) -> set[str]:
    return {idx["name"] for idx in insp.get_indexes(table_name) if idx.get("name")}


def _existing_unique_constraints(insp, table_name: str) -> set[str]:
    return {
        uc["name"] for uc in insp.get_unique_constraints(table_name) if uc.get("name")
    }


def _existing_columns(insp, table_name: str) -> set[str]:
    return {col["name"] for col in insp.get_columns(table_name)}


# ── Upgrade ────────────────────────────────────────────────────────────


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    existing_tables = set(insp.get_table_names())

    # ── 1. Per-table: tenant -> global constraint swap ─────────────
    for entry in _MACRO_TABLES:
        table = entry["table"]
        if table not in existing_tables:
            # Table never made it into the DB. Nothing to do.
            continue

        # 1a. Drop tenant indexes added by 0013. Doing this first means
        # the unique-constraint replacement below cannot stumble on a
        # tenant index that shadows the column being dropped.
        insp = inspect(conn)
        existing_ix = _existing_indexes(insp, table)
        for ix_name in entry["tenant_ix"]:
            if ix_name in existing_ix:
                op.drop_index(ix_name, table_name=table)

        # 1b. Drop the tenant-scoped unique constraint, if any.
        if entry["tenant_uq"]:
            insp = inspect(conn)
            existing_uq = _existing_unique_constraints(insp, table)
            if entry["tenant_uq"] in existing_uq:
                op.drop_constraint(
                    entry["tenant_uq"],
                    table,
                    type_="unique",
                )

        # 1c. Create the global unique constraint declared by the ORM.
        # Idempotent: skip when an earlier partial run already created
        # it (or when 0001 still had it, for tables that 0013 never
        # rewrote into a tenant constraint).
        global_uq_name, global_uq_cols = entry["global_uq"]
        insp = inspect(conn)
        existing_uq = _existing_unique_constraints(insp, table)
        if global_uq_name not in existing_uq:
            op.create_unique_constraint(
                global_uq_name,
                table,
                global_uq_cols,
            )

        # 1d. Drop the user_id column. We do this AFTER the unique
        # constraint swap so any FK or trigger that referenced the old
        # tenant constraint had its dependency removed first. The
        # column carries no data of interest - every row has the
        # sentinel 'system'.
        insp = inspect(conn)
        existing_cols = _existing_columns(insp, table)
        if "user_id" in existing_cols:
            op.drop_column(table, "user_id")

        # 1e. Recreate the global indexes 0013 dropped. Idempotent.
        insp = inspect(conn)
        existing_ix = _existing_indexes(insp, table)
        for ix_name, ix_cols in entry["global_ix"]:
            if ix_name not in existing_ix:
                op.create_index(ix_name, table, ix_cols)

    # ── 2. Drop the dead news_items table ──────────────────────────
    #
    # The news collector was retired before this branch (see
    # engine.macro.scheduler_jobs.register_macro_jobs). No ORM model
    # imports the table; no repository targets it; the retention
    # pruner does not reference it. Dropping it removes a confusing
    # zombie from the schema.
    #
    # We rely on PostgreSQL's documented DROP TABLE cascade to take
    # every owned object with it: plain indexes, the index that
    # backs each UNIQUE constraint, the primary key, and any column
    # default sequences. Pre-dropping the indexes by name (an earlier
    # iteration of this migration did this) is actively wrong because
    # SQLAlchemy's Inspector.get_indexes() reports constraint-backed
    # indexes alongside plain ones - they share the constraint's name
    # but cannot be dropped independently of the constraint. The first
    # such name (uq_news_user_dedupe_hash, the index PostgreSQL
    # auto-created behind UNIQUE (user_id, dedupe_hash)) raises
    # DependentObjectsStillExistError. DROP TABLE handles the whole
    # set in one atomic step, so the loop was unnecessary as well as
    # incorrect.
    insp = inspect(conn)
    existing_tables = set(insp.get_table_names())
    if _DEAD_TABLE in existing_tables:
        op.drop_table(_DEAD_TABLE)


# ── Downgrade ──────────────────────────────────────────────────────────
#
# Reverses upgrade() exactly: recreates news_items in its post-0013
# shape, restores the user_id column with the 'system' default that
# 0013 used, rebuilds the tenant-scoped unique constraints and
# indexes, and drops the global constraints this migration created.
#
# The block uses the same idempotency guards as upgrade() so a
# partially-applied downgrade is safe to resume.


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    existing_tables = set(insp.get_table_names())

    # ── 1. Recreate the news_items table in its post-0013 form ─────
    if _DEAD_TABLE not in existing_tables:
        op.create_table(
            _DEAD_TABLE,
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("uuid_generate_v4()"),
            ),
            sa.Column("headline", sa.String(1000), nullable=False),
            sa.Column("source", sa.String(50), nullable=False),
            sa.Column("url", sa.String(2000), nullable=False, server_default=""),
            sa.Column("summary", sa.Text, nullable=False, server_default=""),
            sa.Column(
                "currencies",
                postgresql.ARRAY(sa.String(5)),
                nullable=False,
                server_default="{}",
            ),
            sa.Column(
                "sentiment",
                sa.String(15),
                nullable=False,
                server_default="NEUTRAL",
            ),
            sa.Column(
                "impact",
                sa.String(10),
                nullable=False,
                server_default="MEDIUM",
            ),
            sa.Column("dedupe_hash", sa.String(64), nullable=False),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "user_id",
                sa.String(64),
                nullable=False,
                server_default="system",
            ),
        )
        op.create_unique_constraint(
            "uq_news_user_dedupe_hash",
            _DEAD_TABLE,
            ["user_id", "dedupe_hash"],
        )
        op.create_index(
            "ix_news_user_published_at",
            _DEAD_TABLE,
            ["user_id", "published_at"],
        )
        op.create_index(
            "ix_news_user_impact",
            _DEAD_TABLE,
            ["user_id", "impact"],
        )
        op.create_index(
            "ix_news_user_id",
            _DEAD_TABLE,
            ["user_id"],
        )

    # ── 2. Reverse the global -> tenant swap on each macro table ───
    #
    # Walk the inventory in reverse so newer dependencies come back
    # before older ones. Within each table the order is:
    #   drop global indexes -> drop global unique constraint ->
    #   re-add user_id column -> recreate tenant unique constraint ->
    #   recreate tenant indexes.
    for entry in reversed(_MACRO_TABLES):
        table = entry["table"]
        insp = inspect(conn)
        if table not in set(insp.get_table_names()):
            continue

        # 2a. Drop the global indexes this migration created.
        existing_ix = _existing_indexes(insp, table)
        for ix_name, _cols in entry["global_ix"]:
            if ix_name in existing_ix:
                op.drop_index(ix_name, table_name=table)

        # 2b. Drop the global unique constraint.
        global_uq_name, _global_uq_cols = entry["global_uq"]
        insp = inspect(conn)
        existing_uq = _existing_unique_constraints(insp, table)
        if global_uq_name in existing_uq:
            op.drop_constraint(
                global_uq_name,
                table,
                type_="unique",
            )

        # 2c. Re-add the user_id column with the 'system' default 0013
        # used. NOT NULL is safe because the server_default fills any
        # existing rows.
        insp = inspect(conn)
        existing_cols = _existing_columns(insp, table)
        if "user_id" not in existing_cols:
            op.add_column(
                table,
                sa.Column(
                    "user_id",
                    sa.String(64),
                    nullable=False,
                    server_default="system",
                ),
            )

        # 2d. Recreate the tenant-scoped unique constraint, where 0013
        # had one. dxy_snapshots and intermarket_snapshots never had a
        # tenant unique constraint - they only had tenant indexes.
        if entry["tenant_uq"]:
            tenant_uq_cols = ["user_id"] + entry["global_uq"][1]
            insp = inspect(conn)
            existing_uq = _existing_unique_constraints(insp, table)
            if entry["tenant_uq"] not in existing_uq:
                op.create_unique_constraint(
                    entry["tenant_uq"],
                    table,
                    tenant_uq_cols,
                )

        # 2e. Recreate the tenant indexes 0013 originally installed.
        #
        # The column list for each tenant index is derived from the
        # name pattern 0013 used (user_id + global key). We rebuild it
        # rather than maintain a parallel list so the inventory above
        # remains the single source of truth.
        tenant_ix_columns = {
            # calendar_events
            "ix_cal_user_currency_time": [
                "user_id",
                "currency",
                "event_time",
            ],
            "ix_cal_user_event_time": ["user_id", "event_time"],
            "ix_cal_user_impact_time": [
                "user_id",
                "impact",
                "event_time",
            ],
            "ix_cal_user_id": ["user_id"],
            # central_bank_events
            "ix_cb_events_user_bank_timestamp": [
                "user_id",
                "bank",
                "event_timestamp",
            ],
            "ix_cb_events_user_event_type": [
                "user_id",
                "event_type",
            ],
            "ix_cb_events_user_created_at": [
                "user_id",
                "created_at",
            ],
            "ix_cb_events_user_policy_action": [
                "user_id",
                "policy_action",
                "event_timestamp",
            ],
            "ix_cb_events_user_id": ["user_id"],
            # cot_reports
            "ix_cot_user_currency_date": [
                "user_id",
                "currency",
                "report_date",
            ],
            "ix_cot_user_report_date": ["user_id", "report_date"],
            "ix_cot_user_extreme_flag": [
                "user_id",
                "extreme_flag",
                "report_date",
            ],
            "ix_cot_user_id": ["user_id"],
            # economic_releases
            "ix_econ_user_release_time": ["user_id", "release_time"],
            "ix_econ_user_id": ["user_id"],
            # dxy_snapshots
            "ix_dxy_user_analyzed_at": ["user_id", "analyzed_at"],
            "ix_dxy_user_id": ["user_id"],
            # intermarket_snapshots
            "ix_intermarket_user_snapshot_at": [
                "user_id",
                "snapshot_at",
            ],
            "ix_intermarket_user_id": ["user_id"],
        }

        insp = inspect(conn)
        existing_ix = _existing_indexes(insp, table)
        for ix_name in entry["tenant_ix"]:
            if ix_name in existing_ix:
                continue
            cols = tenant_ix_columns.get(ix_name)
            if cols is None:
                # Defensive: should never happen for the inventory we
                # maintain, but skip rather than crash an in-progress
                # downgrade if the index name was ever renamed.
                continue
            op.create_index(ix_name, table, cols)
