from __future__ import annotations

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.sentiment import SentimentReadingRow


class SentimentRepository(BaseRepository[SentimentReadingRow]):
    """Persistence for sentiment readings.

    Only the collector writes here (via BaseRepository.bulk_upsert); the
    request path reads from the Redis cache / durable snapshot, so this repo
    carries no read methods.
    """

    model = SentimentReadingRow
    _repo_name = "sentiment"
