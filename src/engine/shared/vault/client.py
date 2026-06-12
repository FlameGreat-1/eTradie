"""Vault HTTP client.

Async KV-v2 client that authenticates with the engine pod's
ServiceAccount token via Vault's Kubernetes auth backend, caches the
Vault token, renews it before expiry, and exposes the three
operations the engine needs for per-tenant credential storage:

  - write(path, data)                 - write a new version under <mount>/data/<path>
  - delete(path)                      - soft-delete the latest version
  - destroy_all_versions(path)        - permanently destroy every version

Wraps the existing engine.shared.http.HttpClient so retry, circuit
breaker, and Prometheus instrumentation are shared with the rest of
the engine's outbound calls. Token refresh is asyncio-Lock-guarded so
concurrent first-touch callers serialise into a single auth round-trip.
"""

from __future__ import annotations

import asyncio
import os
import time as _time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.shared.exceptions import (
    ConfigurationError,
    ETradieBaseError,
    ProviderError,
)
from engine.shared.http.client import HttpClient
from engine.shared.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_SA_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
_DEFAULT_K8S_AUTH_PATH = "kubernetes"
_DEFAULT_KV_MOUNT = "etradie"
_DEFAULT_RENEW_SAFETY_SECS = 60.0
_PROVIDER_NAME = "vault"


class VaultError(ETradieBaseError):
    """Raised on any Vault HTTP failure or misconfiguration."""


@dataclass(frozen=True)
class VaultConfig:
    """Vault client configuration. Constructed from environment."""

    address: str
    namespace: str
    kv_mount: str
    k8s_auth_path: str
    k8s_auth_role: str
    sa_token_path: str
    renew_safety_secs: float

    @classmethod
    def from_env(cls) -> VaultConfig:
        address = os.environ.get("VAULT_ADDR", "").strip().rstrip("/")
        if not address:
            raise ConfigurationError(
                "VAULT_ADDR is not set",
                details={"env_var": "VAULT_ADDR"},
            )
        role = os.environ.get("VAULT_K8S_AUTH_ROLE", "").strip()
        if not role:
            raise ConfigurationError(
                "VAULT_K8S_AUTH_ROLE is not set",
                details={"env_var": "VAULT_K8S_AUTH_ROLE"},
            )
        try:
            renew_safety = float(
                os.environ.get(
                    "VAULT_TOKEN_RENEW_SAFETY_SECS",
                    str(_DEFAULT_RENEW_SAFETY_SECS),
                )
            )
        except ValueError as exc:
            raise ConfigurationError(
                "VAULT_TOKEN_RENEW_SAFETY_SECS must be a number",
                details={"error": str(exc)},
            ) from exc
        if renew_safety < 1:
            raise ConfigurationError(
                "VAULT_TOKEN_RENEW_SAFETY_SECS must be >= 1",
                details={"value": renew_safety},
            )
        return cls(
            address=address,
            namespace=os.environ.get("VAULT_NAMESPACE", "").strip(),
            kv_mount=os.environ.get("VAULT_MOUNT", _DEFAULT_KV_MOUNT).strip() or _DEFAULT_KV_MOUNT,
            k8s_auth_path=os.environ.get("VAULT_K8S_AUTH_PATH", _DEFAULT_K8S_AUTH_PATH).strip()
            or _DEFAULT_K8S_AUTH_PATH,
            k8s_auth_role=role,
            sa_token_path=os.environ.get("VAULT_K8S_SA_TOKEN_PATH", _DEFAULT_SA_TOKEN_PATH).strip()
            or _DEFAULT_SA_TOKEN_PATH,
            renew_safety_secs=renew_safety,
        )


