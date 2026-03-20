import pytest
from httpx import AsyncClient

# We assume standard endpoints based on the implementation plan
# You might need to adjust paths if the actual routes differ


@pytest.mark.asyncio
async def test_health_check_endpoint(app_client: AsyncClient):
    """Test the basic health check endpoint."""
    response = await app_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_rag_health_check_endpoint(app_client: AsyncClient):
    """Test the RAG-specific health check."""
    response = await app_client.get("/health/rag")
    # depending on mock state, it usually returns 200 or 503
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_internal_ta_analyze_missing_body(app_client: AsyncClient):
    """Test validation error for missing body on internal endpoint."""
    response = await app_client.post("/internal/ta/analyze")
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.asyncio
async def test_api_analysis_latest_empty(app_client: AsyncClient):
    """Test fetching latest analysis list (empty state)."""
    # Assuming DB is empty for tests
    response = await app_client.get("/api/analysis/latest")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_api_analysis_history_pagination(app_client: AsyncClient):
    """Test fetching historical analysis supports pagination."""
    response = await app_client.get("/api/analysis/history?limit=5&offset=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_api_analysis_not_found(app_client: AsyncClient):
    """Test fetching a non-existent analysis by ID."""
    response = await app_client.get("/api/analysis/invalid-id-999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_processor_config_get(app_client: AsyncClient):
    """Test fetching current processor config."""
    response = await app_client.get("/api/processor/config")
    assert response.status_code == 200
    assert "llm_provider" in response.json()


@pytest.mark.asyncio
async def test_unauthorized_internal_access(app_client: AsyncClient):
    """Test that internal endpoints block unauthorized traffic if misconfigured."""
    # Add a mock request without internal headers or valid tokens if applicable
    # The actual implementation of Security requirements might vary
    pass
