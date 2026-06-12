"""Integration tests for the AnalysisProcessor pipeline.

Tests the full chain: ProcessorInput -> prompt -> mock LLM -> parse ->
validate -> map -> ProcessorOutput.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator

import pytest

from engine.processor.config import ProcessorConfig
from engine.processor.constants import LLMProvider
from engine.processor.llm.client import LLMClient, LLMResponse
from engine.processor.models.io import ProcessorInput
from engine.processor.service import AnalysisProcessor
from engine.shared.exceptions import ProcessorError, ProcessorInsufficientDataError

pytestmark = pytest.mark.integration


def _valid_json(direction="LONG", grade="A", proceed="YES") -> str:
    return json.dumps({
        "analysis_id": "analysis_EURUSD_20250101_1200_ab12",
        "pair": "EURUSD", "timestamp": "2025-01-01T12:00:00Z",
        "trading_style": "INTRADAY", "session": "NEW_YORK",
        "macro_bias": {"base_currency": {"bias": "BULLISH", "evidence": []}, "quote_currency": {"bias": "BEARISH", "evidence": []}},
        "dxy_bias": {"direction": "BEARISH", "evidence": []},
        "cot_signal": {"summary": "Longs increasing", "extreme_flag": False, "evidence": []},
        "event_risk": [],
        "htf_bias": {"structure": "bullish", "key_levels": [1.12]},
        "mtf_bias": {"structure": "bullish", "key_levels": [1.105]},
        "entry_setup": {"type": "OB", "bounds": [1.1, 1.101], "evidence": []},
        "wyckoff_phase": {"phase": "markup", "evidence": []},
        "confluence_score": {"score": 8.0, "factors": [{"name": "htf", "present": True, "value": 1.0, "notes": "ok"}]},
        "setup_grade": grade, "direction": direction,
        "entry_zone": {"low": 1.1000, "high": 1.1010},
        "stop_loss": {"price": 1.0950, "reason": "Below OB", "evidence": []},
        "take_profits": [
            {"level": 1.11, "size_pct": 40, "basis": "R1"},
            {"level": 1.115, "size_pct": 30, "basis": "R2"},
            {"level": 1.12, "size_pct": 30, "basis": "R3"}
        ],
        "rr_ratio": 3.0, "confidence": "HIGH", "proceed_to_module_b": proceed,
        "execution_mode": "LIMIT", "ltf_confirmed": False,
        "explainable_reasoning": "Strong bullish structure.",
        "rag_sources": [{"doc_id": "d1", "chunk_id": "c1", "relevance_score": 0.9}],
        "audit": {"retrieval": {"query_summary": "test", "top_k": 5}, "citations": []},
    })


class MockLLM(LLMClient):
    # The processor reads self._llm.PROVIDER (class attribute) on the
    # BYOK metering-skip path, mirroring the real provider clients.
    PROVIDER = "mock"

    def __init__(self, text="", fail=False):
        self._text = text
        self._fail = fail
        self.call_count = 0

    async def call(
        self,
        *,
        system_prompt,
        user_message,
        trace_id=None,
        use_structured_output=True,
    ) -> LLMResponse:
        self.call_count += 1
        if self._fail:
            raise Exception("LLM unavailable")
        return LLMResponse(
            text=self._text,
            model="mock",
            provider=self.PROVIDER,
            input_tokens=500,
            output_tokens=200,
            duration_ms=100.0,
            stop_reason="STOP",
        )

    async def stream_call(
        self,
        *,
        system_prompt,
        user_message,
        trace_id=None,
        usage_out: dict | None = None,
        use_structured_output=True,
    ) -> AsyncGenerator[str, None]:
        # AnalysisProcessor._execute consumes the analysis path through
        # stream_call only; call() is retained purely for interface
        # completeness. Counting here keeps `llm.call_count == 1`
        # meaningful for the success assertions.
        self.call_count += 1
        if self._fail:
            raise Exception("LLM unavailable")
        if usage_out is not None:
            usage_out["input_tokens"] = 500
            usage_out["output_tokens"] = 200
            usage_out["finish_reason"] = "STOP"
        # Single-chunk emission is sufficient: the processor accumulates
        # chunks into full_text before parsing.
        yield self._text

    async def close(self):
        pass


@pytest.fixture
def cfg():
    return ProcessorConfig(
        llm_provider=LLMProvider.ANTHROPIC, anthropic_api_key="k", max_retries=0,
        persist_audit_logs=False, require_citations=False,
        total_timeout_seconds=30, llm_timeout_seconds=15
    )


@pytest.fixture
def ctx():
    return ProcessorInput(
        symbol="EURUSD",
        ta_analysis={"status": "success", "smc_candidates": [{"pattern": "X", "direction": "BULLISH"}], "snd_candidates": []},
        macro_analysis={},
        retrieved_knowledge={"chunks": [{"id": "c1"}]},
        metadata={"trace_id": "t"}
    )


class TestSuccess:
    @pytest.mark.asyncio
    async def test_long_setup(self, cfg, ctx):
        llm = MockLLM(text=_valid_json())
        p = AnalysisProcessor(config=cfg, llm_client=llm)
        r = await p.process(ctx, user_id="test_user_id_123", trace_id="t")
        assert r.trade_valid is True
        assert r.direction == "LONG"
        assert r.grade == "A"
        assert r.confidence == 0.85
        assert r.tp1_price == 1.11
        assert llm.call_count == 1

    @pytest.mark.asyncio
    async def test_no_setup(self, cfg, ctx):
        llm = MockLLM(text=_valid_json(direction="NO SETUP", grade="REJECT", proceed="NO"))
        p = AnalysisProcessor(config=cfg, llm_client=llm)
        r = await p.process(ctx, user_id="test_user_id_123", trace_id="t")
        assert r.trade_valid is False
        assert r.direction is None


class TestInsufficientData:
    @pytest.mark.asyncio
    async def test_empty_ta(self, cfg):
        llm = MockLLM(text="x")
        p = AnalysisProcessor(config=cfg, llm_client=llm)
        with pytest.raises(ProcessorInsufficientDataError):
            await p.process(
                ProcessorInput(symbol="X", ta_analysis={}, retrieved_knowledge={"c": 1}),
                user_id="test_user_id_123"
            )
        assert llm.call_count == 0

    @pytest.mark.asyncio
    async def test_no_candidates(self, cfg):
        llm = MockLLM(text="x")
        p = AnalysisProcessor(config=cfg, llm_client=llm)
        with pytest.raises(ProcessorInsufficientDataError):
            await p.process(
                ProcessorInput(symbol="X", ta_analysis={"smc_candidates": [], "snd_candidates": []}, retrieved_knowledge={"c": 1}),
                user_id="test_user_id_123"
            )

    @pytest.mark.asyncio
    async def test_empty_rag(self, cfg):
        llm = MockLLM(text="x")
        p = AnalysisProcessor(config=cfg, llm_client=llm)
        with pytest.raises(ProcessorInsufficientDataError):
            await p.process(
                ProcessorInput(symbol="X", ta_analysis={"smc_candidates": [{"p": 1}]}, retrieved_knowledge={}),
                user_id="test_user_id_123"
            )


class TestErrors:
    @pytest.mark.asyncio
    async def test_garbage_llm(self, cfg, ctx):
        llm = MockLLM(text="not json")
        p = AnalysisProcessor(config=cfg, llm_client=llm)
        with pytest.raises(ProcessorError):
            await p.process(ctx, user_id="test_user_id_123")

    @pytest.mark.asyncio
    async def test_llm_failure(self, cfg, ctx):
        llm = MockLLM(fail=True)
        p = AnalysisProcessor(config=cfg, llm_client=llm)
        with pytest.raises(ProcessorError):
            await p.process(ctx, user_id="test_user_id_123")
