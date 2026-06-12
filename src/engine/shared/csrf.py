"""CSRF enforcement for the Python FastAPI engine.

Implements the same double-submit pattern as the Go gateway
(src/auth/csrf.go) so the SPA's axios interceptor can attach a single
X-CSRF-Token header that is validated by every service it talks to.

Two modes, selected by the AUTH_CSRF_SIGNED env var:

  Signed (default, AUTH_CSRF_SIGNED=true):
    Cookie value = "<random_hex>.<hmac_sha256_hex>" where the HMAC is
    keyed on AUTH_JWT_SECRET and computed over random_hex + ":" + user_id.
    The middleware resolves the authenticated user from the request state
    (populated by get_current_user before this middleware runs) and
    recomputes the HMAC. A sibling-subdomain XSS that reads the cookie
    cannot replay it against a different user's session.

  Unsigned (AUTH_CSRF_SIGNED=false):
    Cookie value = random hex; header echoes it verbatim. Kept for a
    staged rollout when the SPA is being updated in lockstep.

Safe HTTP methods (GET, HEAD, OPTIONS) bypass the check. Mutating
methods (POST, PUT, PATCH, DELETE) are gated unconditionally.

Usage in FastAPI:

    from engine.shared.csrf import CSRFMiddleware
    app.add_middleware(CSRFMiddleware)

The middleware reads AUTH_CSRF_HEADER (default X-CSRF-Token),
AUTH_CSRF_SIGNED (default true), and AUTH_JWT_SECRET from the
environment at startup so it stays in sync with the Go gateway's
configuration without any extra wiring.
"""

from __future__ import annotations

import hashlib
import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

# HTTP methods that require a valid CSRF token. Anything not in this
# set passes through without any cookie/header inspection.
_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Cookie name mirrors the Go gateway's auth.CSRFCookieName. Both the
# prefixed (__Secure-csrf_token) and unprefixed forms are tried so an
# in-flight rollout where the gateway started emitting the prefixed
# name but the browser still holds the old cookie keeps working.
_CSRF_COOKIE_NAMES = ("__Secure-csrf_token", "csrf_token")


def _get_csrf_header_name() -> str:
    return os.environ.get("AUTH_CSRF_HEADER", "X-CSRF-Token").strip() or "X-CSRF-Token"


def _is_signed_mode() -> bool:
    return os.environ.get("AUTH_CSRF_SIGNED", "true").strip().lower() not in (
        "false",
        "0",
        "no",
    )


def _get_jwt_secret() -> bytes:
    return os.environ.get("AUTH_JWT_SECRET", "").encode()


def _compute_expected_mac(secret: bytes, random_hex: str, user_id: str) -> str:
    """Recompute the HMAC the Go gateway embedded in the cookie.

    Mirrors SignCSRFToken in src/auth/csrf.go:
        mac = HMAC-SHA256(secret, random_hex + ":" + user_id)
    """
    msg = (random_hex + ":" + user_id).encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def _constant_time_equal(a: str, b: str) -> bool:
    """Constant-time string comparison that also handles length differences."""
    return hmac.compare_digest(a.encode(), b.encode())


def _read_csrf_cookie(request: Request) -> str | None:
    """Return the CSRF cookie value, trying prefixed then unprefixed name."""
    for name in _CSRF_COOKIE_NAMES:
        val = request.cookies.get(name, "").strip()
        if val:
            return val
    return None


