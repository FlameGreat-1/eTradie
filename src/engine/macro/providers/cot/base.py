from __future__ import annotations

import abc

from engine.shared.models.events import ProviderCategory
from engine.macro.models.provider.cot import COTReport
from engine.macro.providers.base import BaseProvider


class BaseCOTProvider(BaseProvider, abc.ABC):
    category = ProviderCategory.COT

    @abc.abstractmethod
    async def fetch(self) -> COTReport:
        ...
