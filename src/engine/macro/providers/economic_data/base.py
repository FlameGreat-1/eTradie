from __future__ import annotations

import abc

from engine.shared.models.events import ProviderCategory, SurpriseDirection
from engine.macro.models.provider.economic import EconomicRelease
from engine.macro.providers.base import BaseProvider


def compute_surprise_direction(actual: float | None, forecast: float | None) -> SurpriseDirection:
    if actual is None or forecast is None:
        return SurpriseDirection.INLINE
    diff = actual - forecast
    if abs(diff) < 0.001:
        return SurpriseDirection.INLINE
    return SurpriseDirection.BEAT if diff > 0 else SurpriseDirection.MISS


class BaseEconomicDataProvider(BaseProvider, abc.ABC):
    category = ProviderCategory.ECONOMIC_DATA

    @abc.abstractmethod
    async def fetch(self) -> list[EconomicRelease]:
        ...
