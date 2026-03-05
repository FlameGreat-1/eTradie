from __future__ import annotations

import abc
import hashlib

from engine.shared.models.currency import Currency
from engine.shared.models.events import EventImpact, ProviderCategory
from engine.macro.models.provider.news import NewsItem
from engine.macro.providers.base import BaseProvider

_CURRENCY_KEYWORDS: dict[str, Currency] = {
    "dollar": Currency.USD, "usd": Currency.USD, "fed": Currency.USD, "fomc": Currency.USD,
    "euro": Currency.EUR, "eur": Currency.EUR, "ecb": Currency.ECB if hasattr(Currency, "ECB") else Currency.EUR,
    "pound": Currency.GBP, "gbp": Currency.GBP, "boe": Currency.GBP,
    "yen": Currency.JPY, "jpy": Currency.JPY, "boj": Currency.JPY,
    "franc": Currency.CHF, "chf": Currency.CHF,
    "aussie": Currency.AUD, "aud": Currency.AUD,
    "loonie": Currency.CAD, "cad": Currency.CAD,
    "kiwi": Currency.NZD, "nzd": Currency.NZD,
    "gold": Currency.XAU, "xau": Currency.XAU,
    "silver": Currency.XAG, "xag": Currency.XAG,
}

_HIGH_IMPACT_KEYWORDS = frozenset({
    "rate decision", "rate hike", "rate cut", "nfp", "non-farm",
    "cpi", "inflation", "gdp", "fomc", "ecb meeting", "boe meeting",
    "emergency", "crisis", "war", "sanctions",
})


def extract_currencies(text: str) -> list[Currency]:
    lower = text.lower()
    found: set[Currency] = set()
    for keyword, currency in _CURRENCY_KEYWORDS.items():
        if keyword in lower:
            found.add(currency)
    return sorted(found, key=lambda c: c.value)


def classify_impact(text: str) -> EventImpact:
    lower = text.lower()
    if any(kw in lower for kw in _HIGH_IMPACT_KEYWORDS):
        return EventImpact.HIGH
    return EventImpact.MEDIUM


def compute_dedupe_hash(source: str, headline: str) -> str:
    return hashlib.sha256(f"{source}:{headline}".encode()).hexdigest()


class BaseNewsProvider(BaseProvider, abc.ABC):
    category = ProviderCategory.NEWS

    @abc.abstractmethod
    async def fetch(self) -> list[NewsItem]:
        ...
