"""Initial processor schema.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-14
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_outputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("analysis_id", sa.String(128), nullable=False, unique=True),
        sa.Column("pair", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("setup_grade", sa.String(10), nullable=False),
        sa.Column("confluence_score", sa.Float, nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("proceed_to_module_b", sa.String(5), nullable=False),
        sa.Column("rr_ratio", sa.Float, nullable=True),
        sa.Column("entry_price_low", sa.Float, nullable=True),
        sa.Column("entry_price_high", sa.Float, nullable=True),
        sa.Column("stop_loss_price", sa.Float, nullable=True),
        sa.Column("tp1_price", sa.Float, nullable=True),
        sa.Column("tp2_price", sa.Float, nullable=True),
        sa.Column("tp3_price", sa.Float, nullable=True),
        sa.Column("trading_style", sa.String(20), nullable=False, server_default=""),
        sa.Column("session", sa.String(30), nullable=False, server_default=""),
        sa.Column("status", sa.String(30), nullable=False, server_default="success"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("raw_output", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ao_analysis_id", "analysis_outputs", ["analysis_id"], unique=True)
    op.create_index("ix_ao_pair", "analysis_outputs", ["pair"])
    op.create_index("ix_ao_direction", "analysis_outputs", ["direction"])
    op.create_index("ix_ao_setup_grade", "analysis_outputs", ["setup_grade"])
    op.create_index("ix_ao_status", "analysis_outputs", ["status"])
    op.create_index("ix_ao_trace_id", "analysis_outputs", ["trace_id"])
    op.create_index("ix_ao_created_at", "analysis_outputs", ["created_at"])
    op.create_index("ix_ao_pair_created_at", "analysis_outputs", ["pair", "created_at"])

    op.create_table(
        "analysis_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("analysis_id", sa.String(128), nullable=False),
        sa.Column("pair", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retrieval_query_summary", sa.Text, nullable=False, server_default=""),
        sa.Column("retrieval_strategy", sa.String(32), nullable=True),
        sa.Column("retrieval_chunks_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("retrieval_coverage", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("retrieval_coverage_details", sa.Text, nullable=False, server_default=""),
        sa.Column("retrieval_conflicts", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("retrieval_conflict_details", sa.Text, nullable=False, server_default=""),
        sa.Column("llm_model", sa.String(64), nullable=False, server_default=""),
        sa.Column("llm_prompt_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("llm_input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("llm_output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("llm_duration_ms", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("llm_response", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("citations", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("final_direction", sa.String(20), nullable=False, server_default=""),
        sa.Column("final_grade", sa.String(10), nullable=False, server_default=""),
        sa.Column("final_confidence", sa.String(20), nullable=False, server_default=""),
        sa.Column("final_proceed", sa.String(5), nullable=False, server_default=""),
        sa.Column("validation_passed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("validation_errors", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_aal_analysis_id", "analysis_audit_logs", ["analysis_id"])
    op.create_index("ix_aal_pair", "analysis_audit_logs", ["pair"])
    op.create_index("ix_aal_trace_id", "analysis_audit_logs", ["trace_id"])
    op.create_index("ix_aal_created_at", "analysis_audit_logs", ["created_at"])
    op.create_index("ix_aal_llm_model", "analysis_audit_logs", ["llm_model"])


def downgrade() -> None:
    op.drop_table("analysis_audit_logs")
    op.drop_table("analysis_outputs")
