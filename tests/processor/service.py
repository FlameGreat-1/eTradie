"""Tests for AnalysisProcessor service.

Production module: src/engine/processor/service.py

The full AnalysisProcessor requires DB repositories (AnalysisRepository,
AuditRepository) which need a real or mock database session. These are
deferred to integration tests. This file tests the import chain and
configuration wiring.
"""

from engine.processor.config import ProcessorConfig
from engine.processor.constants import LLMProvider


class TestProcessorImports:
    def test_service_importable(self):
        """AnalysisProcessor can be imported without side effects."""
        from engine.processor.service import AnalysisProcessor

        assert AnalysisProcessor is not None

    def test_llm_client_importable(self):
        """LLM client interface can be imported."""
        from engine.processor.llm.client import LLMClient

        assert LLMClient is not None

    def test_factory_importable(self):
        """LLM factory can be imported."""
        from engine.processor.llm.factory import create_llm_client

        assert create_llm_client is not None


class TestProcessorConfig:
    def test_config_builds_for_anthropic(self):
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.ANTHROPIC,
            anthropic_api_key="test",
            max_retries=1,
        )
        assert cfg.llm_provider == LLMProvider.ANTHROPIC
        assert cfg.max_retries == 1

    def test_config_builds_for_openai(self):
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.OPENAI,
            openai_api_key="test",
        )
        assert cfg.llm_provider == LLMProvider.OPENAI
