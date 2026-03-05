from __future__ import annotations

import abc

from engine.shared.models.events import ProviderCategory
from engine.macro.models.provider.market_data import IntermarketSnapshot
from engine.macro.providers.base import BaseProvider


class BaseMarketDataProvider(BaseProvider, abc.ABC):
    category = ProviderCategory.MARKET_DATA

    @abc.abstractmethod
    async def fetch(self) -> IntermarketSnapshot:
        ...
