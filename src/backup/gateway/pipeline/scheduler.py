"""Gateway scheduler registration.

Registers the analysis cycle as a recurring scheduled job using
the existing SchedulerManager infrastructure.

The recurring job reads the user's active symbols from SymbolStore
on every cycle. This means:
- If the user selected EURUSD, every cycle analyses EURUSD.
- If the user hasn't selected anything, defaults are used.
- If the user changes to GBPJPY, the next cycle picks it up.

When a user triggers a cycle from the dashboard, they provide
their own symbols via run_cycle(symbols=[...]) and also update
the SymbolStore so scheduled runs use the same selection.
"""

from __future__ import annotations

from engine.shared.logging import get_logger
from engine.shared.scheduler import SchedulerManager
from gateway.config import GatewayConfig
from gateway.constants import GATEWAY_CYCLE_JOB_ID
from gateway.pipeline.orchestrator import PipelineOrchestrator
from gateway.symbol_store import SymbolStore

logger = get_logger(__name__)


def register_gateway_cycle(
    *,
    scheduler: SchedulerManager,
    orchestrator: PipelineOrchestrator,
    symbol_store: SymbolStore,
    config: GatewayConfig,
) -> None:
    """Register the gateway analysis cycle as a recurring job."""
    if not config.enabled:
        logger.info("gateway_disabled_skipping_scheduler_registration")
        return

    async def _run_cycle() -> None:
        """Recurring job wrapper.

        Reads the active symbols from SymbolStore on every invocation
        so that user changes take effect on the next scheduled cycle
        without requiring a restart.
        """
        symbols = await symbol_store.get_active_symbols()

        logger.info(
            "gateway_scheduled_cycle_starting",
            extra={"symbols": symbols},
        )

        await orchestrator.run_cycle(symbols=symbols)

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
