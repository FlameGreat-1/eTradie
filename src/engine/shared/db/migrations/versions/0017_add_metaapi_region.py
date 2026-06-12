"""Add metaapi_region to broker_connections.

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-02
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "broker_connections",
        sa.Column("metaapi_region", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("broker_connections", "metaapi_region")
