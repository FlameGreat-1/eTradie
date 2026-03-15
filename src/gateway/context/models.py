"""Gateway domain models.

Pure data containers that flow through the pipeline.
All models are frozen (immutable) to guarantee thread safety.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from engine.shared.models.base import FrozenModel, TimestampedModel
from gateway.constants import (
    CycleOutcome,
    CyclePhase,
    CycleStatus,
    GuardRule,
    GuardVerdict,
)


# -- TA output container -----------------------------------------------------


class TASymbolResult(FrozenModel):
    """TA analysis result for a single symbol.

    Contains the full multi-timeframe analysis output from the TA engine.
    The Gateway does NOT dictate which timeframes are analyzed -- the TA
    engine owns that decision via TAConfig.
    """

    symbol: str
    htf_timeframes: list[str] = Field(default_factory=list)
    ltf_timeframes: list[str] = Field(default_factory=list)
    status: str  # "success" | "insufficient_data" | "error"
    smc_candidates: list[dict] = Field(default_factory=list)
    snd_candidates: list[dict] = Field(default_factory=list)
    snapshots: dict[str, dict] = Field(default_factory=dict)
    alignment: dict[str, dict] = Field(default_factory=dict)
    overall_trend: str = "NEUTRAL"
    error: Optional[str] = None


class TAResult(FrozenModel):
    """Aggregated TA output across all configured symbols."""

    symbol_results: list[TASymbolResult] = Field(default_factory=list)
    collected_at: datetime
    duration_ms: float = 0.0

    @property
    def has_candidates(self) -> bool:
        return any(
            r.smc_candidates or r.snd_candidates
            for r in self.symbol_results
            if r.status == "success"
        )

    @property
    def successful_symbols(self) -> list[str]:
        return [r.symbol for r in self.symbol_results if r.status == "success"]


# -- Macro output container --------------------------------------------------


class MacroResult(FrozenModel):
    """Aggregated macro output from all 8 collectors."""

    central_bank: Optional[dict] = None
    cot: Optional[dict] = None
    economic: Optional[dict] = None
    news: Optional[dict] = None
    calendar: Optional[dict] = None
    dxy: Optional[dict] = None
    intermarket: Optional[dict] = None
    sentiment: Optional[dict] = None
    collected_at: datetime
    duration_ms: float = 0.0
    errors: dict[str, str] = Field(default_factory=dict)

    @property
    def available_datasets(self) -> list[str]:
        names = []
        for name in (
            "central_bank", "cot", "economic", "news",
            "calendar", "dxy", "intermarket", "sentiment",
        ):
            if getattr(self, name) is not None:
                names.append(name)
        return names


# -- Processor I/O -----------------------------------------------------------


class ProcessorInput(FrozenModel):
    """Payload sent to the Processor LLM.

    Combines TA output, Macro output, and RAG-retrieved knowledge
    into a single structured context for the LLM to reason over.
    """

    symbol: str
    ta_analysis: dict = Field(default_factory=dict)
    macro_analysis: dict = Field(default_factory=dict)
    retrieved_knowledge: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class ProcessorOutput(FrozenModel):
    """Decision returned by the Processor LLM.

    The gateway does NOT decide trade validity; the processor does.
    Guards run AFTER the processor to enforce hard safety rules.
    """

    trade_valid: bool = False
    direction: Optional[str] = None
    symbol: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    grade: Optional[str] = None
    risk_percentage: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    reasoning: str = ""
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    rejection_rules: list[str] = Field(default_factory=list)
    raw_response: dict = Field(default_factory=dict)


# -- Guard evaluation --------------------------------------------------------


class GuardCheckResult(FrozenModel):
    """Result of a single guard rule evaluation."""

    rule: GuardRule
    verdict: GuardVerdict
    reason: str = ""
    metadata: dict = Field(default_factory=dict)


class GuardEvaluationResult(FrozenModel):
    """Aggregated result of all guard checks."""

    checks: list[GuardCheckResult] = Field(default_factory=list)
    overall_verdict: GuardVerdict = GuardVerdict.PASS
    blocking_rules: list[str] = Field(default_factory=list)

    @property
    def is_approved(self) -> bool:
        return self.overall_verdict == GuardVerdict.PASS


# -- Final gateway output ----------------------------------------------------


class GatewayOutput(TimestampedModel):
    """Complete output of a single analysis cycle."""

    cycle_status: CycleStatus
    cycle_outcome: CycleOutcome
    phase_reached: CyclePhase
    symbol: Optional[str] = None
    processor_output: Optional[ProcessorOutput] = None
    guard_result: Optional[GuardEvaluationResult] = None
    duration_ms: float = 0.0
    trace_id: Optional[str] = None
    error: Optional[str] = None
    error_stage: Optional[str] = None


# -- Cycle state tracking ----------------------------------------------------


class CycleState(FrozenModel):
    """Tracks the current state of an analysis cycle.

    Used internally by the orchestrator to know exactly where
    a cycle is at any moment for observability and debugging.
    """

    cycle_id: str
    trace_id: str
    status: CycleStatus = CycleStatus.RUNNING
    phase: CyclePhase = CyclePhase.INITIALIZING
    outcome: Optional[CycleOutcome] = None
    started_at: datetime
    phase_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    error_stage: Optional[str] = None
    phase_durations_ms: dict[str, float] = Field(default_factory=dict)
