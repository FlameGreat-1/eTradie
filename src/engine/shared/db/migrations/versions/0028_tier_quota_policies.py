"""Tier-based LLM quota policy table.

Replaces the in-memory env-only knobs at
src/auth/config.go::Config.LLMQuotaPolicyForTier with a runtime-mutable
row per tier. Admins edit the rows via the dashboard; the gateway
metering handler reads the row on every Reserve call (with a 30 s
cache).

Audit ref: ADMIN-QUOTA-1.

Revision ID: 0028_tier_quota_policies
Revises: 0027_increase_llm_max_output_tokens
Created:  2026-05-28
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Alembic identifiers.
revision = "0028_tier_quota_policies"
down_revision = "0027_increase_llm_max_output_tokens"
branch_labels = None
depends_on = None


# Canonical seed values. These MUST match the env-default numbers in
# src/auth/config.go at the time of this migration so an upgrade from
# the previous release is byte-identical in behaviour. If the env
# defaults change in a later release, write a new migration that
# UPDATEs these rows; do NOT change the seed below (the seed records
# what was true at this point in history).
_SEED_ROWS = [
    # Pro Managed: paying tier on platform LLM key.
    dict(
        tier="pro_managed",
        daily_input_tokens=2_000_000,
        daily_output_tokens=200_000,
        monthly_input_tokens=20_000_000,
        monthly_output_tokens=2_000_000,
        max_input_tokens_per_call=300_000,
        soft_cap_percent=80,
        reservation_ttl_seconds=300,
        allowed_models=[],
        enforced=True,
    ),
    # Admin: shares the pro_managed envelope. Confirmed with product:
    # admins consume the platform key by default; capping them on the
    # same numbers keeps the operational ceiling visible and editable
    # from the same panel.
    dict(
        tier="admin",
        daily_input_tokens=2_000_000,
        daily_output_tokens=200_000,
        monthly_input_tokens=20_000_000,
        monthly_output_tokens=2_000_000,
        max_input_tokens_per_call=300_000,
        soft_cap_percent=80,
        reservation_ttl_seconds=300,
        allowed_models=[],
        enforced=True,
    ),
    # Pro BYOK: user supplies their own provider key. The platform
    # never debits a reservation for them; all caps zero so the
    # metering pre-flight returns tier_not_eligible if a Reserve ever
    # reaches the handler (defense-in-depth; in normal flow the
    # engine's uses_platform_key gate already short-circuits this).
    dict(
        tier="pro_byok",
        daily_input_tokens=0,
        daily_output_tokens=0,
        monthly_input_tokens=0,
        monthly_output_tokens=0,
        max_input_tokens_per_call=0,
        soft_cap_percent=0,
        reservation_ttl_seconds=300,
        allowed_models=[],
        enforced=False,
    ),
    # Free: same posture as pro_byok. Free users also BYOK on a
    # restricted feature set.
    dict(
        tier="free",
        daily_input_tokens=0,
        daily_output_tokens=0,
        monthly_input_tokens=0,
        monthly_output_tokens=0,
        max_input_tokens_per_call=0,
        soft_cap_percent=0,
        reservation_ttl_seconds=300,
        allowed_models=[],
        enforced=False,
    ),
]


def upgrade() -> None:
    op.create_table(
        "tier_quota_policies",
        sa.Column(
            "tier",
            sa.String(length=32),
            primary_key=True,
            nullable=False,
            comment="Tier identifier; one of free, pro_byok, pro_managed, admin",
        ),
        sa.Column(
            "daily_input_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Hard cap on input tokens (estimated) per UTC day",
        ),
        sa.Column(
            "daily_output_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Hard cap on output tokens (max_output_tokens reservation) per UTC day",
        ),
        sa.Column(
            "monthly_input_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Hard cap on input tokens per monthly billing window",
        ),
        sa.Column(
            "monthly_output_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Hard cap on output tokens per monthly billing window",
        ),
        sa.Column(
            "max_input_tokens_per_call",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Hard ceiling on a single Reserve's estimated input token count",
        ),
        sa.Column(
            "soft_cap_percent",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("0"),
            comment="0..100; threshold (%) at which the soft-cap warning email fires",
        ),
        sa.Column(
            "reservation_ttl_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("300"),
            comment="Wall-clock window inside which Commit or Refund must arrive",
        ),
        sa.Column(
            "allowed_models",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="Lowercase model allow-list; empty array means any model permitted",
        ),
        sa.Column(
            "enforced",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="True only when the tier consumes the platform LLM key (pro_managed, admin)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_by",
            sa.String(length=32),
            nullable=True,
            comment="auth_users.id of the admin who last edited the row; NULL for the initial seed",
        ),
        sa.CheckConstraint(
            "tier IN ('free', 'pro_byok', 'pro_managed', 'admin')",
            name="tier_quota_policies_tier_check",
        ),
        sa.CheckConstraint(
            "soft_cap_percent BETWEEN 0 AND 100",
            name="tier_quota_policies_soft_cap_range_check",
        ),
        sa.CheckConstraint(
            "daily_input_tokens >= 0",
            name="tier_quota_policies_daily_input_nonneg",
        ),
        sa.CheckConstraint(
            "daily_output_tokens >= 0",
            name="tier_quota_policies_daily_output_nonneg",
        ),
        sa.CheckConstraint(
            "monthly_input_tokens >= 0",
            name="tier_quota_policies_monthly_input_nonneg",
        ),
        sa.CheckConstraint(
            "monthly_output_tokens >= 0",
            name="tier_quota_policies_monthly_output_nonneg",
        ),
        sa.CheckConstraint(
            "max_input_tokens_per_call >= 0",
            name="tier_quota_policies_max_per_call_nonneg",
        ),
        sa.CheckConstraint(
            "reservation_ttl_seconds BETWEEN 30 AND 3600",
            name="tier_quota_policies_ttl_range_check",
        ),
    )

    # Foreign-key updated_by -> auth_users(id) is added separately so
    # the constraint name is stable and the table create above stays
    # readable. Use ON DELETE SET NULL so a deleted admin does not
    # cascade-delete the policy row; the historical edit attribution
    # is preserved as NULL.
    op.create_foreign_key(
        constraint_name="tier_quota_policies_updated_by_fkey",
        source_table="tier_quota_policies",
        referent_table="auth_users",
        local_cols=["updated_by"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )

    # Bulk insert the seed rows. bulk_insert keeps the migration
    # deterministic across SQLAlchemy versions and avoids triggering
    # the model layer (which is not yet importable at migration time).
    bind = op.get_bind()
    metadata = sa.MetaData()
    metadata.reflect(bind=bind, only=["tier_quota_policies"])
    table = metadata.tables["tier_quota_policies"]
    op.bulk_insert(
        table,
        [
            {
                **row,
                # JSONB column wants a JSON string at the SQLAlchemy
                # Core layer; the bind converts it back to JSONB on
                # the server. Use sa.text-style cast to keep this
                # portable to non-Postgres test backends.
                "allowed_models": sa.text("'[]'::jsonb")
                if not row["allowed_models"]
                else None,
            }
            for row in _SEED_ROWS
        ],
    )


def downgrade() -> None:
    op.drop_constraint(
        "tier_quota_policies_updated_by_fkey",
        "tier_quota_policies",
        type_="foreignkey",
    )
    op.drop_table("tier_quota_policies")
