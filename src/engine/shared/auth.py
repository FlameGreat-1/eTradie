"""JWT authentication for the Python FastAPI engine.

Verifies JWT Bearer tokens issued by the Go auth service.
Uses the same HMAC-SHA256 shared secret (AUTH_JWT_SECRET env var)
so tokens issued by the Go service are valid here and vice versa.

Usage in FastAPI endpoints:

    from engine.shared.auth import get_current_user, AuthenticatedUser

    @app.get("/api/something")
    async def my_endpoint(user: AuthenticatedUser = Depends(get_current_user)):
        # user.user_id, user.username, user.role are available
        ...
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Reusable FastAPI security scheme.
_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    """Authenticated user extracted from a verified JWT token.

    Available in every protected endpoint via FastAPI dependency injection.
    """

    user_id: str
    username: str
    role: str  # "admin" or "etradie"
    tier: str  # "free", "pro_byok", "pro_managed"
    status: str # "active", "past_due", "canceled"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _get_jwt_secret() -> str:
    """Read the JWT signing secret from environment.

    Must match the AUTH_JWT_SECRET used by the Go auth service.
    Fails fast if not configured in production.
    """
    secret = os.environ.get("AUTH_JWT_SECRET", "")
    if not secret:
        app_env = os.environ.get("APP_ENV", "development").lower()
        if app_env in ("production", "staging"):
            raise RuntimeError(
                "AUTH_JWT_SECRET environment variable is required in production/staging. "
                "It must match the same secret used by the Go auth service."
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
                "require": ["sub", "username", "role", "exp", "iat"],
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
    status = payload.get("status", "active")

    if not user_id or not username or not role:
        raise HTTPException(
            status_code=401,
            detail="Token missing required claims (sub, username, role)",
        )

    if role not in ("admin", "etradie"):
        raise HTTPException(status_code=401, detail=f"Invalid role: {role}")

    return AuthenticatedUser(
        user_id=user_id, 
        username=username, 
        role=role,
        tier=tier,
        status=status
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    """FastAPI dependency: require a valid JWT Bearer token.

    Usage:
        @app.get("/protected")
        async def endpoint(user: AuthenticatedUser = Depends(get_current_user)):
            ...
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _verify_token(credentials.credentials)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[AuthenticatedUser]:
    """FastAPI dependency: optionally authenticate if token is present.

    Returns None if no token is provided (anonymous access).
    Raises 401 if a token IS provided but is invalid.
    """
    if credentials is None:
        return None
    return _verify_token(credentials.credentials)


async def get_admin_user(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """FastAPI dependency: require admin role.

    Usage:
        @app.get("/admin-only")
        async def endpoint(user: AuthenticatedUser = Depends(get_admin_user)):
            ...
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
