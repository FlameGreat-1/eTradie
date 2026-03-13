"""Processor LLM interface (port).

The gateway depends on this abstract interface, NOT on a concrete
implementation. The actual Processor LLM will be implemented in
src/processor/ and injected into the gateway via the Container.

This follows the Dependency Inversion Principle: high-level gateway
module depends on an abstraction, not on low-level processor details.
"""

from __future__ import annotations

import abc
from typing import Optional

from gateway.context.models import ProcessorInput, ProcessorOutput


class ProcessorPort(abc.ABC):
    """Abstract interface for the Processor LLM.

    The gateway calls this to get a trade decision. The implementation
    will send the context to an LLM and parse the structured response.
    """

    @abc.abstractmethod
    async def process(
        self,
        context: ProcessorInput,
        *,
        trace_id: Optional[str] = None,
    ) -> ProcessorOutput:
        """Process the assembled context and return a trade decision.

        Args:
            context: Full TA + Macro + RAG context payload.
            trace_id: Distributed trace ID for correlation.

        Returns:
            ProcessorOutput with trade_valid, direction, confidence, etc.

        Raises:
            ProcessorError: On LLM call failure.
            ProcessorInsufficientDataError: On insufficient context.
        """
        ...
