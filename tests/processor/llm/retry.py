import asyncio

import pytest

from engine.processor.config import ProcessorConfig
from engine.processor.constants import LLMProvider
from engine.processor.llm.retry import retry_llm_call
from engine.shared.exceptions import ProcessorError


async def failing_call_transient(attempts=[]):
    """Simulate a transient failure (timeout) that succeeds on retry."""
    attempts.append(1)
    if len(attempts) < 3:
        # Pydantic/httpx style timeout error
        class MockTimeout(Exception):
            pass
        raise MockTimeout("Connection timeout")
    return "success"


async def failing_call_non_retryable():
    """Simulate a fatal auth error that should not retry."""
    class AuthenticationError(Exception):
        pass
    raise AuthenticationError("Invalid API Key")


async def failing_call_always(attempts=[]):
    """Simulate a failure that exhausts all retries."""
    attempts.append(1)
    class RateLimitError(Exception):
        pass
    raise RateLimitError("Too Many Requests")


@pytest.fixture
def test_config():
    return ProcessorConfig(
        anthropic_api_key="test-key",
        llm_provider=LLMProvider.ANTHROPIC,
        max_retries=3,
        retry_backoff_base_seconds=0.01,  # Super fast for tests
        retry_backoff_max_seconds=0.05,
    )


@pytest.mark.asyncio
async def test_retry_success_after_failures(test_config):
    """Test that a call eventually succeeds if retries haven't been exhausted."""
    attempts_list = []
    
    result = await retry_llm_call(
        failing_call_transient,
        attempts=attempts_list,
        config=test_config,
    )
    
    assert result == "success"
    assert len(attempts_list) == 3


@pytest.mark.asyncio
async def test_retry_aborts_on_fatal_error(test_config):
    """Test that non-retryable errors abort immediately without sleeping."""
    with pytest.raises(ProcessorError, match="Non-retryable LLM error"):
        await retry_llm_call(
            failing_call_non_retryable,
            config=test_config,
        )


@pytest.mark.asyncio
async def test_retry_exhausted(test_config):
    """Test that exhausting max_retries raises a ProcessorError."""
    attempts_list = []
    
    with pytest.raises(ProcessorError, match="LLM call failed after 4 attempts"):
        await retry_llm_call(
            failing_call_always,
            attempts=attempts_list,
            config=test_config,
        )
        
    # initial attempt + 3 retries = 4 total attempts
    assert len(attempts_list) == 4
