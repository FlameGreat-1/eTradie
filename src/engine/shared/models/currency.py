"""Currency and currency-pair domain models.

Defines every tradeable currency and their correlation groups so that
the system can enforce correlated-pair exposure rules and assess
macro bias per currency independently.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from engine.shared.models.base import FrozenModel


class Currency(StrEnum):
    """ISO 4217 currencies supported by the system."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    AUD = "AUD"
    CAD = "CAD"
    NZD = "NZD"
    # Metals (treated as currencies for pairing purposes)
    XAU = "XAU"
    XAG = "XAG"


class CurrencyPair(FrozenModel):
    """A tradeable currency pair with base/quote decomposition."""

    symbol: str = Field(description="Full symbol, e.g. EURUSD")
    base: Currency = Field(description="Base currency")
    quote: Currency = Field(description="Quote currency")

    @property
    def involves_usd(self) -> bool:
        return self.base == Currency.USD or self.quote == Currency.USD

    @property
    def is_usd_base(self) -> bool:
        """USD is the base (e.g. USD/JPY) — bullish DXY = bullish pair."""
        return self.base == Currency.USD

    @property
    def is_usd_quote(self) -> bool:
        """USD is the quote (e.g. EUR/USD) — bullish DXY = bearish pair."""
        return self.quote == Currency.USD

    @property
    def is_metal(self) -> bool:
        return self.base in {Currency.XAU, Currency.XAG}

    @property
    def correlation_group(self) -> str:
        """Returns the correlation group for exposure checks.

        Pairs that share the same USD-side direction belong to the same
        group.  Max 1 trade per group.
        """
        if self.is_usd_base:
            return "USD_BASE"
        if self.is_usd_quote:
            return "USD_QUOTE"
        if self.is_metal:
            return "METALS"
        return f"CROSS_{self.base}_{self.quote}"


# ── Convenience factory ──────────────────────────────────────

_PAIR_REGISTRY: dict[str, CurrencyPair] = {}


def parse_pair(symbol: str) -> CurrencyPair:
    """Parse a 6-char symbol into a ``CurrencyPair``.

    Caches instances to avoid repeated object creation.
    """
    symbol = symbol.upper().replace("/", "")
    if symbol in _PAIR_REGISTRY:
        return _PAIR_REGISTRY[symbol]

    # Handle 6-char FX pairs and XAU/XAG (also 6 chars: XAUUSD)
    if len(symbol) == 6:
        base_str, quote_str = symbol[:3], symbol[3:]
    else:
        msg = f"Cannot parse currency pair from symbol: {symbol}"
        raise ValueError(msg)

    pair = CurrencyPair(
        symbol=symbol,
        base=Currency(base_str),
        quote=Currency(quote_str),
    )
    _PAIR_REGISTRY[symbol] = pair
    return pair


# ── Correlation Groups ───────────────────────────────────────

CORRELATED_GROUPS: dict[str, list[str]] = {
    "USD_QUOTE": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"],
    "USD_BASE": ["USDJPY", "USDCHF", "USDCAD"],
    "METALS": ["XAUUSD", "XAGUSD"],
}
