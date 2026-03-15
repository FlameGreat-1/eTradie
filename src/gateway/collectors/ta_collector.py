"""TA collection adapter.

Calls TAOrchestrator.analyze() for each symbol and passes through
the full multi-timeframe result.  The Gateway does NOT dictate
timeframes, lookback periods, or any TA-specific configuration.
The TA engine owns all of that via TAConfig.

The gateway does NOT own a symbol list. Symbols are provided by the
caller (dashboard/API) at runtime for every cycle.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.orchestrator import TAOrchestrator
from gateway.config import GatewayConfig
from gateway.constants import PipelineStage
from gateway.context.models import TAResult, TASymbolResult
from gateway.observability.metrics import (
    GATEWAY_STAGE_ERRORS,
    GATEWAY_TA_CANDIDATES_PER_CYCLE,
    GATEWAY_TA_COLLECT_DURATION,
)

logger = get_logger(__name__)


class TACollector:
    """Collects TA analysis results for caller-provided symbols.

    The collector is a thin adapter between the Gateway pipeline and
    the TA engine.  It triggers analysis and maps the result into
    the Gateway's TASymbolResult model.  It does NOT configure the
    TA engine -- timeframes, lookback, and detection logic are
    entirely owned by the TA engine.
    """

    def __init__(
        self,
        *,
        ta_orchestrator: TAOrchestrator,
        config: GatewayConfig,
    ) -> None:
        self._orchestrator = ta_orchestrator
        self._config = config

    async def collect(
        self,
        *,
        symbols: list[str],
        trace_id: Optional[str] = None,
    ) -> TAResult:
        """Run TA analysis for the given symbols with bounded concurrency.

        Args:
            symbols: Symbols to analyse. Provided by the caller
                     (dashboard/API) -- never hardcoded.
            trace_id: Distributed trace ID for correlation.
        """
        if not symbols:
            logger.warning(
                "ta_collect_called_with_empty_symbols",
                extra={"trace_id": trace_id},
            )
            return TAResult(
                symbol_results=[],
                collected_at=datetime.now(UTC),
                duration_ms=0.0,
            )

        start = time.monotonic()
        semaphore = asyncio.Semaphore(self._config.max_concurrent_symbols)

        async def _analyze_symbol(symbol: str) -> TASymbolResult:
            async with semaphore:
                return await self._analyze_single(symbol, trace_id=trace_id)

        tasks = [_analyze_symbol(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        symbol_results: list[TASymbolResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                symbol = symbols[i]
                logger.error(
                    "ta_symbol_analysis_exception",
                    extra={
                        "symbol": symbol,
                        "error": str(result),
                        "trace_id": trace_id,
                    },
                )
                GATEWAY_STAGE_ERRORS.labels(
                    stage=PipelineStage.TA_COLLECTOR,
                    error_type=type(result).__name__,
                ).inc()
                symbol_results.append(TASymbolResult(
                    symbol=symbol,
                    status="error",
                    error=str(result),
                ))
            else:
                symbol_results.append(result)

        elapsed_ms = (time.monotonic() - start) * 1000

        logger.info(
            "ta_collection_completed",
            extra={
                "symbols_requested": symbols,
                "symbols_total": len(symbols),
                "symbols_success": sum(1 for r in symbol_results if r.status == "success"),
                "duration_ms": round(elapsed_ms, 1),
                "trace_id": trace_id,
            },
        )

        return TAResult(
            symbol_results=symbol_results,
            collected_at=datetime.now(UTC),
            duration_ms=elapsed_ms,
        )

    async def _analyze_single(
        self,
        symbol: str,
        *,
        trace_id: Optional[str] = None,
    ) -> TASymbolResult:
        """Analyze a single symbol via the TA orchestrator.

        The orchestrator owns all TA logic: timeframe selection,
        candle fetching, pattern detection, snapshot building,
        alignment, and persistence.  This method simply maps
        the orchestrator's result dict into a TASymbolResult.
        """
        sym_start = time.monotonic()

        try:
            result = await self._orchestrator.analyze(symbol=symbol)

            sym_elapsed = time.monotonic() - sym_start
            GATEWAY_TA_COLLECT_DURATION.labels(symbol=symbol).observe(sym_elapsed)

            status = result.get("status", "error")

            smc_candidates = result.get("smc_candidates", [])
            snd_candidates = result.get("snd_candidates", [])

            if status == "success":
                GATEWAY_TA_CANDIDATES_PER_CYCLE.labels(framework="smc").observe(
                    result.get("smc_candidates_count", 0),
                )
                GATEWAY_TA_CANDIDATES_PER_CYCLE.labels(framework="snd").observe(
                    result.get("snd_candidates_count", 0),
                )

            return TASymbolResult(
                symbol=symbol,
                htf_timeframes=result.get("htf_timeframes", []),
                ltf_timeframes=result.get("ltf_timeframes", []),
                status=status,
                smc_candidates=smc_candidates,
                snd_candidates=snd_candidates,
                snapshots=result.get("snapshots", {}),
                alignment=result.get("alignment", {}),
                overall_trend=result.get("overall_trend", "NEUTRAL"),
                error=result.get("error"),
            )

        except Exception as exc:
            sym_elapsed = time.monotonic() - sym_start
            GATEWAY_TA_COLLECT_DURATION.labels(symbol=symbol).observe(sym_elapsed)
            GATEWAY_STAGE_ERRORS.labels(
                stage=PipelineStage.TA_COLLECTOR,
                error_type=type(exc).__name__,
            ).inc()

            logger.error(
                "ta_single_symbol_failed",
                extra={
                    "symbol": symbol,
                    "error": str(exc),
                    "trace_id": trace_id,
                },
                exc_info=True,
            )

            return TASymbolResult(
                symbol=symbol,
                status="error",
                error=str(exc),
            )
