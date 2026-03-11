from enum import IntEnum, StrEnum
from typing import Final


class Timeframe(StrEnum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"


TIMEFRAME_MINUTES: Final[dict[Timeframe, int]] = {
    Timeframe.M1: 1,
    Timeframe.M5: 5,
    Timeframe.M15: 15,
    Timeframe.M30: 30,
    Timeframe.H1: 60,
    Timeframe.H4: 240,
    Timeframe.D1: 1440,
    Timeframe.W1: 10080,
    Timeframe.MN1: 43200,
}


class TimeframeRelation(IntEnum):
    PARENT = 1
    CHILD = -1
    SAME = 0
    UNRELATED = 99


class Session(StrEnum):
    ASIA = "ASIA"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    OVERLAP_LONDON_NY = "OVERLAP_LONDON_NY"


SESSION_UTC_RANGES: Final[dict[Session, tuple[int, int]]] = {
    Session.ASIA: (0, 9),
    Session.LONDON: (7, 16),
    Session.NEW_YORK: (12, 21),
    Session.OVERLAP_LONDON_NY: (12, 16),
}


class Direction(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class StructureType(StrEnum):
    BOS = "BOS"
    CHOCH = "CHOCH"
    BMS = "BMS"
    SMS = "SMS"
    SR_FLIP = "SR_FLIP"
    RS_FLIP = "RS_FLIP"


class LiquidityType(StrEnum):
    BSL = "BSL"
    SSL = "SSL"
    EQUAL_HIGHS = "EQUAL_HIGHS"
    EQUAL_LOWS = "EQUAL_LOWS"
    INDUCEMENT = "INDUCEMENT"
    COMPRESSION = "COMPRESSION"


class ZoneType(StrEnum):
    ORDER_BLOCK = "ORDER_BLOCK"
    FVG = "FVG"
    BREAKER = "BREAKER"
    MITIGATION = "MITIGATION"
    SUPPLY = "SUPPLY"
    DEMAND = "DEMAND"
    QML = "QML"
    QMH = "QMH"
    MPL = "MPL"


class CandleType(StrEnum):
    MARUBOZU_BULLISH = "MARUBOZU_BULLISH"
    MARUBOZU_BEARISH = "MARUBOZU_BEARISH"
    DOJI = "DOJI"
    HAMMER = "HAMMER"
    SHOOTING_STAR = "SHOOTING_STAR"
    ENGULFING_BULLISH = "ENGULFING_BULLISH"
    ENGULFING_BEARISH = "ENGULFING_BEARISH"
    STANDARD = "STANDARD"


class FibonacciLevel(StrEnum):
    LEVEL_0 = "0.0"
    LEVEL_236 = "0.236"
    LEVEL_382 = "0.382"
    LEVEL_50 = "0.5"
    LEVEL_618 = "0.618"
    LEVEL_705 = "0.705"
    LEVEL_786 = "0.786"
    LEVEL_79 = "0.79"
    LEVEL_100 = "1.0"


FIBONACCI_VALUES: Final[dict[FibonacciLevel, float]] = {
    FibonacciLevel.LEVEL_0: 0.0,
    FibonacciLevel.LEVEL_236: 0.236,
    FibonacciLevel.LEVEL_382: 0.382,
    FibonacciLevel.LEVEL_50: 0.5,
    FibonacciLevel.LEVEL_618: 0.618,
    FibonacciLevel.LEVEL_705: 0.705,
    FibonacciLevel.LEVEL_786: 0.786,
    FibonacciLevel.LEVEL_79: 0.79,
    FibonacciLevel.LEVEL_100: 1.0,
}

OTE_LEVELS: Final[list[FibonacciLevel]] = [
    FibonacciLevel.LEVEL_50,
    FibonacciLevel.LEVEL_618,
    FibonacciLevel.LEVEL_705,
    FibonacciLevel.LEVEL_79,
]


class PriceZone(StrEnum):
    PREMIUM = "PREMIUM"
    EQUILIBRIUM = "EQUILIBRIUM"
    DISCOUNT = "DISCOUNT"


class CandidatePattern(StrEnum):
    TURTLE_SOUP_LONG = "TURTLE_SOUP_LONG"
    TURTLE_SOUP_SHORT = "TURTLE_SOUP_SHORT"
    SH_BMS_RTO_BULLISH = "SH_BMS_RTO_BULLISH"
    SH_BMS_RTO_BEARISH = "SH_BMS_RTO_BEARISH"
    SMS_BMS_RTO_BULLISH = "SMS_BMS_RTO_BULLISH"
    SMS_BMS_RTO_BEARISH = "SMS_BMS_RTO_BEARISH"
    AMD_BULLISH = "AMD_BULLISH"
    AMD_BEARISH = "AMD_BEARISH"
    TURTLE_SOUP_SH_BMS_RTO_LONG = "TURTLE_SOUP_SH_BMS_RTO_LONG"
    TURTLE_SOUP_SH_BMS_RTO_SHORT = "TURTLE_SOUP_SH_BMS_RTO_SHORT"
    QML_SR_FLIP_FAKEOUT = "QML_SR_FLIP_FAKEOUT"
    QML_RS_FLIP_FAKEOUT = "QML_RS_FLIP_FAKEOUT"
    QML_MPL_SR_FLIP_FAKEOUT = "QML_MPL_SR_FLIP_FAKEOUT"
    QML_MPL_RS_FLIP_FAKEOUT = "QML_MPL_RS_FLIP_FAKEOUT"
    QML_PREVIOUS_HIGHS_MPL_SR_FLIP = "QML_PREVIOUS_HIGHS_MPL_SR_FLIP"
    QML_PREVIOUS_LOWS_MPL_RS_FLIP = "QML_PREVIOUS_LOWS_MPL_RS_FLIP"
    QML_TRIPLE_FAKEOUT_SELL = "QML_TRIPLE_FAKEOUT_SELL"
    QML_TRIPLE_FAKEOUT_BUY = "QML_TRIPLE_FAKEOUT_BUY"
    FAKEOUT_KING_SELL = "FAKEOUT_KING_SELL"
    FAKEOUT_KING_BUY = "FAKEOUT_KING_BUY"
    PREVIOUS_HIGHS_SUPPLY_FAKEOUT = "PREVIOUS_HIGHS_SUPPLY_FAKEOUT"
    PREVIOUS_LOWS_DEMAND_FAKEOUT = "PREVIOUS_LOWS_DEMAND_FAKEOUT"
    QML_BASELINE = "QML_BASELINE"
    QML_KILLER_TYPE1 = "QML_KILLER_TYPE1"
    QML_KILLER_TYPE2 = "QML_KILLER_TYPE2"
    QMH_BASELINE = "QMH_BASELINE"
    QMH_KILLER_TYPE1 = "QMH_KILLER_TYPE1"
    QMH_KILLER_TYPE2 = "QMH_KILLER_TYPE2"
    FAKEOUT_KING = "FAKEOUT_KING"
    SOP = "SOP"
    SND_CONTINUATION = "SND_CONTINUATION"


class AMDPhase(StrEnum):
    ACCUMULATION = "ACCUMULATION"
    MANIPULATION = "MANIPULATION"
    DISTRIBUTION = "DISTRIBUTION"


MIN_TURTLE_SOUP_SL_PIPS: Final[int] = 10
MIN_SWEEP_PIPS: Final[int] = 5
MAX_SWEEP_PIPS: Final[int] = 20
MIN_FAKEOUT_TOUCHES: Final[int] = 2
MIN_PREVIOUS_LEVELS: Final[int] = 2
