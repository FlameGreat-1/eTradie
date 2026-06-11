"""Tests for engine configuration (Settings, TAConfig, RAGConfig).

Production module: src/engine/config.py
"""

import pytest
from pydantic import ValidationError

from engine.config import RAGConfig, Settings, TAConfig
from engine.processor.config import ProcessorConfig
from engine.processor.constants import DEFAULT_MODELS, LLMProvider
from engine.ta.constants import Timeframe


class TestSettings:
    def test_requires_database_url(self):
        """Settings fails without DATABASE_URL."""
        with pytest.raises(ValidationError):
            Settings(database_url=None)

    def test_valid_settings(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
        s = Settings()
        assert str(s.database_url).startswith("postgresql")
        assert s.app_env.value == "development"

    def test_app_env_default(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
        s = Settings()
        assert s.is_production is False
        assert s.is_testing is False


class TestTAConfig:
    def test_defaults(self):
        cfg = TAConfig()
        assert cfg.enabled is True
        assert cfg.primary_broker == "mt5"
        assert cfg.fallback_broker == "twelve_data"
        assert Timeframe.D1 in cfg.htf_timeframes
        assert Timeframe.H4 in cfg.htf_timeframes
        assert Timeframe.M15 in cfg.ltf_timeframes
        assert Timeframe.M1 in cfg.ltf_timeframes

    def test_invalid_broker_rejected(self):
        with pytest.raises(ValidationError):
            TAConfig(primary_broker="invalid_broker")


class TestRAGConfig:
    def test_defaults(self):
        cfg = RAGConfig()
        assert cfg.enabled is True
        assert cfg.retrieval_top_k == 150
        assert cfg.rerank_enabled is True
        assert cfg.rerank_top_k == 130
        assert cfg.retrieval_default_strategy == "hybrid"
        assert cfg.embedding_provider in ("openai", "sentence_transformers")

    def test_invalid_embedding_provider(self):
        with pytest.raises(ValidationError):
            RAGConfig(embedding_provider="invalid")

    def test_invalid_strategy(self):
        with pytest.raises(ValidationError):
            RAGConfig(retrieval_default_strategy="invalid")


class TestProcessorConfig:
    @pytest.fixture(autouse=True)
    def _clear_env(self, monkeypatch):
        """Ensure local .env doesn't break default tests."""
        monkeypatch.delenv("PROCESSOR_MODEL_NAME", raising=False)
        monkeypatch.delenv("PROCESSOR_LLM_PROVIDER", raising=False)

    def test_default_model_from_provider(self):
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.ANTHROPIC,
            anthropic_api_key="test-key",
            _env_file=None,
        )
        assert cfg.model_name == DEFAULT_MODELS[LLMProvider.ANTHROPIC]

    def test_missing_api_key_fails(self, monkeypatch):
        monkeypatch.delenv("PROCESSOR_ANTHROPIC_API_KEY", raising=False)
        with pytest.raises((ValidationError, ValueError)):
            ProcessorConfig(llm_provider=LLMProvider.ANTHROPIC, _env_file=None)

    def test_invalid_provider_fails(self):
        with pytest.raises((ValidationError, ValueError)):
            ProcessorConfig(llm_provider="invalid_provider", _env_file=None)

    def test_timeout_validation(self):
        with pytest.raises((ValidationError, ValueError)):
            ProcessorConfig(
                anthropic_api_key="test-key",
                llm_timeout_seconds=60,
                total_timeout_seconds=30,
                _env_file=None,
            )

    def test_get_active_api_key(self):
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.OPENAI,
            anthropic_api_key="a-key",
            openai_api_key="o-key",
            _env_file=None,
        )
        assert cfg.get_active_api_key() == "o-key"
