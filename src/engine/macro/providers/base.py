from __future__ import annotations

import abc
import time
from typing import Any

from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    PROVIDER_ERRORS_TOTAL,
    PROVIDER_FETCH_DURATION,
    PROVIDER_FETCH_TOTAL,
)
from engine.shared.models.events import ProviderCategory, ProviderStatus

logger = get_logger(__name__)


class BaseProvider(abc.ABC):
    provider_name: str = "base"
    category: ProviderCategory = ProviderCategory.CENTRAL_BANK

    def __init__(self) -> None:
        self._status = ProviderStatus.HEALTHY
        self._last_fetch_time: float = 0.0
        self._consecutive_failures: int = 0

    @abc.abstractmethod
    async def fetch(self) -> Any:
        ...

    async def health_check(self) -> ProviderStatus:
        return self._status

    def _record_success(self, duration: float) -> None:
        self._consecutive_failures = 0
        self._status = ProviderStatus.HEALTHY
        self._last_fetch_time = time.monotonic()
        PROVIDER_FETCH_TOTAL.labels(
            provider=self.provider_name, category=self.category, status="success",
        ).inc()
        PROVIDER_FETCH_DURATION.labels(
            provider=self.provider_name, category=self.category,
        ).observe(duration)

    def _record_failure(self, duration: float, error_type: str) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= 3:
            self._status = ProviderStatus.DEGRADED
        if self._consecutive_failures >= 5:
            self._status = ProviderStatus.UNAVAILABLE
        PROVIDER_FETCH_TOTAL.labels(
            provider=self.provider_name, category=self.category, status="error",
        ).inc()
        PROVIDER_ERRORS_TOTAL.labels(
            provider=self.provider_name, category=self.category, error_type=error_type,
        ).inc()
        PROVIDER_FETCH_DURATION.labels(
            provider=self.provider_name, category=self.category,
        ).observe(duration)
