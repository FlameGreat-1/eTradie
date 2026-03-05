from __future__ import annotations

import abc

from engine.shared.models.events import ProviderCategory
from engine.macro.providers.base import BaseProvider


class BaseSentimentProvider(BaseProvider, abc.ABC):
    category = ProviderCategory.SENTIMENT

    @abc.abstractmethod
    async def fetch(self) -> list:
        ...
