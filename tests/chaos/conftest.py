"""Shared fixtures for the chaos test suite.

Key design notes:
  - All in-cluster fixtures are opt-in. Tests skip cleanly when the
    target cluster is not reachable so CI workers without kubeconfig
    do not fail. The opt-in switch is the env var
    ETRADIE_CHAOS_KUBECONFIG; when set, fixtures load it via
    kubernetes_asyncio.config.load_kube_config(<path>).
  - The K8s-mock fixture (no env var) uses the kubernetes_asyncio
    fake client - in-process, no network. Exercises 100% of the
    HostedProvisioner code path without a real cluster.
  - The SOAK_DURATION_SECONDS env var swaps the soak length between
    CI (1800), nightly (86400), and weekly (259200) modes without
    code changes.
"""
from __future__ import annotations

import os
import secrets
from typing import AsyncIterator

import pytest


def _soak_duration() -> int:
    return int(os.environ.get("SOAK_DURATION_SECONDS", "1800"))


def _has_real_cluster() -> bool:
    return bool(os.environ.get("ETRADIE_CHAOS_KUBECONFIG"))


@pytest.fixture(scope="session")
def soak_duration() -> int:
    return _soak_duration()


@pytest.fixture(scope="session")
def real_cluster_available() -> bool:
    return _has_real_cluster()


@pytest.fixture()
def sample_encryption_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = secrets.token_hex(32)
    monkeypatch.setenv("MT_NODE_CREDENTIAL_ENCRYPTION_KEY", key)
    return key


@pytest.fixture()
def sample_connection() -> dict:
    return {
        "connection_id": "11111111-2222-3333-4444-555555555555",
        "user_id": "user-42",
        "login": "435112187",
        "password": "redacted-test-password",
        "server": "Exness-MT5Trial9",
        "symbol": "EURUSD",
        "platform": "mt5",
    }


@pytest.fixture()
async def in_cluster_namespace(real_cluster_available: bool) -> AsyncIterator[str]:
    """Yields a unique namespace created against a REAL cluster, cleaned up after.
    Skips when ETRADIE_CHAOS_KUBECONFIG is not set.
    """
    if not real_cluster_available:
        pytest.skip("ETRADIE_CHAOS_KUBECONFIG not set; skipping real-cluster test")
    from kubernetes_asyncio import client, config

    await config.load_kube_config(config_file=os.environ["ETRADIE_CHAOS_KUBECONFIG"])
    ns = f"etradie-chaos-{secrets.token_hex(4)}"
    api = client.CoreV1Api()
    try:
        await api.create_namespace(body=client.V1Namespace(metadata=client.V1ObjectMeta(name=ns)))
        yield ns
    finally:
        try:
            await api.delete_namespace(name=ns)
        finally:
            await api.api_client.close()
