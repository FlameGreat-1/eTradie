"""Add hosted_container_id to broker_connections.

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "broker_connections",
        sa.Column("hosted_container_id", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("broker_connections", "hosted_container_id")
