from __future__ import annotations

from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import ACTIVE_PROVIDERS
from engine.shared.models.events import ProviderCategory, ProviderStatus
from engine.macro.providers.base import BaseProvider

logger = get_logger(__name__)


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}
        self._disabled: set[str] = set()

    def register(self, provider: BaseProvider) -> None:
        self._providers[provider.provider_name] = provider
        logger.info("provider_registered", name=provider.provider_name, category=provider.category)

    def get(self, name: str) -> BaseProvider | None:
        if name in self._disabled:
            return None
        return self._providers.get(name)

    def get_by_category(self, category: ProviderCategory) -> list[BaseProvider]:
        return [
            p for p in self._providers.values()
            if p.category == category and p.provider_name not in self._disabled
        ]

    def disable(self, name: str) -> None:
        self._disabled.add(name)
        logger.info("provider_disabled", name=name)

    def enable(self, name: str) -> None:
        self._disabled.discard(name)
        logger.info("provider_enabled", name=name)

    async def health_check_all(self) -> dict[str, ProviderStatus]:
        results: dict[str, ProviderStatus] = {}
        for name, provider in self._providers.items():
            if name in self._disabled:
                results[name] = ProviderStatus.UNAVAILABLE
                continue
            results[name] = await provider.health_check()

        for category in ProviderCategory:
            active = sum(
                1 for name, status in results.items()
                if self._providers[name].category == category and status == ProviderStatus.HEALTHY
            )
            ACTIVE_PROVIDERS.labels(category=category.value).set(active)

        return results

    @property
    def all_providers(self) -> dict[str, BaseProvider]:
        return dict(self._providers)
