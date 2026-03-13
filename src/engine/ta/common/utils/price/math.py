from decimal import Decimal, ROUND_HALF_UP
from typing import Final

from engine.shared.exceptions import ConfigurationError

_JPY_PAIRS: Final[set[str]] = {"USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CADJPY", "CHFJPY"}

_METAL_PAIRS: Final[set[str]] = {"XAUUSD", "XAGUSD"}

# Index instruments use point-based pricing (1 point = 1 unit of price movement).
# The pip value is set to 1.0 so that calculate_pips() returns the raw point distance.
_INDEX_PATTERNS: Final[tuple[str, ...]] = (
    "US30", "US500", "US2000", "USTEC", "NAS100", "SPX", "SPX500",
    "DJ30", "NDX", "NDX100",
    "DE40", "DAX", "UK100", "FTSE", "FR40", "EU50",
    "JP225", "AU200", "HK50", "CN50",
    "VIX",
)

_PIP_DECIMALS: Final[dict[str, int]] = {
    "JPY": 2,
    "METAL": 2,
    "INDEX": 0,
    "STANDARD": 4,
}

_POINT_MULTIPLIERS: Final[dict[str, int]] = {
    "JPY": 100,
    "METAL": 100,
    "INDEX": 1,
    "STANDARD": 10000,
}


def _get_pair_type(symbol: str) -> str:
    symbol_upper = symbol.upper().replace("/", "").replace("_", "")
    
    if symbol_upper in _METAL_PAIRS:
        return "METAL"
    
    if symbol_upper in _JPY_PAIRS or symbol_upper.endswith("JPY"):
        return "JPY"
    
    # Check if the symbol matches any known index pattern.
    # Supports both exact matches (US30) and broker suffixes (US30.raw, US500_STP).
    for pattern in _INDEX_PATTERNS:
        if symbol_upper == pattern or symbol_upper.startswith(pattern):
            return "INDEX"
    
    return "STANDARD"


def get_pip_value(symbol: str) -> Decimal:
    pair_type = _get_pair_type(symbol)
    
    if pair_type == "JPY":
        return Decimal("0.01")
    elif pair_type == "METAL":
        return Decimal("0.01")
    elif pair_type == "INDEX":
        return Decimal("1.0")
    else:
        return Decimal("0.0001")


def get_pip_decimals(symbol: str) -> int:
    pair_type = _get_pair_type(symbol)
    return _PIP_DECIMALS[pair_type]


def get_point_multiplier(symbol: str) -> int:
    pair_type = _get_pair_type(symbol)
    return _POINT_MULTIPLIERS[pair_type]


def calculate_pips(
    price1: float,
    price2: float,
    symbol: str,
) -> float:
    if price1 < 0 or price2 < 0:
        raise ConfigurationError(
            "Prices must be non-negative",
            details={"price1": price1, "price2": price2, "symbol": symbol},
        )
    
    pip_value = float(get_pip_value(symbol))
    
    if pip_value == 0:
        raise ConfigurationError(
            "Pip value cannot be zero",
            details={"symbol": symbol, "pip_value": pip_value},
        )
    
    return abs(price1 - price2) / pip_value


def calculate_price_from_pips(
    base_price: float,
    pips: float,
    symbol: str,
    direction: int = 1,
) -> float:
    if base_price < 0:
        raise ConfigurationError(
            "Base price must be non-negative",
            details={"base_price": base_price, "symbol": symbol},
        )
    
    if direction not in (-1, 1):
        raise ConfigurationError(
            "Direction must be 1 (up) or -1 (down)",
            details={"direction": direction},
        )
    
    pip_value = float(get_pip_value(symbol))
    price_change = pips * pip_value * direction
    
    return base_price + price_change


def round_to_pip(price: float, symbol: str) -> float:
    decimals = get_pip_decimals(symbol)
    
    decimal_price = Decimal(str(price))
    quantizer = Decimal(10) ** -decimals
    
    rounded = decimal_price.quantize(quantizer, rounding=ROUND_HALF_UP)
    
    return float(rounded)


def is_within_tolerance(
    price1: float,
    price2: float,
    tolerance_pips: float,
    symbol: str,
) -> bool:
    if tolerance_pips < 0:
        raise ConfigurationError(
            "Tolerance must be non-negative",
            details={"tolerance_pips": tolerance_pips},
        )
    
    pip_distance = calculate_pips(price1, price2, symbol)
    
    return pip_distance <= tolerance_pips


def calculate_distance(
    price1: float,
    price2: float,
    symbol: str,
) -> float:
    return calculate_pips(price1, price2, symbol)


def calculate_percentage_change(
    old_price: float,
    new_price: float,
) -> float:
    if old_price == 0:
        raise ConfigurationError(
            "Old price cannot be zero for percentage calculation",
            details={"old_price": old_price, "new_price": new_price},
        )
    
    return ((new_price - old_price) / old_price) * 100.0


def calculate_body_percentage(
    open_price: float,
    close_price: float,
    high_price: float,
    low_price: float,
) -> float:
    if high_price < low_price:
        raise ConfigurationError(
            "High must be >= low",
            details={"high": high_price, "low": low_price},
        )
    
    total_range = high_price - low_price
    
    if total_range == 0:
        return 0.0
    
    body_size = abs(close_price - open_price)
    
    return (body_size / total_range) * 100.0


def calculate_wick_percentage(
    open_price: float,
    close_price: float,
    high_price: float,
    low_price: float,
    upper: bool = True,
) -> float:
    if high_price < low_price:
        raise ConfigurationError(
            "High must be >= low",
            details={"high": high_price, "low": low_price},
        )
    
    total_range = high_price - low_price
    
    if total_range == 0:
        return 0.0
    
    candle_top = max(open_price, close_price)
    candle_bottom = min(open_price, close_price)
    
    if upper:
        wick_size = high_price - candle_top
    else:
        wick_size = candle_bottom - low_price
    
    return (wick_size / total_range) * 100.0
