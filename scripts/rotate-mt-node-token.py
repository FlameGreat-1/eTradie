#!/usr/bin/env python3
"""Rotate the per-tenant ZMQ auth token for a hosted broker connection.

Deletes the existing broker_connections row and re-creates it with
the same MT credentials. The engine's HostedProvisioner generates a
fresh secrets.token_hex(32) on the re-provision, writes a new K8s
Secret, and the StatefulSet rolling-updates the Pod.

Usage:
  rotate-mt-node-token.py \\
    --connection-id=<UUID> \\
    --engine-url=https://engine.etradie-system.svc.cluster.local:8000 \\
    --jwt=<ADMIN_SERVICE_TOKEN>

Env var equivalents (CLI flags win when both are present):
  ETRADIE_ROTATE_CONNECTION_ID
  ETRADIE_ROTATE_ENGINE_URL
  ETRADIE_ROTATE_JWT

Exit codes:
  0  Rotation succeeded; new connection landed in status='connected'.
  1  Required arguments missing.
  2  Pre-flight check failed (connection_id not found, etc.).
  3  Re-provision failed.
  4  Verification timed out (new connection did not reach
     status='connected' within 5 minutes).

This script is intentionally thin - it does NOTHING the engine HTTP
API does not already permit. It exists to prevent operators from
copy-pasting curl commands during incidents. See
docs/runbooks/mt-node-secret-rotation.md Section A for the full
procedure including pre-flight, verification, and rollback.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

_VERIFICATION_TIMEOUT_SECS = 300
_VERIFICATION_POLL_SECS = 5


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rotate the per-tenant ZMQ auth token for a hosted broker connection.",
    )
    parser.add_argument(
        "--connection-id",
        default=os.environ.get("ETRADIE_ROTATE_CONNECTION_ID", ""),
        help="UUID of the broker_connections row to rotate.",
    )
    parser.add_argument(
        "--engine-url",
        default=os.environ.get(
            "ETRADIE_ROTATE_ENGINE_URL",
            "http://localhost:8000",
        ),
        help="Base URL of the engine HTTP API.",
    )
    parser.add_argument(
        "--jwt",
        default=os.environ.get("ETRADIE_ROTATE_JWT", ""),
        help="Admin service-token JWT (Authorization: Bearer header).",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS cert verification (dev only).",
    )
    args = parser.parse_args()
    if not args.connection_id or not args.jwt:
        parser.error("--connection-id and --jwt are both required")
    return args


def _request(
    method: str,
    url: str,
    jwt: str,
    *,
    body: dict | None = None,
    insecure: bool = False,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, method=method, headers=headers, data=data)
    ctx = None
    if insecure:
        import ssl
        ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        try:
            body_text = exc.read().decode("utf-8")
        except Exception:  # noqa: BLE001
            body_text = str(exc)
        raise RuntimeError(f"HTTP {exc.code} {method} {url}: {body_text}") from exc


def main() -> int:
    args = _parse_args()
    engine = args.engine_url.rstrip("/")

    # 1. Pre-flight: fetch the existing row.
    print(f"[1/4] Fetching connection {args.connection_id} ...", file=sys.stderr)
    try:
        existing = _request(
            "GET",
            f"{engine}/api/broker/connections/{args.connection_id}",
            args.jwt,
            insecure=args.insecure,
        )
    except RuntimeError as exc:
        print(f"FATAL: pre-flight failed: {exc}", file=sys.stderr)
        return 2

    if existing.get("connection_type") != "hosted":
        print(
            f"FATAL: connection_type is {existing.get('connection_type')!r}, "
            "but this script only rotates 'hosted' connections.",
            file=sys.stderr,
        )
        return 2

    print(
        f"      user_id={existing.get('user_id')} "
        f"server={existing.get('mt5_server')} "
        f"login={existing.get('mt5_login')} "
        f"status={existing.get('status')}",
        file=sys.stderr,
    )

    # 2. Re-provision via the admin re-provision endpoint. The engine's
    #    HostedProvisioner.provision_account is idempotent and re-rolls
    #    the per-tenant secrets.token_hex(32) ea_auth_token on every
    #    call, so a re-provision IS the rotation - no delete needed.
    print("[2/4] Triggering re-provision ...", file=sys.stderr)
    try:
        result = _request(
            "POST",
            f"{engine}/api/broker/connections/{args.connection_id}/reprovision",
            args.jwt,
            body={"reason": "admin_token_rotation"},
            insecure=args.insecure,
        )
    except RuntimeError as exc:
        print(f"FATAL: re-provision failed: {exc}", file=sys.stderr)
        return 3
    print(f"      reprovision_id={result.get('reprovision_id')}", file=sys.stderr)

    # 3. Poll until the connection's status returns to 'connected'.
    print("[3/4] Verifying new connection lands in status='connected' ...", file=sys.stderr)
    deadline = time.monotonic() + _VERIFICATION_TIMEOUT_SECS
    while time.monotonic() < deadline:
        time.sleep(_VERIFICATION_POLL_SECS)
        try:
            current = _request(
                "GET",
                f"{engine}/api/broker/connections/{args.connection_id}",
                args.jwt,
                insecure=args.insecure,
            )
        except RuntimeError as exc:
            print(f"      poll failed ({exc}); continuing", file=sys.stderr)
            continue
        status = current.get("status")
        print(f"      status={status}", file=sys.stderr)
        if status == "connected":
            break
    else:
        print(
            f"FATAL: connection did not reach status='connected' "
            f"within {_VERIFICATION_TIMEOUT_SECS}s. Inspect the Pod:\n"
            f"  kubectl -n etradie-system describe sts etradie-mt-{args.connection_id[:12]}",
            file=sys.stderr,
        )
        return 4

    print("[4/4] Rotation complete.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
