"""LLM client factory.

Creates the correct LLMClient implementation based on the
configured provider. This is the single construction point.
No provider-specific logic exists outside this factory and
the provider modules themselves.
"""

from __future__ import annotations

from engine.shared.exceptions import ConfigurationError
from engine.shared.logging import get_logger
from engine.processor.config import ProcessorConfig
from engine.processor.constants import LLMProvider
from engine.processor.llm.client import LLMClient

logger = get_logger(__name__)


def create_llm_client(config: ProcessorConfig) -> LLMClient:
    """Create the LLM client for the configured provider.

    Args:
        config: Processor configuration with provider selection.

    Returns:
        Concrete LLMClient implementation.

    Raises:
        ConfigurationError: On unrecognized provider.
    """
    provider = config.llm_provider

    if provider == LLMProvider.ANTHROPIC:
        from engine.processor.llm.providers.anthropic import AnthropicClient
        client = AnthropicClient(config)

    elif provider == LLMProvider.OPENAI:
        from engine.processor.llm.providers.openai_provider import OpenAIClient
        client = OpenAIClient(config)

    elif provider == LLMProvider.GEMINI:
        from engine.processor.llm.providers.gemini import GeminiClient
        client = GeminiClient(config)

    elif provider == LLMProvider.SELF_HOSTED:
        from engine.processor.llm.providers.openai_compatible import OpenAICompatibleClient
        client = OpenAICompatibleClient(config)

    else:
        raise ConfigurationError(
            f"Unsupported LLM provider: '{provider}'",
            details={"provider": provider, "supported": [p.value for p in LLMProvider]},
        )

    logger.info(
        "llm_client_created",
        extra={
            "provider": provider,
            "model": config.model_name,
            "temperature": config.temperature,
            "max_output_tokens": config.max_output_tokens,
            "timeout_seconds": config.llm_timeout_seconds,
        },
    )

    return client
