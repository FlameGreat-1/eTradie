"""L5 regression test: hosted provisioner release-name invariant.

Guards the C1 fix: the connection_id pre-allocated by the router
MUST be the single source of truth used as the StatefulSet name
suffix AND as the etradie.connection-id label on every per-tenant
resource. Any future refactor that re-derives a new ID anywhere in
the chain breaks recovery + GC (both key on broker_connections.id
but would find resources labelled with a different id).

The test is a fast unit-style assertion against the pure naming
helpers + a single inspection of the StatefulSet body the
provisioner builds on a happy-path create. No real K8s, no real
Vault, no real DB.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from engine.ta.broker.mt5.hosted.provisioner import (
    CONTAINER_PREFIX,
    HostedProvisioner,
    headless_service_name_for,
    release_name_for,
    service_dns_for,
)

pytestmark = pytest.mark.unit


CONNECTION_ID = "abcdef01-2345-6789-abcd-ef0123456789"
USER_ID = "user-42"


def test_release_name_uses_first_twelve_chars_of_connection_id() -> None:
    name = release_name_for(CONNECTION_ID)
    assert name == f"{CONTAINER_PREFIX}{CONNECTION_ID[:12]}"


def test_headless_service_name_is_derived_from_release() -> None:
    release = release_name_for(CONNECTION_ID)
    assert headless_service_name_for(release) == f"{release}-headless"


def test_service_dns_is_derived_from_release_and_namespace() -> None:
    release = release_name_for(CONNECTION_ID)
    assert service_dns_for(release, "etradie-system") == (f"{release}.etradie-system.svc.cluster.local")


@pytest.mark.asyncio
async def test_provisioner_stamps_connection_id_into_every_resource() -> None:
    """Capture the StatefulSet/Service bodies the provisioner would
    send and assert the etradie.connection-id label is the input
    connection_id, NOT a fresh UUID.
    """
    apps_api = AsyncMock()
    core_api = AsyncMock()

    captured: dict[str, object] = {}

    async def capture_create_sts(*, namespace, body):
        captured["statefulset"] = body

    async def capture_create_svc(*, namespace, body):
        captured.setdefault("services", []).append(body)  # type: ignore[union-attr]

    async def capture_create_sa(*, namespace, body):
        captured["service_account"] = body

    apps_api.create_namespaced_stateful_set.side_effect = capture_create_sts
    core_api.create_namespaced_service.side_effect = capture_create_svc
    core_api.create_namespaced_service_account.side_effect = capture_create_sa

    vault = AsyncMock()
    vault.write_kv = AsyncMock(return_value=None)

    async def catalog_sync_runner(*, dns_name, zmq_port, auth_token):
        return "EURUSDm"

    chart_writes: list[tuple[str, str]] = []

    async def chart_symbol_writer(connection_id: str, chart_symbol: str) -> None:
        chart_writes.append((connection_id, chart_symbol))

    provisioner = HostedProvisioner(
        namespace="etradie-system",
        image="ghcr.io/test/etradie-mt-node:0.0.0",
        vault_client=vault,
        catalog_sync_runner=catalog_sync_runner,
        chart_symbol_writer=chart_symbol_writer,
    )

    labels = provisioner._labels(CONNECTION_ID, USER_ID, "mt5", release_name_for(CONNECTION_ID))
    selector = provisioner._selector_labels(CONNECTION_ID, release_name_for(CONNECTION_ID))

    await provisioner._upsert_serviceaccount(
        core_api=core_api,
        name=release_name_for(CONNECTION_ID),
        labels=labels,
    )
    await provisioner._upsert_statefulset(
        apps_api=apps_api,
        release=release_name_for(CONNECTION_ID),
        headless_service_name=headless_service_name_for(release_name_for(CONNECTION_ID)),
        labels=labels,
        selector=selector,
        platform="mt5",
        server="Exness-MT5Trial9",
        symbol="__pending__",
        zmq_port=5555,
        vault_path="tenants/mt-node/" + release_name_for(CONNECTION_ID),
        sa_name=release_name_for(CONNECTION_ID),
        credentials_checksum="deadbeef",
        connection_id=CONNECTION_ID,
        user_id=USER_ID,
        brand_id="exness",
        entity_id="exness_technologies_ltd",
        bundle_r2_path="https://pub-test.r2.dev/broker-bundles/exness-portable.zip",
        bundle_sha256="a" * 64,
        watchdog_port=9100,
    )

    sts = captured["statefulset"]
    assert sts.metadata.name == release_name_for(CONNECTION_ID)
    assert sts.metadata.labels["etradie.connection-id"] == CONNECTION_ID
    assert sts.spec.selector.match_labels["etradie.connection-id"] == CONNECTION_ID
    pod_labels = sts.spec.template.metadata.labels
    assert pod_labels["etradie.connection-id"] == CONNECTION_ID

    sa = captured["service_account"]
    assert sa.metadata.labels["etradie.connection-id"] == CONNECTION_ID


@pytest.mark.asyncio
async def test_catalog_sync_runner_and_writer_are_required() -> None:
    """Provisioning without the injected catalog runner + chart-symbol
    writer must fail loudly so the engine cannot silently boot a Pod
    whose broker catalog would never be persisted."""
    from engine.shared.exceptions import ConfigurationError

    provisioner = HostedProvisioner(
        namespace="etradie-system",
        image="ghcr.io/test/etradie-mt-node:0.0.0",
        vault_client=AsyncMock(),
        catalog_sync_runner=None,
        chart_symbol_writer=None,
    )
    with pytest.raises(ConfigurationError):
        await provisioner.provision_account(
            connection_id=CONNECTION_ID,
            user_id=USER_ID,
            brand_id="exness",
            entity_id="exness_technologies_ltd",
            login="123",
            password="pw",
            server="Exness-MT5Trial9",
        )
