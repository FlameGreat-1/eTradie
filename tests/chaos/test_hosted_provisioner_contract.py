"""Unit tests for HostedProvisioner using kubernetes_asyncio mocks.

Validates the full contract against the live Vault/StatefulSet API:
  - provision_account writes per-tenant credentials to Vault (login,
    password, zmq auth token) and upserts the ServiceAccount, watchdog
    ConfigMap, StatefulSet, and BOTH the regular + headless Services.
  - provision is idempotent (a 409 on any create is followed by a
    read + replace, never a duplicate).
  - the readiness gate raises ProviderTimeoutError when the StatefulSet
    never reports a Ready replica (the ZMQ PING is mocked out).
  - delete is idempotent (404 is treated as success), removes both
    Services, the per-replica wine-prefix PVC, and destroys the Vault
    tenant path.
  - gc_orphans deletes StatefulSets whose connection-id label is not in
    the known set.
  - _write_vault_credentials writes the three documented keys and
    returns a stable digest.
  - construction / argument validation fail closed (missing Vault,
    missing catalog/chart hooks, invalid platform).

The HostedProvisioner emits StatefulSets (matching the helm/mt-node
chart shape), so these tests exercise the *_namespaced_stateful_set
call surface on the AppsV1Api mock and the Vault write/destroy surface
on a fake VaultClient.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from engine.shared.exceptions import (
    ConfigurationError,
    ProviderTimeoutError,
)
from engine.ta.broker.mt5.hosted.provisioner import (
    HostedProvisioner,
    _pvc_name_for,
    release_name_for,
)

pytestmark = pytest.mark.asyncio

# release_name_for("11111111-2222-...") == "etradie-mt-" + first 12 chars
# of the connection_id == "etradie-mt-111111111111".
_RELEASE = "etradie-mt-11111111-222"


class _FakeApiException(Exception):
    def __init__(self, status: int, reason: str = "fake", body: str = "") -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.body = body


def _patch_kube_api(monkeypatch: pytest.MonkeyPatch, core_api: MagicMock, apps_api: MagicMock) -> None:
    """Patch HostedProvisioner._api_clients to return the supplied mocks
    and swap the module's ApiException for our local fake so the
    provisioner's `except ApiException` branches match what the mocks
    raise.
    """

    async def _fake_api_clients(self):
        return core_api, apps_api

    monkeypatch.setattr(HostedProvisioner, "_api_clients", _fake_api_clients)
    monkeypatch.setattr(
        "engine.ta.broker.mt5.hosted.provisioner.ApiException",
        _FakeApiException,
    )


def _ready_statefulset() -> MagicMock:
    sts = MagicMock()
    sts.metadata = MagicMock(creation_timestamp=None, labels={})
    sts.metadata.name = _RELEASE
    sts.status = MagicMock(ready_replicas=1, replicas=1, current_replicas=1, conditions=[])
    return sts


def _unready_statefulset() -> MagicMock:
    sts = MagicMock()
    sts.metadata = MagicMock(creation_timestamp=None, labels={})
    sts.metadata.name = _RELEASE
    sts.status = MagicMock(ready_replicas=0, replicas=1, current_replicas=0, conditions=[])
    return sts


def _fake_vault() -> MagicMock:
    vault = MagicMock()
    vault.write_kv = AsyncMock(return_value=None)
    vault.destroy_all_versions = AsyncMock(return_value=None)
    return vault


def _make_provisioner(vault: MagicMock | None = None) -> HostedProvisioner:
    """Construct a fully-wired provisioner with async catalog/chart hooks."""
    return HostedProvisioner(
        namespace="etradie-system",
        image="etradie-mt-node:test",
        vault_client=vault if vault is not None else _fake_vault(),
        catalog_sync_runner=AsyncMock(return_value="EURUSD"),
        chart_symbol_writer=AsyncMock(return_value=None),
    )


# ---------------------------------------------------------------------------
# Naming conventions
# ---------------------------------------------------------------------------


async def test_release_name_matches_connection_prefix(sample_connection: dict):
    assert release_name_for(sample_connection["connection_id"]) == _RELEASE


async def test_pvc_name_matches_statefulset_convention():
    """The provisioner's PVC naming must match the chart's STS
    volumeClaimTemplate output: '<template>-<sts>-<ordinal>'.
    With template='wine-prefix' and ordinal=0, the per-replica PVC is
    'wine-prefix-<release>-0'. An operator who flips a tenant between
    chart-managed and provisioner-managed paths must NOT lose the Wine
    prefix - this convention is the contract that makes it safe."""
    assert _pvc_name_for(_RELEASE) == f"wine-prefix-{_RELEASE}-0"


# ---------------------------------------------------------------------------
# Vault credential write
# ---------------------------------------------------------------------------


async def test_write_vault_credentials_writes_three_keys_and_returns_stable_hash():
    vault = _fake_vault()
    prov = _make_provisioner(vault)

    digest_a = await prov._write_vault_credentials(
        vault=vault,
        path="etradie/tenants/mt-node/etradie-mt-111111111111",
        login="435112187",
        password="redacted-test-password",
        token="deadbeef" * 8,
    )

    assert vault.write_kv.await_count == 1
    written_path, written_data = vault.write_kv.await_args.args
    assert written_path == "etradie/tenants/mt-node/etradie-mt-111111111111"
    assert set(written_data.keys()) == {"mt5_login", "mt5_password", "mt5_zmq_auth_token"}
    assert written_data["mt5_login"] == "435112187"
    assert written_data["mt5_zmq_auth_token"] == "deadbeef" * 8

    # Digest is a deterministic function of the payload.
    digest_b = await prov._write_vault_credentials(
        vault=vault,
        path="etradie/tenants/mt-node/etradie-mt-111111111111",
        login="435112187",
        password="redacted-test-password",
        token="deadbeef" * 8,
    )
    assert digest_a == digest_b
    assert len(digest_a) == 64  # sha256 hexdigest


# ---------------------------------------------------------------------------
# provision_account - happy path
# ---------------------------------------------------------------------------


async def test_provision_happy_path(
    monkeypatch: pytest.MonkeyPatch,
    sample_connection: dict,
):
    vault = _fake_vault()
    core_api = MagicMock()
    apps_api = MagicMock()
    core_api.create_namespaced_service_account = AsyncMock(return_value=None)
    core_api.create_namespaced_config_map = AsyncMock(return_value=None)
    core_api.create_namespaced_service = AsyncMock(return_value=None)
    core_api.api_client = MagicMock(close=AsyncMock())
    apps_api.create_namespaced_stateful_set = AsyncMock(return_value=None)
    apps_api.patch_namespaced_stateful_set = AsyncMock(return_value=None)
    apps_api.read_namespaced_stateful_set = AsyncMock(return_value=_ready_statefulset())
    apps_api.api_client = MagicMock(close=AsyncMock())

    _patch_kube_api(monkeypatch, core_api, apps_api)

    async def _fake_zmq_ping(self, *, dns_name, port, token):
        return True

    monkeypatch.setattr(HostedProvisioner, "_zmq_ping", _fake_zmq_ping)

    prov = _make_provisioner(vault)
    out = await prov.provision_account(
        connection_id=sample_connection["connection_id"],
        user_id=sample_connection["user_id"],
        login=sample_connection["login"],
        password=sample_connection["password"],
        server=sample_connection["server"],
        platform=sample_connection["platform"],
        readiness_timeout_secs=5,
    )

    assert out["state"] == "running"
    assert out["container_id"] == _RELEASE
    assert out["zmq_host"] == f"{_RELEASE}.etradie-system.svc.cluster.local"
    assert out["zmq_port"] == 5555
    assert out["zmq_auth_token"]
    assert out["chart_symbol"] == "EURUSD"

    # Credentials went to Vault, not a sealed Secret.
    assert vault.write_kv.await_count == 1

    # ServiceAccount + watchdog ConfigMap + StatefulSet + BOTH Services
    # (regular + headless) were each created exactly once.
    assert core_api.create_namespaced_service_account.await_count == 1
    assert core_api.create_namespaced_config_map.await_count == 1
    assert apps_api.create_namespaced_stateful_set.await_count == 1
    assert core_api.create_namespaced_service.await_count == 2

    # The two service-create calls are one headless (clusterIP="None")
    # and one regular (clusterIP unset, allocated by K8s).
    cluster_ips = [call.kwargs["body"].spec.cluster_ip for call in core_api.create_namespaced_service.await_args_list]
    assert "None" in cluster_ips
    assert any(ip is None for ip in cluster_ips)

    # Catalog hand-off + symbol patch + DB write-back all ran.
    prov._catalog_sync_runner.assert_awaited_once()
    assert apps_api.patch_namespaced_stateful_set.await_count == 1
    prov._chart_symbol_writer.assert_awaited_once_with(sample_connection["connection_id"], "EURUSD")


async def test_provision_is_idempotent_on_409(
    monkeypatch: pytest.MonkeyPatch,
    sample_connection: dict,
):
    vault = _fake_vault()
    core_api = MagicMock()
    apps_api = MagicMock()

    # Every create returns 409; each must be followed by a read + replace.
    core_api.create_namespaced_service_account = AsyncMock(side_effect=_FakeApiException(409))
    existing_sa = MagicMock()
    existing_sa.metadata = MagicMock(resource_version="11")
    core_api.read_namespaced_service_account = AsyncMock(return_value=existing_sa)
    core_api.replace_namespaced_service_account = AsyncMock(return_value=None)

    core_api.create_namespaced_config_map = AsyncMock(side_effect=_FakeApiException(409))
    existing_cm = MagicMock()
    existing_cm.metadata = MagicMock(resource_version="22")
    core_api.read_namespaced_config_map = AsyncMock(return_value=existing_cm)
    core_api.replace_namespaced_config_map = AsyncMock(return_value=None)

    core_api.create_namespaced_service = AsyncMock(side_effect=_FakeApiException(409))
    existing_svc = MagicMock()
    existing_svc.spec = MagicMock(cluster_ip="10.96.1.2")
    existing_svc.metadata = MagicMock(resource_version="33")
    core_api.read_namespaced_service = AsyncMock(return_value=existing_svc)
    core_api.replace_namespaced_service = AsyncMock(return_value=None)
    core_api.api_client = MagicMock(close=AsyncMock())

    apps_api.create_namespaced_stateful_set = AsyncMock(side_effect=_FakeApiException(409))
    existing_sts = MagicMock()
    existing_sts.metadata = MagicMock(resource_version="44")
    apps_api.read_namespaced_stateful_set = AsyncMock(side_effect=[existing_sts, _ready_statefulset()])
    apps_api.replace_namespaced_stateful_set = AsyncMock(return_value=None)
    apps_api.patch_namespaced_stateful_set = AsyncMock(return_value=None)
    apps_api.api_client = MagicMock(close=AsyncMock())

    _patch_kube_api(monkeypatch, core_api, apps_api)

    async def _fake_zmq_ping(self, *, dns_name, port, token):
        return True

    monkeypatch.setattr(HostedProvisioner, "_zmq_ping", _fake_zmq_ping)

    prov = _make_provisioner(vault)
    out = await prov.provision_account(
        connection_id=sample_connection["connection_id"],
        user_id=sample_connection["user_id"],
        login=sample_connection["login"],
        password=sample_connection["password"],
        server=sample_connection["server"],
        readiness_timeout_secs=5,
    )
    assert out["state"] == "running"

    # Every conflicting create was followed by a replace. Two services
    # (regular + headless) are upserted, so the service replace count is 2.
    assert core_api.replace_namespaced_service_account.await_count == 1
    assert core_api.replace_namespaced_config_map.await_count == 1
    assert core_api.replace_namespaced_service.await_count == 2
    assert apps_api.replace_namespaced_stateful_set.await_count == 1


async def test_provision_readiness_gate_times_out(
    monkeypatch: pytest.MonkeyPatch,
    sample_connection: dict,
):
    vault = _fake_vault()
    core_api = MagicMock()
    apps_api = MagicMock()
    core_api.create_namespaced_service_account = AsyncMock(return_value=None)
    core_api.create_namespaced_config_map = AsyncMock(return_value=None)
    core_api.create_namespaced_service = AsyncMock(return_value=None)
    # Best-effort rollback after the timeout deletes everything.
    core_api.delete_namespaced_service = AsyncMock(return_value=None)
    core_api.delete_namespaced_service_account = AsyncMock(return_value=None)
    core_api.delete_namespaced_secret = AsyncMock(return_value=None)
    core_api.delete_namespaced_config_map = AsyncMock(return_value=None)
    core_api.delete_namespaced_persistent_volume_claim = AsyncMock(return_value=None)
    core_api.api_client = MagicMock(close=AsyncMock())
    apps_api.create_namespaced_stateful_set = AsyncMock(return_value=None)
    apps_api.delete_namespaced_stateful_set = AsyncMock(return_value=None)
    # StatefulSet never reports Ready.
    apps_api.read_namespaced_stateful_set = AsyncMock(return_value=_unready_statefulset())
    apps_api.api_client = MagicMock(close=AsyncMock())

    _patch_kube_api(monkeypatch, core_api, apps_api)
    monkeypatch.setattr(
        "engine.ta.broker.mt5.hosted.provisioner._READINESS_POLL_SECS",
        0.01,
    )

    prov = _make_provisioner(vault)
    with pytest.raises(ProviderTimeoutError):
        await prov.provision_account(
            connection_id=sample_connection["connection_id"],
            user_id=sample_connection["user_id"],
            login=sample_connection["login"],
            password=sample_connection["password"],
            server=sample_connection["server"],
            readiness_timeout_secs=0.2,
        )


# ---------------------------------------------------------------------------
# delete_account
# ---------------------------------------------------------------------------


async def test_delete_is_idempotent(monkeypatch: pytest.MonkeyPatch):
    vault = _fake_vault()
    core_api = MagicMock()
    apps_api = MagicMock()
    # Everything returns 404 -> still counts as success.
    apps_api.delete_namespaced_stateful_set = AsyncMock(side_effect=_FakeApiException(404))
    core_api.delete_namespaced_service = AsyncMock(side_effect=_FakeApiException(404))
    core_api.delete_namespaced_service_account = AsyncMock(side_effect=_FakeApiException(404))
    core_api.delete_namespaced_secret = AsyncMock(side_effect=_FakeApiException(404))
    core_api.delete_namespaced_config_map = AsyncMock(side_effect=_FakeApiException(404))
    core_api.delete_namespaced_persistent_volume_claim = AsyncMock(side_effect=_FakeApiException(404))
    core_api.api_client = MagicMock(close=AsyncMock())
    apps_api.api_client = MagicMock(close=AsyncMock())

    _patch_kube_api(monkeypatch, core_api, apps_api)

    prov = _make_provisioner(vault)
    assert await prov.delete_account(_RELEASE) is True

    # Both the regular AND the headless service were deleted.
    assert core_api.delete_namespaced_service.await_count == 2

    # The per-replica wine-prefix PVC ('wine-prefix-<release>-0') was
    # deleted explicitly because StatefulSet GC does not cascade to its
    # volumeClaimTemplate PVCs.
    pvc_deletion_names = [
        call.kwargs["name"] for call in core_api.delete_namespaced_persistent_volume_claim.await_args_list
    ]
    assert f"wine-prefix-{_RELEASE}-0" in pvc_deletion_names

    # The Vault tenant path was destroyed.
    assert vault.destroy_all_versions.await_count == 1


async def test_gc_orphans_deletes_unknown_releases(monkeypatch: pytest.MonkeyPatch):
    vault = _fake_vault()
    core_api = MagicMock()
    apps_api = MagicMock()
    core_api.api_client = MagicMock(close=AsyncMock())
    apps_api.api_client = MagicMock(close=AsyncMock())

    sts_orphan = MagicMock()
    sts_orphan.metadata = MagicMock(
        name="etradie-mt-orphan000000",
        labels={
            "etradie.connection-id": "orphan",
            "app.kubernetes.io/name": "etradie-mt-node",
        },
    )
    sts_orphan.metadata.name = "etradie-mt-orphan000000"
    sts_known = MagicMock()
    sts_known.metadata = MagicMock(
        name="etradie-mt-known00000",
        labels={
            "etradie.connection-id": "known",
            "app.kubernetes.io/name": "etradie-mt-node",
        },
    )
    sts_known.metadata.name = "etradie-mt-known00000"
    apps_api.list_namespaced_stateful_set = AsyncMock(
        return_value=MagicMock(items=[sts_orphan, sts_known]),
    )
    apps_api.delete_namespaced_stateful_set = AsyncMock(return_value=None)
    core_api.delete_namespaced_service = AsyncMock(return_value=None)
    core_api.delete_namespaced_service_account = AsyncMock(return_value=None)
    core_api.delete_namespaced_secret = AsyncMock(return_value=None)
    core_api.delete_namespaced_config_map = AsyncMock(return_value=None)
    core_api.delete_namespaced_persistent_volume_claim = AsyncMock(return_value=None)

    _patch_kube_api(monkeypatch, core_api, apps_api)

    prov = _make_provisioner(vault)
    out = await prov.gc_orphans(known_connection_ids=["known"])
    assert out["deleted"] == ["etradie-mt-orphan000000"]
    assert out["scanned"] == 2
    # The orphan's Vault tenant path was destroyed; the known one was not.
    assert vault.destroy_all_versions.await_count == 1


# ---------------------------------------------------------------------------
# Construction / argument validation (fail closed)
# ---------------------------------------------------------------------------


async def test_provision_rejects_invalid_platform(sample_connection: dict):
    prov = _make_provisioner()
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


async def test_provision_requires_vault_client(sample_connection: dict):
    prov = HostedProvisioner(
        namespace="etradie-system",
        image="etradie-mt-node:test",
        vault_client=None,
        catalog_sync_runner=AsyncMock(return_value="EURUSD"),
        chart_symbol_writer=AsyncMock(return_value=None),
    )
    with pytest.raises(ConfigurationError):
        await prov.provision_account(
            connection_id=sample_connection["connection_id"],
            user_id=sample_connection["user_id"],
            login=sample_connection["login"],
            password=sample_connection["password"],
            server=sample_connection["server"],
            readiness_timeout_secs=1,
        )


async def test_provision_requires_catalog_and_chart_hooks(sample_connection: dict):
    prov = HostedProvisioner(
        namespace="etradie-system",
        image="etradie-mt-node:test",
        vault_client=_fake_vault(),
        catalog_sync_runner=None,
        chart_symbol_writer=None,
    )
    with pytest.raises(ConfigurationError):
        await prov.provision_account(
            connection_id=sample_connection["connection_id"],
            user_id=sample_connection["user_id"],
            login=sample_connection["login"],
            password=sample_connection["password"],
            server=sample_connection["server"],
            readiness_timeout_secs=1,
        )
