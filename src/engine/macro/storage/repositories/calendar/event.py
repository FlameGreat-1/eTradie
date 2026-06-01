from __future__ import annotations

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.calendar import CalendarEventRow


class CalendarRepository(BaseRepository[CalendarEventRow]):
    """Persistence for economic-calendar events.

    Only the collector writes here (via BaseRepository.bulk_upsert). The
    request path reads calendar data from the Redis cache / durable snapshot,
    and the gateway news guard reads the forwarded dataset map -- neither uses
    this repo for reads, so it carries no read methods.
    """

    model = CalendarEventRow
    _repo_name = "calendar"
