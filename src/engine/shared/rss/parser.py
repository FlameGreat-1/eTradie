from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from time import struct_time
from typing import Any

import feedparser

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.shared.models.base import FrozenModel

logger = get_logger(__name__)


class RSSEntry(FrozenModel):
    guid: str
    title: str
    link: str
    summary: str
    published_at: datetime
    raw_tags: list[str] = []


def _struct_time_to_utc(st: struct_time | None) -> datetime:
    if st is None:
        return datetime.now(UTC)
    return datetime(*st[:6], tzinfo=UTC)


def _entry_guid(entry: Any) -> str:
    raw_id = getattr(entry, "id", "") or getattr(entry, "link", "")
    if raw_id:
        return hashlib.sha256(raw_id.encode()).hexdigest()
    title = getattr(entry, "title", "")
    return hashlib.sha256(title.encode()).hexdigest()


class RSSParser:
    def __init__(self, http_client: HttpClient) -> None:
        self._http = http_client
        self._seen_guids: set[str] = set()

    async def fetch_and_parse(
        self,
        url: str,
        *,
        provider_name: str = "rss",
        category: str = "rss",
        max_entries: int = 50,
    ) -> list[RSSEntry]:
        raw_text = await self._http.get(
            url,
            provider_name=provider_name,
            category=category,
        )
        if not isinstance(raw_text, str):
            logger.error("rss_unexpected_response_type", url=url, type=type(raw_text).__name__)
            return []

        feed = feedparser.parse(raw_text)
        if feed.bozo and not feed.entries:
            logger.warning("rss_parse_error", url=url, error=str(feed.bozo_exception))
            return []

        entries: list[RSSEntry] = []
        for entry in feed.entries[:max_entries]:
            guid = _entry_guid(entry)
            if guid in self._seen_guids:
                continue
            self._seen_guids.add(guid)

            entries.append(
                RSSEntry(
                    guid=guid,
                    title=getattr(entry, "title", ""),
                    link=getattr(entry, "link", ""),
                    summary=getattr(entry, "summary", ""),
                    published_at=_struct_time_to_utc(getattr(entry, "published_parsed", None)),
                    raw_tags=[t.get("term", "") for t in getattr(entry, "tags", [])],
                ),
            )

        logger.info(
            "rss_fetched",
            url=url,
            total_entries=len(feed.entries),
            new_entries=len(entries),
        )
        return entries

    def reset_seen(self) -> None:
        self._seen_guids.clear()
