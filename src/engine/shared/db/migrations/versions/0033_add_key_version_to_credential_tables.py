"""Add key_version to broker_connections and llm_connections.

The engine encrypts user credentials at rest with versioned envelope
encryption (engine.shared.crypto). Each new ciphertext is wrapped by a
Data Encryption Key (DEK) which is itself wrapped by a versioned Key
Encryption Key (KEK). This column records the KEK version that wrapped
the row's CURRENT ciphertext so that:

  - key rotation is observable (operators can see how many rows are
    still on an older KEK version), and
  - the re-wrap maintenance routine can cheaply select rows whose
    key_version != the active KEK version.

Nullable, no server_default, on purpose:
  - Pre-existing rows hold LEGACY (pre-envelope) bare-Fernet ciphertext
    that has no versioned wrap. NULL means "legacy / unknown version".
  - The shared cipher decrypts legacy ciphertext regardless of this
    column, so key_version is NEVER load-bearing for decryption -- it
    is purely operational metadata. New encrypts stamp the active
    version going forward.

Applies to both credential tables so broker MT5 passwords / EA tokens
and LLM API keys share the same rotation tooling.

Revision ID: 0033
Revises: 0032
Create Date: 2026-06-05
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMN = "key_version"
_TABLES = ("broker_connections", "llm_connections")


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    table_names = set(insp.get_table_names())
    for table in _TABLES:
        if table not in table_names:
            continue
        existing = {c["name"] for c in insp.get_columns(table)}
        if _COLUMN in existing:
            continue
        op.add_column(
            table,
            sa.Column(_COLUMN, sa.SmallInteger(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    table_names = set(insp.get_table_names())
    for table in _TABLES:
        if table not in table_names:
            continue
        existing = {c["name"] for c in insp.get_columns(table)}
        if _COLUMN not in existing:
            continue
        op.drop_column(table, _COLUMN)
