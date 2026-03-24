import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
from datetime import datetime, timezone

from engine.ta.orchestrator import TAOrchestrator
from engine.ta.broker.base import BrokerBase
from engine.ta.models.candle import CandleSequence, Candle
from engine.ta.constants import Timeframe


def _make_sequence(symbol="EURUSD", timeframe=Timeframe.H1):
    """Create a valid CandleSequence with one dummy candle."""
    candle = Candle(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        open=1.1000,
        high=1.1050,
        low=1.0950,
        close=1.1020,
        volume=500.0,
    )
    return CandleSequence(symbol=symbol, timeframe=timeframe, candles=[candle])


def _make_mock_uow(candle_rows=None):
    """Create a mock UoW with repos that have async methods."""
    uow = AsyncMock()
    uow.candle_repo = Mock()
    uow.candle_repo.find_by_time_range = AsyncMock(return_value=candle_rows or [])
    uow.candle_repo.find_by_symbol_timeframe_timestamp = AsyncMock(return_value=None)
    uow.candle_repo.create = AsyncMock()
    uow.candle_repo.bulk_create = AsyncMock()
    uow.snapshot_repo = Mock()
    uow.snapshot_repo.create = AsyncMock()
    uow.candidate_repo = Mock()
    uow.candidate_repo.create_smc_candidate = AsyncMock()
    uow.candidate_repo.create_snd_candidate = AsyncMock()
    return uow


def _make_uow_factory(uow):
    """Create a factory callable that returns a mock UoW as async context manager."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=uow)
    ctx.__aexit__ = AsyncMock(return_value=False)

    def factory():
        return ctx

    return factory


@pytest.fixture
def mock_broker():
    broker = Mock(spec=BrokerBase)
    broker.fetch_candles = AsyncMock()
    return broker


@pytest.fixture
def mock_fallback_broker():
    broker = Mock(spec=BrokerBase)
    broker.fetch_candles = AsyncMock()
    return broker


@pytest.fixture
def mock_uow():
    return _make_mock_uow()


@pytest.fixture
def orchestrator(mock_broker, mock_fallback_broker, mock_uow):
    ta_uow_factory = _make_uow_factory(mock_uow)
    ta_read_uow_factory = _make_uow_factory(mock_uow)

    return TAOrchestrator(
        broker_client=mock_broker,
        ta_uow_factory=ta_uow_factory,
        ta_read_uow_factory=ta_read_uow_factory,
        smc_detector=Mock(),
        snd_detector=Mock(),
        snapshot_builder=Mock(),
        alignment_service=Mock(),
        timeframe_manager=Mock(),
        ta_config=Mock(),
        fallback_client=mock_fallback_broker,
    )


@pytest.mark.asyncio
async def test_fetch_sequence_success_primary_broker(orchestrator, mock_broker, mock_fallback_broker):
    # Setup primary broker to succeed
    expected_sequence = _make_sequence()
    mock_broker.fetch_candles.return_value = expected_sequence

    result = await orchestrator._fetch_sequence("EURUSD", Timeframe.H1, 100)

    # Asserts
    assert result is expected_sequence
    mock_broker.fetch_candles.assert_called_once()
    mock_fallback_broker.fetch_candles.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_sequence_fails_over_to_fallback(orchestrator, mock_broker, mock_fallback_broker):
    # Setup primary broker to FAIL
    mock_broker.fetch_candles.side_effect = Exception("MT5 Connection Refused")

    # Setup fallback broker to SUCCEED
    fallback_sequence = _make_sequence()
    mock_fallback_broker.fetch_candles.return_value = fallback_sequence

    result = await orchestrator._fetch_sequence("EURUSD", Timeframe.H1, 100)

    # Asserts
    assert result is fallback_sequence
    mock_broker.fetch_candles.assert_called_once()
    mock_fallback_broker.fetch_candles.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_sequence_both_brokers_fail(orchestrator, mock_broker, mock_fallback_broker):
    # Setup both brokers to FAIL
    mock_broker.fetch_candles.side_effect = Exception("MT5 Down")
    mock_fallback_broker.fetch_candles.side_effect = Exception("TwelveData Rate Limit Exceeded")

    result = await orchestrator._fetch_sequence("EURUSD", Timeframe.M15, 50)

    # If both fail and local DB is empty, it returns None
    assert result is None
    mock_broker.fetch_candles.assert_called_once()
    mock_fallback_broker.fetch_candles.assert_called_once()
