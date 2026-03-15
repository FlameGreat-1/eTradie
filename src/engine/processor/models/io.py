"""Processor input/output models and port interface.

CONTRACT SOURCE OF TRUTH: proto/processor/v1/processor.proto

These Pydantic models MUST match the proto definition field-for-field.
The Go gateway serializes to JSON matching the proto schema, and this
Python service deserializes from that JSON into these models.

To verify parity, run:
    python scripts/validate_processor_contract.py
    # or: make contract-check

If you add, remove, or rename a field here, you MUST also update:
  1. proto/processor/v1/processor.proto (the contract)
  2. src/gateway/internal/models/processor.go (Go side)
  3. Run `make proto-gen` to regenerate Go proto types
  4. Run `make contract-check` to verify Python parity
"""

from __future__ import annotations

import abc
from typing import Optional

from pydantic import Field

from engine.shared.models.base import FrozenModel


class ProcessorInput(FrozenModel):
    """Payload sent to the Processor LLM.

    Combines TA output, Macro output, and RAG-retrieved knowledge
    into a single structured context for the LLM to reason over.

    Proto: processor.v1.ProcessorInput
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

    Proto: processor.v1.ProcessorOutput
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
        trace_id: Optional[str] = None,
    ) -> ProcessorOutput:
        """Process the assembled context and return a trade decision."""
        ...