def _verify_csrf(request: Request, header_name: str, signed: bool, secret: bytes) -> bool:
    """Return True iff the CSRF cookie + header pair is valid.

    In signed mode the authenticated user_id is read from
    request.state.user (set by get_current_user before this runs).
    If the user is not in state (unauthenticated request that somehow
    reached a mutating route), the check fails.
    """
    cookie_val = _read_csrf_cookie(request)
    if not cookie_val:
        return False

    header_val = request.headers.get(header_name, "").strip()
    if not header_val:
        return False

    if not signed:
        return _constant_time_equal(cookie_val, header_val)

    # Signed mode: both cookie and header must be <random>.<mac>.
    if "." not in cookie_val or "." not in header_val:
        return False

    c_random, c_mac = cookie_val.split(".", 1)
    h_random, h_mac = header_val.split(".", 1)

    if not c_random or not c_mac or not h_random or not h_mac:
        return False

    # Double-submit invariant: random portions must match.
    if not _constant_time_equal(c_random, h_random):
        return False

    # MAC portions must match (header echoes cookie verbatim).
    if not _constant_time_equal(c_mac, h_mac):
        return False

    # Resolve the authenticated user from the request directly.
    # Middleware runs BEFORE FastAPI dependencies, so request.state.user
    # is not populated yet. We read the JWT from the cookie or header.
    #
    # The cookie is tried under the __Secure- prefixed name first then
    # the unprefixed fallback: in production the gateway sets
    # `__Secure-access_token` and, under Option B, reverse-proxies the
    # browser's engine calls forwarding that cookie verbatim. Reading
    # only the unprefixed name here left user_id empty and 403'd every
    # mutating engine request in production. Mirrors _read_csrf_cookie
    # above and src/auth/cookies.go::readCookieValue.
    user_id = ""
    token = ""  # nosec B105
    for _name in ("__Secure-access_token", "access_token"):
        _val = request.cookies.get(_name, "").strip()
        if _val:
            token = _val
            break
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    if token:
        import jwt

        try:
            # We skip full validation here because the get_current_user
            # dependency will do it later. We just need the 'sub' claim
            # to verify the CSRF HMAC. An attacker cannot forge the CSRF
            # HMAC even if they forge the unverified JWT sub claim.
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get("sub", "")
        except Exception:  # nosec B110
            pass

    if not user_id:
        return False

    expected_mac = _compute_expected_mac(secret, c_random, user_id)
    return _constant_time_equal(c_mac, expected_mac)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Starlette/FastAPI middleware that enforces double-submit CSRF.

    Configuration is read from environment variables at construction
    time so the middleware stays in sync with the Go gateway without
    any extra wiring:

        AUTH_CSRF_HEADER  -- header name the SPA echoes the cookie in
                             (default: X-CSRF-Token)
        AUTH_CSRF_SIGNED  -- "true" (default) for signed mode,
                             "false" for naive double-submit
        AUTH_JWT_SECRET   -- HMAC key in signed mode (must match the
                             Go gateway's AUTH_JWT_SECRET)

    Paths that bypass the CSRF gate:
        - Any path starting with /internal/ (server-to-server calls
          authenticated by X-Internal-Auth shared secret instead).
        - /health, /health/rag, /metrics (ops endpoints).
        - Any safe HTTP method (GET, HEAD, OPTIONS).

    All other mutating requests (POST, PUT, PATCH, DELETE) are gated.
    A missing or invalid CSRF pair returns 403 with a fixed generic
    message so a probe cannot map out which side failed.
    """

    # Paths that are exempt from CSRF regardless of method. These are
    # server-to-server or public endpoints that never carry a browser
    # cookie jar.
    _EXEMPT_PREFIXES = ("/internal/", "/health", "/metrics")

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._header_name = _get_csrf_header_name()
        self._signed = _is_signed_mode()
        self._secret = _get_jwt_secret()

    async def dispatch(self, request: Request, call_next):
        # Safe methods never need a CSRF token.
        if request.method not in _MUTATING_METHODS:
            return await call_next(request)

        # Exempt paths (internal, health, metrics).
        path = request.url.path
        for prefix in self._EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        if not _verify_csrf(request, self._header_name, self._signed, self._secret):
            return JSONResponse(
                status_code=403,
                content={"detail": "csrf token missing or invalid"},
            )

        return await call_next(request)
