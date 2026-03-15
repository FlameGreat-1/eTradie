"""
TA scheduler job definitions.

Registers TA data infrastructure as a single dynamic recurring job:
- Candle refresh  -- real-time latest candle ingestion per symbol/timeframe
- Backfill        -- fills historical candle gaps
- Broker sync     -- periodic reconciliation of stored vs broker data

The active symbol list is read from SymbolStore (owned by the Gateway)
on every invocation.  When the user changes their selection, the next
data refresh cycle automatically focuses on the new symbols.

Timeframes are read from TAConfig (owned by the TA engine).
Analysis (SMC/SnD detection) is NOT triggered here -- that is the
Gateway's responsibility via TACollector -> TAOrchestrator.analyze().
"""

from __future__ import annotations

import asyncio
import functools
from datetime import datetime, timedelta, UTC
from typing import Any, Callable, Coroutine, Optional

from engine.shared.logging import get_logger
from engine.shared.scheduler import SchedulerManager
from engine.ta.broker.base import BrokerBase
from engine.config import get_ta_config
from engine.ta.constants import Timeframe, TIMEFRAME_MINUTES
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
# Dynamic data refresh for active symbols
# ---------------------------------------------------------------------------

@with_retry(max_retries=2)
async def _refresh_data_for_active_symbols(
    symbol_store: object,
    broker_client: BrokerBase,
    candle_repository: CandleRepository,
) -> None:
    """Refresh candle data for whatever symbols are currently active.

    Reads the active symbol list from SymbolStore on every invocation
    so that when the user changes their selection, the TA data
    infrastructure automatically focuses on the new symbols.

    This is the single recurring job that replaces the old per-symbol
    static registration.  Timeframes come from TAConfig.
    """
    ta_config = get_ta_config()
    htf_timeframes = ta_config.htf_timeframes
    ltf_timeframes = ta_config.ltf_timeframes
    all_timeframes = htf_timeframes + ltf_timeframes
    lookback = ta_config.candle_lookback_periods

    # SymbolStore.get_active_symbols() returns user selection or Gateway defaults
    symbols: list[str] = await symbol_store.get_active_symbols()

    if not symbols:
        logger.warning("ta_data_refresh_no_active_symbols")
        return

    logger.info(
        "ta_data_refresh_started",
        extra={
            "symbols": symbols,
            "timeframes": [tf.value for tf in all_timeframes],
        },
    )

    for symbol in symbols:
        # Candle refresh for every timeframe
        for tf in all_timeframes:
            try:
                await _candle_refresh(
                    symbol=symbol,
                    timeframe=tf,
                    broker_client=broker_client,
                    candle_repository=candle_repository,
                )
            except Exception as exc:
                logger.error(
                    "ta_candle_refresh_failed",
                    extra={
                        "symbol": symbol,
                        "timeframe": tf.value,
                        "error": str(exc),
                    },
                )

        # Broker sync for HTF timeframes
        for tf in htf_timeframes:
            try:
                await _broker_sync(
                    symbol=symbol,
                    timeframe=tf,
                    sync_periods=20,
                    broker_client=broker_client,
                    candle_repository=candle_repository,
                )
            except Exception as exc:
                logger.error(
                    "ta_broker_sync_failed",
                    extra={
                        "symbol": symbol,
                        "timeframe": tf.value,
                        "error": str(exc),
                    },
                )

        # Backfill if enabled
        if ta_config.backfill_on_startup:
            for tf in all_timeframes:
                try:
                    await _backfill(
                        symbol=symbol,
                        timeframe=tf,
                        lookback_periods=lookback,
                        broker_client=broker_client,
                        candle_repository=candle_repository,
                    )
                except Exception as exc:
                    logger.error(
                        "ta_backfill_failed",
                        extra={
                            "symbol": symbol,
                            "timeframe": tf.value,
                            "error": str(exc),
                        },
                    )

    logger.info(
        "ta_data_refresh_completed",
        extra={
            "symbols": symbols,
            "timeframes_count": len(all_timeframes),
        },
    )


# ---------------------------------------------------------------------------
# Job registration
# ---------------------------------------------------------------------------

def register_ta_jobs(
    scheduler: SchedulerManager,
    *,
    symbol_store: object,
    broker_client: BrokerBase,
    candle_repository: CandleRepository,
) -> None:
    """Register TA data infrastructure as a single dynamic recurring job.

    The job reads the active symbol list from SymbolStore on every
    invocation.  When the user changes their symbol selection on the
    dashboard, the next data refresh cycle automatically focuses on
    the new symbols.  No restart required.

    Timeframes are read from TAConfig (owned by the TA engine).
    Symbols are read from SymbolStore (owned by the Gateway).

    Does NOT trigger analysis (SMC/SnD detection) -- that is the
    Gateway's responsibility via TACollector -> TAOrchestrator.analyze().
    """
    ta_config = get_ta_config()

    # Determine refresh interval: use the smallest HTF candle interval
    # so data is always fresh before the next analysis cycle.
    min_htf_minutes = min(
        TIMEFRAME_MINUTES[tf] for tf in ta_config.htf_timeframes
    ) if ta_config.htf_timeframes else 60
    refresh_interval_seconds = min_htf_minutes * 60

    scheduler.add_interval_job(
        _refresh_data_for_active_symbols,
        job_id="ta_data_refresh",
        seconds=refresh_interval_seconds,
        kwargs={
            "symbol_store": symbol_store,
            "broker_client": broker_client,
            "candle_repository": candle_repository,
        },
    )

    logger.info(
        "ta_data_refresh_job_registered",
        extra={
            "refresh_interval_seconds": refresh_interval_seconds,
            "htf_timeframes": [t.value for t in ta_config.htf_timeframes],
            "ltf_timeframes": [t.value for t in ta_config.ltf_timeframes],
            "backfill_enabled": ta_config.backfill_on_startup,
        },
    )
