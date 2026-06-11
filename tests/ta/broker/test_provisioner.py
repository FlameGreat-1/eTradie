"""Unit tests for the Hosted MetaTrader StatefulSet provisioner.

The provisioner (src/engine/ta/broker/mt5/hosted/provisioner.py) is
StatefulSet-based: provision_account() upserts a per-tenant
StatefulSet + Services, and the MetaTrader platform is carried on the
MT_PLATFORM env var of the mt-node container. These tests assert that
env contract for both platforms and that invalid platforms are
rejected before any Kubernetes call is made.

No real K8s, no real Vault, no real DB. Mirrors the mocking pattern in
tests/integration/test_hosted_provisioner_release_naming.py.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from engine.shared.exceptions import ConfigurationError
from engine.ta.broker.mt5.hosted.provisioner import (
    SYMBOL_PENDING_SENTINEL,
    HostedProvisioner,
    headless_service_name_for,
    release_name_for,
)

pytestmark = pytest.mark.unit

CONNECTION_ID = "conn_1234567890"
USER_ID = "user-1"
SERVER = "Test-Server"


def _build_provisioner() -> HostedProvisioner:
    """Provisioner with every required dependency injected as a fake."""

    async def catalog_sync_runner(*, dns_name, zmq_port, auth_token):
        return "EURUSDm"

    async def chart_symbol_writer(connection_id: str, chart_symbol: str) -> None:
        return None

    return HostedProvisioner(
        namespace="etradie-system",
        image="ghcr.io/test/etradie-mt-node:0.0.0",
        vault_client=AsyncMock(),
        catalog_sync_runner=catalog_sync_runner,
        chart_symbol_writer=chart_symbol_writer,
    )


async def _captured_statefulset(provisioner: HostedProvisioner, platform: str):
    """Run _upsert_statefulset against a mocked AppsV1Api and return
    the V1StatefulSet body the provisioner built."""
    apps_api = AsyncMock()
    captured: dict[str, object] = {}

    async def capture_create_sts(*, namespace, body):
        captured["statefulset"] = body

    apps_api.create_namespaced_stateful_set.side_effect = capture_create_sts

    release = release_name_for(CONNECTION_ID)
    labels = provisioner._labels(CONNECTION_ID, USER_ID, platform, release)
    selector = provisioner._selector_labels(CONNECTION_ID, release)

    await provisioner._upsert_statefulset(
        apps_api=apps_api,
        release=release,
        headless_service_name=headless_service_name_for(release),
        labels=labels,
        selector=selector,
        platform=platform,
        server=SERVER,
        symbol=SYMBOL_PENDING_SENTINEL,
        zmq_port=5555,
        vault_path=f"tenants/mt-node/{release}",
        sa_name=release,
        credentials_checksum="deadbeef",
    )

    apps_api.create_namespaced_stateful_set.assert_called_once()
    return captured["statefulset"]


class TestHostedProvisioner:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("platform", ["mt4", "mt5"])
    async def test_statefulset_carries_platform_env(self, platform):
        """The mt-node container env must carry the requested platform."""
        provisioner = _build_provisioner()

        sts = await _captured_statefulset(provisioner, platform)

        assert sts.metadata.name == release_name_for(CONNECTION_ID)
        assert sts.metadata.labels["etradie.platform"] == platform

        container = sts.spec.template.spec.containers[0]
        assert container.name == "mt-node"

        # fieldRef-sourced vars (POD_NAME/POD_NAMESPACE) have value=None;
        # only value-carrying vars participate in this contract.
        env = {e.name: e.value for e in container.env if e.value is not None}
        assert env["MT_PLATFORM"] == platform
        assert env["MT_SERVER"] == SERVER
        assert env["MT_SYMBOL"] == SYMBOL_PENDING_SENTINEL

    @pytest.mark.asyncio
    async def test_provision_account_rejects_invalid_platform(self):
        """provision_account must fail loudly on a platform outside
        {mt4, mt5} before touching Vault or the Kubernetes API."""
        provisioner = _build_provisioner()

        with pytest.raises(ConfigurationError):
            await provisioner.provision_account(
                connection_id=CONNECTION_ID,
                user_id=USER_ID,
                login="12345",
                password="pwd",
                server=SERVER,
                platform="mt3",
            )
