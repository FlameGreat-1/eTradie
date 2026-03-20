from datetime import UTC, datetime, timedelta
from typing import Optional

from engine.processor.models.analysis import (
    AnalysisOutput,
    ConfluenceScoreOutput,
    EntryZone,
    MacroBiasOutput,
    DXYBiasOutput,
    COTSignalOutput,
    CurrencyBias,
    SetupZone,
    StopLossOutput,
    TimeframeBias,
    WyckoffPhaseOutput,
)
from engine.processor.models.io import ProcessorInput
from engine.ta.constants import Direction, Timeframe
from engine.ta.models.candle import Candle, CandleSequence
from engine.ta.models.candidate import SMCCandidate, SnDCandidate


def make_candle(
    timestamp: datetime,
    open: float = 1.0,
    high: float = 1.05,
    low: float = 0.95,
    close: float = 1.02,
    volume: float = 1000.0,
    timeframe: Timeframe = Timeframe.H1,
    symbol: str = "EURUSD",
) -> Candle:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return Candle(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def make_candle_sequence(
    count: int = 100,
    timeframe: Timeframe = Timeframe.H1,
    start_time: Optional[datetime] = None,
    symbol: str = "EURUSD",
    trend: str = "up",
) -> CandleSequence:
    if start_time is None:
        start_time = datetime.now(UTC) - timedelta(hours=count)
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)

    candles = []
    base_price = 1.0

    for i in range(count):
        # Create a simple trend
        if trend == "up":
            open_price = base_price + (i * 0.01)
            close_price = open_price + 0.005
        elif trend == "down":
            open_price = base_price - (i * 0.01)
            close_price = open_price - 0.005
        else: # ranging
            open_price = base_price + (i % 2) * 0.01
            close_price = base_price + ((i+1) % 2) * 0.01

        candle = make_candle(
            timestamp=start_time + timedelta(hours=i),
            open=open_price,
            high=max(open_price, close_price) + 0.002,
            low=min(open_price, close_price) - 0.002,
            close=close_price,
            timeframe=timeframe,
            symbol=symbol,
        )
        candles.append(candle)

    return CandleSequence(symbol=symbol, timeframe=timeframe, candles=candles)


def make_smc_candidate(
    pattern: str = "Bullish OB",
    direction: Direction = Direction.BULLISH,
    entry_price: float = 1.1000,
    score: float = 8.0,
) -> SMCCandidate:
    return SMCCandidate(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        pattern=pattern,
        direction=direction,
        timestamp=datetime.now(UTC),
        entry_price=entry_price,
        stop_loss=entry_price - 0.0050 if direction == Direction.BULLISH else entry_price + 0.0050,
        take_profit=entry_price + 0.0150 if direction == Direction.BULLISH else entry_price - 0.0150,
        score=score,
        zone_top=entry_price + 0.0010,
        zone_bottom=entry_price - 0.0010,
        metadata={},
    )


def make_snd_candidate(
    pattern: str = "Demand Zone",
    direction: Direction = Direction.BULLISH,
    entry_price: float = 1.1000,
    score: float = 8.0,
) -> SnDCandidate:
    return SnDCandidate(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        pattern=pattern,
        direction=direction,
        timestamp=datetime.now(UTC),
        entry_price=entry_price,
        stop_loss=entry_price - 0.0050 if direction == Direction.BULLISH else entry_price + 0.0050,
        take_profit=entry_price + 0.0150 if direction == Direction.BULLISH else entry_price - 0.0150,
        score=score,
        zone_upper=entry_price + 0.0010,
        zone_lower=entry_price - 0.0010,
        metadata={},
    )


def make_processor_input(symbol: str = "EURUSD") -> ProcessorInput:
    return ProcessorInput(
        symbol=symbol,
        ta_analysis={
            "htf_timeframes": ["D1", "H4"],
            "ltf_timeframes": ["M15", "M5"],
            "smc_candidates": [make_smc_candidate().model_dump(mode="json")],
            "snd_candidates": [make_snd_candidate().model_dump(mode="json")],
            "alignment": {"D1_H4": {"trends_aligned": True, "htf_trend": "BULLISH", "ltf_trend": "BULLISH"}},
            "overall_trend": "BULLISH"
        },
        macro_analysis={
            "bias": "BULLISH",
            "dxy_bias": "BEARISH",
            "cot_signal": "BULLISH",
            "events": []
        },
        retrieved_knowledge={
            "chunks": [
                {"chunk_id": "test-chunk-1", "content": "Trade with the trend", "score": 0.9}
            ],
            "scenarios": []
        },
        metadata={"trace_id": "test-trace"}
    )
