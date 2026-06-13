"""JWT authentication for the Python FastAPI engine.

Verifies JWT tokens issued by the Go auth service. Uses the same
HMAC-SHA256 shared secret (AUTH_JWT_SECRET env var) so tokens issued
by the Go service are valid here and vice versa.

Token sources (in priority order, matching src/auth/middleware.go on
the Go gateway side):

  1. ``Authorization: Bearer <token>`` header. Used by CLI tooling
     and server-to-server callers that hold a token explicitly.
  2. ``access_token`` cookie. Used by cookie-auth browsers; the
     cookie is HttpOnly and Secure on the Go gateway, scoped by
     host (not port) under RFC 6265 §5.4, so a single login on the
     gateway is automatically attached to engine requests too.

WebSocket handshakes carry cookies the same way regular HTTP requests
do, so the same precedence applies. The dedicated WS helper
``verify_token_from_websocket`` adds a third, optional channel: a
``token`` field on the init frame, preserved for non-browser WS
clients that hold a token explicitly. Browsers must not use it
(they cannot read the HttpOnly cookie to copy it in).

Usage in FastAPI endpoints:

    from engine.shared.auth import get_current_user, AuthenticatedUser

    @app.get("/api/something")
    async def my_endpoint(user: AuthenticatedUser = Depends(get_current_user)):
        # user.user_id, user.username, user.role, user.tier, user.status
        ...

Usage in FastAPI WebSocket endpoints:

    from engine.shared.auth import verify_token_from_websocket

    @app.websocket("/ws/path")
    async def my_ws(websocket: WebSocket):
        await websocket.accept()
        try:
            user = await verify_token_from_websocket(websocket, init_message=None)
        except AuthError as exc:
            await websocket.close(code=4003, reason=str(exc))
            return
        ...
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Reusable FastAPI security scheme. auto_error=False so we can fall
# through to the cookie reader when the Authorization header is
# absent rather than 401-ing immediately.
_bearer_scheme = HTTPBearer(auto_error=False)

# Canonical cookie name. Mirrors the Go gateway's
# src/auth/cookies.go::AccessTokenCookieName. Kept in sync via
# coordinated change; both services share the same auth contract.
ACCESS_TOKEN_COOKIE_NAME = "access_token"  # nosec B105

# RFC 6265bis __Secure- prefix the Go gateway prepends when
# CookieSecure=true (always in production). The reader helpers below
# try the prefixed name first, then the unprefixed fallback, exactly
# like src/auth/cookies.go::readCookieValue. This MUST be tolerated
# here because under Option B (single public entry point) the gateway
# reverse-proxies the browser's engine calls forwarding the cookie jar
# verbatim, so in production the engine receives `__Secure-access_token`
# rather than `access_token`.
_SECURE_COOKIE_PREFIX = "__Secure-"


def _read_access_token_cookie(cookies) -> str:
    """Return the access-token cookie value, trying the __Secure-
    prefixed name first then the unprefixed fallback. Accepts any
    mapping with a .get(name) accessor (Request.cookies / the
    WebSocket cookie jar). Returns "" when neither is present.
    """
    for name in (
        _SECURE_COOKIE_PREFIX + ACCESS_TOKEN_COOKIE_NAME,
        ACCESS_TOKEN_COOKIE_NAME,
    ):
        val = cookies.get(name)
        if val and val.strip():
            return val.strip()
    return ""


class AuthError(Exception):
    """Raised by ``verify_token_from_websocket`` on auth failure.

    WebSocket endpoints must translate this into a close-frame with an
    application-level code (4001–4003 in this codebase). HTTP
    endpoints use ``HTTPException`` directly.
    """


@dataclass(frozen=True)
class AuthenticatedUser:
    """Authenticated user extracted from a verified JWT token.

    Available in every protected endpoint via FastAPI dependency injection.
    """

    user_id: str
    username: str
    role: str  # "admin" or "etradie"
    tier: str  # "free", "pro_byok", "pro_managed"
    status: str  # "active", "past_due", "canceled", ...

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _get_jwt_secret() -> str:
    """Read the JWT signing secret from environment.

    Must match the AUTH_JWT_SECRET used by the Go auth service.
    Fails fast if not configured in production or staging.
    """
    secret = os.environ.get("AUTH_JWT_SECRET", "")
    app_env = os.environ.get("APP_ENV", "").lower()
    is_prod_like = app_env in ("production", "prod", "staging")

    if not secret:
        if is_prod_like:
            raise RuntimeError(
                f"AUTH_JWT_SECRET is required in {app_env}. "
                "It must match the same secret used by the Go auth service. "
                "Generate with: openssl rand -hex 64"
            )
        # In development, allow empty (Go auth service generates a random one,
        # but for local dev both services should share the same .env file).
        logger.warning(
            "AUTH_JWT_SECRET not set. JWT verification will fail for tokens "
            "issued by the Go auth service unless both share the same secret."
        )
        return secret
    return secret


def _get_jwt_issuer() -> str:
    """Read the expected JWT issuer claim."""
    return os.environ.get("AUTH_ISSUER", "etradie")


def _verify_token(token: str) -> AuthenticatedUser:
    """Verify a JWT token and extract the authenticated user.

    Validates:
    - Signature (HMAC-SHA256 with shared secret)
    - Expiry (exp claim)
    - Issuer (iss claim)
    - Required claims: sub, username, role

    Raises HTTPException(401) on any verification failure.
    """
    secret = _get_jwt_secret()
    if not secret:
        raise HTTPException(
            status_code=500,
            detail="Authentication not configured (AUTH_JWT_SECRET missing)",
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer=_get_jwt_issuer(),
            options={
                # `status` is REQUIRED: it is a security gate (active /
                # suspended / deactivated), not optional metadata. This
                # mirrors the Go gateway's VerifyAccessToken, which fails
                # closed on a missing status claim. Audit ref: A1.
                "require": ["sub", "username", "role", "exp", "iat", "status"],
                "verify_exp": True,
                "verify_iss": True,
            },
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Invalid token issuer")
    except jwt.InvalidTokenError as exc:
        logger.warning("jwt_verification_failed", extra={"error": str(exc)})
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    username = payload.get("username")
    role = payload.get("role")
    tier = payload.get("tier", "free")
    # `status` is a security gate. Fail CLOSED: a missing, empty, or
    # non-string status is rejected rather than coerced to "active".
    # This matches the Go gateway's VerifyAccessToken (Tier 1 item 4)
    # so both verifiers of the same token agree. `tier` keeps its
    # "free" default because defaulting an entitlement floor down is
    # fail-SAFE (least privilege). Audit ref: A1.
    status = payload.get("status")

    if not user_id or not username or not role:
        raise HTTPException(
            status_code=401,
            detail="Token missing required claims (sub, username, role)",
        )

    if not isinstance(status, str) or not status.strip():
        raise HTTPException(
            status_code=401,
            detail="Token missing required claim (status)",
        )

    if role not in ("admin", "etradie"):
        raise HTTPException(status_code=401, detail=f"Invalid role: {role}")

    return AuthenticatedUser(
        user_id=user_id,
        username=username,
        role=role,
        tier=tier,
        status=status,
    )


def _extract_token_from_request(
    credentials: HTTPAuthorizationCredentials | None,
    request: Request,
) -> str | None:
    """Return the raw JWT from the highest-priority source on the request.

    1. The Authorization Bearer credential captured by HTTPBearer.
    2. The ``access_token`` cookie set by the Go gateway.

    A missing or empty source returns ``None`` so the caller can decide
    whether to 401 (RequireAuth) or pass through (OptionalAuth).
    """
    if credentials is not None:
        token = (credentials.credentials or "").strip()
        if token:
            return token
    cookie = _read_access_token_cookie(request.cookies)
    if cookie:
        return cookie
    return None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    """FastAPI dependency: require a valid JWT from header or cookie.

    Resolution order:
      1. Authorization: Bearer <token>
      2. access_token cookie

    Raises 401 if neither channel yields a valid token. The response
    advertises ``WWW-Authenticate: Bearer`` so non-browser clients see
    the canonical challenge; browsers ignore it and re-route to /login
    via the axios interceptor.
    """
    token = _extract_token_from_request(credentials, request)
    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _verify_token(token)


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser | None:
    """FastAPI dependency: optionally authenticate from header or cookie.

    Returns ``None`` if no token is provided (anonymous access).
    Raises 401 if a token IS provided but is invalid — a bad cookie
    must NOT be silently treated as unauthenticated.
    """
    token = _extract_token_from_request(credentials, request)
    if token is None:
        return None
    return _verify_token(token)


async def get_admin_user(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """FastAPI dependency: require admin role."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def verify_token_from_websocket(
    websocket: WebSocket,
    init_message: Mapping[str, Any] | None = None,
) -> AuthenticatedUser:
    """Resolve the authenticated user for a WebSocket connection.

    Resolution order:
      1. Authorization: Bearer <token> header on the upgrade (CLI clients).
      2. ``access_token`` cookie on the upgrade (browser cookie-auth).
      3. ``token`` field on the init frame (legacy non-browser clients).

    Browsers cannot put a token into channel 3 because the cookie is
    HttpOnly; channels 1–2 cover them. Channel 3 stays for backward
    compatibility with CLI tooling that explicitly sends a token in
    the first JSON frame.

    Raises ``AuthError`` on missing or invalid credentials. The caller
    is responsible for translating it into a WS close-frame.
    """
    # 1. Authorization header on the upgrade.
    auth_header = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
    if auth_header:
        token = auth_header.strip()
        if token.lower().startswith("bearer "):
            token = token[len("bearer ") :].strip()
        if token:
            try:
                return _verify_token(token)
            except HTTPException as exc:
                raise AuthError(exc.detail) from exc

    # 2. access_token cookie on the upgrade (prefixed or unprefixed).
    cookie = _read_access_token_cookie(websocket.cookies)
    if cookie:
        try:
            return _verify_token(cookie)
        except HTTPException as exc:
            raise AuthError(exc.detail) from exc

    # 3. Init-frame token for legacy non-browser clients.
    if init_message is not None:
        token_field = init_message.get("token") if isinstance(init_message, Mapping) else None
        if isinstance(token_field, str) and token_field.strip():
            try:
                return _verify_token(token_field.strip())
            except HTTPException as exc:
                raise AuthError(exc.detail) from exc

    raise AuthError("Missing authentication credentials")
