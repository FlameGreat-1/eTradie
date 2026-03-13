"""Macro collection adapter.

Calls all 8 macro collectors via asyncio.gather() and aggregates
their outputs into a single MacroResult.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any, Optional

from engine.macro.collectors.calendar.collector import CalendarCollector
from engine.macro.collectors.central_bank.collector import CentralBankCollector
from engine.macro.collectors.cot.collector import COTCollector
from engine.macro.collectors.dxy.collector import DXYCollector
from engine.macro.collectors.economic_data.collector import EconomicDataCollector
from engine.macro.collectors.intermarket.collector import IntermarketCollector
from engine.macro.collectors.news.collector import NewsCollector
from engine.macro.collectors.sentiment.collector import SentimentCollector
from engine.shared.logging import get_logger
from gateway.constants import PipelineStage
from gateway.context.models import MacroResult
from gateway.observability.metrics import (
    GATEWAY_MACRO_COLLECT_DURATION,
    GATEWAY_STAGE_ERRORS,
)

logger = get_logger(__name__)


class MacroCollector:
    """Collects all macro data in parallel and returns a unified result."""

    def __init__(
        self,
        *,
        cb_collector: CentralBankCollector,
        cot_collector: COTCollector,
        economic_collector: EconomicDataCollector,
        news_collector: NewsCollector,
        calendar_collector: CalendarCollector,
        dxy_collector: DXYCollector,
        intermarket_collector: IntermarketCollector,
        sentiment_collector: SentimentCollector,
    ) -> None:
        self._collectors: dict[str, Any] = {
            "central_bank": cb_collector,
            "cot": cot_collector,
            "economic": economic_collector,
            "news": news_collector,
            "calendar": calendar_collector,
            "dxy": dxy_collector,
            "intermarket": intermarket_collector,
            "sentiment": sentiment_collector,
        }

    async def collect(
        self,
        *,
        trace_id: Optional[str] = None,
    ) -> MacroResult:
        """Run all 8 macro collectors in parallel."""
        start = time.monotonic()
        names = list(self._collectors.keys())
        collectors = list(self._collectors.values())

        tasks = [c.collect() for c in collectors]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        datasets: dict[str, Optional[dict]] = {}
        errors: dict[str, str] = {}

        for name, result in zip(names, raw_results):
            if isinstance(result, Exception):
                logger.error(
                    "macro_collector_failed",
                    extra={
                        "collector": name,
                        "error": str(result),
                        "trace_id": trace_id,
                    },
                )
                GATEWAY_STAGE_ERRORS.labels(
                    stage=PipelineStage.MACRO_COLLECTOR,
                    error_type=type(result).__name__,
                ).inc()
                datasets[name] = None
                errors[name] = str(result)
            else:
                datasets[name] = self._serialize(result)

        elapsed_ms = (time.monotonic() - start) * 1000
        GATEWAY_MACRO_COLLECT_DURATION.observe(elapsed_ms / 1000)

        logger.info(
            "macro_collection_completed",
            extra={
                "datasets_available": [
                    n for n, d in datasets.items() if d is not None
                ],
                "datasets_failed": list(errors.keys()),
                "duration_ms": round(elapsed_ms, 1),
                "trace_id": trace_id,
            },
        )

        return MacroResult(
            central_bank=datasets.get("central_bank"),
            cot=datasets.get("cot"),
            economic=datasets.get("economic"),
            news=datasets.get("news"),
            calendar=datasets.get("calendar"),
            dxy=datasets.get("dxy"),
            intermarket=datasets.get("intermarket"),
            sentiment=datasets.get("sentiment"),
            collected_at=datetime.now(UTC),
            duration_ms=elapsed_ms,
            errors=errors,
        )

    @staticmethod
    def _serialize(result: Any) -> dict:
        """Safely serialize a collector result to a JSON-compatible dict."""
        if isinstance(result, dict):
            return result
        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json")
        return {"raw": str(result)}
