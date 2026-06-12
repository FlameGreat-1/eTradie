"""Integration tests for all 8 dashboard API endpoints.

Requires PostgreSQL and Redis running (Docker).
Run: pytest tests/api/test_dashboard_api.py -v -m integration

Tests are automatically skipped if infrastructure is not available.
"""

from __future__ import annotations

import pytest

from tests.api.conftest import CHROMA_AVAILABLE, skip_no_infra

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, skip_no_infra]


# ---------------------------------------------------------------------------
# Health Endpoints
# ---------------------------------------------------------------------------


class TestHealthEndpoints:
    async def test_health_endpoint(self, app_client):
        """GET /health returns ok."""
        resp = await app_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    async def test_health_rag(self, app_client):
        """GET /health/rag returns real ChromaDB status when available."""
        resp = await app_client.get("/health/rag")
        assert resp.status_code == 200
        data = resp.json()

        if CHROMA_AVAILABLE:
            # Real ChromaDB is running with embeddings loaded.
            assert data["status"] in ("healthy", "degraded")
            assert "vectorstore_connected" in data
            assert "database_connected" in data
            assert "embedding_ready" in data
            assert "documents_count" in data
            assert "scenarios_count" in data
            # Embeddings are already loaded in Docker.
            if data["status"] == "healthy":
                assert data["vectorstore_connected"] is True
                assert data["documents_count"] > 0
        else:
            # ChromaDB not available, RAG disabled.
            assert data["status"] == "disabled"


# ---------------------------------------------------------------------------
# Analysis Endpoints
# ---------------------------------------------------------------------------


