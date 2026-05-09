"""Add platform to broker_connections.

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-09
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0019'
down_revision: Union[str, None] = '0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'broker_connections',
        sa.Column('platform', sa.String(length=10), server_default='mt5', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('broker_connections', 'platform')
