"""Gateway scheduler registration.

Registers the analysis cycle as a recurring scheduled job using
the existing SchedulerManager infrastructure.
"""

from __future__ import annotations

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

    async def _run_cycle() -> None:
        """Wrapper that the scheduler invokes."""
        await orchestrator.run_cycle()

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
        },
    )
