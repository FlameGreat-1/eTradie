"""Tests for retry_llm_call (exponential backoff with jitter).

Production module: src/engine/processor/llm/retry.py
"""

import pytest

from engine.processor.config import ProcessorConfig
from engine.processor.constants import LLMProvider
from engine.processor.llm.retry import retry_llm_call
from engine.shared.exceptions import ProcessorError


@pytest.fixture
def fast_config():
    """Config with fast retries for testing."""
    return ProcessorConfig(
        anthropic_api_key="test-key",
        llm_provider=LLMProvider.ANTHROPIC,
        max_retries=3,
        retry_backoff_base_seconds=0.5,
        retry_backoff_max_seconds=5.0,
        _env_file=None,
    )


class TestRetrySuccess:
    @pytest.mark.asyncio
    async def test_succeeds_after_transient_failures(self, fast_config):
        """Call eventually succeeds if retries haven't been exhausted."""
        call_count = 0

        async def flaky_call():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("Connection timeout")
            return "success"

        result = await retry_llm_call(flaky_call, config=fast_config)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self, fast_config):
        """No retries needed when call succeeds immediately."""
        async def ok_call():
            return "ok"

        result = await retry_llm_call(ok_call, config=fast_config)
        assert result == "ok"


class TestRetryAbort:
    @pytest.mark.asyncio
    async def test_non_retryable_aborts_immediately(self, fast_config):
        """Non-retryable errors abort without sleeping."""
        call_count = 0

        async def auth_fail():
            nonlocal call_count
            call_count += 1

            class AuthenticationError(Exception):
                pass

            raise AuthenticationError("Invalid API Key")

        with pytest.raises(ProcessorError, match="Non-retryable LLM error"):
            await retry_llm_call(auth_fail, config=fast_config)

        assert call_count == 1  # No retries


class TestRetryExhausted:
    @pytest.mark.asyncio
    async def test_exhausted_retries_raises(self, fast_config):
        """Exhausting max_retries raises ProcessorError."""
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Always times out")

        with pytest.raises(ProcessorError, match="LLM call failed after"):
            await retry_llm_call(always_fail, config=fast_config)

        # initial attempt + 3 retries = 4 total
        assert call_count == 4
