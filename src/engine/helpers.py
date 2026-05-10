"""Shared helper functions for engine API endpoints.

Extracted from main.py for maintainability. These are stateless utility
functions used across multiple router modules.
"""
from __future__ import annotations

import json
from datetime import datetime as dt, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import HTTPException

from engine.shared.logging import get_logger

if TYPE_CHECKING:
    from fastapi import Request
    from engine.dependencies import Container
    from engine.processor.service import AnalysisProcessor

logger = get_logger(__name__)


async def _rate_limit(
    request: "Request",
    key_prefix: str,
    max_requests: int = 10,
    window_seconds: int = 60,
) -> None:
    """Redis-based sliding window rate limiter for dashboard API endpoints.

    Raises HTTP 429 if the caller exceeds max_requests within window_seconds.
    Uses the client IP as the rate limit key.
    """
    container: Container = request.app.state.container
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"ratelimit:{key_prefix}:{client_ip}"

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
        # If Redis is down, allow the request (fail open for availability)
        # but log a warning so operators know rate limiting is bypassed.
        logger.warning(
            "rate_limit_redis_unavailable_failing_open",
            extra={
                "key_prefix": key_prefix,
                "client_ip": client_ip,
                "error": str(exc),
            },
        )


async def _resolve_user_processor(
    container: "Container", user: "AuthenticatedUser"
) -> "AnalysisProcessor":
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


async def _resolve_user_broker(container: "Container", user_id: str):
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
    ts = dt.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
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
