from __future__ import annotations

import abc

from engine.macro.models.provider.economic import EconomicRelease
from engine.macro.providers.base import BaseProvider
from engine.shared.models.events import ProviderCategory


class BaseEconomicDataProvider(BaseProvider, abc.ABC):
    category = ProviderCategory.ECONOMIC_DATA

    @abc.abstractmethod
    async def fetch(self) -> list[EconomicRelease]: ...
