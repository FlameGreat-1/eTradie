from __future__ import annotations

from engine.shared.models.events import CentralBank
from engine.shared.rss import RSSParser
from engine.macro.providers.central_bank.base import BaseCentralBankProvider


class FedRSSProvider(BaseCentralBankProvider):
    provider_name = "fed_rss"
    bank = CentralBank.FED

    def __init__(self, rss_parser: RSSParser, *, feed_url: str) -> None:
        super().__init__(rss_parser)
        self.feed_url = feed_url
