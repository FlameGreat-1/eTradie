from __future__ import annotations

import abc

from engine.shared.models.events import ProviderCategory
from engine.macro.models.provider.sentiment import SentimentReading
from engine.macro.providers.base import BaseProvider


class BaseSentimentProvider(BaseProvider, abc.ABC):
    """Base class for sentiment data providers.

    Sentiment providers use the global cache (e.g. COT data).
    """

    category = ProviderCategory.SENTIMENT

    @abc.abstractmethod
    async def fetch(self) -> list[SentimentReading]: ...
