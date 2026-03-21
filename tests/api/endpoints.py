"""Tests for FastAPI endpoint structure.

Production module: src/engine/main.py

Full endpoint tests require a running app with DB/Redis/ChromaDB.
These tests verify the app factory and endpoint registration.
"""


class TestAppFactory:
    def test_create_app_importable(self):
        """create_app factory can be imported."""
        from engine.main import create_app
        assert callable(create_app)


class TestEndpointPaths:
    def test_internal_endpoints_defined(self):
        """Verify all internal endpoint paths exist as strings in main.py."""
        import inspect
        from engine import main
        source = inspect.getsource(main)

        # Intelligence pipeline endpoints
        assert "/internal/ta/analyze" in source
        assert "/internal/macro/collect" in source
        assert "/internal/rag/retrieve" in source
        assert "/internal/processor/process" in source

        # Broker bridge endpoints
        assert "/internal/broker/account_info" in source
        assert "/internal/broker/positions" in source
        assert "/internal/broker/pending_orders" in source
        assert "/internal/broker/symbol_info" in source
        assert "/internal/broker/place_order" in source
        assert "/internal/broker/cancel_order" in source
        assert "/internal/broker/tick_price" in source
        assert "/internal/broker/modify_position" in source
        assert "/internal/broker/close_partial" in source
        assert "/internal/broker/close_position" in source
        assert "/internal/broker/position" in source

    def test_health_endpoint_defined(self):
        import inspect
        from engine import main
        source = inspect.getsource(main)
        assert "/health" in source

    def test_dashboard_endpoints_defined(self):
        import inspect
        from engine import main
        source = inspect.getsource(main)
        assert "/api/analysis/latest" in source
        assert "/api/analysis/history" in source
        assert "/api/processor/config" in source
        assert "/api/processor/models" in source
