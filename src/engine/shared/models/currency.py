
# shared/models/currency.py

from __future__ import annotations

from enum import StrEnum
from threading import Lock
from typing import ClassVar

from pydantic import Field, field_validator

from engine.shared.exceptions import ConfigurationError
from engine.shared.models.base import FrozenModel


class Currency(StrEnum):

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    AUD = "AUD"
    CAD = "CAD"
    NZD = "NZD"
    XAU = "XAU"
    XAG = "XAG"


class CurrencyPair(FrozenModel):

    symbol: str = Field(min_length=6, max_length=7)
    base: Currency
    quote: Currency

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        normalized = v.upper().replace("/", "").replace("_", "")
        if len(normalized) not in (6, 7):
            raise ValueError(f"Invalid currency pair symbol: {v}")
        return normalized

    @property
    def involves_usd(self) -> bool:
        return self.base == Currency.USD or self.quote == Currency.USD

    @property
    def is_usd_base(self) -> bool:
        return self.base == Currency.USD

    @property
    def is_usd_quote(self) -> bool:
        return self.quote == Currency.USD

    @property
    def is_metal(self) -> bool:
        return self.base in {Currency.XAU, Currency.XAG}

    @property
    def correlation_group(self) -> str:
        if self.is_usd_base:
            return "USD_BASE"
        if self.is_usd_quote:
            return "USD_QUOTE"
        if self.is_metal:
            return "METALS"
        return f"CROSS_{self.base}_{self.quote}"


_PAIR_REGISTRY: dict[str, CurrencyPair] = {}
_PAIR_LOCK: Lock = Lock()


def parse_pair(symbol: str) -> CurrencyPair:
    normalized = symbol.upper().replace("/", "").replace("_", "")
    
    with _PAIR_LOCK:
        if normalized in _PAIR_REGISTRY:
            return _PAIR_REGISTRY[normalized]
        
        if len(normalized) == 6:
            base_str, quote_str = normalized[:3], normalized[3:]
        elif len(normalized) == 7 and normalized.startswith("XAU"):
            base_str, quote_str = normalized[:3], normalized[3:]
        elif len(normalized) == 7 and normalized.startswith("XAG"):
            base_str, quote_str = normalized[:3], normalized[3:]
        else:
            raise ConfigurationError(
                f"Cannot parse currency pair from symbol: {symbol}",
                details={"symbol": symbol, "normalized": normalized},
            )
        
        try:
            pair = CurrencyPair(
                symbol=normalized,
                base=Currency(base_str),
                quote=Currency(quote_str),
            )
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid currency in pair {symbol}: {e}",
                details={"symbol": symbol, "base": base_str, "quote": quote_str},
            ) from e
        
        _PAIR_REGISTRY[normalized] = pair
        return pair


class CorrelationConfig(FrozenModel):
    
    groups: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "USD_QUOTE": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"],
            "USD_BASE": ["USDJPY", "USDCHF", "USDCAD"],
            "METALS": ["XAUUSD", "XAGUSD"],
        }
    )
    
    max_trades_per_group: int = Field(default=1, ge=1)
    
    def get_group(self, symbol: str) -> str | None:
        normalized = symbol.upper().replace("/", "")
        for group_name, symbols in self.groups.items():
            if normalized in symbols:
                return group_name
        return None


_correlation_config: CorrelationConfig | None = None
_config_lock: Lock = Lock()


def get_correlation_config() -> CorrelationConfig:
    global _correlation_config
    
    with _config_lock:
        if _correlation_config is None:
            _correlation_config = CorrelationConfig()
        return _correlation_config


def set_correlation_config(config: CorrelationConfig) -> None:
    global _correlation_config
    
    with _config_lock:
        _correlation_config = config
