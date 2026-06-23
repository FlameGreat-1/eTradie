"""Chaos tests for engine.ta.broker.mt5.hosted.recovery.HostedRecoveryService.

In-process unit tests using MagicMock + AsyncMock; no real K8s cluster
required. Cover the four CHECKLIST Section 8 disaster scenarios.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
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


def _make_row(
    connection_id: str,
    user_id: str = "user-1",
    created_at: datetime | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = connection_id
    row.user_id = user_id
    row.platform = "mt5"
    row.mt5_server = "Exness-MT5Trial9"
    row.mt5_login = "123456"
    row.mt5_password_encrypted = "gAAAAA-fake-fernet-ciphertext"
    # Default created_at is OLD (24h ago) so the fresh-provision guard
    # in HostedRecoveryService._sweep (commit 684746d5) NEVER skips
    # the row. Tests that need to exercise the guard pass an explicit
    # recent datetime.
    row.created_at = created_at if created_at is not None else datetime.now(UTC) - timedelta(hours=24)
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
    unhealthy_threshold_secs: float = 1200.0,
    reprovision_cooldown_secs: float = 300.0,
    fresh_provision_grace_secs: float = 0.0,
) -> HostedRecoveryConfig:
    """Construct a HostedRecoveryConfig for tests.

    Defaults match the production-leaning code defaults set in commit
    684746d5: unhealthy_threshold_secs=1200 sits above the provisioner
    readiness gate. fresh_provision_grace_secs defaults to 0 (disabled)
    so the existing tests do not have to fight the guard; the dedicated
    test_fresh_provision_grace_* cases pass an explicit non-zero value.
    """
    return HostedRecoveryConfig(
        enabled=enabled,
        sweep_interval_secs=sweep_interval_secs,
        unhealthy_threshold_secs=unhealthy_threshold_secs,
        reprovision_cooldown_secs=reprovision_cooldown_secs,
        fresh_provision_grace_secs=fresh_provision_grace_secs,
    )


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


async def test_config_from_env_defaults(monkeypatch: pytest.MonkeyPatch):
    for k in (
        "ENGINE_HOSTED_RECOVERY_ENABLED",
        "ENGINE_HOSTED_RECOVERY_SWEEP_INTERVAL_SECS",
        "ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS",
        "ENGINE_HOSTED_RECOVERY_REPROVISION_COOLDOWN_SECS",
        "ENGINE_HOSTED_RECOVERY_MAX_CONCURRENT",
        "ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS",
    ):
        monkeypatch.delenv(k, raising=False)
    cfg = HostedRecoveryConfig.from_env()
    assert cfg.enabled is True
    assert cfg.sweep_interval_secs == 60.0
    # 1200s default (raised from 600s in commit 684746d5) sits above
    # the provisioner readiness gate (_READINESS_TIMEOUT_SECS=600) so
    # the recovery sweep cannot race a still-cold-booting Pod. See
    # docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md.
    assert cfg.unhealthy_threshold_secs == 1200.0
    assert cfg.reprovision_cooldown_secs == 300.0
    assert cfg.max_concurrent_reprovisions == 4
    # Fresh-provision guard: 30min default protects fresh provisions
    # through their genuine first-boot window (Wine init + LiveUpdate +
    # exit-143 + 453-file MQL5 recompile + EA OnInit).
    assert cfg.fresh_provision_grace_secs == 1800.0


async def test_config_from_env_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENGINE_HOSTED_RECOVERY_ENABLED", "false")
    cfg = HostedRecoveryConfig.from_env()
    assert cfg.enabled is False


async def test_config_from_env_rejects_non_numeric(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENGINE_HOSTED_RECOVERY_SWEEP_INTERVAL_SECS", "abc")
    with pytest.raises(ConfigurationError):
        HostedRecoveryConfig.from_env()


async def test_config_from_env_rejects_below_minimum(monkeypatch: pytest.MonkeyPatch):
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
    provisioner = _make_provisioner(status_by_release={release: {"status": "pending", "running": False}})
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
            "readiness gate timed out",
            details={"release": "etradie-mt-222222222222"},
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
# Scenario: fresh-provision guard (commit 684746d5)
#
# A connection younger than fresh_provision_grace_secs is
# legitimately mid-first-boot (Wine init + LiveUpdate + exit-143
# self-restart + 453-file MQL5 recompile + EA OnInit). The
# provisioner's own readiness gate (_READINESS_TIMEOUT_SECS) is the
# authoritative check during this window; the recovery sweep must
# NOT tear it down, even on bypass_threshold=True. Without the
# guard, a coincidental engine restart during a user's first
# provision fed the exit-143 self-restart loop documented in
# docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md.
# ---------------------------------------------------------------------------


async def test_fresh_provision_grace_skips_recent_row_on_startup_sweep():
    """A row created 60s ago must be SKIPPED by the eager startup sweep,
    even though the StatefulSet is missing and bypass_threshold=True."""
    fresh_row = _make_row(
        "aaaaaaaaaaaa-fresh",
        created_at=datetime.now(UTC) - timedelta(seconds=60),
    )
    provisioner = _make_provisioner()  # default 'removed' for every release
    import engine.ta.broker.mt5.hosted.recovery as recovery_mod

    recovery_mod.decrypt_credential = lambda enc: "plaintext"  # type: ignore[assignment]

    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([fresh_row]),
        config=_make_config(fresh_provision_grace_secs=1800.0),
    )
    result = await svc.run_once_at_startup()

    # The fresh row is unhealthy (counted) but NOT reprovisioned.
    provisioner.provision_account.assert_not_awaited()
    assert result == {"scanned": 1, "reprovisioned": 0, "failed": 0}


async def test_fresh_provision_grace_lets_old_row_reprovision():
    """A row older than fresh_provision_grace_secs is reprovisioned
    normally; the guard only protects the FIRST-boot window."""
    old_row = _make_row(
        "bbbbbbbbbbbb-old",
        created_at=datetime.now(UTC) - timedelta(hours=2),
    )
    provisioner = _make_provisioner()
    import engine.ta.broker.mt5.hosted.recovery as recovery_mod

    recovery_mod.decrypt_credential = lambda enc: "plaintext"  # type: ignore[assignment]

    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([old_row]),
        config=_make_config(fresh_provision_grace_secs=1800.0),
    )
    result = await svc.run_once_at_startup()

    provisioner.provision_account.assert_awaited_once()
    assert result == {"scanned": 1, "reprovisioned": 1, "failed": 0}


async def test_fresh_provision_grace_zero_disables_guard():
    """fresh_provision_grace_secs=0 must restore the pre-fix behaviour:
    even a row created milliseconds ago is reprovisioned."""
    new_row = _make_row(
        "cccccccccccc-new",
        created_at=datetime.now(UTC) - timedelta(milliseconds=100),
    )
    provisioner = _make_provisioner()
    import engine.ta.broker.mt5.hosted.recovery as recovery_mod

    recovery_mod.decrypt_credential = lambda enc: "plaintext"  # type: ignore[assignment]

    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([new_row]),
        config=_make_config(fresh_provision_grace_secs=0.0),
    )
    result = await svc.run_once_at_startup()

    provisioner.provision_account.assert_awaited_once()
    assert result == {"scanned": 1, "reprovisioned": 1, "failed": 0}


async def test_fresh_provision_grace_naive_datetime_treated_as_utc():
    """created_at without tzinfo must be normalised to UTC by
    _row_created_at_seconds (the engine's DB DSN sets timezone=UTC,
    but defensive timezone normalisation is the documented contract).
    """
    # Construct a NAIVE datetime (no tzinfo) without calling the
    # deprecated datetime.utcnow(): take a tz-aware UTC instant and
    # strip its tzinfo. The helper's defensive UTC normalisation must
    # treat the resulting naive value as UTC.
    naive_recent = (datetime.now(UTC) - timedelta(seconds=60)).replace(tzinfo=None)
    fresh_row = _make_row("dddddddddddd-naive", created_at=naive_recent)
    provisioner = _make_provisioner()
    import engine.ta.broker.mt5.hosted.recovery as recovery_mod

    recovery_mod.decrypt_credential = lambda enc: "plaintext"  # type: ignore[assignment]

    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([fresh_row]),
        config=_make_config(fresh_provision_grace_secs=1800.0),
    )
    result = await svc.run_once_at_startup()

    provisioner.provision_account.assert_not_awaited()
    assert result == {"scanned": 1, "reprovisioned": 0, "failed": 0}


async def test_fresh_provision_grace_unparseable_created_at_falls_through():
    """A row whose created_at is None / unparseable cannot be evaluated
    against the guard; the helper returns None and the sweep falls
    through to normal recovery (safe: never tears down inappropriately).
    """
    row = _make_row("eeeeeeeeeeee-none", created_at=None)
    row.created_at = None  # explicitly None overrides _make_row default
    provisioner = _make_provisioner()
    import engine.ta.broker.mt5.hosted.recovery as recovery_mod

    recovery_mod.decrypt_credential = lambda enc: "plaintext"  # type: ignore[assignment]

    svc = HostedRecoveryService(
        provisioner=provisioner,
        db=_make_db_with_rows([row]),
        config=_make_config(fresh_provision_grace_secs=1800.0),
    )
    result = await svc.run_once_at_startup()

    # Guard returns None for an unparseable created_at -> the sweep
    # falls through and reprovisions (the row is genuinely missing).
    provisioner.provision_account.assert_awaited_once()
    assert result == {"scanned": 1, "reprovisioned": 1, "failed": 0}


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

    # The real BackgroundTaskCoordinator.create_task schedules the
    # passed coroutine on the loop. A naive `return_value=<task>` mock
    # would silently drop the self._loop() coroutine, leaking it and
    # tripping `RuntimeWarning: coroutine was never awaited` (caught
    # by pytest's unraisable plugin on the next test in the file).
    # Use side_effect to consume the coroutine cleanly.
    def _consume(coro, **kwargs):
        coro.close()
        return asyncio.get_event_loop().create_task(asyncio.sleep(0))

    coordinator.create_task = MagicMock(side_effect=_consume)
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
