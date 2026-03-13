"""Gateway scheduler registration.

Registers the analysis cycle as a recurring scheduled job using
the existing SchedulerManager infrastructure.

The recurring job uses TAConfig.default_symbols as the symbol list
since there is no active user session during scheduled runs.
When a user triggers a cycle from the dashboard, they provide
their own symbols via run_cycle(symbols=[...]).
"""

from __future__ import annotations

from engine.config import get_ta_config
from engine.shared.logging import get_logger
from engine.shared.scheduler import SchedulerManager
from gateway.config import GatewayConfig
from gateway.constants import GATEWAY_CYCLE_JOB_ID
from gateway.pipeline.orchestrator import PipelineOrchestrator

logger = get_logger(__name__)


def register_gateway_cycle(
    *,
    scheduler: SchedulerManager,
    orchestrator: PipelineOrchestrator,
    config: GatewayConfig,
) -> None:
    """Register the gateway analysis cycle as a recurring job."""
    if not config.enabled:
        logger.info("gateway_disabled_skipping_scheduler_registration")
        return

    ta_config = get_ta_config()
    scheduled_symbols = list(ta_config.default_symbols)

    async def _run_cycle() -> None:
        """Recurring job wrapper.

        Uses TAConfig.default_symbols because there is no active
        user session during scheduled runs. Dashboard-triggered
        cycles provide their own symbols directly.
        """
        await orchestrator.run_cycle(symbols=scheduled_symbols)

    scheduler.add_interval_job(
        _run_cycle,
        job_id=GATEWAY_CYCLE_JOB_ID,
        seconds=config.cycle_interval_seconds,
        timeout_seconds=config.cycle_timeout_seconds + 30,
    )

    logger.info(
        "gateway_cycle_registered",
        extra={
            "job_id": GATEWAY_CYCLE_JOB_ID,
            "interval_seconds": config.cycle_interval_seconds,
            "timeout_seconds": config.cycle_timeout_seconds,
            "scheduled_symbols": scheduled_symbols,
        },
    )
