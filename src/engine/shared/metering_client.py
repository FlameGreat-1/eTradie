"""Metering client: calls the gateway's /internal/metering/* endpoints.

The gateway is the single source of truth for LLM token quotas. The
engine calls Reserve before every LLM call, Commit after it returns,
and Refund when the call fails after retries are exhausted. The gateway
writes the provisional debit to billing_usage inside a transaction so
two parallel calls from the same user cannot both slip past the cap.

This module is intentionally thin: it does HTTP, maps status codes to
exceptions, and returns the reservation ID. All policy logic lives in
the gateway (src/gateway/internal/server/metering_handler.go) and the
billing store (src/billing/store/usage.go).

Configuration (read lazily on first reserve / commit / refund call):

    METERING_GATEWAY_URL
        Base URL of the gateway HTTP server, e.g.
        http://gateway:8080. Must NOT have a trailing slash.
        Required when METERING_ENABLED=true in prod/staging.

    METERING_ENABLED
        Set to 'false' / '0' / 'no' to disable metering entirely.
        When disabled, reserve() returns an empty string and commit()
        / refund() are no-ops. Useful for local dev without a running
        gateway. Default: true.

    ENGINE_INTERNAL_SHARED_SECRET
        The shared secret sent in X-Internal-Auth. Must match
        GATEWAY_ENGINE_INTERNAL_SHARED_SECRET. Required when
        METERING_ENABLED=true in prod/staging.

Lazy-load rationale: a module-import-time env read crashes the entire
engine process on a misconfigured deploy, before any health probe can
run. Deferring the read to first call surfaces the same error against
the specific request that needs metering, which the existing
retry_llm_call wrapper maps to a clean HTTP 500. The operator sees
the error in the logs of the failed request instead of in a startup
crash loop.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

from engine.shared.exceptions import QuotaExceededError
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration (lazily resolved on first call; cached thereafter)
# ---------------------------------------------------------------------------

_ENABLED_TRUTHY = {"1", "true", "yes", "on"}

# Timeout for metering calls. These are synchronous on the hot path so
# they must be fast. 3 s is generous; the gateway does a single DB
# upsert + insert inside a transaction.
_TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True)
class MeteringConfig:
    """Snapshot of the env-var configuration consumed by this module.

    Immutable so a concurrent reserve()/commit() race can never observe
    a half-written config. Built once by _build_config() and cached
    by get_config() under a lock.
    """

    enabled: bool
    gateway_url: str
    secret: str


# Module-private cache. None means "not yet resolved".
_config: Optional[MeteringConfig] = None
_config_lock = threading.Lock()


def _build_config() -> MeteringConfig:
    """Read env vars and assemble a MeteringConfig.

    Raises RuntimeError when METERING_ENABLED=true in a prod-like env
    (production, prod, staging) but METERING_GATEWAY_URL or
    ENGINE_INTERNAL_SHARED_SECRET is unset. This raise propagates up
    through reserve()/commit()/refund() to the caller (retry_llm_call
    in processor.service) which maps it to HTTP 500.

    In non-prod-like envs (dev, test, empty APP_ENV) a missing
    gateway_url silently disables metering with a warning log line,
    so a local developer never needs to set METERING_* to get a
    working engine.
    """
    raw = os.environ.get("METERING_ENABLED", "true").strip().lower()
    enabled = raw in _ENABLED_TRUTHY

    gateway_url = os.environ.get("METERING_GATEWAY_URL", "").rstrip("/").strip()
    secret = os.environ.get("ENGINE_INTERNAL_SHARED_SECRET", "").strip()

    app_env = os.environ.get("APP_ENV", "").lower()
    is_prod_like = app_env in ("production", "prod", "staging")

    if enabled and is_prod_like:
        if not gateway_url:
            raise RuntimeError(
                "METERING_GATEWAY_URL is required when METERING_ENABLED=true "
                f"in {app_env}. Set it to the gateway HTTP base URL."
            )
        if not secret:
            raise RuntimeError(
                "ENGINE_INTERNAL_SHARED_SECRET is required when "
                f"METERING_ENABLED=true in {app_env}."
            )

    if enabled and not gateway_url:
        logger.warning(
            "metering_disabled_no_gateway_url",
            extra={"reason": "METERING_GATEWAY_URL not set; metering will be skipped"},
        )
        enabled = False

    return MeteringConfig(enabled=enabled, gateway_url=gateway_url, secret=secret)


def get_config() -> MeteringConfig:
    """Return the cached MeteringConfig, building it on first call.

    Thread-safe: the build path holds _config_lock so two parallel
    first-call reserves cannot both pay the env-read cost. Subsequent
    calls take the fast path (no lock acquisition) because the cached
    config is an immutable frozen dataclass and a stale read of the
    module-level binding is acceptable.
    """
    global _config
    cfg = _config
    if cfg is not None:
        return cfg
    with _config_lock:
        if _config is None:
            _config = _build_config()
        return _config


def reset_config_for_tests() -> None:
    """Clear the cached config so the next get_config() call re-reads env.

    Test-only helper. Production code must never call this; the cache
    is intentional and re-reading env in steady state would be a perf
    regression on the LLM hot path.
    """
    global _config
    with _config_lock:
        _config = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def reserve(
    *,
    user_id: str,
    provider: str,
    model: str,
    estimated_input_tokens: int,
    max_output_tokens: int,
    trace_id: str = "",
) -> str:
    """Reserve a provisional LLM token debit before the call.

    Returns the reservation ID on success. Returns an empty string when
    metering is disabled (dev mode) so the caller can skip Commit/Refund
    without branching on a flag.

    Raises:
        RuntimeError: when METERING_ENABLED=true in prod-like env but
            METERING_GATEWAY_URL or ENGINE_INTERNAL_SHARED_SECRET is
            missing. Surfaced lazily on the first metering call so a
            misconfig does not crash the engine on import.
        QuotaExceededError: when the user has hit a per-tier cap. The
            caller should propagate this as a 429 to the gateway.
        httpx.HTTPError: on transport failure. The caller should treat
            this as a transient error and NOT proceed with the LLM call
            (fail closed: if we cannot meter, we cannot charge).
    """
    cfg = get_config()
    if not cfg.enabled:
        return ""
    if not user_id:
        logger.warning("metering_reserve_skipped_no_user_id")
        return ""

    payload = {
        "provider": provider,
        "model": model,
        "estimated_input_tokens": max(0, estimated_input_tokens),
        "max_output_tokens": max(1, max_output_tokens),
        "trace_id": trace_id or "",
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        resp = await client.post(
            f"{cfg.gateway_url}/internal/metering/reserve",
            json=payload,
            headers={
                "X-Internal-Auth": cfg.secret,
                "X-User-Id": user_id,
                "Content-Type": "application/json",
            },
        )

    if resp.status_code == 429:
        body = _safe_json(resp)
        dimension = body.get("dimension", "unknown")
        limit = int(body.get("limit", 0))
        used = int(body.get("used", 0))
        requested = int(body.get("requested", 0))
        resets_at = body.get("resets_at", "")
        retry_after = _retry_after_seconds(resets_at, resp.headers.get("Retry-After", ""))
        raise QuotaExceededError(
            f"LLM quota exceeded: {dimension} (limit={limit} used={used} requested={requested})",
            dimension=dimension,
            limit=limit,
            used=used,
            requested=requested,
            resets_at=resets_at,
            retry_after=retry_after,
        )

    if resp.status_code != 200:
        logger.error(
            "metering_reserve_failed",
            extra={
                "status": resp.status_code,
                "body": resp.text[:200],
                "user_id": user_id,
                "trace_id": trace_id,
            },
        )
        # Fail closed: do not proceed with the LLM call if we cannot
        # record the debit. Raise so the processor can surface a 503.
        resp.raise_for_status()

    body = _safe_json(resp)
    reservation_id = body.get("reservation_id", "")
    logger.debug(
        "metering_reserved",
        extra={
            "reservation_id": reservation_id,
            "user_id": user_id,
            "estimated_input": estimated_input_tokens,
            "max_output": max_output_tokens,
            "trace_id": trace_id,
        },
    )
    return reservation_id


async def commit(
    *,
    reservation_id: str,
    actual_input_tokens: int,
    actual_output_tokens: int,
) -> None:
    """Settle a held reservation with the real token counts.

    Idempotent: a second call with the same reservation_id is a no-op
    on the gateway side. Errors are logged but NOT re-raised so a
    transient commit failure does not roll back an already-completed
    LLM call from the user's perspective.
    """
    cfg = get_config()
    if not cfg.enabled or not reservation_id:
        return

    payload = {
        "reservation_id": reservation_id,
        "actual_input_tokens": max(0, actual_input_tokens),
        "actual_output_tokens": max(0, actual_output_tokens),
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{cfg.gateway_url}/internal/metering/commit",
                json=payload,
                headers={
                    "X-Internal-Auth": cfg.secret,
                    "Content-Type": "application/json",
                },
            )
        if resp.status_code != 200:
            logger.error(
                "metering_commit_failed",
                extra={
                    "status": resp.status_code,
                    "body": resp.text[:200],
                    "reservation_id": reservation_id,
                },
            )
        else:
            logger.debug(
                "metering_committed",
                extra={
                    "reservation_id": reservation_id,
                    "actual_input": actual_input_tokens,
                    "actual_output": actual_output_tokens,
                },
            )
    except Exception as exc:
        # Commit failure must not surface to the user: the LLM call
        # already completed. Log and move on; the janitor will reap
        # the held reservation after its TTL expires.
        logger.error(
            "metering_commit_exception",
            extra={"error": str(exc), "reservation_id": reservation_id},
        )


async def refund(*, reservation_id: str) -> None:
    """Roll back a held reservation when the LLM call fails.

    Idempotent. Errors are logged but NOT re-raised; the janitor will
    reap the reservation after its TTL if the refund never lands.
    """
    cfg = get_config()
    if not cfg.enabled or not reservation_id:
        return

    payload = {"reservation_id": reservation_id}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{cfg.gateway_url}/internal/metering/refund",
                json=payload,
                headers={
                    "X-Internal-Auth": cfg.secret,
                    "Content-Type": "application/json",
                },
            )
        if resp.status_code != 200:
            logger.error(
                "metering_refund_failed",
                extra={
                    "status": resp.status_code,
                    "body": resp.text[:200],
                    "reservation_id": reservation_id,
                },
            )
        else:
            logger.debug(
                "metering_refunded",
                extra={"reservation_id": reservation_id},
            )
    except Exception as exc:
        logger.error(
            "metering_refund_exception",
            extra={"error": str(exc), "reservation_id": reservation_id},
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_json(resp: httpx.Response) -> dict:
    """Parse JSON body without raising on malformed content."""
    try:
        return resp.json()
    except Exception:
        return {}


def _retry_after_seconds(resets_at: str, header_value: str) -> int:
    """Compute seconds until the quota window resets.

    Prefers the parsed resets_at ISO-8601 timestamp; falls back to the
    Retry-After header value; defaults to 60 s.
    """
    if resets_at:
        try:
            dt = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
            delta = (dt - datetime.now(timezone.utc)).total_seconds()
            return max(1, int(delta))
        except Exception:
            pass
    if header_value:
        try:
            return max(1, int(header_value))
        except Exception:
            pass
    return 60
