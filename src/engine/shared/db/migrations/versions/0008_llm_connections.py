"""Add llm_connections table for user LLM provider setup.

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_connections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False, index=True),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False, server_default="16384"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false", index=True),
        sa.Column("label", sa.String(100), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("llm_connections")
