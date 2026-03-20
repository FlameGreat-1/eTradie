import pytest
from httpx import AsyncClient

from engine.dependencies import Container


def test_container_wiring():
    """Test that the dependency injection container wires all components without errors."""
    container = Container()
    
    # We must init the configuration to prevent MissingProvider errors
    container.settings.from_env()
    container.ta_config.from_env()
    container.rag_config.from_env()
    container.processor_config.from_env()
    
    # Check that core singletons are provided
    assert container.redis_cache() is not None
    assert container.db_pool() is not None
    assert container.scheduler() is not None
    
    # Check that HTTP clients are wired
    assert container.http_client() is not None
    assert container.oanda_client() is not None
    
    # Check that orchestrators build correctly
    assert container.ta_orchestrator() is not None
    assert container.rag_orchestrator() is not None
    
    # Ensure cyclic dependencies don't exist in processor service construction
    assert container.analysis_processor() is not None


@pytest.mark.asyncio
async def test_container_shutdown():
    """Test that the container can safely teardown resources."""
    container = Container()
    
    # Initialize some mock resources
    container.settings.from_env()
    
    try:
        await container.shutdown_resources()
    except Exception as e:
        pytest.fail(f"Container shutdown raised an exception: {e}")
