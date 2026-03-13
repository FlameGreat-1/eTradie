"""TA collection adapter.

Calls TAOrchestrator.analyze() for each symbol and collects
the persisted SMCCandidates, SnDCandidates, and TechnicalSnapshot from
repositories so the gateway has the full typed output.

The gateway does NOT own a symbol list. Symbols are provided by the
caller (dashboard/API) at runtime for every cycle.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.constants import Timeframe
from engine.ta.orchestrator import TAOrchestrator
from engine.ta.storage.repositories.candidate import CandidateRepository
from engine.ta.storage.repositories.snapshot import SnapshotRepository
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
    """Collects TA analysis results for caller-provided symbols."""

    def __init__(
        self,
        *,
        ta_orchestrator: TAOrchestrator,
        candidate_repository: CandidateRepository,
        snapshot_repository: SnapshotRepository,
        config: GatewayConfig,
    ) -> None:
        self._orchestrator = ta_orchestrator
        self._candidate_repo = candidate_repository
        self._snapshot_repo = snapshot_repository
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
                     (dashboard/API) - never hardcoded.
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
        htf = Timeframe(self._config.ta_htf_timeframe)
        ltf = Timeframe(self._config.ta_ltf_timeframe)
        lookback = self._config.ta_lookback_periods

        semaphore = asyncio.Semaphore(self._config.max_concurrent_symbols)

        async def _analyze_symbol(symbol: str) -> TASymbolResult:
            async with semaphore:
                return await self._analyze_single(
                    symbol, htf, ltf, lookback, trace_id=trace_id,
                )

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
                    htf_timeframe=self._config.ta_htf_timeframe,
                    ltf_timeframe=self._config.ta_ltf_timeframe,
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
        htf: Timeframe,
        ltf: Timeframe,
        lookback: int,
        *,
        trace_id: Optional[str] = None,
    ) -> TASymbolResult:
        """Analyze a single symbol and return structured result."""
        sym_start = time.monotonic()

        try:
            result = await self._orchestrator.analyze(
                symbol=symbol,
                htf_timeframe=htf,
                ltf_timeframe=ltf,
                lookback_periods=lookback,
            )

            sym_elapsed = time.monotonic() - sym_start
            GATEWAY_TA_COLLECT_DURATION.labels(symbol=symbol).observe(sym_elapsed)

            status = result.get("status", "error")

            smc_candidates: list[dict] = []
            snd_candidates: list[dict] = []
            snapshot_data: Optional[dict] = None

            if status == "success":
                smc_count = result.get("smc_candidates", 0)
                snd_count = result.get("snd_candidates", 0)

                GATEWAY_TA_CANDIDATES_PER_CYCLE.labels(framework="smc").observe(smc_count)
                GATEWAY_TA_CANDIDATES_PER_CYCLE.labels(framework="snd").observe(snd_count)

                try:
                    smc_raw = await self._candidate_repo.get_latest_smc_candidates(
                        symbol=symbol,
                        timeframe=htf.value,
                        limit=smc_count or 10,
                    )
                    smc_candidates = [
                        c.model_dump(mode="json") if hasattr(c, "model_dump") else c
                        for c in smc_raw
                    ]
                except Exception as exc:
                    logger.warning(
                        "ta_smc_candidate_fetch_failed",
                        extra={"symbol": symbol, "error": str(exc)},
                    )

                try:
                    snd_raw = await self._candidate_repo.get_latest_snd_candidates(
                        symbol=symbol,
                        timeframe=htf.value,
                        limit=snd_count or 10,
                    )
                    snd_candidates = [
                        c.model_dump(mode="json") if hasattr(c, "model_dump") else c
                        for c in snd_raw
                    ]
                except Exception as exc:
                    logger.warning(
                        "ta_snd_candidate_fetch_failed",
                        extra={"symbol": symbol, "error": str(exc)},
                    )

                try:
                    snap = await self._snapshot_repo.get_latest(
                        symbol=symbol,
                        timeframe=htf.value,
                    )
                    if snap is not None:
                        snapshot_data = snap if isinstance(snap, dict) else (
                            snap.model_dump(mode="json") if hasattr(snap, "model_dump") else {}
                        )
                except Exception as exc:
                    logger.warning(
                        "ta_snapshot_fetch_failed",
                        extra={"symbol": symbol, "error": str(exc)},
                    )

            return TASymbolResult(
                symbol=symbol,
                htf_timeframe=htf.value,
                ltf_timeframe=ltf.value,
                status=status,
                smc_candidates=smc_candidates,
                snd_candidates=snd_candidates,
                snapshot=snapshot_data,
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
                htf_timeframe=htf.value,
                ltf_timeframe=ltf.value,
                status="error",
                error=str(exc),
            )
