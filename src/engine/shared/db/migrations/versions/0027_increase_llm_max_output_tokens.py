"""Increase LLM connection max_output_tokens default to 32768.

Revision ID: 0027
Revises: 0026
Create Date: 2026-05-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "llm_connections"


def upgrade() -> None:
    # Change column server_default
    op.alter_column(_TABLE, "max_output_tokens", server_default=sa.text("'32768'"))

    # Update existing connections that have 16384 to 32768
    op.execute(sa.text(f"UPDATE {_TABLE} SET max_output_tokens = 32768 WHERE max_output_tokens = 16384"))


def downgrade() -> None:
    op.alter_column(_TABLE, "max_output_tokens", server_default=sa.text("'16384'"))
    op.execute(sa.text(f"UPDATE {_TABLE} SET max_output_tokens = 16384 WHERE max_output_tokens = 32768"))
