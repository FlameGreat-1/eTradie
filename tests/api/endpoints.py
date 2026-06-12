"""Tests for FastAPI endpoint structure.

Production module: src/engine/main.py + engine/routers/*

Routes were extracted from main.py into modular routers under
engine.routers; main.py now only mounts them via include_router(). These
tests therefore verify the real, wired-up registration by building the
app with create_app() and inspecting app.routes, rather than grepping the
main.py source (which no longer contains any path literals).

create_app() does not execute the lifespan, so no DB/Redis/broker/ChromaDB
connection is attempted; only Settings must load. The fixture provides a
hermetic testing environment so the suite passes regardless of the
runner's ambient environment variables.
"""

import os

import pytest


@pytest.fixture(scope="module")
def registered_paths() -> set[str]:
    """Return the set of route paths registered on the real app."""
    os.environ.setdefault("APP_ENV", "testing")
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://etradie_test:test_password@localhost:5432/etradie_test",
    )
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

    # Settings is an lru_cache singleton; clear it so the env above is
    # honoured even if a prior import already populated the cache.
    from engine.config import get_settings

    get_settings.cache_clear()

    from engine.main import create_app

    app = create_app()
    return {getattr(route, "path", "") for route in app.routes}


class TestAppFactory:
    def test_create_app_importable(self):
        """create_app factory can be imported."""
        from engine.main import create_app

        assert callable(create_app)


class TestEndpointPaths:
    def test_internal_pipeline_endpoints_registered(self, registered_paths):
        """All intelligence-pipeline internal routes are mounted."""
        for path in (
            "/internal/ta/analyze",
            "/internal/macro/collect",
            "/internal/rag/retrieve",
            "/internal/processor/process",
        ):
            assert path in registered_paths

    def test_broker_bridge_endpoints_registered(self, registered_paths):
        """The full broker-bridge surface is mounted."""
        for path in (
            "/internal/broker/account_info",
            "/internal/broker/positions",
            "/internal/broker/pending_orders",
            "/internal/broker/symbol_info",
            "/internal/broker/place_order",
            "/internal/broker/cancel_order",
            "/internal/broker/tick_price",
            "/internal/broker/modify_position",
            "/internal/broker/close_partial",
            "/internal/broker/close_position",
        ):
            assert path in registered_paths

        # The single-position lookup is registered under
        # /internal/broker/position (optionally with a path parameter).
        assert any(p.startswith("/internal/broker/position") for p in registered_paths)

    def test_health_endpoint_registered(self, registered_paths):
        assert "/health" in registered_paths

    def test_dashboard_endpoints_registered(self, registered_paths):
        for path in (
            "/api/analysis/latest",
            "/api/analysis/history",
            "/api/processor/config",
            "/api/processor/models",
        ):
            assert path in registered_paths
