from __future__ import annotations

import abc
import time
from typing import Any, TypeVar

from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import PROCESSOR_RUN_DURATION, PROCESSOR_RUN_TOTAL

logger = get_logger(__name__)
T = TypeVar("T")


class BaseProcessor(abc.ABC):
    processor_name: str = "base"

    async def process(self) -> Any:
        start = time.monotonic()
        try:
            result = await self._do_process()
            PROCESSOR_RUN_TOTAL.labels(processor=self.processor_name, status="success").inc()
            PROCESSOR_RUN_DURATION.labels(processor=self.processor_name).observe(time.monotonic() - start)
            return result
        except Exception as exc:
            PROCESSOR_RUN_TOTAL.labels(processor=self.processor_name, status="error").inc()
            PROCESSOR_RUN_DURATION.labels(processor=self.processor_name).observe(time.monotonic() - start)
            logger.error("processor_failed", processor=self.processor_name, error=str(exc))
            raise

    @abc.abstractmethod
    async def _do_process(self) -> Any:
        ...
