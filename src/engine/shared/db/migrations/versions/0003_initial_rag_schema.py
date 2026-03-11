"""Initial RAG schema.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-11
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("source_path", sa.String(1024), nullable=False),
        sa.Column("source_format", sa.String(32), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("checksum", sa.String(128), nullable=False),
        sa.Column("active_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("framework_tags", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("metadata", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rag_docs_doc_type", "rag_documents", ["doc_type"])
    op.create_index("ix_rag_docs_status", "rag_documents", ["status"])
    op.create_index("ix_rag_docs_doc_type_status", "rag_documents", ["doc_type", "status"])
    op.create_index("ix_rag_docs_source_path", "rag_documents", ["source_path"], unique=True)

    op.create_table(
        "rag_document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("checksum", sa.String(128), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("change_summary", sa.Text, nullable=False, server_default=""),
        sa.Column("metadata", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rag_docver_document_id", "rag_document_versions", ["document_id"])
    op.create_index("ix_rag_docver_doc_version", "rag_document_versions", ["document_id", "version_number"], unique=True)
    op.create_index("ix_rag_docver_status", "rag_document_versions", ["status"])

    op.create_table(
        "rag_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rag_document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column("embedding_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("section", sa.String(256), nullable=True),
        sa.Column("subsection", sa.String(256), nullable=True),
        sa.Column("parent_chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("hierarchy_level", sa.Integer, nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rag_chunks_document_id", "rag_chunks", ["document_id"])
    op.create_index("ix_rag_chunks_version_id", "rag_chunks", ["document_version_id"])
    op.create_index("ix_rag_chunks_doc_type", "rag_chunks", ["doc_type"])
    op.create_index("ix_rag_chunks_embedding_status", "rag_chunks", ["embedding_status"])
    op.create_index("ix_rag_chunks_content_hash", "rag_chunks", ["content_hash"])
    op.create_index("ix_rag_chunks_doc_version_index", "rag_chunks", ["document_version_id", "chunk_index"], unique=True)

    op.create_table(
        "rag_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("framework", sa.String(32), nullable=False),
        sa.Column("setup_family", sa.String(64), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("explanation_text", sa.Text, nullable=False),
        sa.Column("image_refs", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("confluence_tags", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("style_tags", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("linked_chunk_ids", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("metadata", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rag_scenarios_document_id", "rag_scenarios", ["document_id"])
    op.create_index("ix_rag_scenarios_framework", "rag_scenarios", ["framework"])
    op.create_index("ix_rag_scenarios_setup_family", "rag_scenarios", ["setup_family"])
    op.create_index("ix_rag_scenarios_direction", "rag_scenarios", ["direction"])
    op.create_index("ix_rag_scenarios_outcome", "rag_scenarios", ["outcome"])
    op.create_index("ix_rag_scenarios_is_active", "rag_scenarios", ["is_active"])
    op.create_index("ix_rag_scenarios_fw_setup_dir", "rag_scenarios", ["framework", "setup_family", "direction"])

    op.create_table(
        "rag_ingest_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rag_document_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("chunks_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("embeddings_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rag_ingest_document_id", "rag_ingest_jobs", ["document_id"])
    op.create_index("ix_rag_ingest_status", "rag_ingest_jobs", ["status"])
    op.create_index("ix_rag_ingest_created_at", "rag_ingest_jobs", ["created_at"])

    op.create_table(
        "rag_retrieval_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("strategy", sa.String(32), nullable=False),
        sa.Column("filters_applied", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("total_candidates", sa.Integer, nullable=False, server_default="0"),
        sa.Column("chunks_returned", sa.Integer, nullable=False, server_default="0"),
        sa.Column("score_threshold", sa.Float, nullable=False, server_default="0.25"),
        sa.Column("coverage_result", sa.String(20), nullable=False, server_default="insufficient"),
        sa.Column("conflict_result", sa.String(20), nullable=False, server_default="none_detected"),
        sa.Column("duration_ms", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("metadata", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rag_retlog_strategy", "rag_retrieval_logs", ["strategy"])
    op.create_index("ix_rag_retlog_coverage", "rag_retrieval_logs", ["coverage_result"])
    op.create_index("ix_rag_retlog_created_at", "rag_retrieval_logs", ["created_at"])
    op.create_index("ix_rag_retlog_trace_id", "rag_retrieval_logs", ["trace_id"])

    op.create_table(
        "rag_analysis_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("retrieval_log_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rag_retrieval_logs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rag_document_versions.id", ondelete="SET NULL"), nullable=False),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("section", sa.String(256), nullable=True),
        sa.Column("subsection", sa.String(256), nullable=True),
        sa.Column("rule_id", sa.String(64), nullable=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("relevance_score", sa.Float, nullable=False),
        sa.Column("excerpt", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rag_acit_retrieval_id", "rag_analysis_citations", ["retrieval_log_id"])
    op.create_index("ix_rag_acit_chunk_id", "rag_analysis_citations", ["chunk_id"])
    op.create_index("ix_rag_acit_document_id", "rag_analysis_citations", ["document_id"])
    op.create_index("ix_rag_acit_doc_type", "rag_analysis_citations", ["doc_type"])
    op.create_index("ix_rag_acit_created_at", "rag_analysis_citations", ["created_at"])

    op.create_table(
        "rag_reembed_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rag_document_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rag_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_rag_reembed_document_id", "rag_reembed_queue", ["document_id"])
    op.create_index("ix_rag_reembed_status", "rag_reembed_queue", ["status"])
    op.create_index("ix_rag_reembed_created_at", "rag_reembed_queue", ["created_at"])


def downgrade() -> None:
    op.drop_table("rag_reembed_queue")
    op.drop_table("rag_analysis_citations")
    op.drop_table("rag_retrieval_logs")
    op.drop_table("rag_ingest_jobs")
    op.drop_table("rag_scenarios")
    op.drop_table("rag_chunks")
    op.drop_table("rag_document_versions")
    op.drop_table("rag_documents")
