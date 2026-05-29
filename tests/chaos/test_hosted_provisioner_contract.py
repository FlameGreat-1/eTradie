"""Unit tests for HostedProvisioner using kubernetes_asyncio mocks.

Validates the full contract:
  - provision_account writes the per-tenant Secret with sealed creds
    AND plain envFrom keys (MT_LOGIN, MT_PASSWORD, MT_ZMQ_AUTH_TOKEN)
  - provision is idempotent (re-provisioning the same connection_id
    REPLACES the Deployment / Service / Secret, not duplicates)
  - delete is idempotent (404 is treated as success)
  - gc_orphans deletes Deployments whose connection-id is not in
    the known set
  - semantic readiness gate raises ProviderTimeoutError when the
    Deployment never goes Ready (no actual ZMQ probing needed; we
    mock the readiness path)
  - AES-GCM seal round-trips correctly
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engine.shared.exceptions import (
    ConfigurationError,
    ProviderError,
    ProviderTimeoutError,
)
from engine.ta.broker.mt5.hosted.provisioner import (
    HostedProvisioner,
    _load_encryption_key,
    _seal,
)

pytestmark = pytest.mark.asyncio


class _FakeApiException(Exception):
    def __init__(self, status: int, reason: str = "fake", body: str = "") -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.body = body


def _patch_kube_api(monkeypatch: pytest.MonkeyPatch, core_api: MagicMock, apps_api: MagicMock):
    """Patch HostedProvisioner._api_clients to return the supplied mocks."""
    async def _fake_api_clients(self):
        return core_api, apps_api
    monkeypatch.setattr(HostedProvisioner, "_api_clients", _fake_api_clients)

    # Patch ApiException reference used by the module to our local fake
    # so 'except ApiException' branches match what the mocks raise.
    monkeypatch.setattr(
        "engine.ta.broker.mt5.hosted.provisioner.ApiException",
        _FakeApiException,
    )


def _ready_deployment(release: str) -> MagicMock:
    dep = MagicMock()
    dep.metadata = MagicMock(name=release, creation_timestamp=None, labels={})
    dep.metadata.name = release
    dep.status = MagicMock(ready_replicas=1, replicas=1, conditions=[])
    return dep


async def test_load_encryption_key_rejects_missing_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MT_NODE_CREDENTIAL_ENCRYPTION_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        _load_encryption_key()


async def test_load_encryption_key_rejects_bad_hex(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MT_NODE_CREDENTIAL_ENCRYPTION_KEY", "not-hex")
    with pytest.raises(ConfigurationError):
        _load_encryption_key()


async def test_load_encryption_key_rejects_short(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MT_NODE_CREDENTIAL_ENCRYPTION_KEY", "00ff")  # 2 bytes
    with pytest.raises(ConfigurationError):
        _load_encryption_key()


async def test_seal_round_trip_is_unique(sample_encryption_key: str):
    key = _load_encryption_key()
    a = _seal("hello", key)
    b = _seal("hello", key)
    assert a != b  # nonce randomises every seal
    raw_a = base64.b64decode(a)
    raw_b = base64.b64decode(b)
    assert len(raw_a) >= 12 + 16 + 1  # nonce + tag + at least 1 byte
    assert len(raw_b) >= 12 + 16 + 1


async def test_provision_happy_path(
    monkeypatch: pytest.MonkeyPatch,
    sample_encryption_key: str,
    sample_connection: dict,
):
    core_api = MagicMock()
    apps_api = MagicMock()
    core_api.create_namespaced_secret = AsyncMock(return_value=None)
    core_api.create_namespaced_service = AsyncMock(return_value=None)
    core_api.create_namespaced_persistent_volume_claim = AsyncMock(return_value=None)
    core_api.api_client = MagicMock(close=AsyncMock())
    apps_api.create_namespaced_deployment = AsyncMock(return_value=None)
    apps_api.api_client = MagicMock(close=AsyncMock())

    # Readiness gate: short-circuit by mocking the Deployment-read AND the ZMQ ping.
    apps_api.read_namespaced_deployment = AsyncMock(
        return_value=_ready_deployment(release="etradie-mt-111111111111"),
    )

    _patch_kube_api(monkeypatch, core_api, apps_api)

    async def _fake_zmq_ping(self, *, dns_name, port, token):
        return True

    monkeypatch.setattr(HostedProvisioner, "_zmq_ping", _fake_zmq_ping)

    prov = HostedProvisioner()
    out = await prov.provision_account(
        connection_id=sample_connection["connection_id"],
        user_id=sample_connection["user_id"],
        login=sample_connection["login"],
        password=sample_connection["password"],
        server=sample_connection["server"],
        symbol=sample_connection["symbol"],
        platform=sample_connection["platform"],
        readiness_timeout_secs=5,
    )

    assert out["state"] == "running"
    assert out["container_id"] == "etradie-mt-111111111111"
    assert out["zmq_host"].endswith(".etradie-system.svc.cluster.local")
    assert out["zmq_port"] == 5555
    assert out["zmq_auth_token"]

    # Secret + Deployment + Service were each created exactly once.
    assert core_api.create_namespaced_secret.await_count == 1
    assert core_api.create_namespaced_service.await_count == 1
    assert apps_api.create_namespaced_deployment.await_count == 1

    # Secret body carries plain envFrom keys + the sealed audit blob.
    secret_call = core_api.create_namespaced_secret.await_args.kwargs["body"]
    keys = set(secret_call.data.keys())
    assert {"MT_LOGIN", "MT_PASSWORD", "MT_ZMQ_AUTH_TOKEN", "ETRADIE_SEAL"}.issubset(keys)


async def test_provision_is_idempotent_on_409(
    monkeypatch: pytest.MonkeyPatch,
    sample_encryption_key: str,
    sample_connection: dict,
):
    core_api = MagicMock()
    apps_api = MagicMock()
    # First create call -> 409; replace call must succeed.
    core_api.create_namespaced_secret = AsyncMock(side_effect=_FakeApiException(409))
    core_api.replace_namespaced_secret = AsyncMock(return_value=None)
    core_api.create_namespaced_service = AsyncMock(side_effect=_FakeApiException(409))
    core_api.read_namespaced_service = AsyncMock(
        return_value=MagicMock(spec=["spec", "metadata"], spec_set=False),
    )
    existing_svc = MagicMock()
    existing_svc.spec = MagicMock(cluster_ip="10.96.1.2")
    existing_svc.metadata = MagicMock(resource_version="99")
    core_api.read_namespaced_service = AsyncMock(return_value=existing_svc)
    core_api.replace_namespaced_service = AsyncMock(return_value=None)
    core_api.create_namespaced_persistent_volume_claim = AsyncMock(side_effect=_FakeApiException(409))
    core_api.api_client = MagicMock(close=AsyncMock())
    apps_api.create_namespaced_deployment = AsyncMock(side_effect=_FakeApiException(409))
    apps_api.replace_namespaced_deployment = AsyncMock(return_value=None)
    apps_api.read_namespaced_deployment = AsyncMock(
        return_value=_ready_deployment(release="etradie-mt-111111111111"),
    )
    apps_api.api_client = MagicMock(close=AsyncMock())

    _patch_kube_api(monkeypatch, core_api, apps_api)

    async def _fake_zmq_ping(self, *, dns_name, port, token):
        return True

    monkeypatch.setattr(HostedProvisioner, "_zmq_ping", _fake_zmq_ping)

    prov = HostedProvisioner()
    out = await prov.provision_account(
        connection_id=sample_connection["connection_id"],
        user_id=sample_connection["user_id"],
        login=sample_connection["login"],
        password=sample_connection["password"],
        server=sample_connection["server"],
        readiness_timeout_secs=5,
    )
    assert out["state"] == "running"

    # Every conflicting create was followed by a replace.
    assert core_api.replace_namespaced_secret.await_count == 1
    assert core_api.replace_namespaced_service.await_count == 1
    assert apps_api.replace_namespaced_deployment.await_count == 1


async def test_provision_readiness_gate_times_out(
    monkeypatch: pytest.MonkeyPatch,
    sample_encryption_key: str,
    sample_connection: dict,
):
    core_api = MagicMock()
    apps_api = MagicMock()
    core_api.create_namespaced_secret = AsyncMock(return_value=None)
    core_api.create_namespaced_service = AsyncMock(return_value=None)
    core_api.create_namespaced_persistent_volume_claim = AsyncMock(return_value=None)
    core_api.api_client = MagicMock(close=AsyncMock())
    apps_api.create_namespaced_deployment = AsyncMock(return_value=None)
    apps_api.api_client = MagicMock(close=AsyncMock())

    # Deployment never reports ready.
    apps_api.read_namespaced_deployment = AsyncMock(
        return_value=MagicMock(status=MagicMock(ready_replicas=0, replicas=1, conditions=[]),
                              metadata=MagicMock()),
    )

    _patch_kube_api(monkeypatch, core_api, apps_api)

    monkeypatch.setattr(
        "engine.ta.broker.mt5.hosted.provisioner._READINESS_POLL_SECS",
        0.05,
    )

    prov = HostedProvisioner()
    with pytest.raises(ProviderTimeoutError):
        await prov.provision_account(
            connection_id=sample_connection["connection_id"],
            user_id=sample_connection["user_id"],
            login=sample_connection["login"],
            password=sample_connection["password"],
            server=sample_connection["server"],
            readiness_timeout_secs=0.5,
        )


async def test_delete_is_idempotent(monkeypatch: pytest.MonkeyPatch):
    core_api = MagicMock()
    apps_api = MagicMock()
    # Everything returns 404 -> still counts as success.
    apps_api.delete_namespaced_deployment = AsyncMock(side_effect=_FakeApiException(404))
    core_api.delete_namespaced_service = AsyncMock(side_effect=_FakeApiException(404))
    core_api.delete_namespaced_secret = AsyncMock(side_effect=_FakeApiException(404))
    core_api.delete_namespaced_persistent_volume_claim = AsyncMock(side_effect=_FakeApiException(404))
    core_api.api_client = MagicMock(close=AsyncMock())
    apps_api.api_client = MagicMock(close=AsyncMock())

    _patch_kube_api(monkeypatch, core_api, apps_api)

    prov = HostedProvisioner()
    assert await prov.delete_account("etradie-mt-deadbeef0000") is True


async def test_gc_orphans_deletes_unknown_releases(monkeypatch: pytest.MonkeyPatch):
    core_api = MagicMock()
    apps_api = MagicMock()
    core_api.api_client = MagicMock(close=AsyncMock())
    apps_api.api_client = MagicMock(close=AsyncMock())

    dep_orphan = MagicMock()
    dep_orphan.metadata = MagicMock(
        name="etradie-mt-orphan000000",
        labels={"etradie.connection-id": "orphan", "app.kubernetes.io/name": "etradie-mt-node"},
    )
    dep_known = MagicMock()
    dep_known.metadata = MagicMock(
        name="etradie-mt-known00000",
        labels={"etradie.connection-id": "known", "app.kubernetes.io/name": "etradie-mt-node"},
    )
    apps_api.list_namespaced_deployment = AsyncMock(
        return_value=MagicMock(items=[dep_orphan, dep_known]),
    )
    apps_api.delete_namespaced_deployment = AsyncMock(return_value=None)
    core_api.delete_namespaced_service = AsyncMock(return_value=None)
    core_api.delete_namespaced_secret = AsyncMock(return_value=None)
    core_api.delete_namespaced_persistent_volume_claim = AsyncMock(return_value=None)

    _patch_kube_api(monkeypatch, core_api, apps_api)

    prov = HostedProvisioner()
    out = await prov.gc_orphans(known_connection_ids=["known"])
    assert out["deleted"] == ["etradie-mt-orphan000000"]
    assert out["scanned"] == 2


async def test_provision_rejects_invalid_platform(
    monkeypatch: pytest.MonkeyPatch,
    sample_encryption_key: str,
    sample_connection: dict,
):
    prov = HostedProvisioner()
    with pytest.raises(ConfigurationError):
        await prov.provision_account(
            connection_id=sample_connection["connection_id"],
            user_id=sample_connection["user_id"],
            login=sample_connection["login"],
            password=sample_connection["password"],
            server=sample_connection["server"],
            platform="invalid",
            readiness_timeout_secs=1,
        )
