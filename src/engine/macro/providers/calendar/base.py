from __future__ import annotations

import abc

from engine.shared.models.events import ProviderCategory
from engine.macro.models.provider.calendar import CalendarEvent
from engine.macro.providers.base import BaseProvider


class BaseCalendarProvider(BaseProvider, abc.ABC):
    category = ProviderCategory.CALENDAR

    @abc.abstractmethod
    async def fetch(self) -> list[CalendarEvent]:
        ...
