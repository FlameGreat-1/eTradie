import pytest
from aioresponses import aioresponses

from engine.shared.exceptions import (
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
)
from engine.shared.http.client import CircuitState, HttpClient


@pytest.fixture
async def http_client():
    client = HttpClient(
        max_retries=1,
        cb_failure_threshold=2,
        timeout_seconds=5,
    )
    yield client
    await client.close()


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
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_post_success(http_client, mock_aioresponse):
    """Test successful JSON POST request with body."""
    url = "https://api.example.com/data"
    mock_aioresponse.post(url, payload={"id": 1})

    result = await http_client.post(url, json_body={"name": "test"}, provider_name="test")

    assert result == {"id": 1}


@pytest.mark.asyncio
async def test_url_validation(http_client):
    """Test HttpClient rejects malformed or unsecure URLs."""
    with pytest.raises(ProviderValidationError):
        await http_client.get("ftp://api.example.com")

    with pytest.raises(ProviderValidationError):
        await http_client.get("not_a_url")


@pytest.mark.asyncio
async def test_head_success_returns_status(http_client, mock_aioresponse):
    """HEAD on a reachable URL returns a HeadResult carrying the status,
    without reading a body. This is the broker-bundle reachability
    probe's happy path."""
    url = "https://pub-example.r2.dev/broker-bundles/deriv-portable.zip"
    mock_aioresponse.head(url, status=200)

    result = await http_client.head(url, provider_name="broker_bundle_r2", timeout=10.0)

    assert result.status_code == 200


@pytest.mark.asyncio
async def test_head_returns_4xx_without_raising(http_client, mock_aioresponse):
    """A 4xx HEAD is a reachable-but-missing object: head() RETURNS the
    status (the caller decides what >=400 means), it does not raise."""
    url = "https://pub-example.r2.dev/broker-bundles/missing.zip"
    mock_aioresponse.head(url, status=404)

    result = await http_client.head(url, provider_name="broker_bundle_r2", timeout=10.0)

    assert result.status_code == 404


@pytest.mark.asyncio
async def test_head_connection_error_raises_unavailable(http_client, mock_aioresponse):
    """A network-level failure surfaces as ProviderUnavailableError so the
    probe's except-branch can map it to a 422 'bundle unreachable'."""
    import aiohttp

    url = "https://pub-example.r2.dev/broker-bundles/deriv-portable.zip"
    mock_aioresponse.head(url, exception=aiohttp.ClientConnectionError("refused"))

    with pytest.raises(ProviderUnavailableError):
        await http_client.head(url, provider_name="broker_bundle_r2", timeout=10.0)


@pytest.mark.asyncio
async def test_timeout_retry_and_exhaustion(http_client, mock_aioresponse):
    """Test that timeouts trigger retries and eventually surface a ProviderTimeoutError."""
    url = "https://api.example.com/timeout"

    # Two failures = max_retries (1) + initial attempt (1) exhausted
    mock_aioresponse.get(url, exception=TimeoutError(), repeat=True)

    with pytest.raises(ProviderTimeoutError):
        await http_client.get(url)


@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore::ResourceWarning")
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
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_server_error_retry(http_client, mock_aioresponse):
    """Test 500 Server Error triggers retry."""
    url = "https://api.example.com/500"

    mock_aioresponse.get(url, status=500, body="Internal Server Error")
    mock_aioresponse.get(url, status=200, payload={"recovered": True})

    result = await http_client.get(url)

    assert result == {"recovered": True}


@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore::ResourceWarning")
async def test_circuit_breaker_trip(http_client, mock_aioresponse):
    """Test circuit breaker opens after consecutive failures.

    HttpClient keeps one circuit breaker per provider_name
    (self._circuits registry). The fixture sets cb_failure_threshold=2
    and max_retries=1, so the initial attempt plus one retry record
    exactly 2 failures and trip the "test" provider's circuit.
    """
    url = "https://api.example.com/fail"

    mock_aioresponse.get(url, status=500, body="Error 1")
    mock_aioresponse.get(url, status=500, body="Error 2")

    with pytest.raises(ProviderUnavailableError):
        await http_client.get(url, provider_name="test")

    assert await http_client.get_circuit_state("test") == CircuitState.OPEN

    # Next call for the same provider must fail fast without hitting
    # the network.
    with pytest.raises(ProviderUnavailableError, match="Circuit breaker OPEN"):
        await http_client.get("https://api.example.com/different_url", provider_name="test")
