"""Internal routes for Performance Review dispatch.

The Go gateway calls /internal/performance-review/dispatch when the
user clicks 'Run review now'. We schedule the LLM job on the engine's
background-task coordinator and return 202 Accepted immediately so
the gateway can respond quickly to the SPA.

The weekly / monthly cron (in engine.processor.performance_review.scheduler)
calls `dispatch_generation` directly, IN-PROCESS, instead of issuing a
self-HTTP request. Both paths share the same single-flight key, the
same cooldown, and the same timeout — that is the single source of
truth for dispatch policy.

No user authentication on the HTTP surface: the gateway already
authenticated the caller. We verify the shared-secret HMAC via the
same dependency the rest of the /internal/* surface uses.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

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
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., min_length=1, max_length=64)
    period: str = Field(..., pattern=r"^(weekly|monthly)$")
    period_start: datetime
    period_end: datetime
    profile_version: int = Field(..., ge=0)
    journal_mode: str = Field(default="system", pattern=r"^(system|manual)$")
    # Identity fields forwarded by the gateway so the engine can apply
    # tier policy on the dispatch path. Optional on the wire for the
    # same backward-compatibility reason as trading-plan.
    role: str = Field(default="", max_length=32)
    tier: str = Field(default="", max_length=32)


# Cooldown chosen so a runaway client cannot trigger duplicate LLM
# calls within the same window. The gateway already enforces a per-
# user rate limit (5/h on /generate); this is defense-in-depth at
# the engine layer and also throttles the cron path which fans out
# to every active user.
_COOLDOWN_S = 300.0

# Timeout per job. The aggregator + profile fetch + LLM call typically
# completes in 20-60s; 240s leaves 4x headroom.
_TIMEOUT_S = 240.0


async def _resolve_generator(
    container: Container,
) -> Optional[PerformanceReviewGenerator]:
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


async def dispatch_generation(
    container: Container,
    gen_req: GenerationRequest,
) -> dict[str, object]:
    """Schedule a review generation job on the engine's background-task
    coordinator.

    This is the SINGLE source of truth for dispatch policy: the HTTP
    endpoint below and the weekly/monthly cron both call this
    function. The cooldown + single-flight + timeout are enforced
    centrally by container.background_tasks.

    Returns:
      {
        "dispatched": bool,   # always True when the generator is configured
        "spawned":    bool,   # True when a fresh task was started, False
                              # when single-flight or cooldown coalesced it
        "reason":     str?,   # populated when dispatched=False
      }

    Raises HTTPException(503) when the generator is not configured
    (missing gateway URL, management URL, or shared secret) so the
    HTTP caller surfaces the right error; the cron interprets the
    same condition by inspecting the returned dict.
    """
    generator = await _resolve_generator(container)
    if generator is None:
        logger.warning(
            "performance_review_dispatch_generator_unavailable",
            extra={
                "user_id": gen_req.user_id,
                "period": gen_req.period,
            },
        )
        raise HTTPException(
            status_code=503,
            detail="performance review generator is not configured",
        )

    # week and the week before) do not coalesce onto the same
    # single-flight slot when the user retries near a boundary.
    key = (
        f"performance_review:{gen_req.user_id}:{gen_req.period}:"
        f"{gen_req.period_start.isoformat()}:{gen_req.journal_mode}"
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
            "user_id": gen_req.user_id,
            "period": gen_req.period,
            "period_start": gen_req.period_start.isoformat(),
            "period_end": gen_req.period_end.isoformat(),
            "profile_version": gen_req.profile_version,
            "spawned": spawned,
        },
    )
    return {"dispatched": True, "spawned": spawned}


@router.post("/internal/performance-review/dispatch", status_code=202)
async def dispatch_performance_review(
    request: Request,
    body: DispatchBody,
    _: None = Depends(verify_internal_auth),
) -> dict:
    container: Container = request.app.state.container

    role = (
        body.role.strip() or request.headers.get("X-User-Role", "").strip() or "etradie"
    ).lower()
    tier = (
        body.tier.strip() or request.headers.get("X-User-Tier", "").strip() or "free"
    ).lower()

    gen_req = GenerationRequest(
        user_id=body.user_id,
        period=body.period,
        period_start=body.period_start,
        period_end=body.period_end,
        profile_version=body.profile_version,
        journal_mode=body.journal_mode,
        role=role,
        tier=tier,
    )
    return await dispatch_generation(container, gen_req)
