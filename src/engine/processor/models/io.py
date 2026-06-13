"""Processor input/output models and port interface.

CONTRACT SOURCE OF TRUTH: proto/engine/v1/engine.proto

The engine.proto defines ProcessLLMRequest and ProcessLLMResponse which
are the authoritative contract between the Go gateway and this Python
processor service. These Pydantic models MUST match those proto messages
field-for-field.

The Go gateway serializes to JSON matching the proto schema, and this
Python service deserializes from that JSON into these models.

To verify parity, run:
    python scripts/validate_processor_contract.py
    # or: make contract-check

If you add, remove, or rename a field here, you MUST also update:
  1. proto/engine/v1/engine.proto (ProcessLLMResponse)
  2. src/gateway/internal/models/processor.go (Go side)
  3. Run `make proto-gen` to regenerate Go proto types
  4. Run `make contract-check` to verify Python parity
"""
from __future__ import annotations



import abc
from typing import Any, Optional

from pydantic import Field

from engine.shared.models.base import FrozenModel


class ProcessorInput(FrozenModel):
    """Payload sent to the Processor LLM.

    Combines TA output, Macro output, and RAG-retrieved knowledge
    into a single structured context for the LLM to reason over.

    Proto: engine.v1.ProcessLLMRequest (processor_input_json field)
    """

    symbol: str
    ta_analysis: dict[str, Any] = Field(default_factory=dict[str, Any])
    macro_analysis: dict[str, Any] = Field(default_factory=dict[str, Any])
    retrieved_knowledge: dict[str, Any] = Field(default_factory=dict[str, Any])
    metadata: dict[str, Any] = Field(default_factory=dict[str, Any])


class ProcessorOutput(FrozenModel):
    """Decision returned by the Processor LLM.

    The gateway does NOT decide trade validity; the processor does.
    Guards run AFTER the processor to enforce hard safety rules.
    When guards pass, this is forwarded to Module B for execution.

    Proto: engine.v1.ProcessLLMResponse
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
    raw_response: dict[str, Any] = Field(default_factory=dict[str, Any])

    # Execution-critical fields for Module B.
    # entry_price above is the midpoint (kept for backward compat with guards);
    # these provide the actual zone boundaries for limit order placement.
    entry_zone_low: Optional[float] = None
    entry_zone_high: Optional[float] = None

    # All three TP levels with position sizing percentages.
    # Module B needs these for partial close management.
    tp1_price: Optional[float] = None
    tp1_pct: int = 0
    tp2_price: Optional[float] = None
    tp2_pct: int = 0
    tp3_price: Optional[float] = None
    tp3_pct: int = 0

    # Context required by Module B's pre-execution validator.
    trading_style: Optional[str] = None
    session: Optional[str] = None
    rr_ratio: Optional[float] = None
    confluence_score: float = 0.0
    analysis_id: Optional[str] = None

    # Execution control overrides explicitly set by the AI processor.
    execution_mode: Optional[str] = None
    ltf_confirmed: bool = False
    setup_type: Optional[str] = None


class ProcessorPort(abc.ABC):
    """Abstract interface for the Processor LLM.

    The gateway calls this to get a trade decision. The implementation
    sends the context to an LLM and parses the structured response.
    """

    @abc.abstractmethod
    async def process(
        self,
        context: ProcessorInput,
        *,
        user_id: str,
        trace_id: Optional[str] = None,
    ) -> ProcessorOutput:
        """Process the assembled context and return a trade decision."""
        ...
