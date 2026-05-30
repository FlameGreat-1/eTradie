"""Add symbol_map JSONB and drop EURUSD server_default on mt5_symbol.

Revision ID: 0030
Revises: 0029
Create Date: 2026-05-30

Rationale:
  The hosted MT-node provisioner used to stamp 'EURUSD' into MT_SYMBOL
  before MT5 logged into the broker. Brokers that publish their pairs
  under suffixed names (EURUSDm on Exness, EURUSD.r on IC Markets,
  EURUSD+ on FTMO, EURUSD.cash on some ECN brokers, etc.) silently
  failed because the unsuffixed name did not exist on the broker's
  Market Watch. The user was then asked to type the suffix manually,
  which violated the 'server + login + password only' contract.

  This migration lays the DB foundation for automatic resolution:

  1. symbol_map (NEW): canonical -> broker-actual JSONB mapping
     written by the resolver after the Pod boots and the EA reports
     the broker's full Market Watch via GET_ALL_SYMBOLS. Empty {}
     means 'resolver has not run yet'. Every symbol-taking engine
     code path (place_order, fetch_candles, get_tick_price)
     translates the canonical pair through this map at the ZmqClient
     boundary so the rest of the platform never has to know about
     broker symbol quirks.

  2. mt5_symbol.server_default (REMOVED): silently defaulting new
     rows to 'EURUSD' was the original silent-failure footgun. The
     column stays nullable; the resolver writes the broker-actual
     value alongside symbol_map. Existing rows keep whatever value
     they have.

No backfill is performed for existing rows: the resolver will populate
symbol_map on the next HostedRecoveryService sweep (within
ENGINE_HOSTED_RECOVERY_SWEEP_INTERVAL_SECS, default 60s) for every
active hosted connection. metaapi/ea connection rows keep symbol_map
= '{}' because they do not need per-broker translation (metaapi
normalises symbols cloud-side; ea is local-dev only).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '0030'
down_revision: Union[str, None] = '0029'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'broker_connections',
        sa.Column(
            'symbol_map',
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column(
        'broker_connections',
        'mt5_symbol',
        server_default=None,
        existing_type=sa.String(length=50),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'broker_connections',
        'mt5_symbol',
        server_default=sa.text("'EURUSD'"),
        existing_type=sa.String(length=50),
        existing_nullable=True,
    )
    op.drop_column('broker_connections', 'symbol_map')
