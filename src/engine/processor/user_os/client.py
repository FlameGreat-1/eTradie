"""Async HTTP client for the gateway's trading-system internal API.

Mirrors the gateway -> engine X-Internal-Auth + X-User-Id contract
used by every other /internal/* call, just inverted: now the engine
is the caller and the gateway is the server.

Failure mode by design: any error (network, 5xx, malformed JSON,
status != 'active') returns None. The processor pipeline then falls
back to the default institutional profile, which is the correct
behaviour per PRACTICE.md — a transient outage must NEVER prevent an
analysis from running.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Header names mirror src/gateway/internal/infra/engine_http.go so any
# future rename is a one-line change on both sides.
_INTERNAL_AUTH_HEADER = "X-Internal-Auth"
_INTERNAL_USER_ID_HEADER = "X-User-Id"

_DEFAULT_TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True)
class UserOSRecord:
    """Lightweight engine-side view of the gateway record."""

    user_id: str
    status: str  # 'none' | 'skipped' | 'active'
    version: int
    profile: Optional[dict[str, Any]]
    has_profile: bool

    @property
    def is_active(self) -> bool:
        return self.status == "active" and self.has_profile and self.profile is not None


class UserOSClient:
    """Fetches user trading systems from the gateway's internal API.

    A single instance is built at engine startup and shared across
    every processor request. The underlying httpx.AsyncClient is
    long-lived (connection pooling) and closed via close() on shutdown.
    """

    def __init__(
        self,
        *,
        gateway_base_url: str,
        internal_secret: str,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = gateway_base_url.rstrip("/")
        self._secret = internal_secret
        self._client: Optional[httpx.AsyncClient] = None
        self._timeout = timeout_seconds
        self._lock = asyncio.Lock()

    @classmethod
    def from_env(cls) -> Optional["UserOSClient"]:
        """Build a client from environment variables.

        Returns None when the gateway URL or shared secret is missing,
        so the processor can run in unit tests / local dev without
        attempting an HTTP call. Production deployments must set both
        ENGINE_GATEWAY_URL and ENGINE_INTERNAL_SHARED_SECRET.
        """
        base_url = (
            os.environ.get("ENGINE_GATEWAY_URL")
            or os.environ.get("GATEWAY_HTTP_URL")
            or ""
        ).strip()
        secret = (
            os.environ.get("ENGINE_INTERNAL_SHARED_SECRET")
            or os.environ.get("GATEWAY_ENGINE_INTERNAL_SHARED_SECRET")
            or ""
        ).strip()
        if not base_url or not secret:
            logger.info(
                "user_os_client_disabled",
                extra={
                    "base_url_set": bool(base_url),
                    "secret_set": bool(secret),
                },
            )
            return None
        return cls(gateway_base_url=base_url, internal_secret=secret)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        async with self._lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    timeout=self._timeout,
                    headers={"Content-Type": "application/json"},
                )
        return self._client

    async def get(self, user_id: str) -> Optional[UserOSRecord]:
        """Fetch the user's trading system from the gateway.

        Returns None on any error or when the user has no active
        profile. Callers must NOT block the LLM pipeline on this call;
        a missing profile is a successful fast-path that yields the
        default institutional behaviour.
        """
        if not user_id:
            return None

        url = f"{self._base_url}/internal/trading-system/get"
        try:
            client = await self._get_client()
            resp = await client.post(
                url,
                json={"user_id": user_id},
                headers={
                    _INTERNAL_AUTH_HEADER: self._secret,
                    _INTERNAL_USER_ID_HEADER: user_id,
                },
            )
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.warning(
                "user_os_fetch_failed_transport",
                extra={"user_id": user_id, "error": str(exc)},
            )
            return None

        if resp.status_code != 200:
            logger.warning(
                "user_os_fetch_failed_status",
                extra={
                    "user_id": user_id,
                    "status": resp.status_code,
                    "body_preview": resp.text[:200],
                },
            )
            return None

        try:
            body = resp.json()
        except ValueError:
            logger.warning(
                "user_os_fetch_failed_json",
                extra={"user_id": user_id, "body_preview": resp.text[:200]},
            )
            return None

        return UserOSRecord(
            user_id=str(body.get("user_id", user_id)),
            status=str(body.get("status", "none")),
            version=int(body.get("version", 0) or 0),
            profile=body.get("profile") if isinstance(body.get("profile"), dict) else None,
            has_profile=bool(body.get("has_profile", False)),
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
