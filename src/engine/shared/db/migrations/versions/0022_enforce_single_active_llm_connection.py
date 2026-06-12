"""enforce_single_active_llm_connection

Revision ID: 0022
Revises: 0021
Create Date: 2026-05-24 00:00:00.000000

Adds DB-level uniqueness for the "one active LLM connection per scope"
invariant the application has always claimed but never enforced. Heals
any pre-existing duplicate-active rows on the way up so the upgrade is
safe on corrupted installs.

Scope semantics:
  * Personal: (user_id, is_platform = false) -> at most one is_active
    row per user.
  * Platform: (is_platform = true)           -> at most one is_active
    row globally (singleton).

The two scopes are mutually exclusive (a personal row has
is_platform = false; the platform row has is_platform = true and
user_id = NULL) so they get separate partial unique indexes that
cannot interact.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


PERSONAL_INDEX = "uq_llm_connections_one_active_personal_per_user"
PLATFORM_INDEX = "uq_llm_connections_one_active_platform"


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Heal pre-existing duplicate-active rows.
    #
    #    Personal scope: per (user_id, is_platform=false) group, keep the
    #    most recently updated row active, deactivate the rest. Tie-break
    #    on id so the choice is deterministic when two rows share an
    #    updated_at timestamp (rare but possible after server-side
    #    upserts).
    #
    #    Platform scope: at most one row should have is_platform = true.
    #    Same logic without the user_id partition.
    # ------------------------------------------------------------------
    op.execute("""
        WITH ranked AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY user_id
                    ORDER BY updated_at DESC, id ASC
                ) AS rn
            FROM llm_connections
            WHERE is_active = true
              AND is_platform = false
              AND user_id IS NOT NULL
        )
        UPDATE llm_connections
           SET is_active = false,
               updated_at = NOW()
         WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
        """)

    op.execute("""
        WITH ranked AS (
            SELECT
                id,
                row_number() OVER (
                    ORDER BY updated_at DESC, id ASC
                ) AS rn
            FROM llm_connections
            WHERE is_active = true
              AND is_platform = true
        )
        UPDATE llm_connections
           SET is_active = false,
               updated_at = NOW()
         WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
        """)

    # ------------------------------------------------------------------
    # 2. Personal-scope partial unique index.
    #
    #    UNIQUE (user_id) WHERE is_active = true AND is_platform = false
    #
    #    Allows many inactive rows per user and prevents a second
    #    is_active row from being inserted or activated for the same
    #    user. Concurrent transactions racing through the
    #    `_deactivate_all -> insert/update` sequence will have one of
    #    them fail with a unique-violation that the caller can retry,
    #    instead of silently corrupting the table.
    # ------------------------------------------------------------------
    op.create_index(
        PERSONAL_INDEX,
        "llm_connections",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true AND is_platform = false"),
    )

    # ------------------------------------------------------------------
    # 3. Platform-scope partial unique index.
    #
    #    UNIQUE (is_platform) WHERE is_active = true AND is_platform = true
    #
    #    Indexing the constant `true` produces a single-row uniqueness
    #    constraint: at most one active platform connection globally.
    # ------------------------------------------------------------------
    op.create_index(
        PLATFORM_INDEX,
        "llm_connections",
        ["is_platform"],
        unique=True,
        postgresql_where=sa.text("is_active = true AND is_platform = true"),
    )


def downgrade() -> None:
    op.drop_index(PLATFORM_INDEX, table_name="llm_connections")
    op.drop_index(PERSONAL_INDEX, table_name="llm_connections")
