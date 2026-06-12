"""Add llm_connections table for user LLM provider setup.

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


from sqlalchemy import inspect

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    table_name = "llm_connections"

    # Check if table exists
    if table_name not in inspector.get_table_names():
        # Create full table
        op.create_table(
            table_name,
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("provider", sa.String(30), nullable=False),
            sa.Column("model_name", sa.String(100), nullable=False),
            sa.Column("api_key_encrypted", sa.Text(), nullable=False),
            sa.Column("base_url", sa.String(500), nullable=True),
            sa.Column("temperature", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column(
                "max_output_tokens",
                sa.Integer(),
                nullable=False,
                server_default="16384",
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("label", sa.String(100), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

        # Create indexes
        op.create_index("ix_llm_connections_provider", table_name, ["provider"])
        op.create_index("ix_llm_connections_is_active", table_name, ["is_active"])
    else:
        # Table exists - add missing columns
        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}

        # Add each missing column individually
        if "id" not in existing_columns:
            op.add_column(table_name, sa.Column("id", UUID(as_uuid=True), primary_key=True))

        if "provider" not in existing_columns:
            op.add_column(table_name, sa.Column("provider", sa.String(30), nullable=False))

        if "model_name" not in existing_columns:
            op.add_column(table_name, sa.Column("model_name", sa.String(100), nullable=False))

        if "api_key_encrypted" not in existing_columns:
            op.add_column(table_name, sa.Column("api_key_encrypted", sa.Text(), nullable=False))

        if "base_url" not in existing_columns:
            op.add_column(table_name, sa.Column("base_url", sa.String(500), nullable=True))

        if "temperature" not in existing_columns:
            op.add_column(
                table_name,
                sa.Column("temperature", sa.Float(), nullable=False, server_default="0.0"),
            )

        if "max_output_tokens" not in existing_columns:
            op.add_column(
                table_name,
                sa.Column(
                    "max_output_tokens",
                    sa.Integer(),
                    nullable=False,
                    server_default="16384",
                ),
            )

        if "is_active" not in existing_columns:
            op.add_column(
                table_name,
                sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
            )

        if "label" not in existing_columns:
            op.add_column(
                table_name,
                sa.Column("label", sa.String(100), nullable=False, server_default=""),
            )

        if "created_at" not in existing_columns:
            op.add_column(
                table_name,
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.func.now(),
                ),
            )

        if "updated_at" not in existing_columns:
            op.add_column(
                table_name,
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.func.now(),
                ),
            )

        # Add missing indexes
        existing_indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}

        if "ix_llm_connections_provider" not in existing_indexes:
            op.create_index("ix_llm_connections_provider", table_name, ["provider"])

        if "ix_llm_connections_is_active" not in existing_indexes:
            op.create_index("ix_llm_connections_is_active", table_name, ["is_active"])


def downgrade() -> None:
    op.drop_table("llm_connections")
