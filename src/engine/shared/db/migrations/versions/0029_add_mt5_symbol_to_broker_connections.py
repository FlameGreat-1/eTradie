"""Add mt5_symbol to broker_connections.

Revision ID: 0029
Revises: 0028
Create Date: 2026-05-29

Rationale:
  The HostedProvisioner.provision_account() accepts a 'symbol' parameter
  that is written into the per-tenant StatefulSet's MT_SYMBOL env var.
  Previously this value was never persisted to the broker_connections row,
  so the HostedRecoveryService had to hardcode symbol='EURUSD' when
  re-provisioning a connection after a crash. This caused the user's
  configured symbol to be silently replaced with EURUSD on every recovery
  cycle.

  This migration adds mt5_symbol (VARCHAR 50, nullable, default 'EURUSD')
  so the symbol is stored at creation time and read back by the recovery
  service on re-provision.
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "broker_connections",
        sa.Column(
            "mt5_symbol",
            sa.String(length=50),
            nullable=True,
            server_default="EURUSD",
        ),
    )


def downgrade() -> None:
    op.drop_column("broker_connections", "mt5_symbol")
