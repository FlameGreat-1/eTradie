"""Rename metadata to meta_data in RAG tables.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-22
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename 'metadata' to 'meta_data' in all RAG tables
    tables = [
        "rag_documents",
        "rag_document_versions",
        "rag_chunks",
        "rag_scenarios",
        "rag_ingest_jobs",
        "rag_retrieval_logs",
        "rag_reembed_queue",
    ]
    for table in tables:
        op.alter_column(table, "metadata", new_column_name="meta_data")


def downgrade() -> None:
    # Rename 'meta_data' back to 'metadata'
    tables = [
        "rag_documents",
        "rag_document_versions",
        "rag_chunks",
        "rag_scenarios",
        "rag_ingest_jobs",
        "rag_retrieval_logs",
        "rag_reembed_queue",
    ]
    for table in tables:
        op.alter_column(table, "meta_data", new_column_name="metadata")
