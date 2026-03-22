import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from engine.ta.orchestrator import TAOrchestrator
from engine.ta.broker.base import BrokerBase
from engine.ta.models.candle import CandleSequence, Candle
from engine.ta.constants import Timeframe
from engine.ta.storage.repositories.candle import CandleRepository

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
def mock_candle_repo():
    repo = Mock(spec=CandleRepository)
    repo.find_by_time_range = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def orchestrator(
    mock_broker, mock_fallback_broker, mock_candle_repo
):
    # Mocking all other dependencies with simple MagicMocks since _fetch_sequence 
    # only hits broker_client, fallback_client, and candle_repository.
    return TAOrchestrator(
        broker_client=mock_broker,
        candle_repository=mock_candle_repo,
        snapshot_repository=Mock(),
        candidate_repository=Mock(),
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
    expected_sequence = CandleSequence(symbol="EURUSD", timeframe=Timeframe.H1, candles=[])
    expected_sequence.count = 100
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
    fallback_sequence = CandleSequence(symbol="EURUSD", timeframe=Timeframe.H1, candles=[])
    fallback_sequence.count = 100
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
