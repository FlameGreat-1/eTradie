"""Audit trail models for processor persistence.

These models represent the rows written to Postgres for every
processor invocation, as required by LLM.md Section 9.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from engine.shared.models.base import FrozenModel, TimestampedModel


class AnalysisRecord(TimestampedModel):
    """Persisted analysis output record.

    Written to analysis_outputs table on every processor invocation.
    """

    analysis_id: str
    pair: str
    direction: str
    setup_grade: str
    confluence_score: float
    confidence: str
    proceed_to_module_b: str
    rr_ratio: Optional[float] = None
    entry_price_low: Optional[float] = None
    entry_price_high: Optional[float] = None
    stop_loss_price: Optional[float] = None
    tp1_price: Optional[float] = None
    tp2_price: Optional[float] = None
    tp3_price: Optional[float] = None
    trading_style: str = ""
    session: str = ""
    status: str = "success"
    error_message: Optional[str] = None
    duration_ms: float = 0.0
    trace_id: Optional[str] = None
    raw_output: dict = Field(default_factory=dict)


class AuditLogRecord(TimestampedModel):
    """Persisted audit trail record.

    Written to analysis_audit_logs table alongside every AnalysisRecord.
    Contains retrieval context, citations, and verification results.
    """

    analysis_id: str
    pair: str
    timestamp: datetime

    # Retrieval context
    retrieval_query_summary: str = ""
    retrieval_strategy: Optional[str] = None
    retrieval_chunks_count: int = 0
    retrieval_coverage: bool = False
    retrieval_coverage_details: str = ""
    retrieval_conflicts: bool = False
    retrieval_conflict_details: str = ""

    # LLM call reference
    llm_model: str = ""
    llm_prompt_hash: str = ""
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    llm_duration_ms: float = 0.0

    # Response
    llm_response: dict = Field(default_factory=dict)

    # Citations
    citations: list[dict] = Field(default_factory=list)

    # Final decision
    final_direction: str = ""
    final_grade: str = ""
    final_confidence: str = ""
    final_proceed: str = ""

    # Post-LLM validation
    validation_passed: bool = False
    validation_errors: list[str] = Field(default_factory=list)

    trace_id: Optional[str] = None
