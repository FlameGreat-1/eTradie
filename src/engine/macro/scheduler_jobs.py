from __future__ import annotations

from engine.shared.logging import get_logger
from engine.shared.scheduler import SchedulerManager

logger = get_logger(__name__)


def register_macro_jobs(
    scheduler: SchedulerManager,
    *,
    cb_collector_fn: object,
    cot_collector_fn: object,
    economic_collector_fn: object,
    news_collector_fn: object,
    calendar_collector_fn: object,
    dxy_collector_fn: object,
    intermarket_collector_fn: object,
    sentiment_collector_fn: object,
    poll_cb: int = 600,
    poll_news: int = 900,
    poll_calendar: int = 1800,
    poll_cot: int = 604800,
    poll_dxy: int = 14400,
    poll_intermarket: int = 86400,
    poll_sentiment: int = 604800,
    poll_economic: int = 3600,
) -> None:
    """Register macro data collection jobs on the scheduler.

    Each collector function MUST accept a ``user_id: str`` parameter.
    The caller is responsible for wrapping the collector's ``.collect()``
    method with the appropriate user_id.  In multi-tenant mode, the
    Gateway scheduler issues per-user service tokens and calls the
    Python engine's ``/internal/macro/collect`` endpoint with the
    user's JWT, so the engine resolves user_id from the token.

    For the Python-side APScheduler jobs (background polling), the
    caller wraps each collector call with a closure that provides
    the user_id from the request context or service token.
    """
    scheduler.add_interval_job(
        cb_collector_fn,  # type: ignore[arg-type]
        job_id="collect_central_bank",
        seconds=poll_cb,
    )
    scheduler.add_interval_job(
        news_collector_fn,  # type: ignore[arg-type]
        job_id="collect_news",
        seconds=poll_news,
    )
    scheduler.add_interval_job(
        calendar_collector_fn,  # type: ignore[arg-type]
        job_id="collect_calendar",
        seconds=poll_calendar,
    )
    scheduler.add_interval_job(
        economic_collector_fn,  # type: ignore[arg-type]
        job_id="collect_economic_data",
        seconds=poll_economic,
    )
    scheduler.add_interval_job(
        dxy_collector_fn,  # type: ignore[arg-type]
        job_id="collect_dxy",
        seconds=poll_dxy,
    )
    scheduler.add_interval_job(
        intermarket_collector_fn,  # type: ignore[arg-type]
        job_id="collect_intermarket",
        seconds=poll_intermarket,
    )
    scheduler.add_interval_job(
        cot_collector_fn,  # type: ignore[arg-type]
        job_id="collect_cot",
        seconds=poll_cot,
    )
    scheduler.add_interval_job(
        sentiment_collector_fn,  # type: ignore[arg-type]
        job_id="collect_sentiment",
        seconds=poll_sentiment,
    )
    logger.info("macro_scheduler_jobs_registered")
