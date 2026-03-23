"""Tests for ProcessorConfig (LLM provider/model configuration).

Production module: src/engine/processor/config.py
"""

import pytest
from pydantic import ValidationError

from engine.processor.config import ProcessorConfig
from engine.processor.constants import DEFAULT_MODELS, LLMProvider


class TestProviderValidation:
    def test_invalid_provider_rejected(self, monkeypatch):
        """Unrecognized provider string raises ValueError."""
        monkeypatch.delenv("PROCESSOR_ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("PROCESSOR_OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("PROCESSOR_GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("PROCESSOR_API_BASE_URL", raising=False)
        with pytest.raises((ValidationError, ValueError)):
            ProcessorConfig(llm_provider="fake-ai", anthropic_api_key="k", _env_file=None)

    def test_anthropic_requires_key(self, monkeypatch):
        """Anthropic provider without API key raises ValueError."""
        monkeypatch.delenv("PROCESSOR_ANTHROPIC_API_KEY", raising=False)
        with pytest.raises((ValidationError, ValueError), match="API_KEY"):
            ProcessorConfig(llm_provider=LLMProvider.ANTHROPIC, _env_file=None)

    def test_openai_requires_key(self, monkeypatch):
        """OpenAI provider without API key raises ValueError."""
        monkeypatch.delenv("PROCESSOR_OPENAI_API_KEY", raising=False)
        with pytest.raises((ValidationError, ValueError), match="API_KEY"):
            ProcessorConfig(llm_provider=LLMProvider.OPENAI, _env_file=None)

    def test_gemini_requires_key(self, monkeypatch):
        """Gemini provider without API key raises ValueError."""
        monkeypatch.delenv("PROCESSOR_GEMINI_API_KEY", raising=False)
        with pytest.raises((ValidationError, ValueError), match="API_KEY"):
            ProcessorConfig(llm_provider=LLMProvider.GEMINI, _env_file=None)

    def test_self_hosted_requires_base_url(self, monkeypatch):
        """Self-hosted provider without base URL raises ValueError."""
        monkeypatch.delenv("PROCESSOR_API_BASE_URL", raising=False)
        monkeypatch.delenv("PROCESSOR_SELF_HOSTED_API_KEY", raising=False)
        with pytest.raises((ValidationError, ValueError), match="API_BASE_URL"):
            ProcessorConfig(llm_provider=LLMProvider.SELF_HOSTED, _env_file=None)

    def test_self_hosted_valid_with_url(self):
        """Self-hosted with base URL and no key is valid."""
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.SELF_HOSTED,
            api_base_url="http://localhost:8000/v1",
        )
        assert cfg.llm_provider == LLMProvider.SELF_HOSTED


class TestTimeoutBudget:
    def test_total_must_exceed_llm_timeout(self):
        """total_timeout_seconds must be > llm_timeout_seconds."""
        with pytest.raises((ValidationError, ValueError), match="total_timeout_seconds"):
            ProcessorConfig(
                llm_provider=LLMProvider.ANTHROPIC,
                anthropic_api_key="sk-test",
                llm_timeout_seconds=45,
                total_timeout_seconds=30,
            )

    def test_valid_timeout_budget(self):
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.ANTHROPIC,
            anthropic_api_key="sk-test",
            llm_timeout_seconds=30,
            total_timeout_seconds=60,
        )
        assert cfg.llm_timeout_seconds == 30
        assert cfg.total_timeout_seconds == 60


class TestDefaultModelInference:
    @pytest.fixture(autouse=True)
    def clear_env(self, monkeypatch):
        """Ensure local .env doesn't break default tests."""
        monkeypatch.delenv("PROCESSOR_MODEL_NAME", raising=False)
        monkeypatch.delenv("PROCESSOR_LLM_PROVIDER", raising=False)

    def test_anthropic_default_model(self):
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.ANTHROPIC,
            anthropic_api_key="k",
            _env_file=None,
        )
        assert cfg.model_name == DEFAULT_MODELS[LLMProvider.ANTHROPIC]

    def test_openai_default_model(self):
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.OPENAI,
            openai_api_key="k",
            _env_file=None,
        )
        assert cfg.model_name == DEFAULT_MODELS[LLMProvider.OPENAI]

    def test_gemini_default_model(self):
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.GEMINI,
            gemini_api_key="k",
            _env_file=None,
        )
        assert cfg.model_name == DEFAULT_MODELS[LLMProvider.GEMINI]

    def test_self_hosted_default_model(self):
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.SELF_HOSTED,
            api_base_url="http://localhost:8000/v1",
            _env_file=None,
        )
        assert cfg.model_name == DEFAULT_MODELS[LLMProvider.SELF_HOSTED]

    def test_explicit_model_overrides_default(self):
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.ANTHROPIC,
            anthropic_api_key="k",
            model_name="claude-3-5-haiku-20241022",
        )
        assert cfg.model_name == "claude-3-5-haiku-20241022"


class TestGetActiveAPIKey:
    def test_returns_correct_key_for_provider(self):
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.OPENAI,
            openai_api_key="O_KEY",
            anthropic_api_key="A_KEY",
            _env_file=None,
        )
        assert cfg.get_active_api_key() == "O_KEY"

    def test_anthropic_key(self):
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.ANTHROPIC,
            anthropic_api_key="A_KEY",
            _env_file=None,
        )
        assert cfg.get_active_api_key() == "A_KEY"

    def test_self_hosted_empty_key(self, monkeypatch):
        monkeypatch.delenv("PROCESSOR_SELF_HOSTED_API_KEY", raising=False)
        cfg = ProcessorConfig(
            llm_provider=LLMProvider.SELF_HOSTED,
            api_base_url="http://localhost:8000/v1",
            _env_file=None,
        )
        assert cfg.get_active_api_key() == ""
