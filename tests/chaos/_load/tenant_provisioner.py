"""Bulk tenant provisioner for Section 10 load tests.

Provisions N hosted broker connections via the engine's HTTP API in
parallel with bounded concurrency (default 20). Yields each
provisioned tenant as a structured Tenant dataclass; cleanup is
automatic via an async context manager.

The credentials come from a JSON file the operator points at via
ETRADIE_CHAOS_TEST_CREDS_FILE. The file MUST be a JSON array of
objects with the keys {login, password, server}. The harness errors
clean if the requested N exceeds the file length - we do NOT make
up credentials because the engine's provision_account readiness gate
runs a real ZMQ PING and would fail against a synthetic account.
"""
from __future__ import annotations

import asyncio
import json
import os
import ssl
import urllib.error
import urllib.request
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

_PROVISION_TIMEOUT_SECS = 300.0  # matches HostedProvisioner._READINESS_TIMEOUT_SECS
_PROVISION_CONCURRENCY = 20
_POLL_INTERVAL_SECS = 5.0


@dataclass
class Tenant:
    user_id: str
    connection_id: str
    name: str
    login: str
    server: str


@dataclass
class ProvisioningOutcome:
    successful: list[Tenant] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)  # (login, error)
    elapsed_secs: float = 0.0


def _load_creds_file() -> list[dict[str, str]]:
    path = os.environ.get("ETRADIE_CHAOS_TEST_CREDS_FILE", "").strip()
    if not path:
        raise RuntimeError(
            "ETRADIE_CHAOS_TEST_CREDS_FILE not set. Provide a path to a JSON "
            "array of {login, password, server} objects (one per tenant)."
        )
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise RuntimeError(
            f"{path}: expected a JSON array of credential objects, got {type(data).__name__}"
        )
    for i, entry in enumerate(data):
        for k in ("login", "password", "server"):
            if k not in entry or not str(entry[k]).strip():
                raise RuntimeError(
                    f"{path}[{i}]: missing required field {k!r}"
                )
    return data


class TenantProvisioner:
    def __init__(
        self,
        *,
        engine_url: str,
        admin_jwt: str,
        insecure_tls: bool = False,
    ) -> None:
        self._engine_url = engine_url.rstrip("/")
        self._admin_jwt = admin_jwt
        self._insecure = insecure_tls
        self._semaphore = asyncio.Semaphore(_PROVISION_CONCURRENCY)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        url = self._engine_url + path
        headers = {
            "Authorization": f"Bearer {self._admin_jwt}",
            "Content-Type": "application/json",
        }
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, method=method, headers=headers, data=data)
        ctx = None
        if self._insecure:
            ctx = ssl._create_unverified_context()

        # urllib is blocking; run in a worker thread so a slow engine
        # cannot pin the asyncio loop. asyncio.to_thread serialises the
        # call but the semaphore above already bounds parallelism.
        def _do() -> str:
            try:
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                    return resp.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                try:
                    err_body = exc.read().decode("utf-8")
                except Exception:  # noqa: BLE001
                    err_body = str(exc)
                raise RuntimeError(f"HTTP {exc.code} {method} {path}: {err_body}")

        raw = await asyncio.to_thread(_do)
        if not raw:
            return {}
        return json.loads(raw)

    async def _provision_one(
        self,
        creds: dict[str, str],
        user_id_prefix: str,
    ) -> Tenant | tuple[str, str]:
        async with self._semaphore:
            user_id = f"{user_id_prefix}-{uuid.uuid4().hex[:8]}"
            name = f"load-test-{creds['login']}"
            try:
                created = await self._request(
                    "POST",
                    "/api/broker/connections",
                    body={
                        "connection_type": "hosted",
                        "name": name,
                        "mt5_login": creds["login"],
                        "mt5_password": creds["password"],
                        "mt5_server": creds["server"],
                        "platform": "mt5",
                    },
                    timeout=_PROVISION_TIMEOUT_SECS,
                )
            except RuntimeError as exc:
                return (creds["login"], str(exc))

            connection_id = created.get("id")
            if not connection_id:
                return (creds["login"], f"engine response missing id: {created}")

            # Poll until status=='connected' with bounded timeout.
            deadline = asyncio.get_event_loop().time() + _PROVISION_TIMEOUT_SECS
            while asyncio.get_event_loop().time() < deadline:
                await asyncio.sleep(_POLL_INTERVAL_SECS)
                try:
                    current = await self._request(
                        "GET",
                        f"/api/broker/connections/{connection_id}",
                        timeout=30.0,
                    )
                except RuntimeError as exc:
                    continue
                if current.get("status") == "connected":
                    return Tenant(
                        user_id=user_id,
                        connection_id=connection_id,
                        name=name,
                        login=creds["login"],
                        server=creds["server"],
                    )
            return (
                creds["login"],
                f"connection {connection_id} did not reach status='connected' within {_PROVISION_TIMEOUT_SECS}s",
            )

    async def provision_n(
        self,
        n: int,
        *,
        user_id_prefix: str = "loadtest",
    ) -> ProvisioningOutcome:
        creds_pool = _load_creds_file()
        if n > len(creds_pool):
            raise RuntimeError(
                f"requested {n} tenants but only {len(creds_pool)} test creds "
                f"are available in ETRADIE_CHAOS_TEST_CREDS_FILE"
            )
        start = asyncio.get_event_loop().time()
        coros = [
            self._provision_one(creds, user_id_prefix=user_id_prefix)
            for creds in creds_pool[:n]
        ]
        results = await asyncio.gather(*coros, return_exceptions=False)
        outcome = ProvisioningOutcome(
            elapsed_secs=asyncio.get_event_loop().time() - start,
        )
        for r in results:
            if isinstance(r, Tenant):
                outcome.successful.append(r)
            else:
                outcome.failed.append(r)
        return outcome

    async def teardown(self, tenants: list[Tenant]) -> None:
        """Delete every provisioned connection in parallel. Errors are
        logged via print but never raised; the test cleanup MUST be
        best-effort to avoid masking the real test failure."""
        async def _delete(t: Tenant) -> None:
            async with self._semaphore:
                try:
                    await self._request(
                        "DELETE",
                        f"/api/broker/connections/{t.connection_id}",
                        timeout=60.0,
                    )
                except RuntimeError as exc:
                    print(
                        f"teardown: DELETE {t.connection_id} failed: {exc}",
                        flush=True,
                    )

        await asyncio.gather(*(_delete(t) for t in tenants), return_exceptions=True)

    @asynccontextmanager
    async def lease(
        self,
        n: int,
        *,
        user_id_prefix: str = "loadtest",
    ) -> AsyncIterator[ProvisioningOutcome]:
        """Provision N tenants for the duration of an async context.
        Cleans up on exit regardless of test pass/fail."""
        outcome = await self.provision_n(n, user_id_prefix=user_id_prefix)
        try:
            yield outcome
        finally:
            await self.teardown(outcome.successful)
