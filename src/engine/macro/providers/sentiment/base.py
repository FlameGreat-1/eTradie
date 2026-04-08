from __future__ import annotations

import abc

from engine.shared.models.events import ProviderCategory
from engine.macro.models.provider.sentiment import SentimentReading
from engine.macro.providers.base import BaseProvider


class BaseSentimentProvider(BaseProvider, abc.ABC):
    """Base class for sentiment data providers.

    Sentiment providers may need user context to read user-scoped
    caches (e.g. COT data).  Subclasses that require user context
    should override ``fetch_for_user``.
    """

    category = ProviderCategory.SENTIMENT

    @abc.abstractmethod
    async def fetch(self) -> list[SentimentReading]: ...

    async def fetch_for_user(self, user_id: str) -> list[SentimentReading]:
        """Fetch sentiment data scoped to a specific user.

        Subclasses that depend on user-scoped caches (e.g. COT data)
        MUST override this method.  The default delegates to fetch()
        for providers that consume only public data.

        Args:
            user_id: The authenticated user's ID for cache isolation.
        """
        return await self.fetch()
