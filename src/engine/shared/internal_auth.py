"""Shared-secret authentication for engine internal endpoints.

The engine's /internal/* routes are called server-to-server by the Go
gateway. They must NOT be reachable with a regular user cookie because
that would let any authenticated user trigger TA analysis, macro
collection, RAG retrieval, processor runs, and broker operations
directly without going through the gateway's guard layer.

This module provides a FastAPI dependency that validates the
X-Internal-Auth header against the ENGINE_INTERNAL_SHARED_SECRET
environment variable using constant-time comparison. The secret must
be at least 32 characters; startup fails fast if it is absent or too
short in production/staging.

The Go gateway sends this header on every call to /internal/* via the
EngineHTTPClient (src/gateway/internal/infra/engine_http.go). The
billing service uses the same pattern for /internal/checkout with the
X-Internal-Auth header and BILLING_INTERNAL_SHARED_SECRET.

Usage in FastAPI endpoints:

    from engine.shared.internal_auth import verify_internal_auth

    @router.post("/internal/ta/analyze")
    async def internal_ta_analyze(
        request: Request,
        body: InternalTARequest,
        _: None = Depends(verify_internal_auth),
    ) -> dict:
        ...

The dependency returns None on success and raises HTTP 401 on failure
so the error shape is consistent with the user-auth dependencies.
"""
from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request

# Header name mirrors billing/server/http.go::InternalAuthHeader.
INTERNAL_AUTH_HEADER = "X-Internal-Auth"

# Minimum secret length. Matches the Go gateway's validation for
# BILLING_INTERNAL_SHARED_SECRET (32 chars).
_MIN_SECRET_LEN = 32


def _load_secret() -> bytes:
    """Read and validate the shared secret at import time.

    Fails fast in production/staging if the secret is absent or too
    short. In development (APP_ENV unset or 'development'), a missing
    secret is allowed but a warning is logged so developers know the
    internal endpoints are effectively open.
    """
    secret = os.environ.get("ENGINE_INTERNAL_SHARED_SECRET", "").strip()
    app_env = os.environ.get("APP_ENV", "").lower()
    is_prod_like = app_env in ("production", "prod", "staging")

    if not secret:
        if is_prod_like:
            raise RuntimeError(
                f"ENGINE_INTERNAL_SHARED_SECRET is required in {app_env}. Generate with: openssl rand -hex 32"
            )
        # Development: log a warning but don't crash. The dependency
        # will reject every request with 401 until the secret is set,
        # which is the safe default.
        import logging

        logging.getLogger(__name__).warning(
            "ENGINE_INTERNAL_SHARED_SECRET is not set. "
            "All /internal/* requests will be rejected with 401. "
            "Set the variable to enable gateway-to-engine calls."
        )
        return b""

    if len(secret) < _MIN_SECRET_LEN:
        raise RuntimeError(
            f"ENGINE_INTERNAL_SHARED_SECRET must be at least {_MIN_SECRET_LEN} "
            f"characters, got {len(secret)}. "
            "Generate with: openssl rand -hex 32"
        )

    return secret.encode()


# Loaded once at module import time so the startup check runs before
# any request is served. The value is module-level so tests can patch
# it without reloading the module.
_INTERNAL_SECRET: bytes = _load_secret()


async def verify_internal_auth(request: Request) -> None:
    """FastAPI dependency: require a valid X-Internal-Auth shared secret.

    Compares the header value to ENGINE_INTERNAL_SHARED_SECRET using
    constant-time comparison (hmac.compare_digest) so the check is
    not vulnerable to timing attacks.

    Raises HTTP 401 on any failure. The response body is intentionally
    generic so a probe cannot distinguish "header absent" from "header
    present but wrong".
    """
    if not _INTERNAL_SECRET:
        # Secret not configured: always reject. This is the safe
        # default for a development environment where the operator
        # has not yet set the variable.
        raise HTTPException(status_code=401, detail="unauthorized")

    provided = request.headers.get(INTERNAL_AUTH_HEADER, "").strip().encode()
    if not provided:
        raise HTTPException(status_code=401, detail="unauthorized")

    if not hmac.compare_digest(provided, _INTERNAL_SECRET):
        raise HTTPException(status_code=401, detail="unauthorized")
