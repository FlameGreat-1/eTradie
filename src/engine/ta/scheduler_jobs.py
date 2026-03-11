"""
TA scheduler job definitions.

Registers all TA-related periodic jobs with the shared SchedulerManager:
- Candle refresh  – real-time latest candle ingestion per symbol/timeframe
- Analysis trigger – runs full SMC/SnD detection pipeline
- Backfill         – fills historical candle gaps on startup or on-demand
- Broker sync      – periodic reconciliation of stored vs broker data

All jobs use ``engine.shared.scheduler.SchedulerManager`` and share the
same lifecycle: config-driven registration via ``register_ta_jobs()``.
"""

from __future__ import annotations

import asyncio
import functools
from datetime import datetime, timedelta, UTC
from typing import Any, Callable, Coroutine, Optional

from engine.shared.logging import get_logger
from engine.shared.scheduler import SchedulerManager
from engine.ta.broker.base import BrokerBase
from engine.config import TAConfig
from engine.ta.constants import Timeframe, TIMEFRAME_MINUTES
from engine.ta.orchestrator import TAOrchestrator
from engine.ta.storage.repositories.candle import CandleRepository

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Retry decorator (lifecycle hook: automatic retry with backoff)
# ---------------------------------------------------------------------------

def with_retry(
    max_retries: int = 3,
    backoff_base: float = 2.0,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator that adds retry logic with exponential backoff to async jobs.

    Args:
        max_retries: Maximum number of retry attempts.
        backoff_base: Base for exponential backoff (seconds).
        retry_exceptions: Tuple of exception types that trigger a retry.
    """
    def decorator(
        func: Callable[..., Coroutine[Any, Any, Any]],
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Optional[Exception] = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        wait = backoff_base ** attempt
                        logger.warning(
                            "job_retry_scheduled",
                            extra={
                                "job": func.__name__,
                                "attempt": attempt,
                                "max_retries": max_retries,
                                "backoff_seconds": wait,
                                "error": str(exc),
                            },
                        )
                        await asyncio.sleep(wait)
                    else:
                        logger.error(
                            "job_retries_exhausted",
                            extra={
                                "job": func.__name__,
                                "attempts": max_retries,
                                "error": str(exc),
                            },
                            exc_info=True,
                        )
            raise last_exc  # type: ignore[misc]

        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Job functions
# ---------------------------------------------------------------------------

@with_retry(max_retries=3)
async def _candle_refresh(
    symbol: str,
    timeframe: Timeframe,
    broker_client: BrokerBase,
    candle_repository: CandleRepository,
) -> None:
    """Fetch the latest candle from broker and persist if new."""
    latest = await broker_client.fetch_latest_candle(symbol, timeframe)

    if not latest:
        logger.warning(
            "candle_refresh_no_data",
            extra={"symbol": symbol, "timeframe": timeframe.value},
        )
        return

    existing = await candle_repository.find_by_symbol_timeframe_timestamp(
        symbol, timeframe.value, latest.timestamp,
    )

    if existing:
        return

    await candle_repository.create(latest)

    logger.info(
        "candle_refreshed",
        extra={
            "symbol": symbol,
            "timeframe": timeframe.value,
            "timestamp": latest.timestamp.isoformat(),
        },
    )


@with_retry(max_retries=3)
async def _analysis_trigger(
    symbol: str,
    htf_timeframe: Timeframe,
    ltf_timeframe: Timeframe,
    orchestrator: TAOrchestrator,
) -> None:
    """Trigger full TA analysis for a symbol/timeframe pair."""
    result = await orchestrator.analyze(
        symbol, htf_timeframe, ltf_timeframe,
    )

    logger.info(
        "analysis_triggered",
        extra={
            "symbol": symbol,
            "htf": htf_timeframe.value,
            "ltf": ltf_timeframe.value,
            "status": result.get("status", "unknown"),
        },
    )


@with_retry(max_retries=2)
async def _backfill(
    symbol: str,
    timeframe: Timeframe,
    lookback_periods: int,
    broker_client: BrokerBase,
    candle_repository: CandleRepository,
) -> None:
    """
    Back-fill historical candle data for a symbol/timeframe.

    Identifies gaps between the earliest stored candle and the requested
    lookback window, then fetches the missing candles from the broker
    and persists them.
    """
    end_time = datetime.now(UTC)
    minutes = TIMEFRAME_MINUTES[timeframe] * lookback_periods
    start_time = end_time - timedelta(minutes=minutes)

    stored = await candle_repository.find_by_time_range(
        symbol, timeframe.value, start_time, end_time,
    )
    stored_count = len(stored) if stored else 0

    if stored_count >= lookback_periods * 0.9:
        logger.debug(
            "backfill_not_needed",
            extra={
                "symbol": symbol,
                "timeframe": timeframe.value,
                "stored": stored_count,
                "required": lookback_periods,
            },
        )
        return

    sequence = await broker_client.fetch_candles(
        symbol=symbol,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
        count=lookback_periods,
    )

    if not sequence or sequence.count == 0:
        logger.warning(
            "backfill_no_broker_data",
            extra={"symbol": symbol, "timeframe": timeframe.value},
        )
        return

    stored_timestamps = {c.timestamp for c in stored} if stored else set()
    new_candles = [
        c for c in sequence.candles if c.timestamp not in stored_timestamps
    ]

    if new_candles:
        await candle_repository.bulk_create(new_candles)

    logger.info(
        "backfill_completed",
        extra={
            "symbol": symbol,
            "timeframe": timeframe.value,
            "candles_added": len(new_candles),
            "total_fetched": sequence.count,
            "previously_stored": stored_count,
        },
    )


@with_retry(max_retries=3)
async def _broker_sync(
    symbol: str,
    timeframe: Timeframe,
    sync_periods: int,
    broker_client: BrokerBase,
    candle_repository: CandleRepository,
) -> None:
    """
    Reconcile recent stored candles with broker data.

    Fetches the last ``sync_periods`` candles from the broker and inserts
    any that are missing from storage.  This catches dropped websocket
    updates, partial writes, or missed real-time refreshes.
    """
    end_time = datetime.now(UTC)
    minutes = TIMEFRAME_MINUTES[timeframe] * sync_periods
    start_time = end_time - timedelta(minutes=minutes)

    sequence = await broker_client.fetch_candles(
        symbol=symbol,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
        count=sync_periods,
    )

    if not sequence or sequence.count == 0:
        logger.debug(
            "broker_sync_no_data",
            extra={"symbol": symbol, "timeframe": timeframe.value},
        )
        return

    stored = await candle_repository.find_by_time_range(
        symbol, timeframe.value, start_time, end_time,
    )
    stored_timestamps = {c.timestamp for c in stored} if stored else set()

    new_candles = [
        c for c in sequence.candles if c.timestamp not in stored_timestamps
    ]

    if new_candles:
        await candle_repository.bulk_create(new_candles)

    logger.info(
        "broker_sync_completed",
        extra={
            "symbol": symbol,
            "timeframe": timeframe.value,
            "candles_synced": len(new_candles),
            "broker_total": sequence.count,
        },
    )


# ---------------------------------------------------------------------------
# Job registration
# ---------------------------------------------------------------------------

def register_ta_jobs(
    scheduler: SchedulerManager,
    *,
    ta_config: TAConfig,
    orchestrator: TAOrchestrator,
    broker_client: BrokerBase,
    candle_repository: CandleRepository,
) -> None:
    """
    Register all TA scheduler jobs.

    Follows the same pattern as ``register_macro_jobs`` in
    ``engine.macro.scheduler_jobs``: reads symbols and timeframes
    from configuration so nothing is hardcoded.

    Jobs registered per symbol:
    - ``candle_refresh`` – one per HTF + LTF timeframe
    - ``analysis_trigger`` – one per symbol (HTF/LTF pair)
    - ``broker_sync`` – one per HTF timeframe (hourly reconciliation)
    - ``backfill`` – one per HTF + LTF timeframe (if enabled, runs once then long interval)
    """
    symbols = ta_config.default_symbols
    htf_timeframes = ta_config.htf_timeframes
    ltf_timeframes = ta_config.ltf_timeframes
    analysis_interval = ta_config.analysis_interval_seconds
    lookback = ta_config.candle_lookback_periods
    all_timeframes = htf_timeframes + ltf_timeframes

    for symbol in symbols:
        # ── Candle refresh jobs (one per timeframe) ──
        for tf in all_timeframes:
            interval_seconds = TIMEFRAME_MINUTES[tf] * 60

            scheduler.add_interval_job(
                _candle_refresh,
                job_id=f"candle_refresh_{symbol}_{tf.value}",
                seconds=interval_seconds,
                kwargs={
                    "symbol": symbol,
                    "timeframe": tf,
                    "broker_client": broker_client,
                    "candle_repository": candle_repository,
                },
            )

        # ── Analysis trigger job ──
        htf = htf_timeframes[0] if htf_timeframes else Timeframe.H4
        ltf = ltf_timeframes[0] if ltf_timeframes else Timeframe.M15

        scheduler.add_interval_job(
            _analysis_trigger,
            job_id=f"analysis_trigger_{symbol}_{htf.value}_{ltf.value}",
            seconds=analysis_interval,
            kwargs={
                "symbol": symbol,
                "htf_timeframe": htf,
                "ltf_timeframe": ltf,
                "orchestrator": orchestrator,
            },
        )

        # ── Broker sync jobs (one per HTF, every hour) ──
        for tf in htf_timeframes:
            sync_interval = max(TIMEFRAME_MINUTES[tf] * 60, 3600)

            scheduler.add_interval_job(
                _broker_sync,
                job_id=f"broker_sync_{symbol}_{tf.value}",
                seconds=sync_interval,
                kwargs={
                    "symbol": symbol,
                    "timeframe": tf,
                    "sync_periods": 20,
                    "broker_client": broker_client,
                    "candle_repository": candle_repository,
                },
            )

        # ── Backfill jobs (if enabled, run at long interval) ──
        if ta_config.backfill_on_startup:
            for tf in all_timeframes:
                backfill_interval = 86_400  # once per day

                scheduler.add_interval_job(
                    _backfill,
                    job_id=f"backfill_{symbol}_{tf.value}",
                    seconds=backfill_interval,
                    kwargs={
                        "symbol": symbol,
                        "timeframe": tf,
                        "lookback_periods": lookback,
                        "broker_client": broker_client,
                        "candle_repository": candle_repository,
                    },
                )

    total_jobs = len(symbols) * (
        len(all_timeframes)                        # candle refresh
        + 1                                         # analysis trigger
        + len(htf_timeframes)                       # broker sync
        + (len(all_timeframes) if ta_config.backfill_on_startup else 0)  # backfill
    )

    logger.info(
        "ta_scheduler_jobs_registered",
        extra={
            "symbols": symbols,
            "htf_timeframes": [t.value for t in htf_timeframes],
            "ltf_timeframes": [t.value for t in ltf_timeframes],
            "backfill_enabled": ta_config.backfill_on_startup,
            "total_jobs": total_jobs,
        },
    )
