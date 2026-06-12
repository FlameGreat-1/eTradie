"""Drop EURUSD server_default on mt5_symbol.

Revision ID: 0030
Revises: 0029
Create Date: 2026-05-30

Rationale:
  The hosted MT-node provisioner used to stamp 'EURUSD' into MT_SYMBOL
  before MT5 logged into the broker. Brokers that publish their pairs
  under suffixed names silently failed because the unsuffixed name did
  not exist on the broker's Market Watch.

  Automatic resolution is now done by the existing BrokerSyncService:
  the provisioner calls sync_all_symbols() synchronously after the Pod
  becomes Ready, which populates the existing broker_symbols table
  (migration 0018) with one row per broker-published instrument. The
  provisioner then picks the first row as the chart-attach symbol and
  writes it to mt5_symbol; the dashboard reads from broker_symbols.

  This migration only removes the silent EURUSD default; no new
  columns are introduced. The broker's own catalog is the canonical
  source of truth.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0030"
down_revision: Union[str, None] = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "broker_connections",
        "mt5_symbol",
        server_default=None,
        existing_type=sa.String(length=50),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "broker_connections",
        "mt5_symbol",
        server_default=sa.text("'EURUSD'"),
        existing_type=sa.String(length=50),
        existing_nullable=True,
    )
