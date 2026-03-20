import pytest
from pydantic import ValidationError

from engine.processor.config import ProcessorConfig
from engine.processor.constants import LLMProvider


def test_processor_config_provider_validation():
    """Provider must match enum."""
    with pytest.raises(ValidationError):
        ProcessorConfig(llm_provider="fake-ai")


def test_processor_config_timeout_budget():
    """Total timeout must be strictly greater than LLM timeout."""
    with pytest.raises(ValueError, match="total_timeout_seconds"):
        ProcessorConfig(
            llm_provider=LLMProvider.ANTHROPIC,
            anthropic_api_key="sk-test",
            llm_timeout_seconds=45,
            total_timeout_seconds=30
        )


def test_processor_config_anthropic_key_required():
    """Anthropic provider requires anthropic key."""
    with pytest.raises(ValueError, match="API key required"):
        ProcessorConfig(llm_provider=LLMProvider.ANTHROPIC)


def test_processor_config_openai_key_required():
    """OpenAI provider requires openai key."""
    with pytest.raises(ValueError, match="API key required"):
        ProcessorConfig(llm_provider=LLMProvider.OPENAI)


def test_processor_config_default_model_inference():
    """If model is not set explicitly, picks defaults from processor.constants."""
    an = ProcessorConfig(llm_provider=LLMProvider.ANTHROPIC, anthropic_api_key="k")
    op = ProcessorConfig(llm_provider=LLMProvider.OPENAI, openai_api_key="k")
    gm = ProcessorConfig(llm_provider=LLMProvider.GEMINI, gemini_api_key="k")
    sf = ProcessorConfig(llm_provider=LLMProvider.SELF_HOSTED)
    
    assert an.model_name == "claude-sonnet-4-20250514"
    assert op.model_name == "gpt-4o"
    assert gm.model_name == "gemini-2.5-pro"
    assert sf.model_name == "default"


def test_processor_config_active_key_router():
    """get_active_api_key returns correct key based on provider enum."""
    config = ProcessorConfig(
        llm_provider=LLMProvider.OPENAI,
        openai_api_key="O_KEY",
        anthropic_api_key="A_KEY"
    )
    
    assert config.get_active_api_key() == "O_KEY"
