"""Execution Engine interface (port) - Module B.

The gateway depends on this abstract interface. The actual execution
engine will be implemented in src/execution/ and injected via Container.
"""

from __future__ import annotations

import abc
from typing import Any, Optional

from gateway.context.models import ProcessorOutput


class ExecutionPort(abc.ABC):
    """Abstract interface for the Execution Engine (Module B)."""

    @abc.abstractmethod
    async def execute(
        self,
        decision: ProcessorOutput,
        *,
        trace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute a trade based on the processor's decision.

        Args:
            decision: Validated processor output with trade parameters.
            trace_id: Distributed trace ID for correlation.

        Returns:
            Execution result dict with order details.
        """
        ...