class VaultClient:
    """Async Vault KV-v2 client with K8s-auth token caching."""

    def __init__(self, *, http_client: HttpClient, config: VaultConfig) -> None:
        self._http = http_client
        self._config = config
        self._token: str | None = None
        self._token_expires_mono: float = 0.0
        self._renewable: bool = False
        self._lock = asyncio.Lock()

    # ---- KV-v2 operations -----------------------------------------------

    async def write_kv(self, path: str, data: dict[str, Any]) -> None:
        """Write a new version of the secret at <mount>/data/<path>."""
        if not path:
            raise VaultError("Vault path must not be empty")
        if not isinstance(data, dict) or not data:
            raise VaultError("Vault data payload must be a non-empty dict")
        url = self._kv_url(path, sub="data")
        body = {"data": data}
        await self._request_with_auth("POST", url, json_body=body, category="kv_write")

    async def delete_kv(self, path: str) -> None:
        """Soft-delete the latest version at <mount>/data/<path>."""
        if not path:
            raise VaultError("Vault path must not be empty")
        url = self._kv_url(path, sub="data")
        await self._request_with_auth("DELETE", url, category="kv_delete")

    async def destroy_all_versions(self, path: str) -> None:
        """Permanently destroy every version at <mount>/metadata/<path>."""
        if not path:
            raise VaultError("Vault path must not be empty")
        url = self._kv_url(path, sub="metadata")
        await self._request_with_auth("DELETE", url, category="kv_destroy")

    # ---- Authentication --------------------------------------------------

    async def _ensure_token(self) -> str:
        """Return a valid Vault token, refreshing when within the safety window."""
        async with self._lock:
            now = _time.monotonic()
            if self._token is not None and now + self._config.renew_safety_secs < self._token_expires_mono:
                return self._token
            await self._login_locked()
            assert self._token is not None
            return self._token

    async def _login_locked(self) -> None:
        sa_token = self._read_sa_token()
        url = f"{self._config.address}/v1/auth/{self._config.k8s_auth_path}/login"
        body = {"jwt": sa_token, "role": self._config.k8s_auth_role}
        headers = self._headers(include_token=False)
        resp = await self._http.request(
            "POST",
            url,
            provider_name=_PROVIDER_NAME,
            category="login",
            headers=headers,
            json_body=body,
        )
        if not isinstance(resp, dict):
            raise VaultError(
                "Vault login returned unexpected payload",
                details={"type": type(resp).__name__},
            )
        auth = resp.get("auth") or {}
        token = auth.get("client_token")
        if not token:
            raise VaultError(
                "Vault login response missing auth.client_token",
                details={"response_keys": list(resp.keys())},
            )
        lease_duration = float(auth.get("lease_duration") or 0)
        self._token = token
        self._renewable = bool(auth.get("renewable"))
        self._token_expires_mono = _time.monotonic() + lease_duration
        logger.info(
            "vault_login_success",
            extra={
                "role": self._config.k8s_auth_role,
                "lease_duration_secs": lease_duration,
                "renewable": self._renewable,
            },
        )

    def _invalidate_token(self) -> None:
        self._token = None
        self._token_expires_mono = 0.0
        self._renewable = False

    def _read_sa_token(self) -> str:
        try:
            return Path(self._config.sa_token_path).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise VaultError(
                "Cannot read pod ServiceAccount token",
                details={"path": self._config.sa_token_path, "error": str(exc)},
            ) from exc

    # ---- HTTP plumbing ---------------------------------------------------

    async def _request_with_auth(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        category: str = "unknown",
    ) -> Any:
        """Execute a Vault request with one auto-reauth on 403."""
        for attempt in range(2):
            token = await self._ensure_token()
            headers = self._headers(include_token=True, token=token)
            try:
                return await self._http.request(
                    method,
                    url,
                    provider_name=_PROVIDER_NAME,
                    category=category,
                    headers=headers,
                    json_body=json_body,
                )
            except ProviderError as exc:
                status = (exc.details or {}).get("status")
                if status in (401, 403) and attempt == 0:
                    logger.warning(
                        "vault_token_rejected_reauthenticating",
                        extra={"status": status, "category": category},
                    )
                    self._invalidate_token()
                    continue
                raise VaultError(
                    f"Vault {method} failed: {exc}",
                    details={"url": url, "category": category, **(exc.details or {})},
                ) from exc
        # Defensive; the loop either returns or raises above.
        raise VaultError(
            f"Vault {method} failed after re-auth attempt",
            details={"url": url, "category": category},
        )

    def _headers(self, *, include_token: bool, token: str | None = None) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._config.namespace:
            headers["X-Vault-Namespace"] = self._config.namespace
        if include_token and token:
            headers["X-Vault-Token"] = token
        return headers

    def _kv_url(self, path: str, *, sub: str) -> str:
        path = path.strip("/")
        return f"{self._config.address}/v1/{self._config.kv_mount}/{sub}/{path}"
