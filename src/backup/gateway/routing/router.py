"""Post-processor decision router.

Routes the Processor LLM output through guards, then to Module B
(execution) if approved, or logs NO SETUP.

The router does NOT make trade decisions - it enforces the pipeline:
  Processor decides -> Guards validate -> Router routes.
"""

from __future__ import annotations

from typing import Any, Optional

from engine.shared.logging import get_logger
from gateway.constants import CycleOutcome, GuardVerdict
from gateway.context.models import (
    GatewayOutput,
    GuardEvaluationResult,
    MacroResult,
    ProcessorOutput,
    TASymbolResult,
)
from gateway.observability.metrics import (
    GATEWAY_NO_SETUP_TOTAL,
    GATEWAY_TRADE_ROUTED,
)
from gateway.routing.execution_port import ExecutionPort
from gateway.routing.guards import GuardEvaluator

logger = get_logger(__name__)


class DecisionRouter:
    """Routes processor decisions through guards to execution."""

    def __init__(
        self,
        *,
        guard_evaluator: GuardEvaluator,
        execution_port: Optional[ExecutionPort] = None,
    ) -> None:
        self._guards = guard_evaluator
        self._execution = execution_port

    async def route(
        self,
        *,
        processor_output: ProcessorOutput,
        ta_result: TASymbolResult,
        macro_result: MacroResult,
        trace_id: Optional[str] = None,
    ) -> tuple[CycleOutcome, Optional[GuardEvaluationResult], Optional[dict[str, Any]]]:
        """Route the processor decision through guards to execution.

        Returns:
            Tuple of (outcome, guard_result, execution_result).
        """
        # Step 1: If processor says NO SETUP, respect it
        if not processor_output.trade_valid:
            reason = processor_output.reasoning or "Processor determined no valid setup"
            GATEWAY_NO_SETUP_TOTAL.labels(reason="processor_no_setup").inc()

            logger.info(
                "route_no_setup",
                extra={
                    "symbol": processor_output.symbol,
                    "reason": reason,
                    "rejection_rules": processor_output.rejection_rules,
                    "trace_id": trace_id,
                },
            )

            return CycleOutcome.NO_SETUP, None, None

        # Step 2: Run post-processor guards
        guard_result = self._guards.evaluate(
            processor_output=processor_output,
            ta_result=ta_result,
            macro_result=macro_result,
            trace_id=trace_id,
        )

        # Step 3: If guards reject, block execution
        if guard_result.overall_verdict == GuardVerdict.REJECT:
            GATEWAY_NO_SETUP_TOTAL.labels(reason="guard_rejection").inc()

            logger.warning(
                "route_guard_rejected",
                extra={
                    "symbol": processor_output.symbol,
                    "blocking_rules": guard_result.blocking_rules,
                    "trace_id": trace_id,
                },
            )

            return CycleOutcome.REJECTED_BY_GUARD, guard_result, None

        # Step 4: Route to execution engine (Module B)
        execution_result = await self._execute_trade(
            processor_output, trace_id=trace_id,
        )

        GATEWAY_TRADE_ROUTED.labels(
            symbol=processor_output.symbol or "unknown",
            direction=processor_output.direction or "unknown",
        ).inc()

        logger.info(
            "route_trade_approved",
            extra={
                "symbol": processor_output.symbol,
                "direction": processor_output.direction,
                "confidence": processor_output.confidence,
                "grade": processor_output.grade,
                "guard_verdict": guard_result.overall_verdict.value,
                "trace_id": trace_id,
            },
        )

        return CycleOutcome.TRADE_APPROVED, guard_result, execution_result

    async def _execute_trade(
        self,
        decision: ProcessorOutput,
        *,
        trace_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Forward to execution engine if available."""
        if self._execution is None:
            logger.info(
                "execution_engine_not_available",
                extra={
                    "symbol": decision.symbol,
                    "direction": decision.direction,
                    "trace_id": trace_id,
                },
            )
            return {"status": "pending", "reason": "execution_engine_not_implemented"}

        return await self._execution.execute(decision, trace_id=trace_id)
