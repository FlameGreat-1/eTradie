"""Tests for the Candle and CandleSequence domain models."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from engine.shared.exceptions import ConfigurationError
from engine.ta.constants import CandleType, Timeframe
from engine.ta.models.candle import Candle, CandleSequence
from tests.factories import make_candle, make_candle_sequence


class TestCandleValidation:
    def test_valid_candle(self):
        c = make_candle(open=1.10, high=1.12, low=1.09, close=1.11)
        assert c.open == 1.10
        assert c.high == 1.12
        assert c.low == 1.09
        assert c.close == 1.11

    def test_high_less_than_low_raises(self):
        with pytest.raises(ConfigurationError, match="High must be >= low"):
            make_candle(open=1.10, high=1.08, low=1.09, close=1.10)

    def test_high_less_than_open_raises(self):
        with pytest.raises(ConfigurationError, match="High must be >= open and close"):
            make_candle(open=1.10, high=1.09, low=1.08, close=1.09)

    def test_low_greater_than_open_raises(self):
        with pytest.raises(ConfigurationError, match="Low must be <= open and close"):
            make_candle(open=1.10, high=1.12, low=1.11, close=1.12)

    def test_negative_price_raises(self):
        with pytest.raises(ValidationError):
            make_candle(open=-1.0, high=1.0, low=-2.0, close=0.5)

    def test_symbol_normalization(self):
        c = make_candle(symbol="eur/usd")
        assert c.symbol == "EURUSD"

    def test_naive_timestamp_gets_utc(self):
        naive = datetime(2024, 1, 15, 10, 0, 0)
        c = make_candle(timestamp=naive)
        assert c.timestamp.tzinfo is not None


class TestCandleComputedFields:
    def test_bullish_candle(self):
        c = make_candle(open=1.10, high=1.12, low=1.09, close=1.11)
        assert c.is_bullish is True
        assert c.is_bearish is False
        assert c.is_doji is False

    def test_bearish_candle(self):
        c = make_candle(open=1.11, high=1.12, low=1.09, close=1.10)
        assert c.is_bearish is True
        assert c.is_bullish is False

    def test_doji_candle(self):
        c = make_candle(open=1.10, high=1.12, low=1.09, close=1.10)
        assert c.is_doji is True

    def test_body_size(self):
        c = make_candle(open=1.10, high=1.12, low=1.09, close=1.11)
        assert abs(c.body_size - 0.01) < 1e-10

    def test_total_range(self):
        c = make_candle(open=1.10, high=1.12, low=1.09, close=1.11)
        assert abs(c.total_range - 0.03) < 1e-10

    def test_marubozu_bullish(self):
        c = make_candle(open=1.10, high=1.20, low=1.10, close=1.20)
        assert c.candle_type == CandleType.MARUBOZU_BULLISH

    def test_marubozu_bearish(self):
        c = make_candle(open=1.20, high=1.20, low=1.10, close=1.10)
        assert c.candle_type == CandleType.MARUBOZU_BEARISH


class TestCandleSequence:
    def test_valid_sequence(self):
        seq = make_candle_sequence(count=10)
        assert seq.count == 10
        assert seq.symbol == "EURUSD"
        assert seq.timeframe == Timeframe.H1

    def test_sorted_by_timestamp(self):
        seq = make_candle_sequence(count=20)
        for i in range(1, len(seq.candles)):
            assert seq.candles[i].timestamp > seq.candles[i - 1].timestamp

    def test_computed_fields(self):
        seq = make_candle_sequence(count=10, trend="up")
        assert seq.start_time == seq.candles[0].timestamp
        assert seq.end_time == seq.candles[-1].timestamp
        assert seq.highest_high >= seq.lowest_low

    def test_slice(self):
        seq = make_candle_sequence(count=20)
        sliced = seq.slice(5, 10)
        assert sliced.count == 5
        assert sliced.candles[0].timestamp == seq.candles[5].timestamp

    def test_get_candle_at(self):
        seq = make_candle_sequence(count=10)
        ts = seq.candles[3].timestamp
        found = seq.get_candle_at(ts)
        assert found is not None
        assert found.timestamp == ts

    def test_get_candle_at_missing(self):
        seq = make_candle_sequence(count=10)
        found = seq.get_candle_at(datetime(2000, 1, 1, tzinfo=UTC))
        assert found is None

    def test_empty_sequence_raises(self):
        with pytest.raises(ValidationError):
            CandleSequence(symbol="EURUSD", timeframe=Timeframe.H1, candles=[])

    def test_mixed_symbols_raises(self):
        c1 = make_candle(symbol="EURUSD", timestamp=datetime(2024, 1, 1, 1, tzinfo=UTC))
        c2 = make_candle(symbol="GBPUSD", timestamp=datetime(2024, 1, 1, 2, tzinfo=UTC))
        with pytest.raises(ValueError, match="same symbol"):
            CandleSequence(symbol="EURUSD", timeframe=Timeframe.H1, candles=[c1, c2])
