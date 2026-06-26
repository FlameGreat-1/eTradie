"""Hosted MetaTrader provisioner using Kubernetes StatefulSets.

Spawns isolated Kubernetes StatefulSets running headless MetaTrader 4
or 5 terminals via Wine/Xvfb. Each StatefulSet is fronted by both a
ClusterIP Service on :5555 (ZMQ) + :9100 (watchdog) AND a headless
Service that gives the per-replica pod a stable DNS name. The
engine's ZmqClient dials the regular ClusterIP Service in-cluster.

Production posture (mirrors the helm/mt-node chart EXACTLY):
  - StatefulSet is created with the same labels the chart uses, so
    the chart's NetworkPolicy / PodDisruptionBudget / ServiceMonitor
    selectors match and the engine NetworkPolicy egress allowlist
    (etradie-mt-node) reaches it.
  - volumeClaimTemplates owns the Wine prefix PVC. K8s produces the
    per-replica PVC named 'wine-prefix-<release>-0' automatically.
    There is NO explicit _ensure_pvc helper; the STS reconcile loop
    creates the PVC as part of the StatefulSet's first pod scheduling.
  - Credentials are AES-GCM sealed before writing to the per-tenant
    Secret; the StatefulSet mounts the Secret via envFrom so creds
    never appear in V1EnvVar value strings.
  - provision_account() does NOT return until the StatefulSet has at
    least one Ready replica AND a ZMQ PING succeeds through the
    Service. Up to 300s.
  - delete_account() removes the StatefulSet, both Services, the
    per-tenant Secret, and the per-replica PVC (StatefulSet GC does
    NOT cascade to volumeClaimTemplate PVCs by design - we delete
    them explicitly here).
  - gc_orphans() can be called by a background task to delete
    StatefulSets whose connection_id has been removed from the DB.

Resilience: the K8s StatefulSet controller handles process-restart
loops; the chart's in-pod entrypoint supervises MT5 inside the
container; the watchdog sidecar enforces semantic restart
(EA disconnected, memory soft-cap, CPU soft-cap). All three layers
are independent.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import time as _time
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

import zmq
import zmq.asyncio as zmq_async
from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.exceptions import ApiException
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from engine.shared.exceptions import (
    ConfigurationError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from engine.shared.logging import get_logger
from engine.shared.vault import VaultClient, VaultError

logger = get_logger(__name__)

# Sentinel value written into MT_SYMBOL on first boot. entrypoint.sh
# treats it as 'skip chart template; keep MT5 logged in only'.
# Resolution runs once Ready + PING succeed; the provisioner then
# patches MT_SYMBOL to a real broker-published name and K8s rolls
# the Pod once.
SYMBOL_PENDING_SENTINEL = "__pending__"

# Runs BrokerSyncService against a freshly-ready Pod and returns the
# chart-attach symbol name (the first instrument the broker publishes,
# or None when the broker exposes nothing). Injected by Container.
CatalogSyncRunner = Callable[..., Awaitable[str | None]]

# Persists the chart-attach symbol onto broker_connections.mt5_symbol.
# Injected by Container; keeps DB coupling out of the K8s module.
ChartSymbolWriter = Callable[[str, str], Awaitable[None]]

# ---------------------------------------------------------------------
# Chart contract (must match helm/mt-node)
# ---------------------------------------------------------------------
# Dev-only fallback. Production / staging MUST set MT_NODE_IMAGE in
# the engine ConfigMap (helm/engine/templates/configmap.yaml +
# helm/engine/values.yaml::config.mtNode.image). The constructor
# enforces this contract via _resolve_image() below.
MT_NODE_IMAGE_DEV_FALLBACK = "etradie-mt-node:dev"
CONTAINER_PREFIX = "etradie-mt-"  # release-name prefix; first 12 chars of connection_id appended
DEFAULT_ZMQ_PORT = 5555
DEFAULT_WATCHDOG_PORT = 9100
NAMESPACE_DEFAULT = "etradie-system"

# volumeClaimTemplate name MUST match helm/mt-node/templates/statefulset.yaml.
# StatefulSet produces per-replica PVCs named '<tmpl>-<sts>-<ordinal>'.
# With template 'wine-prefix' + sts '<release>' + ordinal 0, the PVC is
# 'wine-prefix-<release>-0'. Both the chart and this provisioner
# converge on this name; an operator can flip a tenant between
# GitOps-managed (chart) and runtime-managed (this provisioner)
# without losing the Wine prefix.
_PVC_TEMPLATE_NAME = "wine-prefix"

# Labels matching helm/mt-node's selectorLabels + labels helpers.
_LABEL_APP_NAME = "app.kubernetes.io/name"
_LABEL_INSTANCE = "app.kubernetes.io/instance"
_LABEL_PART_OF = "app.kubernetes.io/part-of"
_LABEL_COMPONENT = "app.kubernetes.io/component"
_LABEL_MANAGED_BY = "app.kubernetes.io/managed-by"
_LABEL_CONN_ID = "etradie.connection-id"
_LABEL_USER_ID = "etradie.user-id"
_LABEL_PLATFORM = "etradie.platform"

_APP_NAME_VALUE = "etradie-mt-node"
_PART_OF_VALUE = "etradie"
_MANAGED_BY_VALUE = "etradie-engine"


def release_name_for(connection_id: str) -> str:
    """Return the StatefulSet/Service/Secret release name for a connection.

    Pure string formatter shared with factory.py so callers that only
    need name resolution do not instantiate HostedProvisioner with no
    args (which previously masked missing Vault config).
    """
    return f"{CONTAINER_PREFIX}{connection_id[:12]}"


def headless_service_name_for(release: str) -> str:
    return f"{release}-headless"


def service_dns_for(release: str, namespace: str) -> str:
    return f"{release}.{namespace}.svc.cluster.local"


def namespace_default() -> str:
    return os.environ.get("MT_NODE_NAMESPACE", NAMESPACE_DEFAULT)


# Environment-bound resource sizing (overridable via env, with chart-aligned defaults).
_MEM_LIMIT = os.environ.get("MT_NODE_MEM_LIMIT", "1536Mi")
_MEM_REQUEST = os.environ.get("MT_NODE_MEM_REQUEST", "1Gi")
_CPU_LIMIT = os.environ.get("MT_NODE_CPU_LIMIT", "1500m")
_CPU_REQUEST = os.environ.get("MT_NODE_CPU_REQUEST", "500m")
_EPHEMERAL_LIMIT = os.environ.get("MT_NODE_EPHEMERAL_LIMIT", "1Gi")
_EPHEMERAL_REQUEST = os.environ.get("MT_NODE_EPHEMERAL_REQUEST", "512Mi")

# Scheduling envelope sourced from the engine ConfigMap so the runtime
# provisioner and the chart-rendered platform path produce wire-identical
# pod specs. Empty values mean 'do not set the field'.
_PRIORITY_CLASS_NAME_RAW = os.environ.get("MT_NODE_PRIORITY_CLASS_NAME", "").strip()
_TOLERATIONS_JSON_RAW = os.environ.get("MT_NODE_TOLERATIONS_JSON", "").strip()
_NODE_SELECTOR_JSON_RAW = os.environ.get("MT_NODE_NODE_SELECTOR_JSON", "").strip()
_AFFINITY_JSON_RAW = os.environ.get("MT_NODE_AFFINITY_JSON", "").strip()
_TOPOLOGY_SPREAD_JSON_RAW = os.environ.get("MT_NODE_TOPOLOGY_SPREAD_JSON", "").strip()
_POD_ANNOTATIONS_JSON_RAW = os.environ.get("MT_NODE_POD_ANNOTATIONS_JSON", "").strip()

# Name of the chart-rendered platform Secret that holds
# DEFAULT_ZMQ_AUTH_TOKEN. When non-empty, every runtime-provisioned
# mt-node + watchdog container envFroms this Secret so the entrypoint
# and watchdog have a fallback token if the Vault Agent file render
# fails. Sourced from the engine ConfigMap so the value lives in one
# place (helm/engine/values.yaml::config.mtNode.platformSecretName).
# Empty in dev / docker-compose; the chart-rendered behaviour is the
# same when externalSecrets.enabled=false.
_PLATFORM_SECRET_NAME = os.environ.get("MT_NODE_PLATFORM_SECRET_NAME", "").strip()


def _parse_json_envelope(env_name: str, raw: str, expected: type) -> Any:
    """Parse a JSON envelope env var into a dict or list.

    Returns None when the env var is empty or decodes to an empty
    container, so callers can pass the result directly to the
    kubernetes_asyncio constructors without emitting empty {} or [].
    Raises ConfigurationError on malformed JSON or a type mismatch.
    """
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            f"{env_name} is not valid JSON: {exc}",
            details={"env_var": env_name, "error": str(exc)},
        ) from exc
    if not isinstance(parsed, expected):
        raise ConfigurationError(
            f"{env_name} must be a JSON {expected.__name__}, got {type(parsed).__name__}",
            details={"env_var": env_name, "got_type": type(parsed).__name__},
        )
    if isinstance(parsed, dict) and not parsed:
        return None
    if isinstance(parsed, list) and not parsed:
        return None
    return parsed


# Readiness gate.
#
# 600s default covers the genuine FIRST-boot work-time on a fresh PVC:
#   Wine init (~10s) + MT5 launch (~15s) + LiveUpdate download of
#   mt5onnx64 ~15MB (~30-90s on a slow upstream) + exit-143 self-restart
#   (~5s) + relaunch (~15s) + full 453-file MQL5 recompile (~100s) +
#   chart load + EA OnInit + :5555 bind. Total 175-280s of genuine work,
#   easily 350-450s under any I/O contention. The previous 300s value
#   left ~zero margin and was the single biggest contributor to
#   first-boot ProviderTimeoutError, which used to delete the PVC in
#   _best_effort_cleanup (now fixed) and feed the LiveUpdate loop.
#   Subsequent boots are sub-30s because MT5's LiveUpdate-applied
#   component persists on the wine-prefix PVC.
#
# Operators can lower this for fast-broker installs via
# MT_NODE_READINESS_TIMEOUT_SECS but the 600s default is the safe
# enterprise floor. See docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md.
_READINESS_TIMEOUT_SECS = float(os.environ.get("MT_NODE_READINESS_TIMEOUT_SECS", "600"))
_READINESS_POLL_SECS = float(os.environ.get("MT_NODE_READINESS_POLL_SECS", "3"))
_ZMQ_PROBE_TIMEOUT_SECS = float(os.environ.get("MT_NODE_ZMQ_PROBE_TIMEOUT_SECS", "5"))

# Vault path layout under VAULT_MOUNT.
_VAULT_TENANT_PATH_PREFIX = "tenants/mt-node"
# Vault role the per-tenant Pod's Vault Agent uses (matches
# infrastructure/cluster/vault-paths/mt_node_tenant_secrets.tf).
_VAULT_TENANT_ROLE = os.environ.get("MT_NODE_VAULT_TENANT_ROLE", "mt-node-tenant").strip() or "mt-node-tenant"
# File the Vault Agent Injector renders the credentials into; the
# mt-node entrypoint sources it.
_VAULT_SECRETS_FILE = "mt-credentials.env"
_VAULT_SECRETS_MOUNT = "/vault/secrets"


def _hash_secret_data(data: dict[str, str]) -> str:
    """Stable SHA-256 of a K8s Secret data dict.

    The dict is canonicalised (sorted keys, no whitespace) so the same
    payload always produces the same digest regardless of insertion
    order. Stamped on the StatefulSet pod template so K8s observes a
    diff and rolls the Pod whenever the underlying credentials change.
    envFrom-mounted Secret data changes are otherwise invisible to the
    StatefulSet controller.
    """
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _pvc_name_for(release: str) -> str:
    """Return the per-replica PVC name that the StatefulSet's
    volumeClaimTemplate produces. The format is
    '<template-name>-<sts-name>-<ordinal>' and ordinal is always 0
    because the chart runs a single replica per tenant.
    """
    return f"{_PVC_TEMPLATE_NAME}-{release}-0"


class HostedProvisioner:
    """Manages the lifecycle of per-user mt-node StatefulSets + Services."""

    def __init__(
        self,
        *,
        namespace: str | None = None,
        image: str | None = None,
        platform_default_token_secret_name: str | None = None,
        vault_client: VaultClient | None = None,
        broker_registry: Any | None = None,
        catalog_sync_runner: CatalogSyncRunner | None = None,
        chart_symbol_writer: ChartSymbolWriter | None = None,
    ) -> None:
        self._namespace = namespace or namespace_default()
        self._image = image or self._resolve_image()
        # Platform Secret name the chart provisions. Defaults to the
        # release-scoped name helm/mt-node renders for a release.
        self._platform_secret_template = platform_default_token_secret_name or "{release}-platform"
        self._vault = vault_client
        self._broker_registry = broker_registry
        # Injected by Container: keeps DB + broker-client coupling out
        # of the K8s module. Both are required for hosted provisioning;
        # absence is enforced at provision_account().
        self._catalog_sync_runner = catalog_sync_runner
        self._chart_symbol_writer = chart_symbol_writer

    def _require_vault(self) -> VaultClient:
        if self._vault is None:
            app_env = os.environ.get("APP_ENV", "development").strip().lower()
            raise ConfigurationError(
                "VaultClient is required for hosted provisioning. Set VAULT_ADDR "
                "and VAULT_K8S_AUTH_ROLE so the engine can write per-tenant "
                "credentials to Vault.",
                details={"app_env": app_env},
            )
        return self._vault

    @staticmethod
    def _vault_path_for(release: str) -> str:
        return f"{_VAULT_TENANT_PATH_PREFIX}/{release}"

    def _vault_data_path(self, path: str) -> str:
        mount = os.environ.get("VAULT_MOUNT", "etradie").strip() or "etradie"
        return f"{mount}/data/{path}"

    @staticmethod
    def _resolve_image() -> str:
        """Resolve the mt-node container image with environment-aware
        strictness.

        Production + staging MUST set MT_NODE_IMAGE explicitly. The
        helm/engine chart wires this via ConfigMap from
        config.mtNode.image. Failing to set it in a hosted-MT-node
        deployment is a deployment misconfiguration that must surface
        immediately at engine boot - not silently use a dev fallback
        and ship the wrong image to tenants.

        Dev (APP_ENV != production/staging) keeps the
        MT_NODE_IMAGE_DEV_FALLBACK so docker-compose, pytest, and
        ad-hoc engine runs continue to work without ceremony.

        Same posture pattern as
        broker_connection_repository._derive_encryption_key().
        """
        explicit = os.environ.get("MT_NODE_IMAGE", "").strip()
        if explicit:
            return explicit
        app_env = os.environ.get("APP_ENV", "development").strip().lower()
        if app_env in ("production", "staging"):
            raise ConfigurationError(
                "MT_NODE_IMAGE is required when APP_ENV is 'production' or 'staging'. "
                "Set helm/engine/values.yaml::config.mtNode.image (rendered into the "
                "engine ConfigMap as MT_NODE_IMAGE) to the pinned mt-node image, "
                "e.g. ghcr.io/<your-org>/etradie-mt-node@sha256:<digest>.",
                details={"env_var": "MT_NODE_IMAGE", "app_env": app_env},
            )
        return MT_NODE_IMAGE_DEV_FALLBACK

    # -- K8s client -----------------------------------------------------------

    async def _api_clients(self) -> tuple[client.CoreV1Api, client.AppsV1Api]:
        """Initialise CoreV1 + AppsV1 with in-cluster auth.

        Construction is NOT cheap (parses kubeconfig OR reads
        the in-cluster service-account token + builds the
        ApiClient + per-resource client). Callers should hold the
        returned pair for the duration of a logical operation
        rather than reopening per-iteration.
        """
        try:
            try:
                config.load_incluster_config()
            except config.ConfigException:
                await config.load_kube_config()
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(
                "Kubernetes API is not reachable",
                details={"error": str(exc)},
            ) from exc
        return client.CoreV1Api(), client.AppsV1Api()

    @staticmethod
    async def _close(api) -> None:
        try:
            await api.api_client.close()
        except Exception:  # noqa: BLE001
            pass  # nosec B110

    # -- Naming + label helpers ---------------------------------------------

    @staticmethod
    def _release_name(connection_id: str) -> str:
        return release_name_for(connection_id)

    @staticmethod
    def _headless_service_name(release: str) -> str:
        return headless_service_name_for(release)

    @classmethod
    def _labels(
        cls,
        connection_id: str,
        user_id: str,
        platform: str,
        release: str,
    ) -> dict[str, str]:
        return {
            _LABEL_APP_NAME: _APP_NAME_VALUE,
            _LABEL_INSTANCE: release,
            _LABEL_PART_OF: _PART_OF_VALUE,
            _LABEL_COMPONENT: "mt-node",
            _LABEL_MANAGED_BY: _MANAGED_BY_VALUE,
            _LABEL_CONN_ID: connection_id,
            _LABEL_USER_ID: user_id,
            _LABEL_PLATFORM: platform,
        }

    @classmethod
    def _selector_labels(cls, connection_id: str, release: str) -> dict[str, str]:
        # Mirrors helm/mt-node's selectorLabels exactly.
        return {
            _LABEL_APP_NAME: _APP_NAME_VALUE,
            _LABEL_INSTANCE: release,
            _LABEL_CONN_ID: connection_id,
        }

    @staticmethod
    def _resource_requirements() -> client.V1ResourceRequirements:
        return client.V1ResourceRequirements(
            requests={
                "cpu": _CPU_REQUEST,
                "memory": _MEM_REQUEST,
                "ephemeral-storage": _EPHEMERAL_REQUEST,
            },
            limits={
                "cpu": _CPU_LIMIT,
                "memory": _MEM_LIMIT,
                "ephemeral-storage": _EPHEMERAL_LIMIT,
            },
        )

    # -- Public API ---------------------------------------------------------

    async def provision_account(
        self,
        *,
        connection_id: str,
        user_id: str,
        brand_id: str,
        entity_id: str,
        login: str,
        password: str,
        server: str,
        platform: str = "mt5",
        zmq_port: int = DEFAULT_ZMQ_PORT,
        per_user_zmq_token: str | None = None,
        readiness_timeout_secs: float | None = None,
        existing_chart_symbol: str | None = None,
    ) -> dict[str, Any]:
        """Provision a new hosted mt-node release.

        Side effects (idempotent w.r.t. an existing release of the same name):
          1. Create / update the per-tenant Vault secret with sealed creds.
          2. Create / update the per-tenant ServiceAccount.
          3. Create / update the per-release watchdog ConfigMap.
          4. Create / update the StatefulSet with MT_SYMBOL=
             SYMBOL_PENDING_SENTINEL on first boot so the entrypoint
             skips chart template writing until the broker catalog is
             reachable.
          5. Create / update the regular ClusterIP Service AND the
             headless Service the StatefulSet needs for stable pod-DNS.
          6. Wait until the StatefulSet has at least one Ready replica
             AND a ZMQ PING succeeds.
          7. Ask the EA for the broker's symbol-name list via the
             injected catalog_sync_runner; pick the first published
             name as the chart-attach symbol. The runner also schedules
             the full per-symbol metadata sync as a background task.
          8. Patch the StatefulSet pod template to replace the
             sentinel with the chart-attach symbol and persist the
             same value to broker_connections.mt5_symbol via the
             injected chart_symbol_writer. K8s rolls the Pod once.

        Returns the runtime metadata the router persists onto the
        broker_connections row plus the chart_symbol picked from the
        broker's live catalog.
        """
        if platform not in ("mt4", "mt5"):
            raise ConfigurationError(
                f"platform must be mt4 or mt5 (got {platform!r})",
                details={"platform": platform, "connection_id": connection_id},
            )

        if self._broker_registry is None:
            raise ConfigurationError(
                "BrokerRegistry must be injected to provision hosted accounts.",
                details={"connection_id": connection_id},
            )

        resolved_broker = self._broker_registry.resolve(brand_id, entity_id, platform)

        # Defence-in-depth: the registry loader already enforces
        # bundle_r2_path / bundle_sha256 / live servers on every active
        # platform entry. Re-validate the shapes here so a half-populated
        # catalog entry (e.g. someone manually edited a JSON to flip
        # status='pending_bake'->'active' without filling the bundle
        # fields) can never reach the K8s API. The bundle pin is
        # MANDATORY: the image no longer carries any MetaTrader install,
        # so a missing bundle means the Pod has no terminal binary.
        _bundle_r2_path = getattr(resolved_broker, "bundle_r2_path", "") or ""
        _bundle_sha256 = getattr(resolved_broker, "bundle_sha256", "") or ""
        if not _bundle_r2_path:
            raise ConfigurationError(
                "Resolved broker is missing bundle_r2_path; the mt-node "
                "image carries no MetaTrader install, so a bundle is "
                "required for every hosted provision.",
                details={
                    "connection_id": connection_id,
                    "brand_id": brand_id,
                    "entity_id": entity_id,
                    "platform": platform,
                },
            )
        if not (_bundle_r2_path.startswith("https://") or _bundle_r2_path.startswith("http://")):
            raise ConfigurationError(
                "Resolved broker bundle_r2_path must be an http(s):// URL "
                "the initContainer can wget; the catalog's r2:// alias is "
                "documentation-only.",
                details={
                    "connection_id": connection_id,
                    "brand_id": brand_id,
                    "entity_id": entity_id,
                    "platform": platform,
                    "bundle_r2_path": _bundle_r2_path,
                },
            )
        if not _bundle_sha256 or len(_bundle_sha256) != 64 or any(c not in "0123456789abcdef" for c in _bundle_sha256):
            raise ConfigurationError(
                "Resolved broker bundle_sha256 must be 64 lowercase hex "
                "characters; the initContainer verifies the downloaded "
                "zip against this digest before unpacking.",
                details={
                    "connection_id": connection_id,
                    "brand_id": brand_id,
                    "entity_id": entity_id,
                    "platform": platform,
                    "bundle_sha256": _bundle_sha256,
                },
            )

        # Fall back to development token if not explicitly provided
        zmq_auth_token = per_user_zmq_token or os.environ.get("DEFAULT_ZMQ_AUTH_TOKEN", "")

        if self._catalog_sync_runner is None or self._chart_symbol_writer is None:
            raise ConfigurationError(
                "HostedProvisioner requires catalog_sync_runner and "
                "chart_symbol_writer for automatic broker catalog population. "
                "Inject them via Container.",
                details={"connection_id": connection_id},
            )

        vault = self._require_vault()
        release = self._release_name(connection_id)
        labels = self._labels(connection_id, user_id, platform, release)
        selector = self._selector_labels(connection_id, release)
        service_name = release
        headless_service_name = self._headless_service_name(release)
        sa_name = release
        vault_path = self._vault_path_for(release)

        dns_name = f"{service_name}.{self._namespace}.svc.cluster.local"

        # Effective per-tenant token. The engine generates one when the
        # caller did not supply (first-time provision). The caller
        # (factory.py) also persists it in broker_connections.ea_auth_token
        # (column-encrypted at REST) so ZmqClient can re-read it.
        effective_token = (per_user_zmq_token or secrets.token_hex(32)).strip()

        # Persistent api clients for the whole provision flow including
        # the readiness gate so each readiness poll does not re-open an
        # ApiClient. The persistent client also keeps the kube-apiserver
        # connection warm for the duration.
        core_api, apps_api = await self._api_clients()
        try:
            try:
                credentials_checksum = await self._write_vault_credentials(
                    vault=vault,
                    path=vault_path,
                    login=login,
                    password=password,
                    token=effective_token,
                )
                await self._upsert_serviceaccount(
                    core_api=core_api,
                    name=sa_name,
                    labels=labels,
                )
                await self._upsert_watchdog_configmap(
                    core_api=core_api,
                    name=f"{release}-watchdog-config",
                    labels=labels,
                    zmq_port=zmq_port,
                    watchdog_port=DEFAULT_WATCHDOG_PORT,
                )
                # 4. Upsert StatefulSet (skip catalog sync if already resolved)
                target_symbol = existing_chart_symbol or SYMBOL_PENDING_SENTINEL
                await self._upsert_statefulset(
                    apps_api=apps_api,
                    connection_id=connection_id,
                    user_id=user_id,
                    platform=platform,
                    brand_id=brand_id,
                    entity_id=entity_id,
                    bundle_r2_path=resolved_broker.bundle_r2_path,
                    bundle_sha256=resolved_broker.bundle_sha256,
                    release=release,
                    sa_name=sa_name,
                    vault_path=vault_path,
                    symbol=target_symbol,
                    watchdog_port=DEFAULT_WATCHDOG_PORT,
                    zmq_port=zmq_port,
                    headless_service_name=headless_service_name,
                    labels=labels,
                    selector=selector,
                    server=server,
                    credentials_checksum=credentials_checksum,
                )
                await self._upsert_service(
                    core_api=core_api,
                    name=service_name,
                    labels=labels,
                    selector=selector,
                    zmq_port=zmq_port,
                    headless=False,
                )
                await self._upsert_service(
                    core_api=core_api,
                    name=headless_service_name,
                    labels=labels,
                    selector=selector,
                    zmq_port=zmq_port,
                    headless=True,
                )
            except ApiException as exc:
                logger.error(
                    "hosted_provisioning_k8s_error",
                    extra={
                        "connection_id": connection_id,
                        "release": release,
                        "status": exc.status,
                        "reason": exc.reason,
                        "body": (exc.body or "")[:500],
                    },
                )
                # Best-effort rollback so we do not leak orphans on a
                # partial failure.
                await self._best_effort_cleanup(
                    core_api=core_api,
                    apps_api=apps_api,
                    vault=vault,
                    release=release,
                    service_name=service_name,
                    headless_service_name=headless_service_name,
                    sa_name=sa_name,
                    vault_path=vault_path,
                )
                raise ProviderError(
                    f"Failed to create hosted mt-node release: {exc.reason}",
                    details={
                        "connection_id": connection_id,
                        "release": release,
                        "status": exc.status,
                    },
                ) from exc

            # Readiness gate, broker catalog hand-off, and STS env
            # patch all run AFTER the K8s upserts succeeded. Any
            # failure here would otherwise leave the StatefulSet +
            # Services + watchdog CM + SA + Vault path alive in the
            # cluster while the broker_connections row never gets
            # persisted (the router rolls back its DB transaction on
            # ProviderError). That orphan keeps consuming Pod resources
            # + Vault token leases until gc_orphans() sweeps it.
            #
            # Wrap the entire post-upsert sequence in a try/except
            # that runs _best_effort_cleanup on ANY exception (not
            # only ApiException) and re-raises so the router still
            # surfaces the original error to the dashboard.
            try:
                timeout = readiness_timeout_secs if readiness_timeout_secs is not None else _READINESS_TIMEOUT_SECS
                await self._wait_ready(
                    core_api=core_api,
                    apps_api=apps_api,
                    release=release,
                    dns_name=dns_name,
                    zmq_port=zmq_port,
                    token=effective_token,
                    timeout=timeout,
                )

                chart_symbol = await self._populate_broker_catalog(
                    connection_id=connection_id,
                    dns_name=dns_name,
                    zmq_port=zmq_port,
                    token=effective_token,
                    existing_chart_symbol=existing_chart_symbol,
                )

                await self._patch_statefulset_symbol(
                    apps_api=apps_api,
                    release=release,
                    active_symbol=chart_symbol,
                )
                # Only write back to the DB when the resolver actually
                # picked a new symbol. A non-empty existing_chart_symbol
                # short-circuits _populate_broker_catalog above to return
                # that same value, so this conditional is the H-4 guard
                # that prevents recovery sweeps from overwriting a
                # user's previously-resolved mt5_symbol.
                if not (existing_chart_symbol and existing_chart_symbol.strip()):
                    await self._chart_symbol_writer(connection_id, chart_symbol)
            except Exception as post_upsert_exc:  # noqa: BLE001
                logger.error(
                    "hosted_provisioning_post_upsert_failed",
                    extra={
                        "connection_id": connection_id,
                        "release": release,
                        "error": str(post_upsert_exc),
                        "error_type": type(post_upsert_exc).__name__,
                    },
                )
                await self._best_effort_cleanup(
                    core_api=core_api,
                    apps_api=apps_api,
                    vault=vault,
                    release=release,
                    service_name=service_name,
                    headless_service_name=headless_service_name,
                    sa_name=sa_name,
                    vault_path=vault_path,
                )
                raise
        finally:
            await self._close(core_api)
            await self._close(apps_api)

        logger.info(
            "hosted_provisioning_success",
            extra={
                "connection_id": connection_id,
                "release": release,
                "service": service_name,
                "dns": dns_name,
                "chart_symbol": chart_symbol,
            },
        )

        return {
            "container_id": release,
            "container_name": release,
            "zmq_host": dns_name,
            "zmq_port": zmq_port,
            "zmq_auth_token": effective_token,
            "state": "running",
            "chart_symbol": chart_symbol,
        }

    async def get_account_status(self, container_id: str) -> dict[str, Any]:
        """Return StatefulSet readiness + Service endpoint state."""
        core_api, apps_api = await self._api_clients()
        try:
            try:
                sts = await apps_api.read_namespaced_stateful_set(
                    name=container_id,
                    namespace=self._namespace,
                )
            except ApiException as exc:
                if exc.status == 404:
                    return {
                        "container_id": container_id,
                        "status": "removed",
                        "running": False,
                        "ready_replicas": 0,
                        "started_at": None,
                        "exit_code": -1,
                    }
                raise ProviderError(
                    f"Failed to read StatefulSet: {exc.reason}",
                    details={"container_id": container_id, "status": exc.status},
                ) from exc

            ready = int(sts.status.ready_replicas or 0)
            replicas = int(sts.status.replicas or 0)
            current = int(sts.status.current_replicas or 0) if hasattr(sts.status, "current_replicas") else replicas
            running = ready >= 1
            return {
                "container_id": container_id,
                "status": "running" if running else "pending",
                "running": running,
                "ready_replicas": ready,
                "replicas": replicas,
                "current_replicas": current,
                "started_at": (str(sts.metadata.creation_timestamp) if sts.metadata.creation_timestamp else None),
                "exit_code": 0 if running else -1,
            }
        finally:
            await self._close(core_api)
            await self._close(apps_api)

    async def delete_account(self, container_id: str) -> bool:
        """Remove every resource associated with a release.

        Order:
          1. StatefulSet                                (K8s)
          2. Regular Service                            (K8s)
          3. Headless Service                           (K8s)
          4. Per-tenant ServiceAccount                  (K8s)
          5. Legacy per-tenant Secret                   (K8s; best-effort)
          6. Per-replica Wine-prefix PVC                (K8s)
          7. Vault tenant path (destroy all versions)   (Vault)

        StatefulSet GC does NOT cascade to volumeClaimTemplate PVCs;
        the Wine prefix PVC is deleted explicitly. The legacy Secret
        delete covers the cutover window when some releases were
        provisioned before the Vault Agent Injector migration.
        """
        core_api, apps_api = await self._api_clients()
        ok = True
        try:
            ok &= await self._safe_delete(
                apps_api.delete_namespaced_stateful_set,
                container_id,
                "StatefulSet",
            )
            ok &= await self._safe_delete(
                core_api.delete_namespaced_service,
                container_id,
                "Service",
            )
            ok &= await self._safe_delete(
                core_api.delete_namespaced_service,
                self._headless_service_name(container_id),
                "Service(headless)",
            )
            ok &= await self._safe_delete(
                core_api.delete_namespaced_service_account,
                container_id,
                "ServiceAccount",
            )
            ok &= await self._safe_delete(
                core_api.delete_namespaced_secret,
                f"{container_id}-creds",
                "Secret(legacy-creds)",
            )
            ok &= await self._safe_delete(
                core_api.delete_namespaced_config_map,
                f"{container_id}-watchdog-config",
                "ConfigMap(watchdog-config)",
            )
            ok &= await self._safe_delete(
                core_api.delete_namespaced_persistent_volume_claim,
                _pvc_name_for(container_id),
                "PVC(wine-prefix)",
            )
            await self._destroy_vault_path(
                self._vault_path_for(container_id),
            )
            logger.info(
                "hosted_release_deleted",
                extra={"container_id": container_id, "all_ok": ok},
            )
            return ok
        finally:
            await self._close(core_api)
            await self._close(apps_api)

    async def _destroy_vault_path(self, path: str) -> None:
        """Best-effort destroy of every version at the tenant Vault path.

        Vault outage MUST NOT block the rest of the cleanup: a half-
        deleted K8s release is harder to recover from than orphan
        Vault credentials. The orphan path can be manually purged by
        the operator.
        """
        if self._vault is None:
            return
        try:
            await self._vault.destroy_all_versions(path)
            logger.info("hosted_vault_path_destroyed", extra={"path": path})
        except VaultError as exc:
            logger.warning(
                "hosted_vault_path_destroy_failed",
                extra={"path": path, "error": str(exc), **(exc.details or {})},
            )

    async def gc_orphans(self, known_connection_ids: Iterable[str]) -> dict[str, Any]:
        """Delete StatefulSets whose connection-id is no longer in the DB.

        Called by a background task on the engine. Idempotent.
        """
        known = {cid for cid in known_connection_ids if cid}
        core_api, apps_api = await self._api_clients()
        deleted: list[str] = []
        try:
            sts_list = await apps_api.list_namespaced_stateful_set(
                namespace=self._namespace,
                label_selector=f"{_LABEL_APP_NAME}={_APP_NAME_VALUE}",
            )
            for sts in sts_list.items:
                lbl = (sts.metadata.labels or {}).get(_LABEL_CONN_ID)
                if lbl and lbl not in known:
                    name = sts.metadata.name
                    logger.warning(
                        "hosted_gc_orphan",
                        extra={"statefulset": name, "connection_id": lbl},
                    )
                    await self._safe_delete(
                        apps_api.delete_namespaced_stateful_set,
                        name,
                        "StatefulSet",
                    )
                    await self._safe_delete(
                        core_api.delete_namespaced_service,
                        name,
                        "Service",
                    )
                    await self._safe_delete(
                        core_api.delete_namespaced_service,
                        self._headless_service_name(name),
                        "Service(headless)",
                    )
                    await self._safe_delete(
                        core_api.delete_namespaced_service_account,
                        name,
                        "ServiceAccount",
                    )
                    await self._safe_delete(
                        core_api.delete_namespaced_secret,
                        f"{name}-creds",
                        "Secret(legacy-creds)",
                    )
                    await self._safe_delete(
                        core_api.delete_namespaced_config_map,
                        f"{name}-watchdog-config",
                        "ConfigMap(watchdog-config)",
                    )
                    await self._safe_delete(
                        core_api.delete_namespaced_persistent_volume_claim,
                        _pvc_name_for(name),
                        "PVC",
                    )
                    await self._destroy_vault_path(self._vault_path_for(name))
                    deleted.append(name)
            return {"deleted": deleted, "scanned": len(sts_list.items)}
        finally:
            await self._close(core_api)
            await self._close(apps_api)

    # -- Internal: upsert helpers (idempotent) ------------------------------

    async def _retrying(self) -> AsyncRetrying:
        return AsyncRetrying(
            reraise=True,
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            retry=retry_if_exception_type(ApiException),
        )

    async def _write_vault_credentials(
        self,
        *,
        vault: VaultClient,
        path: str,
        login: str,
        password: str,
        token: str,
    ) -> str:
        """Write per-tenant MT credentials to Vault.

        Returns a SHA-256 digest over the payload. The caller stamps
        it on the StatefulSet pod template so K8s rolls the Pod when
        the underlying credentials rotate (Vault Agent does NOT push
        updates into a running Pod's tmpfs; the Pod must restart for
        the new credentials to take effect).
        """
        data = {
            "mt5_login": login,
            "mt5_password": password,
            "mt5_zmq_auth_token": token,
        }
        try:
            await vault.write_kv(path, data)
        except VaultError as exc:
            raise ProviderError(
                f"Failed to write per-tenant credentials to Vault: {exc}",
                details={"path": path, **(exc.details or {})},
            ) from exc
        return _hash_secret_data(data)

    async def _upsert_watchdog_configmap(
        self,
        *,
        core_api: client.CoreV1Api,
        name: str,
        labels: dict[str, str],
        zmq_port: int,
        watchdog_port: int,
    ) -> None:
        """Idempotent create-or-update of the per-release watchdog
        ConfigMap.

        Carries the same seven keys helm/mt-node/templates/
        configmap-watchdog.yaml emits so chart-rendered and runtime-
        provisioned Pods feed their watchdog from a ConfigMap with an
        identical wire shape.
        """
        data = {
            "WATCHDOG_ZMQ_ENDPOINT": f"tcp://127.0.0.1:{zmq_port}",
            "WATCHDOG_HTTP_PORT": str(watchdog_port),
            "WATCHDOG_POLL_INTERVAL_SECONDS": "10",
            "WATCHDOG_MAX_FAILURES": "6",
            "WATCHDOG_MEMORY_SOFT_CAP_FRACTION": "0.8",
            "WATCHDOG_CPU_THROTTLE_SOFT_CAP_FRACTION": "0.5",
            "WATCHDOG_CPU_THROTTLE_CONSECUTIVE_POLLS": "6",
            "WATCHDOG_LIVEZ_GRACE_SECONDS": "60",
            # Cold-boot grace. The genuine first-boot work-time on a
            # fresh Wine prefix covers Wine seed (~10s) + Xvfb / MT5
            # launch (~15s) + LiveUpdate download + exit-143 + 30s
            # settle + relaunch (~60s; Cluster 1 fix, one-shot per
            # fresh PVC) + 453-file MQL5 recompile (~100s; build 5836)
            # + xdotool auto-login driver (~30s; Cluster 4 fix, see
            # docker/mt-node/entrypoint.sh::auto_login_driver and
            # docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md sections
            # 2.x) + chart open + EA OnInit + :5555 bind (~10s).
            # ~215s baseline. Subsequent boots use accounts.dat (written
            # by MT5 itself during the xdotool-driven first login) and
            # complete in ~20-30s total. LOCKSTEP INVARIANT: must mirror
            # helm/mt-node/values.yaml::sidecar.watchdog.config
            # .startupGraceSeconds so engine-runtime-provisioned tenant
            # pods are wire-identical to chart-rendered ones. 450s is
            # >= the entrypoint auto-login driver budget (420s) + hard-
            # kill grace (30s) so the watchdog never SIGTERMs MT5 while
            # the driver is still completing login + chart-attach.
            "WATCHDOG_STARTUP_GRACE_SECONDS": "450",
        }
        body = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=self._namespace,
                labels=labels,
            ),
            data=data,
        )
        async for attempt in await self._retrying():
            with attempt:
                try:
                    await core_api.create_namespaced_config_map(
                        namespace=self._namespace,
                        body=body,
                    )
                    return
                except ApiException as exc:
                    if exc.status == 409:
                        existing = await core_api.read_namespaced_config_map(
                            name=name,
                            namespace=self._namespace,
                        )
                        body.metadata.resource_version = existing.metadata.resource_version
                        await core_api.replace_namespaced_config_map(
                            name=name,
                            namespace=self._namespace,
                            body=body,
                        )
                        return
                    raise

    async def _upsert_serviceaccount(
        self,
        *,
        core_api: client.CoreV1Api,
        name: str,
        labels: dict[str, str],
    ) -> None:
        """Idempotent create-or-update of the per-tenant ServiceAccount.

        The SA name matches the Vault tenant role's
        bound_service_account_names glob ('etradie-mt-*') so the
        per-tenant Pod can authenticate against Vault and read its
        own tenant path. automountServiceAccountToken=True is
        required because the Vault Agent init-container uses the
        projected token.
        """
        body = client.V1ServiceAccount(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=self._namespace,
                labels=labels,
            ),
            automount_service_account_token=True,
        )
        async for attempt in await self._retrying():
            with attempt:
                try:
                    await core_api.create_namespaced_service_account(
                        namespace=self._namespace,
                        body=body,
                    )
                    return
                except ApiException as exc:
                    if exc.status == 409:
                        existing = await core_api.read_namespaced_service_account(
                            name=name,
                            namespace=self._namespace,
                        )
                        body.metadata.resource_version = existing.metadata.resource_version
                        await core_api.replace_namespaced_service_account(
                            name=name,
                            namespace=self._namespace,
                            body=body,
                        )
                        return
                    raise

    async def _upsert_statefulset(
        self,
        *,
        apps_api: client.AppsV1Api,
        release: str,
        headless_service_name: str,
        labels: dict[str, str],
        selector: dict[str, str],
        platform: str,
        server: str,
        symbol: str,
        zmq_port: int,
        vault_path: str,
        sa_name: str,
        credentials_checksum: str = "",
        connection_id: str,
        user_id: str,
        brand_id: str,
        entity_id: str,
        bundle_r2_path: str,
        bundle_sha256: str,
        watchdog_port: int,
    ) -> None:
        """Create or update the per-tenant StatefulSet.

        Wire shape matches helm/mt-node/templates/statefulset.yaml so
        the chart-rendered and engine-runtime paths produce equivalent
        resources: same labels / selectorLabels, same volumeClaimTemplate
        name, same watchdog sidecar with /healthz + /livez, same
        lifecycle.preStop, same terminationGracePeriodSeconds, same
        security context, and the same Vault Agent Injector annotations.
        """
        # ── mt-node container env ──────────────────────────────────────────
        env = [
            client.V1EnvVar(name="MT_PLATFORM", value=platform),
            client.V1EnvVar(name="MT_SERVER", value=server),
            client.V1EnvVar(name="MT_SYMBOL", value=symbol),
            client.V1EnvVar(name="ZMQ_PORT", value=str(zmq_port)),
            client.V1EnvVar(name="MT_BROKER_ID", value=brand_id),
            client.V1EnvVar(name="MT_BROKER_ENTITY_ID", value=entity_id),
            client.V1EnvVar(name="BUNDLE_R2_PATH", value=bundle_r2_path),
            client.V1EnvVar(name="BUNDLE_SHA256", value=bundle_sha256),
            client.V1EnvVar(
                name="POD_NAME",
                value_from=client.V1EnvVarSource(
                    field_ref=client.V1ObjectFieldSelector(field_path="metadata.name"),
                ),
            ),
            client.V1EnvVar(
                name="POD_NAMESPACE",
                value_from=client.V1EnvVarSource(
                    field_ref=client.V1ObjectFieldSelector(field_path="metadata.namespace"),
                ),
            ),
        ]
        # Per-tenant credentials are rendered into /vault/secrets/<file>
        # by the Vault Agent init-container. The platform Secret
        # (DEFAULT_ZMQ_AUTH_TOKEN) is consumed via envFrom on BOTH the
        # mt-node container and the watchdog sidecar so entrypoint.sh
        # and watchdog.py have a fallback when the Vault Agent file
        # render fails. optional=True so a brief Secret absence during
        # cluster bootstrap does not block Pod scheduling - Vault Agent
        # remains the primary source for per-tenant MT_ZMQ_AUTH_TOKEN.
        #
        # When MT_NODE_PLATFORM_SECRET_NAME is empty (dev / docker-
        # compose / pytest), the envFrom list stays empty, matching
        # the chart's externalSecrets.enabled=false posture.
        env_from: list[client.V1EnvFromSource] = []
        if _PLATFORM_SECRET_NAME:
            env_from.append(
                client.V1EnvFromSource(
                    secret_ref=client.V1SecretEnvSource(
                        name=_PLATFORM_SECRET_NAME,
                        optional=True,
                    ),
                ),
            )

        # ── Shared security context (both containers) ──────────────────────
        container_security_ctx = client.V1SecurityContext(
            allow_privilege_escalation=False,
            read_only_root_filesystem=True,
            run_as_non_root=True,
            run_as_user=1000,
            capabilities=client.V1Capabilities(drop=["ALL"]),
        )

        # ── Shared lifecycle preStop (Wine + LiveUpdate finalize) ──────────
        # LOCKSTEP INVARIANT: must mirror helm/mt-node/values.yaml::
        # lifecycle.preStop. The chart was raised from 5s to 30s as part
        # of the Cluster 1 fix (commit ea5f0c1a; see
        # docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md section 1.4):
        # the original 5s value was enough for the steady-state journal
        # flush but raced LiveUpdate's on-disk rename and left
        # $WINE_PREFIX/.update-timestamp.lock behind, which fed the
        # corruption-reset loop. 30s covers the worst-case rename
        # finalize on the PVC-backed prefix. Combined with entrypoint.sh's
        # SIGTERM trap this gives a clean shutdown across both normal
        # rollout and LiveUpdate-mid-eviction scenarios.
        lifecycle = client.V1Lifecycle(
            pre_stop=client.V1LifecycleHandler(
                _exec=client.V1ExecAction(command=["/bin/sh", "-c", "sleep 30"]),
            ),
        )

        # ── mt-node main container ─────────────────────────────────────────
        # startupProbe: TCP on ZMQ port. Budgets 20 + 5*60 = 320s for
        # cold Wine boot (first-time MT5 install into the Wine prefix).
        # readinessProbe + livenessProbe: HTTP on watchdog /healthz and
        # /livez. Readiness only turns true once the EA reports
        # mt5_connected=true AND authenticated=true within the last 30s.
        container = client.V1Container(
            name="mt-node",
            image=self._image,
            image_pull_policy="IfNotPresent",
            env=env,
            env_from=env_from,
            ports=[
                client.V1ContainerPort(name="zmq", container_port=zmq_port, protocol="TCP"),
            ],
            resources=self._resource_requirements(),
            security_context=container_security_ctx,
            startup_probe=client.V1Probe(
                tcp_socket=client.V1TCPSocketAction(port=zmq_port),
                initial_delay_seconds=20,
                period_seconds=5,
                timeout_seconds=3,
                success_threshold=1,
                # LOCKSTEP INVARIANT: must mirror
                # helm/mt-node/values.yaml::startupProbe.failureThreshold.
                # 120 * 5s + 20s initialDelay = 620s startupProbe budget.
                # Sized for: Wine seed (~10s) + Xvfb/MT5 launch (~15s)
                # + LiveUpdate download + exit-143 self-restart + 30s
                # settle + relaunch (~60s; Cluster 1, one-shot per fresh
                # PVC) + 453-file MQL5 recompile (~100s; build 5836) +
                # Phase 2a dialog poll (~30s) + Phase 2c menu-driven
                # Login invocation hotkey + Alt+F menu fallback (~60s)
                # + Phase 3 credential typing (~30s) + chart open + EA
                # OnInit + :5555 bind (~10s). ~305s baseline; 620s gives
                # 2x headroom. The previous failure_threshold=60 (320s
                # budget) was a latent LOCKSTEP violation against the
                # chart's 120 that became operationally fatal once
                # Phase 2c first-boot work pushed total time past 320s.
                # See docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md
                # §1.4 and the diagnostic capture from 2026-06-24.
                failure_threshold=120,
            ),
            readiness_probe=client.V1Probe(
                http_get=client.V1HTTPGetAction(
                    path="/healthz",
                    port=watchdog_port,
                    scheme="HTTP",
                ),
                initial_delay_seconds=0,
                period_seconds=10,
                timeout_seconds=5,
                success_threshold=1,
                failure_threshold=3,
            ),
            liveness_probe=client.V1Probe(
                http_get=client.V1HTTPGetAction(
                    path="/livez",
                    port=watchdog_port,
                    scheme="HTTP",
                ),
                initial_delay_seconds=0,
                period_seconds=30,
                timeout_seconds=5,
                success_threshold=1,
                failure_threshold=3,
            ),
            lifecycle=lifecycle,
            volume_mounts=[
                # wine-prefix is supplied by volumeClaimTemplates below;
                # K8s wires the per-replica PVC automatically.
                client.V1VolumeMount(name=_PVC_TEMPLATE_NAME, mount_path="/home/mt/.wine"),
                client.V1VolumeMount(name="mt-cache", mount_path="/home/mt/.cache"),
                client.V1VolumeMount(name="tmp", mount_path="/tmp"),  # nosec B108
                client.V1VolumeMount(name="var-tmp", mount_path="/var/tmp"),  # nosec B108
                # aud=vault projected token (volume defined in pod_spec).
                # The Vault Agent reads it via the auth-config-token-path
                # annotation so its login JWT carries aud=vault.
                client.V1VolumeMount(name="vault-token", mount_path="/var/run/secrets/vault", read_only=True),
                client.V1VolumeMount(name="broker-bundle", mount_path="/broker-bundle", read_only=True),
            ],
        )

        # ── Watchdog sidecar ───────────────────────────────────────────────
        # Mirrors chart sidecar.watchdog. Polls the EA HEALTH command,
        # exposes /healthz + /livez + /metrics on :9100. Enforces
        # memory soft-cap (RSS > 0.8 × cgroup limit → restart MT5) and
        # CPU soft-cap (CFS throttled > 0.5 of periods for 60s → restart).
        # Reuses the same mt-node image (watchdog.py is baked in at
        # /opt/watchdog/watchdog.py by the Dockerfile).
        #
        # Watchdog resource sizing mirrors chart values-production.yaml:
        # requests == limits (Guaranteed QoS for the Pod) with sub-core
        # CPU so the watchdog stays in the shared pool while the mt-node
        # container can get exclusive cores via static CPU manager.
        watchdog_resources = client.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "64Mi"},
            limits={"cpu": "100m", "memory": "64Mi"},
        )
        # Watchdog runtime tunables live in a per-release ConfigMap so
        # the engine-runtime provisioner and the chart-rendered
        # platform path produce identical envFrom shapes. POD_NAME and
        # POD_NAMESPACE stay inline because ConfigMaps cannot carry
        # fieldRef.
        watchdog_cm_name = f"{release}-watchdog-config"
        watchdog_env_from = [
            client.V1EnvFromSource(
                config_map_ref=client.V1ConfigMapEnvSource(
                    name=watchdog_cm_name,
                    optional=False,
                ),
            ),
        ]
        # Same platform-Secret envFrom as the mt-node container above
        # so the watchdog's AUTH_TOKEN fallback logic (MT_ZMQ_AUTH_TOKEN
        # or DEFAULT_ZMQ_AUTH_TOKEN) has the platform value available
        # when the Vault Agent file is not yet rendered.
        if _PLATFORM_SECRET_NAME:
            watchdog_env_from.append(
                client.V1EnvFromSource(
                    secret_ref=client.V1SecretEnvSource(
                        name=_PLATFORM_SECRET_NAME,
                        optional=True,
                    ),
                ),
            )
        watchdog_env = [
            client.V1EnvVar(
                name="POD_NAME",
                value_from=client.V1EnvVarSource(
                    field_ref=client.V1ObjectFieldSelector(field_path="metadata.name"),
                ),
            ),
            client.V1EnvVar(
                name="POD_NAMESPACE",
                value_from=client.V1EnvVarSource(
                    field_ref=client.V1ObjectFieldSelector(field_path="metadata.namespace"),
                ),
            ),
        ]
        watchdog_container = client.V1Container(
            name="watchdog",
            image=self._image,
            image_pull_policy="IfNotPresent",
            command=[
                "/usr/bin/tini",
                "--",
                "/usr/bin/env",
                "python3",
                "/opt/watchdog/watchdog.py",
            ],
            env=watchdog_env,
            env_from=watchdog_env_from,
            ports=[
                client.V1ContainerPort(name="watchdog", container_port=watchdog_port, protocol="TCP"),
            ],
            resources=watchdog_resources,
            security_context=container_security_ctx,
            volume_mounts=[
                # Watchdog only needs /tmp (for any transient writes).
                client.V1VolumeMount(name="tmp", mount_path="/tmp"),  # nosec B108
            ],
        )

        # ── broker-bundle initContainer ─────────────────────────────────────
        # Downloads the platform/broker-specific MetaTrader terminal bundle
        # from R2, verifies its SHA256 digest, and unpacks it into the
        # emptyDir volume that the main container mounts at /broker-bundle.
        bundle_init_container = client.V1Container(
            name="broker-bundle",
            image=self._image,  # Reuses mt-node image which has wget + unzip
            image_pull_policy="IfNotPresent",
            command=[
                "/bin/sh",
                "-c",
                (
                    f"echo 'Downloading {bundle_r2_path}...' && "
                    # readOnlyRootFilesystem=true: / and /tmp are NOT
                    # writable. The broker-bundle emptyDir IS writable
                    # (it is the unzip target), so stage the zip there.
                    f"wget -qO /broker-bundle/bundle.zip '{bundle_r2_path}' && "
                    f"echo '{bundle_sha256}  /broker-bundle/bundle.zip' | sha256sum -c - && "
                    f"unzip -q /broker-bundle/bundle.zip -d /broker-bundle && "
                    f"rm /broker-bundle/bundle.zip && "
                    f"echo 'Bundle extracted successfully.'"
                ),
            ],
            security_context=container_security_ctx,
            volume_mounts=[
                client.V1VolumeMount(name="broker-bundle", mount_path="/broker-bundle"),
            ],
        )

        # Parse each scheduling envelope from its ConfigMap-sourced JSON
        # string. kubernetes_asyncio accepts raw dicts/lists in place of
        # typed Tolerations / Affinity / TopologySpreadConstraint objects
        # because the OpenAPI serialisation handles the camelCase mapping.
        tolerations_raw = _parse_json_envelope(
            "MT_NODE_TOLERATIONS_JSON",
            _TOLERATIONS_JSON_RAW,
            list,
        )
        node_selector = _parse_json_envelope(
            "MT_NODE_NODE_SELECTOR_JSON",
            _NODE_SELECTOR_JSON_RAW,
            dict,
        )
        affinity_raw = _parse_json_envelope(
            "MT_NODE_AFFINITY_JSON",
            _AFFINITY_JSON_RAW,
            dict,
        )
        topology_spread_raw = _parse_json_envelope(
            "MT_NODE_TOPOLOGY_SPREAD_JSON",
            _TOPOLOGY_SPREAD_JSON_RAW,
            list,
        )
        pod_annotations = _parse_json_envelope(
            "MT_NODE_POD_ANNOTATIONS_JSON",
            _POD_ANNOTATIONS_JSON_RAW,
            dict,
        )

        # ── Pod spec ───────────────────────────────────────────────────────
        pod_spec = client.V1PodSpec(
            service_account_name=sa_name,
            automount_service_account_token=True,
            security_context=client.V1PodSecurityContext(
                run_as_non_root=True,
                run_as_user=1000,
                run_as_group=1000,
                fs_group=1000,
                seccomp_profile=client.V1SeccompProfile(type="RuntimeDefault"),
            ),
            # LOCKSTEP INVARIANT: must mirror helm/mt-node/values.yaml::
            # terminationGracePeriodSeconds. Raised from 60s to 180s as
            # part of the Cluster 1 fix (commit ea5f0c1a). The 60s value
            # raced the LiveUpdate on-disk rename finalize on pod
            # eviction (rolling update, node drain, image bump), leaving
            # a stale wineboot lock on the PVC and forcing a corruption
            # reset on the next boot. 180s = 30s preStop + 150s SIGTERM
            # grace covers worst-case LiveUpdate finalize plus Wine +
            # MetaTrader write-back plus Vault Agent sidecar shutdown.
            # See docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md.
            termination_grace_period_seconds=180,
            # Share the PID namespace between the mt-node container and
            # the watchdog sidecar so the watchdog's psutil.process_iter
            # can see terminal64.exe and SIGTERM it on a soft-cap trip.
            # Each container has its own PID namespace by default, which
            # would make every soft-cap signal a no-op.
            share_process_namespace=True,
            containers=[container, watchdog_container],
            # The broker-bundle initContainer downloads + sha256-verifies
            # + unzips the broker terminal bundle into the /broker-bundle
            # emptyDir BEFORE the mt-node container starts, so
            # entrypoint.sh finds the broker's servers.dat to install.
            # The Vault injector (agent-init-first=true) prepends its own
            # vault-agent-init ahead of this one; both run to completion
            # before the mt-node container launches.
            init_containers=[bundle_init_container],
            # Inline volumes only; the wine-prefix volume is supplied by
            # volumeClaimTemplates below.
            volumes=[
                client.V1Volume(
                    name="broker-bundle",
                    empty_dir=client.V1EmptyDirVolumeSource(),
                ),
                client.V1Volume(
                    name="mt-cache",
                    empty_dir=client.V1EmptyDirVolumeSource(size_limit="256Mi"),
                ),
                client.V1Volume(
                    name="tmp",
                    empty_dir=client.V1EmptyDirVolumeSource(size_limit="256Mi"),
                ),
                client.V1Volume(
                    name="var-tmp",
                    empty_dir=client.V1EmptyDirVolumeSource(size_limit="64Mi"),
                ),
                # Projected ServiceAccountToken scoped to audience="vault"
                # so the injected Vault Agent presents an aud=vault JWT
                # (the mt-node-tenant role requires audience="vault").
                # The Vault Agent is pointed at this file via the
                # vault.hashicorp.com/auth-config-token-path annotation
                # below. Mirrors the engine's vault-token projection in
                # helm/engine/templates/deployment.yaml. The kubelet mints
                # + rotates the token bound to the pod.
                client.V1Volume(
                    name="vault-token",
                    projected=client.V1ProjectedVolumeSource(
                        sources=[
                            client.V1VolumeProjection(
                                service_account_token=client.V1ServiceAccountTokenProjection(
                                    path="token",
                                    audience="vault",
                                    expiration_seconds=3600,
                                ),
                            ),
                        ],
                    ),
                ),
            ],
            priority_class_name=_PRIORITY_CLASS_NAME_RAW or None,
            tolerations=tolerations_raw,
            node_selector=node_selector,
            affinity=affinity_raw,
            topology_spread_constraints=topology_spread_raw,
            # Match the chart-rendered PodSpec wire shape exactly so a
            # 'kubectl get sts -o yaml' diff between chart-rendered and
            # runtime-provisioned Pods is empty. K8s defaults for both
            # fields already match these values (ClusterFirst is the
            # default when hostNetwork is False; Always is the only
            # valid restartPolicy on a StatefulSet PodTemplate and the
            # API server enforces it), so this is a pure spec-match.
            dns_policy="ClusterFirst",
            restart_policy="Always",
        )

        # Vault Agent Injector annotations. The injector mutates the
        # Pod at admission and adds an initContainer that authenticates
        # against Vault using the Pod's SA token, fetches the secret
        # at <vault_path>, and renders /vault/secrets/mt-credentials.env
        # which the entrypoint and watchdog source at startup.
        #
        # agent-pre-populate-only=false keeps the Vault Agent running
        # as a sidecar so a future token-renewal path can refresh the
        # rendered file. agent-init-first ensures the initContainer
        # runs before the mt-node container, so the file exists by
        # the time entrypoint.sh reads it.
        #
        # The credentials checksum annotation forces a rolling update
        # when the underlying Vault data rotates. Vault Agent does not
        # push updates into a running Pod's tmpfs; the Pod must
        # restart for the new credentials to take effect.
        vault_template = (
            '{{- with secret "' + f"{self._vault_data_path(vault_path)}" + '" -}}\n'
            "export MT_LOGIN={{ .Data.data.mt5_login }}\n"
            "export MT_PASSWORD={{ .Data.data.mt5_password }}\n"
            "export MT_ZMQ_AUTH_TOKEN={{ .Data.data.mt5_zmq_auth_token }}\n"
            "export MT_VAULT_RENDERED_AT={{ timestamp }}\n"
            "{{- end -}}"
        )
        merged_annotations: dict[str, str] = {
            "vault.hashicorp.com/agent-inject": "true",
            "vault.hashicorp.com/role": _VAULT_TENANT_ROLE,
            # The mt-node-tenant Vault k8s-auth role is created with
            # audience="vault" (infrastructure/cluster/vault-paths/
            # mt_node_tenant_secrets.tf). Without this annotation the
            # injected Vault Agent logs in with the pod's DEFAULT SA
            # token (aud=https://kubernetes.default.svc) and Vault
            # rejects it 403 'invalid audience (aud) claim'. This
            # injects "audience":"vault" into the agent's auto_auth
            # kubernetes method config so the login JWT carries
            # aud=vault and matches the role. Mirrors the engine's own
            # aud=vault projected-token fix.
            "vault.hashicorp.com/auth-config-audience": "vault",
            # Point the agent at the projected aud=vault token (mounted
            # at /var/run/secrets/vault from the vault-token volume) so
            # its kubernetes-auth login presents aud=vault, matching the
            # mt-node-tenant role. Without this the agent reads the
            # default API-server SA token and Vault 403s on audience.
            "vault.hashicorp.com/auth-config-token-path": "/var/run/secrets/vault/token",
            # The injector-created vault-agent-init/sidecar containers do
            # not mount our custom vault-token projected volume by
            # default, so the agent cannot read the aud=vault token at
            # the token-path above. Copy the mt-node container's volume
            # mounts (which include /var/run/secrets/vault) onto the
            # agent containers so the token file is visible to them.
            "vault.hashicorp.com/agent-copy-volume-mounts": "mt-node",
            "vault.hashicorp.com/agent-pre-populate-only": "false",
            "vault.hashicorp.com/agent-init-first": "true",
            f"vault.hashicorp.com/agent-inject-secret-{_VAULT_SECRETS_FILE}": self._vault_data_path(vault_path),
            f"vault.hashicorp.com/agent-inject-template-{_VAULT_SECRETS_FILE}": vault_template,
            "etradie.io/broker-bundle-sha256": bundle_sha256,
        }
        # Stamp the sentinel-or-real symbol's resolution moment on the
        # initial pod template so a chart upgrade that replaces the
        # StatefulSet does not lose the annotation; HostedRecoveryService
        # uses it as a freshness signal.
        if symbol != SYMBOL_PENDING_SENTINEL:
            merged_annotations["etradie.io/symbol-resolved-at"] = str(int(_time.time()))
        if pod_annotations:
            merged_annotations.update(pod_annotations)
        if credentials_checksum:
            merged_annotations["etradie.io/vault-credentials-checksum"] = credentials_checksum

        pod_template_metadata = client.V1ObjectMeta(
            labels=selector
            | {
                _LABEL_PART_OF: _PART_OF_VALUE,
                _LABEL_COMPONENT: "mt-node",
                _LABEL_USER_ID: labels[_LABEL_USER_ID],
                _LABEL_PLATFORM: platform,
            },
            annotations=merged_annotations or None,
        )
        pod_template = client.V1PodTemplateSpec(
            metadata=pod_template_metadata,
            spec=pod_spec,
        )

        # volumeClaimTemplate. K8s materialises this into a per-replica
        # PVC named '<template>-<sts>-<ordinal>' = 'wine-prefix-<release>-0'.
        # The reclaim policy is set at the StorageClass level; the chart's
        # convention is Retain so the Wine prefix survives a helm uninstall.
        pvc_template = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(
                name=_PVC_TEMPLATE_NAME,
                labels={
                    _LABEL_APP_NAME: _APP_NAME_VALUE,
                    _LABEL_INSTANCE: release,
                    _LABEL_COMPONENT: "wine-prefix",
                },
            ),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(
                    requests={"storage": os.environ.get("MT_NODE_PVC_SIZE", "4Gi")},
                ),
            ),
        )

        sts = client.V1StatefulSet(
            metadata=client.V1ObjectMeta(name=release, namespace=self._namespace, labels=labels),
            spec=client.V1StatefulSetSpec(
                replicas=1,
                service_name=headless_service_name,
                pod_management_policy="OrderedReady",
                update_strategy=client.V1StatefulSetUpdateStrategy(
                    type="RollingUpdate",
                    rolling_update=client.V1RollingUpdateStatefulSetStrategy(partition=0),
                ),
                revision_history_limit=5,
                selector=client.V1LabelSelector(match_labels=selector),
                template=pod_template,
                volume_claim_templates=[pvc_template],
            ),
        )

        async for attempt in await self._retrying():
            with attempt:
                try:
                    await apps_api.create_namespaced_stateful_set(
                        namespace=self._namespace,
                        body=sts,
                    )
                    return
                except ApiException as exc:
                    if exc.status == 409:
                        await apps_api.replace_namespaced_stateful_set(
                            name=release,
                            namespace=self._namespace,
                            body=sts,
                        )
                        return
                    raise

    async def _upsert_service(
        self,
        *,
        core_api: client.CoreV1Api,
        name: str,
        labels: dict[str, str],
        selector: dict[str, str],
        zmq_port: int,
        headless: bool,
    ) -> None:
        """Idempotent create-or-update of a Service.

        When headless=True, sets clusterIP='None' so the Service is
        used only for stable per-pod DNS by the StatefulSet. When
        False (the regular ClusterIP Service), engine ZmqClient
        traffic flows through this Service AND Prometheus scrapes
        the watchdog /metrics on :9100.
        """
        watchdog_port = DEFAULT_WATCHDOG_PORT
        # The headless Service is for stable pod-DNS only; it does not
        # need to expose the watchdog port because Prometheus discovers
        # the watchdog via the regular ClusterIP Service's ServiceMonitor.
        ports = [
            client.V1ServicePort(
                name="zmq",
                port=zmq_port,
                target_port="zmq",
                protocol="TCP",
            ),
        ]
        if not headless:
            ports.append(
                client.V1ServicePort(
                    name="watchdog",
                    port=watchdog_port,
                    target_port="watchdog",
                    protocol="TCP",
                ),
            )
        service_spec = client.V1ServiceSpec(
            type="ClusterIP",
            cluster_ip="None" if headless else None,
            publish_not_ready_addresses=False,
            selector=selector,
            ports=ports,
        )
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=name, namespace=self._namespace, labels=labels),
            spec=service_spec,
        )
        async for attempt in await self._retrying():
            with attempt:
                try:
                    await core_api.create_namespaced_service(
                        namespace=self._namespace,
                        body=service,
                    )
                    return
                except ApiException as exc:
                    if exc.status == 409:
                        existing = await core_api.read_namespaced_service(
                            name=name,
                            namespace=self._namespace,
                        )
                        # Preserve clusterIP (immutable). For a headless
                        # service the existing clusterIP is 'None' and
                        # we keep it; for a regular service it's the
                        # allocated IP and we must also keep it.
                        service.spec.cluster_ip = existing.spec.cluster_ip
                        service.metadata.resource_version = existing.metadata.resource_version
                        await core_api.replace_namespaced_service(
                            name=name,
                            namespace=self._namespace,
                            body=service,
                        )
                        return
                    raise

    # -- Internal: readiness gate -------------------------------------------

    async def _wait_ready(
        self,
        *,
        core_api: client.CoreV1Api,
        apps_api: client.AppsV1Api,
        release: str,
        dns_name: str,
        zmq_port: int,
        token: str,
        timeout: float,
    ) -> None:
        """Block until StatefulSet has a Ready replica AND ZMQ PING
        returns ok, or raise.

        Uses the api clients provided by the caller - no per-iteration
        construction/close churn. The caller (provision_account) owns
        the lifecycle.
        """
        del core_api  # unused here; reserved for future use
        deadline = _time.monotonic() + timeout
        last_error: Exception | None = None

        # Phase 1 - StatefulSet has at least one Ready replica.
        while _time.monotonic() < deadline:
            try:
                sts = await apps_api.read_namespaced_stateful_set(
                    name=release,
                    namespace=self._namespace,
                )
                ready = int(sts.status.ready_replicas or 0)
                if ready >= 1:
                    break
            except ApiException as exc:
                last_error = exc
                logger.debug(
                    "hosted_readiness_sts_poll_error",
                    extra={
                        "release": release,
                        "status": exc.status,
                        "reason": exc.reason,
                    },
                )
            await asyncio.sleep(_READINESS_POLL_SECS)
        else:
            raise ProviderTimeoutError(
                "mt-node StatefulSet did not become Ready within timeout",
                details={
                    "release": release,
                    "timeout_secs": timeout,
                    "last_error": str(last_error) if last_error else None,
                },
            )

        # Phase 2 - ZMQ PING through Service DNS.
        while _time.monotonic() < deadline:
            try:
                ok = await self._zmq_ping(dns_name=dns_name, port=zmq_port, token=token)
                if ok:
                    return
            except ProviderError:
                # The EA returned an explicit error envelope (typically
                # auth failure). No amount of further polling will
                # change the answer; surface immediately so the caller
                # gets the real diagnostic instead of a deadline.
                raise
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.debug(
                    "hosted_readiness_ping_error",
                    extra={"release": release, "dns": dns_name, "error": str(exc)},
                )
            await asyncio.sleep(_READINESS_POLL_SECS)

        raise ProviderTimeoutError(
            "mt-node ZMQ PING did not succeed within timeout",
            details={
                "release": release,
                "dns": dns_name,
                "timeout_secs": timeout,
                "last_error": str(last_error) if last_error else None,
            },
        )

    # -- Internal: broker catalog population + StatefulSet env patch --

    async def _populate_broker_catalog(
        self,
        *,
        connection_id: str,
        dns_name: str,
        zmq_port: int,
        token: str,
        existing_chart_symbol: str | None = None,
    ) -> str:
        """Pick the chart-attach symbol from the broker's Market Watch.

        The provision-time path is intentionally fast: it asks the EA
        for the symbol-name list (one ZMQ round-trip), returns the
        first name, and defers the per-symbol metadata sync
        (path/digits/point) to a background task scheduled by the
        Container's BackgroundTaskCoordinator. The dashboard's
        /api/broker/symbols endpoint triggers a lazy sync on first
        read so the user sees their catalogue while metadata enrichment
        finishes asynchronously.

        When existing_chart_symbol is non-empty (recovery re-provision
        on an already-resolved connection), the catalog runner is STILL
        invoked so the background BrokerSyncService refreshes
        broker_symbols, but the existing symbol is returned for the
        StatefulSet env patch instead of names[0]. This is the H-4
        guard: a Market Watch order shift on the broker side cannot
        silently reshuffle a user's persisted mt5_symbol.

        Raises ProviderError when there is no existing symbol AND the
        broker reports zero instruments so the caller never receives
        a 'success' result for a Pod whose chart could not be resolved.
        This prevents the silent stuck-on-sentinel state
        HostedRecoveryService had to keep retrying out of.
        """
        assert self._catalog_sync_runner is not None
        assert self._chart_symbol_writer is not None
        # Always run the runner so the background catalog sync fires
        # (broker_symbols freshness on every provision). The runner's
        # return value is the first-name pick; we only use it when
        # there is no existing value to preserve.
        resolver_pick = await self._catalog_sync_runner(
            dns_name=dns_name,
            zmq_port=zmq_port,
            auth_token=token,
        )
        if existing_chart_symbol and existing_chart_symbol.strip():
            return existing_chart_symbol.strip()
        if not resolver_pick:
            raise ProviderError(
                "Broker did not publish any tradeable symbols; cannot "
                "select a chart-attach symbol. The connection has not "
                "been persisted.",
                details={
                    "connection_id": connection_id,
                    "dns_name": dns_name,
                },
            )
        return resolver_pick

    async def _patch_statefulset_symbol(
        self,
        *,
        apps_api: client.AppsV1Api,
        release: str,
        active_symbol: str,
    ) -> None:
        """Patch MT_SYMBOL on the pod template once the broker is reachable.

        The provisioner first-boots the StatefulSet with
        SYMBOL_PENDING_SENTINEL so the entrypoint skips chart-template
        writing. After the broker reports its first published symbol
        we patch MT_SYMBOL to that value; K8s observes the pod template
        diff and performs one rolling restart, after which the
        entrypoint writes the chart template normally.

        The caller (provision_account) raises ProviderError on an
        empty broker catalog so this method is only invoked with a
        non-empty symbol.
        """
        if not active_symbol:
            logger.warning(
                "hosted_symbol_resolution_empty",
                extra={"release": release},
            )
            return

        env_patch = [
            {"name": "MT_SYMBOL", "value": active_symbol},
        ]
        patch_body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "etradie.io/symbol-resolved-at": str(int(_time.time())),
                        },
                    },
                    "spec": {
                        "containers": [
                            {"name": "mt-node", "env": env_patch},
                        ],
                    },
                },
            },
        }
        try:
            await apps_api.patch_namespaced_stateful_set(
                name=release,
                namespace=self._namespace,
                body=patch_body,
            )
            logger.info(
                "hosted_statefulset_symbol_patched",
                extra={"release": release, "active_symbol": active_symbol},
            )
        except ApiException as exc:
            raise ProviderError(
                f"Failed to patch StatefulSet with resolved symbol: {exc.reason}",
                details={
                    "release": release,
                    "active_symbol": active_symbol,
                    "status": exc.status,
                },
            ) from exc

    async def _zmq_ping(self, *, dns_name: str, port: int, token: str) -> bool:
        """PING the EA. Returns True on auth success.

        Raises ProviderError on an explicit EA error envelope (auth
        rejected, EA not running, command unsupported) so the caller
        does not waste the readiness budget polling a permanent failure.
        Network-level failures bubble up as their native exception type
        and are treated as transient by _wait_ready.
        """
        endpoint = f"tcp://{dns_name}:{port}"
        ctx = zmq_async.Context.instance()
        sock = ctx.socket(zmq.REQ)
        sock.setsockopt(zmq.LINGER, 0)
        sock.setsockopt(zmq.RCVTIMEO, int(_ZMQ_PROBE_TIMEOUT_SECS * 1000))
        sock.setsockopt(zmq.SNDTIMEO, int(_ZMQ_PROBE_TIMEOUT_SECS * 1000))
        try:
            sock.connect(endpoint)
            await asyncio.wait_for(
                sock.send_string(json.dumps({"command": "PING", "auth_token": token})),
                timeout=_ZMQ_PROBE_TIMEOUT_SECS,
            )
            raw = await asyncio.wait_for(sock.recv(), timeout=_ZMQ_PROBE_TIMEOUT_SECS)
            reply = json.loads(raw.decode("utf-8"))
            if not isinstance(reply, dict):
                return False
            if reply.get("status") == "ok":
                return True
            ea_error = reply.get("error")
            if ea_error:
                raise ProviderError(
                    f"EA rejected PING: {ea_error}",
                    details={
                        "endpoint": endpoint,
                        "ea_error": str(ea_error)[:200],
                    },
                )
            return False
        finally:
            try:
                sock.close(linger=0)
            except Exception:  # noqa: BLE001
                pass  # nosec B110

    # -- Internal: deletion helpers -----------------------------------------

    async def _safe_delete(self, fn, name: str, kind: str) -> bool:
        try:
            await fn(name=name, namespace=self._namespace)
            logger.info("hosted_resource_deleted", extra={"kind": kind, "name": name})
            return True
        except ApiException as exc:
            if exc.status == 404:
                return True
            logger.warning(
                "hosted_resource_delete_failed",
                extra={
                    "kind": kind,
                    "name": name,
                    "status": exc.status,
                    "reason": exc.reason,
                },
            )
            return False

    async def _best_effort_cleanup(
        self,
        *,
        core_api: client.CoreV1Api,
        apps_api: client.AppsV1Api,
        vault: VaultClient | None,
        release: str,
        service_name: str,
        headless_service_name: str,
        sa_name: str,
        vault_path: str,
    ) -> None:
        """Roll back orphan K8s objects on a transient provision failure.

        CRITICAL: this function MUST NOT delete the wine-prefix PVC.
        The PVC carries MetaTrader's LiveUpdate-applied components
        (e.g. mt5onnx64), the broker's trusted-device profile, the
        EA's compiled state, and the chart-template files. Destroying
        it on a transient readiness/PING/post-upsert failure forces
        the next provision attempt to seed from the image-baked
        template, which MT5 then sees as out-of-date and re-runs
        LiveUpdate against, producing the exit-143 self-restart loop
        documented in docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md.

        PVC deletion is ONLY correct on explicit user action
        (delete_account) or when a connection_id is gone from the
        database (gc_orphans). Never on error rollback.

        Vault credentials are also preserved here - they belong to
        the same connection_id and HostedRecoveryService.reprovision
        will reuse them on the next sweep. Destroying them would
        force the engine to mint a new ZMQ token that the EA running
        on the surviving PVC's restored prefix no longer matches.
        """
        # NOTE: order is best-effort; every step is idempotent.
        # NOTE: wine-prefix PVC is INTENTIONALLY omitted; see docstring.
        # NOTE: Vault path destroy is INTENTIONALLY omitted; see docstring.
        for fn, name, kind in (
            (apps_api.delete_namespaced_stateful_set, release, "StatefulSet"),
            (core_api.delete_namespaced_service, service_name, "Service"),
            (
                core_api.delete_namespaced_service,
                headless_service_name,
                "Service(headless)",
            ),
            (core_api.delete_namespaced_service_account, sa_name, "ServiceAccount"),
            (
                core_api.delete_namespaced_secret,
                f"{release}-creds",
                "Secret(legacy-creds)",
            ),
            (
                core_api.delete_namespaced_config_map,
                f"{release}-watchdog-config",
                "ConfigMap(watchdog-config)",
            ),
        ):
            try:
                await fn(name=name, namespace=self._namespace)
            except ApiException as exc:
                if exc.status != 404:
                    logger.warning(
                        "hosted_rollback_warning",
                        extra={"kind": kind, "name": name, "status": exc.status},
                    )
        # Vault path is INTENTIONALLY preserved. The PVC is INTENTIONALLY
        # preserved. Both belong to the connection_id and will be reused
        # by the next reconciliation (HostedRecoveryService or a user-
        # initiated re-provision). Only delete_account() and gc_orphans()
        # are allowed to destroy them.
        del vault, vault_path  # unused on purpose; see docstring.
