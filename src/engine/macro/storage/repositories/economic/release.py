from __future__ import annotations

from engine.macro.storage.schemas.economic import EconomicReleaseRow
from engine.shared.db.repositories.base_repository import BaseRepository


class EconomicReleaseRepository(BaseRepository[EconomicReleaseRow]):
    """Persistence for economic releases.

    Only the collector writes here today (via BaseRepository.bulk_upsert).
    The previously defined read methods (get_latest_by_indicator,
    get_by_currency, get_recent_high_impact) were removed in the
    2026-05 cleanup: they had no callers and queried columns that the
    LLM-only payload trim has retired.
    """

    model = EconomicReleaseRow
    _repo_name = "economic_release"
