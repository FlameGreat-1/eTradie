from __future__ import annotations

from engine.shared.logging import get_logger
from engine.shared.scheduler import SchedulerManager
from engine.ta.config import TAConfig
from engine.ta.constants import Timeframe, TIMEFRAME_MINUTES

logger = get_logger(__name__)


async def _candle_refresh(
    symbol: str,
    timeframe: Timeframe,
    broker_client: object,
    candle_repository: object,
) -> None:
    """Fetch the latest candle from broker and persist if new."""
    latest = await broker_client.fetch_latest_candle(symbol, timeframe)  # type: ignore[attr-defined]

    if not latest:
        logger.warning(
            "candle_refresh_no_data",
            extra={"symbol": symbol, "timeframe": timeframe.value},
        )
        return

    existing = await candle_repository.find_by_symbol_timeframe_timestamp(  # type: ignore[attr-defined]
        symbol, timeframe.value, latest.timestamp,
    )

    if existing:
        return

    await candle_repository.create(latest)  # type: ignore[attr-defined]

    logger.info(
        "candle_refreshed",
        extra={
            "symbol": symbol,
            "timeframe": timeframe.value,
            "timestamp": latest.timestamp.isoformat(),
        },
    )


async def _analysis_trigger(
    symbol: str,
    htf_timeframe: Timeframe,
    ltf_timeframe: Timeframe,
    orchestrator: object,
) -> None:
    """Trigger full TA analysis for a symbol/timeframe pair."""
    result = await orchestrator.analyze(  # type: ignore[attr-defined]
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


def register_ta_jobs(
    scheduler: SchedulerManager,
    *,
    ta_config: TAConfig,
    orchestrator: object,
    broker_client: object,
    candle_repository: object,
) -> None:
    """
    Register all TA scheduler jobs.

    Follows the same pattern as ``register_macro_jobs`` in
    ``engine.macro.scheduler_jobs``: reads symbols and timeframes
    from configuration so nothing is hardcoded.
    """
    symbols = ta_config.default_symbols
    htf_timeframes = ta_config.htf_timeframes
    ltf_timeframes = ta_config.ltf_timeframes
    analysis_interval = ta_config.analysis_interval_seconds

    for symbol in symbols:
        for tf in htf_timeframes:
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

        for tf in ltf_timeframes:
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

    logger.info(
        "ta_scheduler_jobs_registered",
        extra={
            "symbols": symbols,
            "htf_timeframes": [t.value for t in htf_timeframes],
            "ltf_timeframes": [t.value for t in ltf_timeframes],
            "total_jobs": len(symbols) * (len(htf_timeframes) + len(ltf_timeframes) + 1),
        },
    )
