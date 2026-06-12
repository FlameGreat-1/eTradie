"""add_is_platform_to_llm_connections

Revision ID: 0021
Revises: 0020
Create Date: 2026-05-16 08:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add is_platform column
    op.add_column(
        "llm_connections",
        sa.Column("is_platform", sa.Boolean(), server_default="false", nullable=False),
    )

    # 2. Make user_id nullable (so platform connection can have user_id = null)
    op.alter_column("llm_connections", "user_id", existing_type=sa.String(length=64), nullable=True)

    # 3. Create index for is_platform
    op.create_index(
        "ix_llm_connections_is_platform",
        "llm_connections",
        ["is_platform"],
        unique=False,
    )


def downgrade() -> None:
    # 1. Remove index
    op.drop_index("ix_llm_connections_is_platform", table_name="llm_connections")

    # 2. Revert user_id back to non-nullable
    # Warning: if there are rows with user_id = null, this will fail.
    # To be safe, we would delete the platform row first.
    op.execute("DELETE FROM llm_connections WHERE is_platform = true")
    op.alter_column("llm_connections", "user_id", existing_type=sa.String(length=64), nullable=False)

    # 3. Drop is_platform column
    op.drop_column("llm_connections", "is_platform")
