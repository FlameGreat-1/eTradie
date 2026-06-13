"""
Register retention pruning jobs on the scheduler.

Runs a single daily prune cycle at 03:00 UTC (off-peak hours)
when trading activity is at its lowest. The pruner handles all
TA and Macro tables in a single pass.

The cron schedule is configurable via environment variable:
    RETENTION_PRUNE_CRON="0 3 * * *"  (default: daily at 03:00 UTC)
"""
from __future__ import annotations

import os

from engine.shared.logging import get_logger
from engine.shared.retention.pruner import RetentionPruner
from engine.shared.scheduler import SchedulerManager

logger = get_logger(__name__)

# Default: daily at 03:00 UTC.
DEFAULT_PRUNE_CRON = "0 3 * * *"

# Timeout: 10 minutes. Pruning large tables may take a while.
PRUNE_JOB_TIMEOUT = 600


def register_retention_jobs(
    scheduler: SchedulerManager,
    pruner: RetentionPruner,
) -> None:
    """Register the data retention pruning job on the scheduler.

    Args:
        scheduler: The shared SchedulerManager instance.
        pruner: The RetentionPruner instance (backed by DatabaseManager).
    """
    cron_expr = os.environ.get("RETENTION_PRUNE_CRON", DEFAULT_PRUNE_CRON)

    async def _run_prune() -> None:
        """Async wrapper for the pruner — required by APScheduler."""
        await pruner.prune_all()

    scheduler.add_cron_job(
        _run_prune,
        job_id="retention_data_prune",
        cron_expression=cron_expr,
        timeout_seconds=PRUNE_JOB_TIMEOUT,
    )

    logger.info(
        "retention_scheduler_jobs_registered",
        extra={
            "cron_expression": cron_expr,
            "timeout_seconds": PRUNE_JOB_TIMEOUT,
        },
    )
