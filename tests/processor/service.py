from unittest.mock import AsyncMock, MagicMock

import pytest

from engine.processor.config import ProcessorConfig
from engine.processor.constants import LLMProvider
from engine.processor.llm.client import LLMClient, LLMResponse
from engine.processor.models.io import ProcessorInput
from engine.processor.service import AnalysisProcessor
from engine.shared.exceptions import ProcessorError, ProviderTimeoutError


class MockLLMClient(LLMClient):
    """A mock LLM client for testing the processor service."""
    def __init__(self, response_text: str = "", fail_with: Exception | None = None):
        self.response_text = response_text
        self.fail_with = fail_with
        self.call_args = []
        self.called = 0
        
    async def call(self, *, system_prompt: str, user_message: str, trace_id: str | None = None) -> LLMResponse:
        self.called += 1
        self.call_args.append({"sys": system_prompt, "usr": user_message})
        
        if self.fail_with:
            raise self.fail_with
            
        return LLMResponse(
            text=self.response_text,
            model="mock-model",
            provider="mock-provider",
            input_tokens=100,
            output_tokens=50,
            duration_ms=100.0,
        )

    async def close(self) -> None:
        pass


@pytest.fixture
def processor_config():
    return ProcessorConfig(
        llm_provider=LLMProvider.ANTHROPIC,
        anthropic_api_key="test",
        max_retries=1,
        retry_backoff_base_seconds=0.01,
        retry_backoff_max_seconds=0.05,
    )


@pytest.fixture
def processor(processor_config):
    # Overwrite _build_llm_client to return MockLLMClient directly? 
    # Or just inject. Let's patch the builder for this test.
    proc = AnalysisProcessor(processor_config)
    return proc


@pytest.fixture
def valid_llm_json():
    import json
    return json.dumps({
        "analysis_id": "test-123",
        "pair": "EURUSD",
        "timestamp": "2025-01-01T12:00:00Z",
        "trading_style": "INTRADAY",
        "session": "NEW_YORK",
        "macro_bias": {
            "base_currency": {"bias": "BULLISH", "evidence": []},
            "quote_currency": {"bias": "BEARISH", "evidence": []}
        },
        "dxy_bias": {"direction": "BEARISH", "evidence": []},
        "cot_signal": {"summary": "increasing", "extreme_flag": False, "evidence": []},
        "event_risk": [],
        "htf_bias": {"structure": "bullish", "key_levels": []},
        "mtf_bias": {"structure": "bullish", "key_levels": []},
        "entry_setup": {"type": "OB", "bounds": [1.0, 1.1], "evidence": []},
        "wyckoff_phase": {"phase": "markup", "evidence": []},
        "confluence_score": {"score": 8.0, "factors": []},
        "setup_grade": "A",
        "direction": "LONG",
        "entry_zone": {"low": 1.1000, "high": 1.1010},
        "stop_loss": {"price": 1.0950, "reason": "OB", "evidence": []},
        "take_profits": [
            {"level": 1.1100, "size_pct": 50, "basis": "R1"},
            {"level": 1.1200, "size_pct": 50, "basis": "R2"}
        ],
        "rr_ratio": 2.0,
        "confidence": "HIGH",
        "proceed_to_module_b": "YES",
        "execution_mode": "LIMIT",
        "ltf_confirmed": True,
        "explainable_reasoning": "Looks good.",
        "rag_sources": [],
        "audit": {"retrieval": {"query_summary": "", "top_k": 0}, "citations": []}
    })


@pytest.fixture
def sample_input():
    return ProcessorInput(
        symbol="EURUSD",
        ta_analysis={"candidates": [1]},
        macro_analysis={"bias": "BULLISH"},
        retrieved_knowledge={"chunks": [{"id": 1}]},
        metadata={"trace_id": "test-trace"}
    )


@pytest.mark.asyncio
async def test_processor_success(processor, sample_input, valid_llm_json):
    """Test full successful processing pipeline."""
    mock_client = MockLLMClient(response_text=valid_llm_json)
    processor._client = mock_client
    
    result = await processor.process(sample_input)
    
    assert mock_client.called == 1
    assert result.trade_valid is True
    assert result.direction == "LONG"
    assert result.symbol == "EURUSD"


@pytest.mark.asyncio
async def test_processor_insufficient_data(processor):
    """Test standard rejection when missing TA candidates entirely."""
    empty_input = ProcessorInput(
        symbol="EURUSD",
        ta_analysis={"smc_candidates": [], "snd_candidates": []},
        macro_analysis={},
        retrieved_knowledge={},
    )
    
    # Should not even call LLM
    mock_client = MockLLMClient(response_text="{}")
    processor._client = mock_client
    
    result = await processor.process(empty_input)
    
    assert mock_client.called == 0
    assert result.trade_valid is False
    assert result.direction is None
    assert "insufficient_technical_data" in result.rejection_rules


@pytest.mark.asyncio
async def test_processor_provider_timeout(processor, sample_input):
    """Test pipeline raises ProcessorError gracefully on repeated timeouts."""
    mock_client = MockLLMClient(fail_with=ProviderTimeoutError("Connection timed out"))
    processor._client = mock_client
    
    with pytest.raises(ProcessorError, match="Connection timed out"):
        await processor.process(sample_input)


@pytest.mark.asyncio
async def test_processor_parse_error(processor, sample_input):
    """Test pipeline raises ProcessorError gracefully on malformed LLM responses."""
    mock_client = MockLLMClient(response_text="This is not JSON")
    processor._client = mock_client
    
    with pytest.raises(ProcessorError, match="Failed to parse"):
        await processor.process(sample_input)


@pytest.mark.asyncio
async def test_processor_metrics_labels(processor, sample_input, valid_llm_json):
    """Verify trace_id traverses the entire pipeline."""
    mock_client = MockLLMClient(response_text=valid_llm_json)
    processor._client = mock_client
    
    await processor.process(sample_input)
    
    # The dictionary appended to call_args
    assert "test-trace" in mock_client.call_args[0]["usr"]
