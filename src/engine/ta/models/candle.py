from datetime import datetime, UTC
from typing import Optional

from pydantic import Field, field_validator, computed_field

from engine.shared.exceptions import ConfigurationError
from engine.shared.models.base import FrozenModel
from engine.ta.constants import Timeframe, CandleType


class Candle(FrozenModel):
    
    symbol: str = Field(min_length=2, max_length=20)
    timeframe: Timeframe
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0, default=0.0)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        normalized = v.upper().replace("/", "").replace("_", "")
        if len(normalized) < 2:
            raise ValueError(f"Invalid symbol: {v}")
        return normalized
    
    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v
    
    def model_post_init(self, __context) -> None:
        if self.high < self.low:
            raise ConfigurationError(
                "High must be >= low",
                details={
                    "symbol": self.symbol,
                    "timestamp": self.timestamp.isoformat(),
                    "high": self.high,
                    "low": self.low,
                },
            )
        
        if self.high < self.open or self.high < self.close:
            raise ConfigurationError(
                "High must be >= open and close",
                details={
                    "symbol": self.symbol,
                    "timestamp": self.timestamp.isoformat(),
                    "high": self.high,
                    "open": self.open,
                    "close": self.close,
                },
            )
        
        if self.low > self.open or self.low > self.close:
            raise ConfigurationError(
                "Low must be <= open and close",
                details={
                    "symbol": self.symbol,
                    "timestamp": self.timestamp.isoformat(),
                    "low": self.low,
                    "open": self.open,
                    "close": self.close,
                },
            )
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.close < self.open
    
    @computed_field
    @property
    def is_doji(self) -> bool:
        return self.close == self.open
    
    @computed_field
    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)
    
    @computed_field
    @property
    def total_range(self) -> float:
        return self.high - self.low
    
    @computed_field
    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)
    
    @computed_field
    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low
    
    @computed_field
    @property
    def body_percentage(self) -> float:
        if self.total_range == 0:
            return 0.0
        return (self.body_size / self.total_range) * 100.0
    
    @computed_field
    @property
    def upper_wick_percentage(self) -> float:
        if self.total_range == 0:
            return 0.0
        return (self.upper_wick / self.total_range) * 100.0
    
    @computed_field
    @property
    def lower_wick_percentage(self) -> float:
        if self.total_range == 0:
            return 0.0
        return (self.lower_wick / self.total_range) * 100.0
    
    @computed_field
    @property
    def candle_type(self) -> CandleType:
        if self.is_doji:
            return CandleType.DOJI
        
        body_pct = self.body_percentage
        upper_wick_pct = self.upper_wick_percentage
        lower_wick_pct = self.lower_wick_percentage
        
        if body_pct >= 80:
            if self.is_bullish:
                return CandleType.MARUBOZU_BULLISH
            else:
                return CandleType.MARUBOZU_BEARISH
        
        if self.is_bullish and lower_wick_pct >= 60 and upper_wick_pct <= 10:
            return CandleType.HAMMER
        
        if self.is_bearish and upper_wick_pct >= 60 and lower_wick_pct <= 10:
            return CandleType.SHOOTING_STAR
        
        return CandleType.STANDARD
    
    def engulfs(self, previous: "Candle") -> bool:
        if self.symbol != previous.symbol or self.timeframe != previous.timeframe:
            return False
        
        if self.is_bullish and previous.is_bearish:
            return (
                self.open <= previous.close
                and self.close >= previous.open
                and self.body_size > previous.body_size
            )
        
        if self.is_bearish and previous.is_bullish:
            return (
                self.open >= previous.close
                and self.close <= previous.open
                and self.body_size > previous.body_size
            )
        
        return False


class CandleSequence(FrozenModel):
    
    symbol: str = Field(min_length=2, max_length=20)
    timeframe: Timeframe
    candles: list[Candle] = Field(min_length=1)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @field_validator("candles")
    @classmethod
    def validate_candles(cls, v: list[Candle]) -> list[Candle]:
        if not v:
            raise ValueError("Candle sequence cannot be empty")
        
        symbol = v[0].symbol
        timeframe = v[0].timeframe
        
        for candle in v:
            if candle.symbol != symbol:
                raise ValueError(
                    f"All candles must have same symbol. Expected {symbol}, got {candle.symbol}"
                )
            if candle.timeframe != timeframe:
                raise ValueError(
                    f"All candles must have same timeframe. Expected {timeframe}, got {candle.timeframe}"
                )
        
        timestamps = [c.timestamp for c in v]
        if len(timestamps) != len(set(timestamps)):
            raise ValueError("Duplicate timestamps in candle sequence")
        
        return sorted(v, key=lambda c: c.timestamp)
    
    @computed_field
    @property
    def start_time(self) -> datetime:
        return self.candles[0].timestamp
    
    @computed_field
    @property
    def end_time(self) -> datetime:
        return self.candles[-1].timestamp
    
    @computed_field
    @property
    def count(self) -> int:
        return len(self.candles)
    
    @computed_field
    @property
    def highest_high(self) -> float:
        return max(c.high for c in self.candles)
    
    @computed_field
    @property
    def lowest_low(self) -> float:
        return min(c.low for c in self.candles)
    
    def get_candle_at(self, timestamp: datetime) -> Optional[Candle]:
        for candle in self.candles:
            if candle.timestamp == timestamp:
                return candle
        return None
    
    def get_candles_between(
        self,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        return [
            c for c in self.candles
            if start <= c.timestamp <= end
        ]
    
    def slice(self, start_idx: int, end_idx: Optional[int] = None) -> "CandleSequence":
        if start_idx < 0 or start_idx >= len(self.candles):
            raise ConfigurationError(
                "Invalid start index",
                details={"start_idx": start_idx, "count": len(self.candles)},
            )
        
        if end_idx is not None and (end_idx < start_idx or end_idx > len(self.candles)):
            raise ConfigurationError(
                "Invalid end index",
                details={"end_idx": end_idx, "start_idx": start_idx, "count": len(self.candles)},
            )
        
        sliced_candles = self.candles[start_idx:end_idx]
        
        return CandleSequence(
            symbol=self.symbol,
            timeframe=self.timeframe,
            candles=sliced_candles,
        )