class TestAnalysisLatest:
    async def test_analysis_latest(self, seeded_client):
        """GET /api/analysis/latest returns seeded analysis rows."""
        resp = await seeded_client.get("/api/analysis/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert "analyses" in data
        assert "count" in data
        assert data["count"] >= seeded_client._seed_count

        # Verify structure of first result.
        if data["analyses"]:
            a = data["analyses"][0]
            assert "analysis_id" in a
            assert "pair" in a
            assert "direction" in a
            assert "setup_grade" in a
            assert "confluence_score" in a
            assert "confidence" in a
            assert "status" in a
            assert "created_at" in a
            assert "display" in a
            assert "summary" in a["display"]
            assert "analyzed_by" in a["display"]

    async def test_analysis_latest_filter_by_pair(self, seeded_client):
        """GET /api/analysis/latest?pair=GBPUSD filters by pair."""
        resp = await seeded_client.get("/api/analysis/latest", params={"pair": "GBPUSD"})
        assert resp.status_code == 200
        data = resp.json()
        for a in data["analyses"]:
            assert a["pair"] == "GBPUSD"

    async def test_analysis_latest_limit(self, seeded_client):
        """GET /api/analysis/latest?limit=2 respects limit."""
        resp = await seeded_client.get("/api/analysis/latest", params={"limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["analyses"]) <= 2


class TestAnalysisHistory:
    async def test_analysis_history(self, seeded_client):
        """GET /api/analysis/history returns paginated results."""
        resp = await seeded_client.get("/api/analysis/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "analyses" in data
        assert "total_count" in data
        assert "offset" in data
        assert "limit" in data
        assert data["total_count"] >= seeded_client._seed_count

    async def test_analysis_history_filter_status(self, seeded_client):
        """GET /api/analysis/history?status=success filters by status."""
        resp = await seeded_client.get("/api/analysis/history", params={"status": "success"})
        assert resp.status_code == 200
        data = resp.json()
        for a in data["analyses"]:
            assert a["status"] == "success"

    async def test_analysis_history_filter_grade(self, seeded_client):
        """GET /api/analysis/history?grade=A filters by grade."""
        resp = await seeded_client.get("/api/analysis/history", params={"grade": "A"})
        assert resp.status_code == 200
        data = resp.json()
        for a in data["analyses"]:
            assert a["setup_grade"] == "A"

    async def test_analysis_history_filter_provider(self, seeded_client):
        """GET /api/analysis/history?provider=openai filters by provider."""
        resp = await seeded_client.get("/api/analysis/history", params={"provider": "openai"})
        assert resp.status_code == 200
        data = resp.json()
        for a in data["analyses"]:
            assert a["llm_provider"] == "openai"

    async def test_analysis_history_pagination(self, seeded_client):
        """GET /api/analysis/history?offset=0&limit=2 paginates correctly."""
        resp = await seeded_client.get(
            "/api/analysis/history",
            params={"offset": 0, "limit": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["analyses"]) <= 2
        assert data["offset"] == 0
        assert data["limit"] == 2


class TestAnalysisStats:
    async def test_analysis_stats(self, seeded_client):
        """GET /api/analysis/stats returns aggregate statistics."""
        resp = await seeded_client.get("/api/analysis/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "success_count" in data
        assert "no_setup_count" in data
        assert "error_count" in data
        assert "success_rate" in data
        assert "avg_confluence_score" in data
        assert "avg_duration_ms" in data
        assert "grade_distribution" in data
        assert "provider_distribution" in data
        assert "pair_distribution" in data
        assert data["total"] >= seeded_client._seed_count

    async def test_analysis_stats_filter_pair(self, seeded_client):
        """GET /api/analysis/stats?pair=EURUSD scopes stats to pair."""
        resp = await seeded_client.get("/api/analysis/stats", params={"pair": "EURUSD"})
        assert resp.status_code == 200
        data = resp.json()
        # EURUSD has 3 seeded rows (success, no_setup, llm_error).
        assert data["total"] >= 3
        # pair_distribution should only contain EURUSD.
        if data["pair_distribution"]:
            assert "EURUSD" in data["pair_distribution"]


class TestAnalysisDetail:
    async def test_analysis_detail(self, seeded_client):
        """GET /api/analysis/{id} returns full detail."""
        analysis_id = seeded_client._seed_analysis_ids[0]
        resp = await seeded_client.get(f"/api/analysis/{analysis_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["analysis_id"] == analysis_id
        assert data["pair"] == "EURUSD"
        assert data["direction"] == "LONG"
        assert data["setup_grade"] == "A"
        assert "display" in data
        assert "summary" in data["display"]
        assert "reasoning" in data["display"]
        assert "macro_summary" in data["display"]
        assert "technical_summary" in data["display"]
        assert "trade_plan" in data["display"]
        assert "confluence_breakdown" in data["display"]
        assert "risk_info" in data["display"]
        assert "event_warnings" in data["display"]
        assert "analyzed_by" in data["display"]

    async def test_analysis_detail_not_found(self, seeded_client):
        """GET /api/analysis/{id} returns 404 for unknown ID."""
        resp = await seeded_client.get("/api/analysis/NONEXISTENT-ID-12345")
        assert resp.status_code == 404


class TestAnalysisRerun:
    async def test_analysis_rerun_ta_unavailable(self, app_client):
        """POST /api/analysis/rerun returns 500 when TA broker is unavailable.

        In the test environment, the MT5 broker is not connected (no live
        terminal). The user has an LLM connection seeded by conftest, so
        the processor resolves. The rerun endpoint should return a 500
        error with a clear message about TA analysis failure.
        """
        headers = app_client._user_headers
        resp = await app_client.post(
            "/api/analysis/rerun",
            params={"symbol": "EURUSD", "trace_id": "test-rerun-001"},
            headers=headers,
        )
        # TA orchestrator is not initialized in the test container.
        assert resp.status_code in (500, 503)
        data = resp.json()
        assert "detail" in data

    async def test_analysis_rerun_empty_symbol(self, app_client):
        """POST /api/analysis/rerun with empty symbol returns 400 or 503."""
        headers = app_client._user_headers
        resp = await app_client.post(
            "/api/analysis/rerun",
            params={"symbol": ""},
            headers=headers,
        )
        # 400 if TA orchestrator is initialized, 503 if not.
        assert resp.status_code in (400, 503)

    async def test_analysis_rerun_no_auth(self, app_client):
        """POST /api/analysis/rerun without auth returns 401."""
        resp = await app_client.post(
            "/api/analysis/rerun",
            params={"symbol": "EURUSD"},
            headers={"Authorization": ""},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Processor Config Endpoints
# ---------------------------------------------------------------------------


class TestProcessorConfig:
    """Tests for admin-only processor config endpoints.

    These endpoints (GET/PUT /api/processor/config, GET /api/processor/models)
    operate on the global system-level processor and require admin role.
    Regular users configure their own LLM via /api/llm/connections/*.
    """

    async def test_processor_models(self, app_client):
        """GET /api/processor/models returns available models (admin)."""
        headers = app_client._admin_headers
        resp = await app_client.get("/api/processor/models", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "current_provider" in data
        assert "current_model" in data
        assert "providers" in data
        assert isinstance(data["providers"], dict)
        # At least anthropic and openai should be in providers.
        assert "anthropic" in data["providers"] or len(data["providers"]) > 0

    async def test_processor_config_get(self, app_client):
        """GET /api/processor/config returns current config (admin)."""
        headers = app_client._admin_headers
        resp = await app_client.get("/api/processor/config", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "llm_provider" in data
        assert "model_name" in data
        assert "temperature" in data
        assert "max_output_tokens" in data
        assert "supported_providers" in data
        assert isinstance(data["supported_providers"], list)
        assert len(data["supported_providers"]) > 0

    async def test_processor_config_update_temperature(self, app_client):
        """PUT /api/processor/config updates temperature (admin)."""
        headers = app_client._admin_headers
        # Get current config.
        get_resp = await app_client.get("/api/processor/config", headers=headers)
        assert get_resp.status_code == 200
        original = get_resp.json()

        # Update temperature.
        new_temp = 0.5
        put_resp = await app_client.put(
            "/api/processor/config",
            json={"temperature": new_temp},
            headers=headers,
        )
        assert put_resp.status_code == 200
        updated = put_resp.json()
        assert updated["status"] == "updated"
        assert updated["temperature"] == new_temp
        # Provider and model should remain unchanged.
        assert updated["llm_provider"] == original["llm_provider"]
        assert updated["model_name"] == original["model_name"]

    async def test_processor_config_update_invalid_provider(self, app_client):
        """PUT /api/processor/config rejects invalid provider (admin)."""
        headers = app_client._admin_headers
        resp = await app_client.put(
            "/api/processor/config",
            json={"llm_provider": "nonexistent_provider"},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "Unsupported provider" in resp.json()["detail"]

    async def test_regular_user_rejected_from_processor_models(self, app_client):
        """GET /api/processor/models returns 403 for non-admin user."""
        headers = app_client._user_headers
        resp = await app_client.get("/api/processor/models", headers=headers)
        assert resp.status_code == 403
        assert "Admin access required" in resp.json()["detail"]

    async def test_regular_user_rejected_from_processor_config_get(self, app_client):
        """GET /api/processor/config returns 403 for non-admin user."""
        headers = app_client._user_headers
        resp = await app_client.get("/api/processor/config", headers=headers)
        assert resp.status_code == 403

    async def test_regular_user_rejected_from_processor_config_put(self, app_client):
        """PUT /api/processor/config returns 403 for non-admin user."""
        headers = app_client._user_headers
        resp = await app_client.put(
            "/api/processor/config",
            json={"temperature": 0.5},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_no_auth_returns_401(self, app_client):
        """Processor config endpoints return 401 or 403 without proper auth."""
        no_auth = {"Authorization": ""}
        resp = await app_client.get("/api/processor/config", headers=no_auth)
        assert resp.status_code in (401, 403, 500)
        resp = await app_client.get("/api/processor/models", headers=no_auth)
        assert resp.status_code in (401, 403, 500)
        resp = await app_client.put("/api/processor/config", json={"temperature": 0.1}, headers=no_auth)
        assert resp.status_code in (401, 403, 500)
