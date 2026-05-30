"""Align broker_connections with the BrokerConnectionRow ORM.

After revision 0019 the DB schema is missing two columns the ORM
declares and the application writes to:

  * hosted_container_id — used by:
      - routers.broker_connections.create_broker_connection
        (stores the K8s release name when connection_type='hosted')
      - factory.create_mt5_broker_from_connection
        (resolves the in-cluster Service DNS from this value)
      - hosted.recovery.HostedRecoveryService
        (per-row StatefulSet lookups in the sweep loop)
      - hosted.provisioner.HostedProvisioner.delete_account
        (releases the K8s resources by container_id at row-delete time)

  * mt5_symbol — written by:
      - repositories.broker_connection_repository.update_chart_symbol
        which is the only callsite of the provisioner's chart_symbol_writer
        callback. The provisioner picks the chart-attach symbol from
        BrokerSyncService once the Pod is Ready and the broker catalog
        is reachable, then persists it here so HostedRecoveryService
        can re-provision with the same value without re-resolving.

Without these columns, every hosted-connection create fails at the
first write with UndefinedColumn and the K8s resources are rolled
back by _best_effort_cleanup.

This migration intentionally does NOT drop the dead
metaapi_token_encrypted column (created in 0009, no longer declared
on the ORM). A destructive drop requires verifying no other consumer
in the wider system reads it and that the column holds no production
data. That investigation is deferred to a separate audit pass.

Fully idempotent: re-running on an already-migrated DB is a no-op.

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-30
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "broker_connections"
_INDEX_HOSTED_CONTAINER_ID = "ix_bc_hosted_container_id"


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = set(inspector.get_table_names())
    if _TABLE not in existing_tables:
        # broker_connections is created in 0009; nothing to align.
        return

    existing_columns = {col["name"] for col in inspector.get_columns(_TABLE)}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes(_TABLE)}

    # 1) hosted_container_id
    if "hosted_container_id" not in existing_columns:
        op.add_column(
            _TABLE,
            sa.Column("hosted_container_id", sa.String(length=100), nullable=True),
        )

    # Index supports HostedRecoveryService.get_account_status lookups
    # and the gc_orphans sweep. Column is only populated for
    # connection_type='hosted' rows so the index stays naturally sparse.
    if _INDEX_HOSTED_CONTAINER_ID not in existing_indexes:
        op.create_index(
            _INDEX_HOSTED_CONTAINER_ID,
            _TABLE,
            ["hosted_container_id"],
        )

    # 2) mt5_symbol
    if "mt5_symbol" not in existing_columns:
        op.add_column(
            _TABLE,
            sa.Column("mt5_symbol", sa.String(length=50), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = set(inspector.get_table_names())
    if _TABLE not in existing_tables:
        return

    existing_columns = {col["name"] for col in inspector.get_columns(_TABLE)}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes(_TABLE)}

    if "mt5_symbol" in existing_columns:
        op.drop_column(_TABLE, "mt5_symbol")

    if _INDEX_HOSTED_CONTAINER_ID in existing_indexes:
        op.drop_index(_INDEX_HOSTED_CONTAINER_ID, table_name=_TABLE)
    if "hosted_container_id" in existing_columns:
        op.drop_column(_TABLE, "hosted_container_id")
