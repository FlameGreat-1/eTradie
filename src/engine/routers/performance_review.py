"""Internal routes for Performance Review dispatch + scheduler.

The Go gateway calls /internal/performance-review/dispatch when the
user clicks 'Run review now' (or when the engine's own scheduler
fires the weekly / monthly cron). We schedule the LLM job on the
engine's background-task coordinator and return 202 Accepted
immediately so the gateway can respond quickly to the SPA.

No user authentication here: the gateway already authenticated the
caller and forwards the user_id in the body. We verify the shared-
secret HMAC instead via the same dependency the rest of the
/internal/* surface uses.

Route:
    POST /internal/performance-review/dispatch

Body:
    {
      "user_id":         "<auth user id>",
      "period":          "weekly" | "monthly",
      "period_start":    "<RFC3339>",
      "period_end":      "<RFC3339>",
      "profile_version": <int>
    }
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from engine.dependencies import Container
from engine.processor.performance_review import (
    GenerationRequest,
    PerformanceReviewGenerator,
)
from engine.shared.internal_auth import verify_internal_auth
from engine.shared.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class DispatchBody(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    period: str = Field(..., pattern=r"^(weekly|monthly)$")
    period_start: datetime
    period_end: datetime
    profile_version: int = Field(..., ge=0)


# Cooldown chosen so a runaway client cannot trigger duplicate LLM
# calls within the same minute. The gateway already enforces a per-
# user rate limit (5/h on /generate); this is defense-in-depth at
# the engine layer.
_COOLDOWN_S = 300.0
# Timeout per job. The aggregator + profile fetch + LLM call typically
# completes in 20-60s; 240s leaves 4x headroom.
_TIMEOUT_S = 240.0


async def _resolve_generator(container: Container) -> Optional[PerformanceReviewGenerator]:
    """Lazily build (and cache on the container) the generator instance.

    Same pattern as trading_plan: build under an asyncio.Lock so a
    cold-start burst does not leak httpx clients.
    """
    gen = getattr(container, "_performance_review_generator", None)
    if gen is not None:
        return gen
    lock: asyncio.Lock = getattr(container, "_performance_review_generator_lock", None)
    if lock is None:
        lock = asyncio.Lock()
        container._performance_review_generator_lock = lock  # type: ignore[attr-defined]
    async with lock:
        gen = getattr(container, "_performance_review_generator", None)
        if gen is not None:
            return gen
        gen = PerformanceReviewGenerator.from_container(container)
        container._performance_review_generator = gen  # type: ignore[attr-defined]
        return gen


@router.post("/internal/performance-review/dispatch", status_code=202)
async def dispatch_performance_review(
    request: Request,
    body: DispatchBody,
    _: None = Depends(verify_internal_auth),
) -> dict:
    container: Container = request.app.state.container

    generator = await _resolve_generator(container)
    if generator is None:
        logger.warning(
            "performance_review_dispatch_generator_unavailable",
            extra={"user_id": body.user_id, "period": body.period},
        )
        raise HTTPException(
            status_code=503,
            detail="performance review generator is not configured",
        )

    gen_req = GenerationRequest(
        user_id=body.user_id,
        period=body.period,
        period_start=body.period_start,
        period_end=body.period_end,
        profile_version=body.profile_version,
    )

    # Key includes period_start so two distinct windows (e.g. last
    # week and the week before) do not coalesce onto the same
    # single-flight slot when the user retries near a boundary.
    key = (
        f"performance_review:{body.user_id}:{body.period}:"
        f"{body.period_start.isoformat()}"
    )
    spawned = await container.background_tasks.schedule_once(
        key,
        lambda: generator.run(gen_req),
        cooldown_s=_COOLDOWN_S,
        timeout_s=_TIMEOUT_S,
    )

    logger.info(
        "performance_review_dispatch_accepted",
        extra={
            "user_id": body.user_id,
            "period": body.period,
            "period_start": body.period_start.isoformat(),
            "period_end": body.period_end.isoformat(),
            "profile_version": body.profile_version,
            "spawned": spawned,
        },
    )
    return {
        "dispatched": True,
        "spawned": spawned,
    }
