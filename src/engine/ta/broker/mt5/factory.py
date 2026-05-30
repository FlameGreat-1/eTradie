"""MT5 broker factory.

Reads MT5Config.provider and returns the correct BrokerBase
implementation.  This is the single entry point for creating
an MT5-compatible broker client.

Three creation paths from DB rows:
  1. connection_type='ea'      -> ZmqClient (LOCAL DEVELOPMENT ONLY.
                                  Reads single-tenant MT5_ZMQ_* env vars
                                  from the engine's own environment.
                                  Rejected at the router in production
                                  and staging.)
  2. connection_type='metaapi'  -> MetaApiClient (cloud REST)
  3. connection_type='hosted'   -> ZmqClient (per-tenant Wine+Xvfb+MT5
                                   Pod in-cluster, provisioned by
                                   HostedProvisioner)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from engine.shared.exceptions import ConfigurationError
from engine.shared.logging import get_logger
from engine.ta.broker.base import BrokerBase
from engine.ta.broker.connectivity import (
    OutboundRateLimiter,
    ReconnectPolicy,
    TickFreshnessGuard,
)
from engine.ta.broker.mt5.clock_skew import ClockSkewMonitor
from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.mt5.ea_identity import (
    EAIdentityVerifier,
    ExpectedEAIdentity,
)

if TYPE_CHECKING:
    from engine.processor.storage.schemas.broker_connection_schema import (
        BrokerConnectionRow,
    )
    from engine.shared.http.client import HttpClient

logger = get_logger(__name__)


# ---------------------------------------------------------------------
# Section 2: connectivity primitive wiring
# ---------------------------------------------------------------------
def _f(env_name: str, default: float) -> float:
    """Read a positive float from env with a safe fallback."""
    try:
        v = float(os.environ.get(env_name, "").strip() or default)
        return v if v >= 0 else default
    except (TypeError, ValueError):
        return default


def _i(env_name: str, default: int) -> int:
    """Read a positive int from env with a safe fallback."""
    try:
        v = int(os.environ.get(env_name, "").strip() or default)
        return v if v >= 0 else default
    except (TypeError, ValueError):
        return default


def _build_connectivity_kwargs(provider: str, account_id: str) -> dict[str, Any]:
    """Construct the TickFreshnessGuard + ReconnectPolicy kwargs the
    broker clients accept.

    Pulled from the ENGINE_CONNECTIVITY_* env vars surfaced by
    helm/engine/templates/configmap.yaml. Defaults mirror the chart
    defaults so a missing env var never kills client construction.
    Audit ref: CHECKLIST Section 2.
    """
    tick_max_age = _f("ENGINE_CONNECTIVITY_TICK_MAX_AGE_SECS", 10.0)
    return {
        "freshness_guard": TickFreshnessGuard(
            max_age_seconds=tick_max_age,
            provider=provider,
            account_id=account_id or "unknown",
        ),
        "reconnect_policy": ReconnectPolicy(
            base_secs=_f("ENGINE_CONNECTIVITY_RECONNECT_BASE_SECS", 1.0),
            cap_secs=_f("ENGINE_CONNECTIVITY_RECONNECT_CAP_SECS", 30.0),
            max_attempts=_i("ENGINE_CONNECTIVITY_RECONNECT_MAX_ATTEMPTS", 10),
            provider=provider,
            account_id=account_id or "unknown",
        ),
    }


def _build_throttle_kwargs(provider: str, account_id: str) -> dict[str, Any]:
    """Build the Section-5 outbound limiter + in-flight gate kwargs.

    Returns kwargs accepted by ZmqClient: outbound_limiter,
    inflight_limit, outbound_limit_deadline_secs. Defaults are
    production-safe (10/s, 20 burst, 4 in-flight).

    Audit ref: CHECKLIST Section 5.
    """
    rate = _f("ENGINE_OUTBOUND_RATE_PER_SECOND", 10.0)
    burst = _i("ENGINE_OUTBOUND_BURST_SIZE", 20)
    inflight = _i("ENGINE_ZMQ_INFLIGHT_LIMIT", 4)
    deadline = _f("ENGINE_OUTBOUND_LIMIT_DEADLINE_SECS", 0.5)
    return {
        "outbound_limiter": OutboundRateLimiter(
            provider=provider,
            account_id=account_id or "unknown",
            rate_per_second=rate,
            burst_size=burst,
        ),
        "inflight_limit": inflight,
        "outbound_limit_deadline_secs": deadline,
    }


def _ea_verify_enabled() -> bool:
    """Operator kill-switch for the Section 4 verifier.

    Set ENGINE_EA_IDENTITY_VERIFY_ENABLED=false to disable identity
    verification WITHOUT redeploying. Same pattern as Section 2's
    heartbeat opt-out. Defaults to true.
    """
    val = os.environ.get("ENGINE_EA_IDENTITY_VERIFY_ENABLED", "true").strip().lower()
    return val not in ("false", "0", "no", "off", "")


def _build_ea_verification_kwargs(
    provider: str,
    account_id: str,
    row: "BrokerConnectionRow | None",
) -> dict[str, Any]:
    """Construct the Section-4 EA identity verifier + clock skew
    monitor kwargs the ZmqClient accepts.

    The expected identity is read from the connection row's mt5_login
    + mt5_server columns. magic_number is left at the sentinel 0 ('do
    not enforce') because the schema does not store it today. When
    the row is None (the pure-config create_mt5_broker path), no
    verifier is wired - tests and the legacy compose flow continue
    to work unchanged. When the operator kill-switch is off, an
    empty dict is returned so the client falls back to the
    pre-Section-4 behaviour.

    Audit ref: CHECKLIST Section 4.
    """
    if not _ea_verify_enabled() or row is None:
        return {}
    expected = ExpectedEAIdentity(
        magic_number=0,  # schema does not store this yet; sentinel = any
        account_login=(row.mt5_login or "").strip(),
        account_server=(row.mt5_server or "").strip(),
        minimum_ea_version=os.environ.get("ENGINE_EA_MIN_VERSION", "").strip(),
    )
    return {
        "identity_verifier": EAIdentityVerifier(
            provider=provider,
            account_id=account_id or "unknown",
        ),
        "expected_identity": expected,
        "clock_skew_monitor": ClockSkewMonitor(
            provider=provider,
            account_id=account_id or "unknown",
            window_size=16,
            max_acceptable_skew_secs=_f("ENGINE_EA_MAX_CLOCK_SKEW_SECS", 10.0),
        ),
    }


def create_mt5_broker(
    config: MT5Config,
    http_client: "HttpClient | None" = None,
) -> BrokerBase:
    """Create the MT5 broker client based on the configured provider.

    Args:
        config: MT5 configuration with provider selection.
        http_client: Shared HTTP client (required for metaapi provider).

    Returns:
        A fully configured BrokerBase implementation.

    Raises:
        ConfigurationError: On invalid provider or missing dependencies.
    """
    if config.provider == "metaapi":
        if http_client is None:
            raise ConfigurationError(
                "HttpClient is required for metaapi provider",
                details={"provider": config.provider},
            )
        from engine.ta.broker.mt5.metaapi.client import MetaApiClient

        acct_id = config.metaapi_account_id
        client = MetaApiClient(
            config=config,
            http_client=http_client,
            **_build_connectivity_kwargs("metaapi", acct_id or "unknown"),
        )
        logger.info(
            "mt5_broker_created",
            extra={
                "provider": "metaapi",
                "account_id": (acct_id[:8] + "...") if acct_id else "(none)",
            },
        )
        return client

    if config.provider == "native":
        from engine.ta.broker.mt5.zmq.client import ZmqClient

        endpoint_account = f"{config.zmq_host}:{config.zmq_port}"
        client = ZmqClient(
            config=config,
            auth_token=config.zmq_auth_token,
            **_build_connectivity_kwargs("zmq", endpoint_account),
        )
        logger.info(
            "mt5_broker_created",
            extra={
                "provider": "native",
                "endpoint": f"tcp://{endpoint_account}",
            },
        )
        return client

    raise ConfigurationError(
        f"Unknown MT5 provider: {config.provider}",
        details={"provider": config.provider, "allowed": ["metaapi", "native"]},
    )


def create_mt5_broker_from_connection(
    row: "BrokerConnectionRow",
    http_client: "HttpClient",
    *,
    ea_auth_token: str = "",
    platform_token: str = "",
) -> BrokerBase:
    """Create an MT5 broker client from a database connection row.

    Builds an MT5Config programmatically from the decrypted credentials
    stored in the broker_connections table, then delegates to the
    appropriate client constructor.

    Args:
        row: BrokerConnectionRow with connection details.
        http_client: Shared HTTP client (required for metaapi).
        ea_auth_token: Decrypted EA auth token (for EA connections).
        platform_token: Platform-level MetaAPI token from env var
            MT5_METAAPI_TOKEN (for MetaAPI connections).

    Returns:
        A fully configured BrokerBase implementation.

    Raises:
        ConfigurationError: On invalid connection type or missing data.
    """
    if row.connection_type == "ea":
        # connection_type='ea' is a local-development-only path that
        # reads single-tenant MT5_ZMQ_* env vars from the engine. The
        # router rejects new 'ea' row CREATES in production/staging;
        # this gate stops a pre-existing 'ea' row (from a shared DB or
        # an out-of-band migration) from bypassing that policy at
        # client-build time.
        _app_env = os.environ.get("APP_ENV", "").strip().lower()
        if _app_env in ("production", "staging"):
            raise ConfigurationError(
                "connection_type='ea' is a local-development path and is "
                "refused in production/staging. Delete this row and "
                "re-provision as connection_type='hosted' or 'metaapi'.",
                details={
                    "connection_id": str(row.id),
                    "connection_type": row.connection_type,
                    "app_env": _app_env,
                },
            )
        if not row.ea_host or row.ea_port is None:
            raise ConfigurationError(
                "EA connection requires host and port",
                details={"connection_id": str(row.id)},
            )

        # Build MT5Config for ZeroMQ native provider.
        config = MT5Config.model_construct(
            enabled=True,
            provider="native",
            metaapi_token="",
            metaapi_account_id="",
            metaapi_base_url="",
            zmq_host=row.ea_host,
            zmq_port=row.ea_port,
            zmq_auth_token=ea_auth_token,
            terminal_path=None,
            account=0,
            password="",
            server=row.mt5_server or "",
            timeout_seconds=60,
            max_retries=3,
            retry_delay_seconds=2,
            connection_timeout_seconds=30,
            max_candles_per_request=5000,
            enable_tick_data=False,
            magic_number=0,
        )

        from engine.ta.broker.mt5.zmq.client import ZmqClient

        endpoint_account = f"{row.ea_host}:{row.ea_port}"
        client = ZmqClient(
            config=config,
            auth_token=ea_auth_token,
            **_build_connectivity_kwargs("zmq-ea", endpoint_account),
            **_build_ea_verification_kwargs("zmq-ea", endpoint_account, row),
            **_build_throttle_kwargs("zmq-ea", endpoint_account),
        )
        logger.info(
            "mt5_broker_created_from_db",
            extra={
                "provider": "native",
                "connection_id": str(row.id),
                "name": row.name,
                "endpoint": f"tcp://{endpoint_account}",
            },
        )
        return client

    if row.connection_type == "metaapi":
        if not platform_token:
            raise ConfigurationError(
                "MT5_METAAPI_TOKEN env var is required for MetaAPI connections. "
                "Set this in your .env file.",
                details={"connection_id": str(row.id)},
            )
        if not row.metaapi_account_id:
            raise ConfigurationError(
                "MetaAPI connection has no provisioned account_id. "
                "The account may not have been provisioned yet.",
                details={"connection_id": str(row.id)},
            )

        # Build MT5Config for MetaAPI cloud provider.
        # Uses the platform-level token (from env), NOT a per-user token.
        mt5_settings = MT5Config()
        config = MT5Config.model_construct(
            enabled=True,
            provider="metaapi",
            metaapi_token=platform_token,
            metaapi_account_id=row.metaapi_account_id,
            metaapi_region=row.metaapi_region or mt5_settings.metaapi_region,
            metaapi_base_url="",
            zmq_host="",
            zmq_port=5555,
            terminal_path=None,
            account=0,
            password="",
            server=row.mt5_server or "",
            timeout_seconds=60,
            max_retries=3,
            retry_delay_seconds=2,
            connection_timeout_seconds=30,
            max_candles_per_request=5000,
            enable_tick_data=False,
            magic_number=0,
        )

        from engine.ta.broker.mt5.metaapi.client import MetaApiClient

        client = MetaApiClient(
            config=config,
            http_client=http_client,
            **_build_connectivity_kwargs("metaapi", row.metaapi_account_id or "unknown"),
        )
        acct_id = row.metaapi_account_id
        logger.info(
            "mt5_broker_created_from_db",
            extra={
                "provider": "metaapi",
                "connection_id": str(row.id),
                "name": row.name,
                "account_id": (acct_id[:8] + "...") if acct_id else "(none)",
            },
        )
        return client

    if row.connection_type == "hosted":
        # MT4 hosted connections are non-functional because the MT4 EA
        # binary is not bundled in the mt-node image (see
        # docker/mt-node/ea/README.md). Fail fast with a clear error.
        if (row.platform or "mt5").strip().lower() == "mt4":
            raise ConfigurationError(
                "platform='mt4' hosted connections are not currently "
                "supported: the MT4 EA binary is not bundled in the "
                "mt-node image. Re-create this connection with "
                "platform='mt5'.",
                details={
                    "connection_id": str(row.id),
                    "platform": row.platform,
                },
            )
        if not row.hosted_container_id:
            raise ConfigurationError(
                "Hosted connection has no container_id. "
                "The container may not have been provisioned yet.",
                details={"connection_id": str(row.id)},
            )

        # Resolve the in-cluster Service DNS for the per-user mt-node
        # release. HostedProvisioner deploys the Service with this exact
        # naming convention. resolve_zmq_host() is a pure string
        # formatter — it does not verify the Service exists. We rely on
        # the ZmqClient's connect timeout to surface a missing Service
        # quickly (the startup probe + readiness probe on the Pod ensure
        # the Service is only reachable when the EA is healthy).
        #
        # If the StatefulSet was deleted (operator action, ArgoCD prune,
        # namespace wipe), the HostedRecoveryService will detect the
        # missing StatefulSet on its next sweep (within
        # ENGINE_HOSTED_RECOVERY_SWEEP_INTERVAL_SECS, default 60s) and
        # re-provision it. Until then, ZmqClient calls will fail with
        # ProviderTimeoutError, which the caller surfaces to the user.
        from engine.ta.broker.mt5.hosted.provisioner import HostedProvisioner

        provisioner = HostedProvisioner()
        zmq_host = provisioner.resolve_zmq_host(row.hosted_container_id)

        if not zmq_host:
            raise ConfigurationError(
                "Cannot resolve hosted mt-node Service DNS. "
                "The release may have been deleted.",
                details={
                    "connection_id": str(row.id),
                    "container_id": row.hosted_container_id,
                },
            )

        # Per-tenant ZMQ auth token. HostedProvisioner generates one
        # at provision_account() time and the caller stores it in
        # broker_connections.ea_auth_token (column-encrypted at rest
        # by broker_encryption_key). ea_auth_token reaches this code
        # path already DECRYPTED via the same path used for
        # connection_type=='ea' (see line ~98 above).
        #
        # Backwards-compatibility: rows that pre-date this contract
        # have ea_auth_token=NULL. We surface a clear ConfigurationError
        # because a hosted release whose token the engine no longer
        # knows cannot be authenticated against the EA - the user must
        # re-provision via the dashboard.
        if not ea_auth_token:
            raise ConfigurationError(
                "Hosted connection has no ea_auth_token. "
                "Re-provision via the dashboard to regenerate one.",
                details={
                    "connection_id": str(row.id),
                    "container_id": row.hosted_container_id,
                },
            )

        # Build MT5Config for ZeroMQ native provider pointed at the
        # in-cluster Service DNS.
        config = MT5Config.model_construct(
            enabled=True,
            provider="native",
            metaapi_token="",
            metaapi_account_id="",
            metaapi_base_url="",
            zmq_host=zmq_host,
            zmq_port=5555,
            zmq_auth_token=ea_auth_token,
            terminal_path=None,
            account=0,
            password="",
            server=row.mt5_server or "",
            timeout_seconds=60,
            max_retries=3,
            retry_delay_seconds=2,
            connection_timeout_seconds=30,
            max_candles_per_request=5000,
            enable_tick_data=False,
            magic_number=0,
        )

        from engine.ta.broker.mt5.zmq.client import ZmqClient

        client = ZmqClient(
            config=config,
            auth_token=ea_auth_token,
            **_build_connectivity_kwargs("zmq-hosted", row.hosted_container_id),
            **_build_ea_verification_kwargs("zmq-hosted", row.hosted_container_id, row),
            **_build_throttle_kwargs("zmq-hosted", row.hosted_container_id),
        )
        logger.info(
            "mt5_broker_created_from_db",
            extra={
                "provider": "hosted",
                "connection_id": str(row.id),
                "name": row.name,
                "endpoint": f"tcp://{zmq_host}:5555",
                "container_id": row.hosted_container_id[:12],
            },
        )
        return client

    raise ConfigurationError(
        f"Unknown connection type: {row.connection_type}",
        details={
            "connection_id": str(row.id),
            "connection_type": row.connection_type,
            "allowed": ["ea", "metaapi", "hosted"],
        },
    )

