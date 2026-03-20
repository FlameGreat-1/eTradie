import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from engine.config import TAConfig
from engine.ta.orchestrator import TAOrchestrator
from tests.factories import make_candle_sequence


@pytest.fixture
def mock_broker():
    """Mock broker client that returns predictable candle sequences."""
    client = AsyncMock()
    # By default, return a 100-candle uptrend
    client.get_historical_candles.return_value = make_candle_sequence(count=100, trend="up")
    return client


@pytest.fixture
def mock_snapshot_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_candidate_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def ta_orchestrator(mock_broker, mock_snapshot_repo, mock_candidate_repo):
    config = TAConfig(
        htf_timeframes=["D1", "H4"],
        ltf_timeframes=["H1", "M15"],
        active_broker="mock"
    )
    orch = TAOrchestrator(
        config=config,
        broker_client=mock_broker,
        snapshot_repo=mock_snapshot_repo,
        candidate_repo=mock_candidate_repo,
    )
    return orch


@pytest.mark.asyncio
async def test_orchestrator_successful_analysis(ta_orchestrator, mock_broker, mock_snapshot_repo, mock_candidate_repo):
    """Test full top-down analysis pipeline."""
    result = await ta_orchestrator.analyze("EURUSD")
    
    # 1. Broker should be called for all 4 timeframes (D1, H4, H1, M15)
    assert mock_broker.get_historical_candles.call_count == 4
    
    # 2. Repo should persist 4 snapshots
    assert mock_snapshot_repo.save.call_count == 4
    
    # 3. Orchestrator should return a structured result dict
    assert "EURUSD" in result
    assert "status" in result["EURUSD"]
    assert result["EURUSD"]["status"] == "success"
    
    analysis_data = result["EURUSD"]["data"]
    assert "htf_timeframes" in analysis_data
    assert "D1" in analysis_data["htf_timeframes"]
    
    # Uptrend factories should produce candidates
    assert "smc_candidates" in analysis_data
    assert "overall_trend" in analysis_data


@pytest.mark.asyncio
async def test_orchestrator_broker_failure(ta_orchestrator, mock_broker):
    """Test analysis fails correctly when broker is down."""
    mock_broker.get_historical_candles.side_effect = Exception("API Offline")
    
    result = await ta_orchestrator.analyze("EURUSD")
    
    assert "EURUSD" in result
    assert result["EURUSD"]["status"] == "error"
    assert "API Offline" in result["EURUSD"]["error"]


@pytest.mark.asyncio
async def test_orchestrator_insufficient_data(ta_orchestrator, mock_broker):
    """Test analysis handles insufficient candles safely."""
    # Return only 5 candles (need at least 10-20 for swings)
    mock_broker.get_historical_candles.return_value = make_candle_sequence(count=5)
    
    result = await ta_orchestrator.analyze("EURUSD")
    
    assert "EURUSD" in result
    assert result["EURUSD"]["status"] == "error"
    assert "insufficient" in result["EURUSD"]["error"].lower()


@pytest.mark.asyncio
async def test_orchestrator_multi_symbol(ta_orchestrator):
    """Test analyzing multiple symbols concurrently."""
    result = await ta_orchestrator.analyze(["EURUSD", "GBPUSD"])
    
    assert "EURUSD" in result
    assert "GBPUSD" in result
    assert result["EURUSD"]["status"] == "success"
    assert result["GBPUSD"]["status"] == "success"
