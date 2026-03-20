import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from engine.config import ProcessorConfig, RAGConfig, Settings, TAConfig
from engine.processor.constants import LLMProvider


def test_settings_validation_success(monkeypatch):
    """Test successful Settings loading with required environment variables."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SECURITY_API_KEY", "secret_key")

    settings = Settings()
    assert getattr(settings, "database_url", None) == "postgresql+asyncpg://user:pass@localhost:5432/db"
    assert getattr(settings, "api_environment", None) == "development"


def test_settings_validation_failure():
    """Test Settings validation fails when required environment variables are missing."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValidationError):
            Settings()


def test_ta_config_defaults():
    """Test TAConfig loads with correct defaults."""
    config = TAConfig()
    assert "D1" in [tf.value for tf in getattr(config, "htf_timeframes", [])]
    assert "M15" in [tf.value for tf in getattr(config, "ltf_timeframes", [])]
    assert getattr(config, "active_broker", None) == "oanda"


def test_rag_config_defaults():
    """Test RAGConfig loads with correct defaults."""
    config = RAGConfig()
    assert getattr(config, "retrieval_top_k", None) == 25
    assert getattr(config, "rerank_enabled", None) is True


def test_rag_config_production_embedding_key_required(monkeypatch):
    """Test RAGConfig requires an embedding API key in production when using OpenAI."""
    monkeypatch.setenv("API_ENVIRONMENT", "production")
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "openai")
    monkeypatch.delenv("RAG_EMBEDDING_API_KEY", raising=False)

    with patch("engine.config.get_settings") as mock_settings:
        mock_settings.return_value.api_environment = "production"
        with pytest.raises(ValueError, match="RAG_EMBEDDING_API_KEY must be set"):
            RAGConfig()


def test_processor_config_defaults():
    """Test ProcessorConfig assigns default model based on provider."""
    config = ProcessorConfig(
        anthropic_api_key="test-key",
        llm_provider=LLMProvider.ANTHROPIC,
    )
    assert getattr(config, "llm_provider", None) == LLMProvider.ANTHROPIC
    assert getattr(config, "model_name", None) == "claude-sonnet-4-20250514"


def test_processor_config_missing_api_key():
    """Test ProcessorConfig fails if active provider API key is missing."""
    with pytest.raises(ValueError, match="PROCESSOR_ANTHROPIC_API_KEY"):
        ProcessorConfig(llm_provider=LLMProvider.ANTHROPIC)


def test_processor_config_invalid_provider():
    """Test ProcessorConfig fails with unrecognized provider."""
    with pytest.raises(ValidationError):
        ProcessorConfig(llm_provider="invalid_provider")


def test_processor_config_timeout_validation():
    """Test ProcessorConfig ensures total timeout > llm timeout."""
    with pytest.raises(ValueError, match="total_timeout_seconds"):
        ProcessorConfig(
            anthropic_api_key="test-key",
            llm_timeout_seconds=60,
            total_timeout_seconds=30,
        )


def test_processor_config_get_active_api_key():
    """Test ProcessorConfig returns the correct API key for the active provider."""
    config = ProcessorConfig(
        llm_provider=LLMProvider.OPENAI,
        anthropic_api_key="anthropic-key",
        openai_api_key="openai-key",
    )
    assert config.get_active_api_key() == "openai-key"
