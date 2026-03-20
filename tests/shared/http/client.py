import json

import aiohttp
import pytest
from aioresponses import aioresponses

from engine.shared.exceptions import (
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
)
from engine.shared.http.client import CircuitState, HttpClient


@pytest.fixture
def http_client():
    return HttpClient(
        max_retries=1,
        cb_failure_threshold=2,
        timeout_seconds=5,
    )


@pytest.fixture
def mock_aioresponse():
    with aioresponses() as m:
        yield m


@pytest.mark.asyncio
async def test_get_success(http_client, mock_aioresponse):
    """Test successful JSON GET request."""
    url = "https://api.example.com/data"
    mock_aioresponse.get(url, payload={"status": "ok"})
    
    result = await http_client.get(url, provider_name="test")
    
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_post_success(http_client, mock_aioresponse):
    """Test successful JSON POST request with body."""
    url = "https://api.example.com/data"
    mock_aioresponse.post(url, payload={"id": 1})
    
    result = await http_client.post(
        url,
        json_body={"name": "test"},
        provider_name="test"
    )
    
    assert result == {"id": 1}


@pytest.mark.asyncio
async def test_url_validation(http_client):
    """Test HttpClient rejects malformed or unsecure URLs."""
    with pytest.raises(ProviderValidationError):
        await http_client.get("ftp://api.example.com")
        
    with pytest.raises(ProviderValidationError):
        await http_client.get("not_a_url")


@pytest.mark.asyncio
async def test_timeout_retry_and_exhaustion(http_client, mock_aioresponse):
    """Test that timeouts trigger retries and eventually surface a ProviderTimeoutError."""
    url = "https://api.example.com/timeout"
    
    # Two failures = max_retries (1) + initial attempt (1) exhausted
    mock_aioresponse.get(url, exception=import_module_dynamic_fix(), repeat=True)
    
    with pytest.raises(ProviderTimeoutError):
        await http_client.get(url)


@pytest.mark.asyncio
async def test_rate_limit_handling(http_client, mock_aioresponse):
    """Test 429 response is handled with backoff."""
    url = "https://api.example.com/ratelimit"
    
    # First request: 429 Rate Limit with a small Retry-After
    # Second request: 200 OK
    mock_aioresponse.get(url, status=429, headers={"Retry-After": "0.1"})
    mock_aioresponse.get(url, status=200, payload={"success": True})
    
    result = await http_client.get(url)
    
    assert result == {"success": True}


@pytest.mark.asyncio
async def test_non_retryable_error(http_client, mock_aioresponse):
    """Test 400 Bad Request fails immediately without retry."""
    url = "https://api.example.com/bad"
    
    mock_aioresponse.get(url, status=400, body="Bad Request")
    
    with pytest.raises(ProviderUnavailableError, match="returned 400"):
        await http_client.get(url)


@pytest.mark.asyncio
async def test_server_error_retry(http_client, mock_aioresponse):
    """Test 500 Server Error triggers retry."""
    url = "https://api.example.com/500"
    
    mock_aioresponse.get(url, status=500, body="Internal Server Error")
    mock_aioresponse.get(url, status=200, payload={"recovered": True})
    
    result = await http_client.get(url)
    
    assert result == {"recovered": True}


@pytest.mark.asyncio
async def test_circuit_breaker_trip(http_client, mock_aioresponse):
    """Test circuit breaker opens after consecutive failures."""
    url = "https://api.example.com/fail"
    
    # Our fixture sets cb_failure_threshold=2
    # So 2 failures should open the circuit
    mock_aioresponse.get(url, status=500, body="Error 1")
    mock_aioresponse.get(url, status=500, body="Error 2")
    
    # Both fail and trigger retry which also fails (4 total requests attempted)
    # The client retries *internally*, so max_retries=1 means 1 call + 1 retry = 2 failures.
    # That exactly hits the cb_failure_threshold of 2.
    with pytest.raises(ProviderUnavailableError):
        await http_client.get(url)
        
    assert await http_client._circuit.state == CircuitState.OPEN
    
    # Next call should fail immediately without hitting the network
    with pytest.raises(ProviderUnavailableError, match="Circuit breaker OPEN"):
        await http_client.get("https://api.example.com/different_url")


def import_module_dynamic_fix():
    """Helper to get aiohttp Timeout error without messy imports in global scope."""
    import asyncio
    return asyncio.TimeoutError()
