"""Gateway enums and constants.

All gateway-specific enumerations live here to avoid circular imports.
Every other gateway module imports from this file.
"""

from __future__ import annotations

from enum import StrEnum, unique
from typing import Final


@unique
class CyclePhase(StrEnum):
    """Discrete phases within a single analysis cycle."""

    INITIALIZING = "INITIALIZING"
    COLLECTING_TA = "COLLECTING_TA"
    COLLECTING_MACRO = "COLLECTING_MACRO"
    COLLECTING_PARALLEL = "COLLECTING_PARALLEL"
    BUILDING_QUERY = "BUILDING_QUERY"
    RETRIEVING_RAG = "RETRIEVING_RAG"
    ASSEMBLING_CONTEXT = "ASSEMBLING_CONTEXT"
    PROCESSING_LLM = "PROCESSING_LLM"
    EVALUATING_GUARDS = "EVALUATING_GUARDS"
    ROUTING_DECISION = "ROUTING_DECISION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@unique
class CycleStatus(StrEnum):
    """Overall status of an analysis cycle."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    SKIPPED = "SKIPPED"


@unique
class CycleOutcome(StrEnum):
    """Final outcome after the processor LLM has made its decision."""

    TRADE_APPROVED = "TRADE_APPROVED"
    NO_SETUP = "NO_SETUP"
    REJECTED_BY_GUARD = "REJECTED_BY_GUARD"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    PROCESSOR_ERROR = "PROCESSOR_ERROR"
    PIPELINE_ERROR = "PIPELINE_ERROR"


@unique
class PipelineStage(StrEnum):
    """Identifies which service produced an error or metric."""

    TA_COLLECTOR = "ta_collector"
    MACRO_COLLECTOR = "macro_collector"
    QUERY_BUILDER = "query_builder"
    RAG_RETRIEVAL = "rag_retrieval"
    CONTEXT_ASSEMBLY = "context_assembly"
    PROCESSOR_LLM = "processor_llm"
    GUARD_EVALUATION = "guard_evaluation"
    DECISION_ROUTING = "decision_routing"


@unique
class GuardVerdict(StrEnum):
    """Result of a single pre-execution guard check."""

    PASS = "PASS"
    REJECT = "REJECT"
    WARN = "WARN"


@unique
class GuardRule(StrEnum):
    """Identifiers for hard rejection rules evaluated after the processor."""

    SESSION_RESTRICTION = "MR-REJECT-002"
    NEWS_PROXIMITY = "MR-REJECT-001"
    DAILY_LOSS_LIMIT = "MR-REJECT-003"
    SPREAD_TOO_WIDE = "MR-REJECT-004"
    CORRELATION_LIMIT = "MR-REJECT-005"
    COUNTER_TREND_NO_CHOCH = "MR-REJECT-006"
    MAX_CONCURRENT_TRADES = "MR-REJECT-007"
    WEEKEND_GAP_RISK = "MR-REJECT-008"
    LOW_LIQUIDITY_HOURS = "MR-REJECT-009"
    DRAWDOWN_CIRCUIT_BREAKER = "MR-REJECT-010"


# Scheduler job identifiers
GATEWAY_CYCLE_JOB_ID: Final[str] = "gateway_analysis_cycle"
GATEWAY_HEALTH_JOB_ID: Final[str] = "gateway_health_check"

# Cache namespaces
GATEWAY_CACHE_NAMESPACE: Final[str] = "gateway"
TA_RESULT_CACHE_KEY_PREFIX: Final[str] = "ta_result"
MACRO_RESULT_CACHE_KEY_PREFIX: Final[str] = "macro_result"
