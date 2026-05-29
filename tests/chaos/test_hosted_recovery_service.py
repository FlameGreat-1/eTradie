"""Chaos tests for engine.ta.broker.mt5.hosted.recovery.HostedRecoveryService.

In-process unit tests using MagicMock + AsyncMock; no real K8s cluster
required. Cover the four CHECKLIST Section 8 disaster scenarios.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from engine.shared.exceptions import (
    ConfigurationError,
    ProviderTimeoutError,
)
from engine.ta.broker.mt5.hosted.recovery import (
    HostedRecoveryConfig,
    HostedRecoveryService,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(connection_id: str, user_id: str = "user-1") -> MagicMock:
    row = MagicMock()
    row.id = connection_id
    row.user_id = user_id
    row.platform = "mt5"
    row.mt5_server = "Exness-MT5Trial9"
    row.mt5_login = "123456"
    row.mt5_password_encrypted = "gAAAAA-fake-fernet-ciphertext"
    return row


def _make_db_with_rows(rows: list) -> MagicMock:
    """Build a fake DatabaseManager whose read_session() yields a session
    that returns `rows` from any select()."""
    db = MagicMock()

    scalar_result = MagicMock()
    scalar_result.all = MagicMock(return_value=rows)
    exec_result = MagicMock()
    exec_result.scalars = MagicMock(return_value=scalar_result)

    session = MagicMock()
    session.execute = AsyncMock(return_value=exec_result)

    class _SessionCtx:
        async def __aenter__(self):
            return session
        async def __aexit__(self, *exc):
            return False

    db.read_session = MagicMock(return_value=_SessionCtx())
    return db


def _make_provisioner(
    status_by_release: dict[str, dict] | None = None,
    provision_side_effect=None,
) -> MagicMock:
    """Build a fake HostedProvisioner.

    - get_account_status returns the configured dict for each release,
      defaulting to a missing-StatefulSet response.
    - provision_account is an AsyncMock; pass `side_effect` to inject
      a failure.
    """
    status_by_release = status_by_release or {}
    p = MagicMock()

    p._release_name = lambda connection_id: f"etradie-mt-{connection_id[:12]}"

    async def _get_status(release: str) -> dict:
        if release in status_by_release:
            return status_by_release[release]
        return {"status": "removed", "running": False, "ready_replicas": 0}

    p.get_account_status = AsyncMock(side_effect=_get_status)
    p.provision_account = AsyncMock(side_effect=provision_side_effect)
    return p


def _make_config(
    enabled: bool = True,
    sweep_interval_secs: float = 60.0,
    unhealthy_threshold_secs: float = 600.0,
    reprovision_cooldown_secs: float = 300.0,
) -> HostedRecoveryConfig:
    return HostedRecoveryConfig(
        enabled=enabled,
        sweep_interval_secs=sweep_interval_secs,
        unhealthy_threshold_secs=unhealthy_threshold_secs,
        reprovision_cooldown_secs=reprovision_cooldown_secs,
    )


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

def test_config_from_env_defaults(monkeypatch: pytest.MonkeyPatch):
    for k in (
        "ENGINE_HOSTED_RECOVERY_ENABLED",
        "ENGINE_HOSTED_RECOVERY_SWEEP_INTERVAL_SECS",
        "ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS",
        "ENGINE_HOSTED_RECOVERY_REPROVISION_COOLDOWN_SECS",
    ):
        monkeypatch.delenv(k, raising=False)
    cfg = HostedRecoveryConfig.from_env()
    assert cfg.enabled is True
    assert cfg.sweep_interval_secs == 60.0
    assert cfg.unhealthy_threshold_secs == 600.0
    assert cfg.reprovision_cooldown_secs == 300.0


def test_config_from_env_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENGINE_HOSTED_RECOVERY_ENABLED", "false")
    cfg = HostedRecoveryConfig.from_env()
    assert cfg.enabled is False


def test_config_from_env_rejects_non_numeric(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENGINE_HOSTED_RECOVERY_SWEEP_INTERVAL_SECS", "abc")
    with pytest.raises(ConfigurationError):
        HostedRecoveryConfig.from_env()


def test_config_from_env_rejects_below_minimum(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENGINE_HOSTED_RECOVERY_SWEEP_INTERVAL_SECS", "1")
    with pytest.raises(ConfigurationError):
        HostedRecoveryConfig.from_env()


# ---------------------------------------------------------------------------
# Scenario 1: full system restart (eager startup sweep)
# ---------------------------------------------------------------------------

async def test_startup_disabled_short_circuits():
    svc = HostedRecoveryService(
        provisioner=_make_provisioner(),
        db=_make_db_with_rows([_make_row("aaaaaaaaaaaa-1")]),
        config=_make_config(enabled=False),
    )
    result = await svc.run_once_at_startup()
    assert result == {"scanned": 0, "reprovisioned": 0, "failed": 0}


async def test_startup_reprovisions_missing_statefulset():
    row = _make_row("aaaaaaaaaaaa-1")
    provisioner = _make_provisioner()  # default: every release returns 'removed'
    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([row]),
        config=_make_config(),
    )

    # decrypt_credential is called inside _reprovision. Patch it so we
    # do not need a real Fernet key.
    import engine.ta.broker.mt5.hosted.recovery as recovery_mod
    recovery_mod.decrypt_credential = lambda enc: "plaintext-password"  # type: ignore[assignment]

    result = await svc.run_once_at_startup()

    provisioner.provision_account.assert_awaited_once()
    call_kwargs = provisioner.provision_account.await_args.kwargs
    assert call_kwargs["connection_id"] == "aaaaaaaaaaaa-1"
    assert call_kwargs["user_id"] == "user-1"
    assert call_kwargs["login"] == "123456"
    assert call_kwargs["password"] == "plaintext-password"
    assert call_kwargs["server"] == "Exness-MT5Trial9"
    assert call_kwargs["platform"] == "mt5"
    assert result == {"scanned": 1, "reprovisioned": 1, "failed": 0}


async def test_startup_skips_ready_statefulset():
    row = _make_row("bbbbbbbbbbbb-1")
    release = f"etradie-mt-{row.id[:12]}"
    provisioner = _make_provisioner(
        status_by_release={release: {"status": "running", "running": True, "ready_replicas": 1}}
    )
    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([row]),
        config=_make_config(),
    )
    result = await svc.run_once_at_startup()
    provisioner.provision_account.assert_not_awaited()
    assert result == {"scanned": 1, "reprovisioned": 0, "failed": 0}


async def test_startup_mixed_only_missing_reprovisioned():
    healthy = _make_row("cccccccccccc-1")
    missing = _make_row("dddddddddddd-2")
    healthy_release = f"etradie-mt-{healthy.id[:12]}"
    provisioner = _make_provisioner(
        status_by_release={
            healthy_release: {"status": "running", "running": True, "ready_replicas": 1},
        }
    )
    import engine.ta.broker.mt5.hosted.recovery as recovery_mod
    recovery_mod.decrypt_credential = lambda enc: "plaintext"  # type: ignore[assignment]

    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([healthy, missing]),
        config=_make_config(),
    )
    result = await svc.run_once_at_startup()

    assert provisioner.provision_account.await_count == 1
    assert provisioner.provision_account.await_args.kwargs["connection_id"] == "dddddddddddd-2"
    assert result == {"scanned": 2, "reprovisioned": 1, "failed": 0}


async def test_startup_db_failure_does_not_crash():
    db = MagicMock()
    db.read_session = MagicMock(side_effect=RuntimeError("db down"))
    svc = HostedRecoveryService(
        provisioner=_make_provisioner(),
        db=db,
        config=_make_config(),
    )
    result = await svc.run_once_at_startup()
    assert result == {"scanned": 0, "reprovisioned": 0, "failed": 0}


# ---------------------------------------------------------------------------
# Scenario 2: partial recovery (periodic sweep)
# ---------------------------------------------------------------------------

async def test_periodic_below_threshold_no_action():
    row = _make_row("eeeeeeeeeeee-1")
    release = f"etradie-mt-{row.id[:12]}"
    provisioner = _make_provisioner(
        status_by_release={release: {"status": "pending", "running": False, "ready_replicas": 0}}
    )
    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([row]),
        config=_make_config(unhealthy_threshold_secs=600.0),
    )
    result = await svc._sweep(phase="periodic", bypass_threshold=False)
    provisioner.provision_account.assert_not_awaited()
    assert result == {"scanned": 1, "reprovisioned": 0, "failed": 0}


async def test_periodic_cooldown_blocks_second_attempt():
    row = _make_row("ffffffffffff-1")
    provisioner = _make_provisioner()  # default 'removed'
    import engine.ta.broker.mt5.hosted.recovery as recovery_mod
    recovery_mod.decrypt_credential = lambda enc: "plaintext"  # type: ignore[assignment]

    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([row]),
        config=_make_config(reprovision_cooldown_secs=300.0),
    )

    # First sweep: 'missing' bypasses the unhealthy threshold so it acts.
    await svc._sweep(phase="periodic", bypass_threshold=False)
    assert provisioner.provision_account.await_count == 1

    # Second sweep immediately after: cooldown must block.
    await svc._sweep(phase="periodic", bypass_threshold=False)
    assert provisioner.provision_account.await_count == 1


async def test_periodic_unhealthy_acts_when_bypass_threshold():
    row = _make_row("111111111111-1")
    release = f"etradie-mt-{row.id[:12]}"
    provisioner = _make_provisioner(
        status_by_release={release: {"status": "pending", "running": False}}
    )
    import engine.ta.broker.mt5.hosted.recovery as recovery_mod
    recovery_mod.decrypt_credential = lambda enc: "plaintext"  # type: ignore[assignment]

    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([row]),
        config=_make_config(),
    )
    result = await svc._sweep(phase="startup", bypass_threshold=True)
    assert result == {"scanned": 1, "reprovisioned": 1, "failed": 0}


# ---------------------------------------------------------------------------
# Scenario 3: broker outage (provision_account raises)
# ---------------------------------------------------------------------------

async def test_reprovision_failure_logged_and_counted():
    row = _make_row("222222222222-1")
    provisioner = _make_provisioner(
        provision_side_effect=ProviderTimeoutError(
            "readiness gate timed out", details={"release": "etradie-mt-222222222222"},
        ),
    )
    import engine.ta.broker.mt5.hosted.recovery as recovery_mod
    recovery_mod.decrypt_credential = lambda enc: "plaintext"  # type: ignore[assignment]

    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([row]),
        config=_make_config(),
    )
    result = await svc.run_once_at_startup()
    assert provisioner.provision_account.await_count == 1
    assert result == {"scanned": 1, "reprovisioned": 0, "failed": 1}

    # Cooldown is set even on failure so the next sweep does not stampede.
    await svc._sweep(phase="periodic", bypass_threshold=False)
    assert provisioner.provision_account.await_count == 1


async def test_reprovision_missing_credentials_raises_configuration_error():
    row = _make_row("333333333333-1")
    row.mt5_login = None  # missing required field
    provisioner = _make_provisioner()
    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([row]),
        config=_make_config(),
    )
    result = await svc.run_once_at_startup()
    provisioner.provision_account.assert_not_awaited()
    assert result == {"scanned": 1, "reprovisioned": 0, "failed": 1}


# ---------------------------------------------------------------------------
# Scenario 4: K8s API hang during status probe
# ---------------------------------------------------------------------------

async def test_status_check_failure_skips_row():
    row = _make_row("444444444444-1")
    provisioner = _make_provisioner()
    provisioner.get_account_status = AsyncMock(side_effect=RuntimeError("k8s api down"))
    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([row]),
        config=_make_config(),
    )
    result = await svc.run_once_at_startup()
    provisioner.provision_account.assert_not_awaited()
    assert result == {"scanned": 1, "reprovisioned": 0, "failed": 0}


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

async def test_stop_is_idempotent():
    svc = HostedRecoveryService(
        provisioner=_make_provisioner(),
        db=_make_db_with_rows([]),
        config=_make_config(),
    )
    await svc.stop()
    await svc.stop()  # safe to call twice


async def test_start_background_loop_idempotent():
    svc = HostedRecoveryService(
        provisioner=_make_provisioner(),
        db=_make_db_with_rows([]),
        config=_make_config(),
    )
    coordinator = MagicMock()
    coordinator.create_task = MagicMock(
        return_value=asyncio.get_event_loop().create_task(asyncio.sleep(0))
    )
    svc.start_background_loop(coordinator=coordinator)
    svc.start_background_loop(coordinator=coordinator)  # second call is a no-op
    assert coordinator.create_task.call_count == 1
    await svc.stop()


async def test_start_background_loop_skipped_when_disabled():
    svc = HostedRecoveryService(
        provisioner=_make_provisioner(),
        db=_make_db_with_rows([]),
        config=_make_config(enabled=False),
    )
    coordinator = MagicMock()
    coordinator.create_task = MagicMock()
    svc.start_background_loop(coordinator=coordinator)
    coordinator.create_task.assert_not_called()