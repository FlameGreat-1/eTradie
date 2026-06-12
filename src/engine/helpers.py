"""Shared helper functions for engine API endpoints.

Extracted from main.py for maintainability. These are stateless utility
functions used across multiple router modules.
"""

from __future__ import annotations

import json
import threading
import time
from collections import OrderedDict
from datetime import UTC
from datetime import datetime as dt
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import HTTPException

from engine.shared.logging import get_logger

if TYPE_CHECKING:
    from fastapi import Request

    from engine.dependencies import Container
    from engine.processor.service import AnalysisProcessor

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# In-process rate-limit fallback
#
# _rate_limit's authoritative limiter is the shared Redis sliding window
# so the cap is cluster-wide. When Redis is unavailable we must NOT fail
# open on an abuse control: instead we fall back to a per-process fixed-
# window counter so each pod still enforces the same numeric cap locally.
# This mirrors the Go auth attempt-limiter's two-layer design (Redis
# primary + in-memory fallback) and is the same fail-SAFE posture.
#
# Bounded in size via an OrderedDict used as an LRU so a malicious IP
# rotation cannot grow the map without limit. Guarded by a mutex because
# FastAPI handlers run across a threadpool / multiple tasks.
# ---------------------------------------------------------------------------

_FALLBACK_MAX_KEYS = 16384
_fallbackLock = threading.Lock()
# key -> (window_start_epoch_seconds, count)
_fallbackCounters: OrderedDict[str, tuple[float, int]] = OrderedDict()


def _fallback_allow(key: str, max_requests: int, window_seconds: int) -> bool:
    """Per-process fixed-window rate check used when Redis is down.

    Returns True when the request is within the cap for the current
    window, False when it exceeds it. Fail-SAFE replacement for the
    previous fail-OPEN behaviour. Bounded map size (LRU eviction).
    """
    now = time.monotonic()
    with _fallbackLock:
        entry = _fallbackCounters.get(key)
        if entry is None or (now - entry[0]) >= window_seconds:
            # New window.
            _fallbackCounters[key] = (now, 1)
            _fallbackCounters.move_to_end(key)
            # Evict oldest entries beyond the cap.
            while len(_fallbackCounters) > _FALLBACK_MAX_KEYS:
                _fallbackCounters.popitem(last=False)
            return True
        window_start, count = entry
        if count >= max_requests:
            return False
        _fallbackCounters[key] = (window_start, count + 1)
        _fallbackCounters.move_to_end(key)
        return True


async def _rate_limit(
    request: Request,
    key_prefix: str,
    max_requests: int = 10,
    window_seconds: int = 60,
    user_id: str | None = None,
) -> None:
    """Redis-based sliding window rate limiter for dashboard API endpoints.

    Raises HTTP 429 if the caller exceeds max_requests within window_seconds.

    Keying:
      * When user_id is provided, the limiter keys on the authenticated
        user ("user:<user_id>"), giving a true per-user window. This is
        the correct axis for authenticated endpoints behind Cloudflare
        Tunnel, where request.client.host is the tunnel / ingress IP
        (shared across all users) rather than the real client IP.
      * When user_id is omitted, it keys on the client IP, preserving
        the original behaviour for callers that want an IP axis.
    """
    container: Container = request.app.state.container
    rate_subject = f"user:{user_id}" if user_id else request.client.host if request.client else "unknown"
    rate_key = f"ratelimit:{key_prefix}:{rate_subject}"

    try:
        current = await container.cache.increment(rate_key)
        if current == 1:
            await container.cache.expire(rate_key, window_seconds)
        if current > max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Redis is unavailable. Do NOT fail open on an abuse control:
        # fall back to a bounded per-process fixed-window cap so each
        # pod still enforces the same numeric limit locally (the limit
        # degrades from cluster-wide to per-pod instead of vanishing).
        # Mirrors the Go auth attempt-limiter's Redis-primary +
        # in-memory-fallback design. Logged at WARN so operators see
        # the degraded mode. Audit ref: B2.
        logger.warning(
            "rate_limit_redis_unavailable_using_in_process_fallback",
            extra={
                "key_prefix": key_prefix,
                "rate_subject": rate_subject,
                "error": str(exc),
            },
        )
        if not _fallback_allow(rate_key, max_requests, window_seconds):
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s.",
            )


async def _resolve_user_processor(container: Container, user: AuthenticatedUser) -> AnalysisProcessor:
    """Resolve the authenticated user's LLM processor.

    Called by every endpoint that runs the LLM processor to ensure
    each user's analysis uses their own API key, model, and settings.

    Uses the Container's per-user processor cache. Every user MUST
    configure their own LLM connection via the dashboard. There is
    no env-var fallback for regular users (unless they are pro_managed).
    """
    try:
        return await container.resolve_user_processor(user)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


async def _resolve_user_broker(container: Container, user_id: str):
    """Resolve the authenticated user's broker connection.

    Called by every endpoint that needs broker access to ensure
    operations execute against the correct user's MT5 account.

    Every user (including admin) MUST configure their own broker
    connection via the dashboard. There is NO env-var fallback and
    NO platform-level broker.

    Resolution (handled by container.load_user_broker):
      1. Active broker connection from DB for this user
      2. None -> raises HTTP 503

    Works for both MetaAPI and ZeroMQ EA connection types.
    """
    client = await container.load_user_broker(user_id)
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="No broker connection configured. Please set up a broker connection via the dashboard.",
        )
    return client


def _save_debug_output(
    symbol: str,
    ta_data: dict,
    macro_data: dict | None = None,
    rag_data: dict | None = None,
    processor_data: dict | None = None,
    execution_request: dict | None = None,
    subdirectory: str = "rerun",
) -> dict:
    """Persist analysis outputs to /output/<subdirectory>/<symbol>_<ts>/ as separate JSON files.

    Args:
        symbol: The trading symbol (e.g. "GBPUSDm").
        ta_data: TA analysis result dict.
        macro_data: Macro analysis result dict.
        rag_data: RAG knowledge bundle dict.
        processor_data: Processor LLM result dict.
        subdirectory: Output subdirectory name ("rerun" or "runcycle").

    Returns a dict of {label: filepath} for every file written.
    """
    ts = dt.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path("/output") / subdirectory / f"{symbol}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, str] = {}

    def _write(name: str, data: dict | None) -> None:
        if data is None:
            return
        path = out_dir / f"{name}.json"
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        files[name] = str(path)

    if ta_data is not None:
        _write("ta_snapshots", ta_data.get("snapshots"))
        _write("ta_smc_candidates", ta_data.get("smc_candidates"))
        _write("ta_snd_candidates", ta_data.get("snd_candidates"))

        ta_meta = {k: v for k, v in ta_data.items() if k not in ("snapshots", "smc_candidates", "snd_candidates")}
        _write("ta_metadata", ta_meta)

    _write("macro_analysis", macro_data)
    _write("rag_knowledge", rag_data)
    _write("processor_result", processor_data)
    _write("execution_request", execution_request)

    logger.info(
        "debug_output_saved",
        extra={
            "symbol": symbol,
            "subdirectory": subdirectory,
            "directory": str(out_dir),
            "files": list(files.keys()),
        },
    )
    return files
