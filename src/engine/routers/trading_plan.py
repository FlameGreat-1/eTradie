"""Internal route for Trading Plan generation dispatch.

The Go gateway calls this when the user clicks \"Generate plan\" (or
when the Trading System builder auto-triggers a fresh plan after Save
& Activate). We schedule the LLM job on the engine's background-task
coordinator and return 202 Accepted immediately so the gateway can
respond quickly to the SPA.

No user authentication here: the gateway already authenticated the
caller and forwards the user_id in the body. We verify the
shared-secret HMAC instead via the same dependency the rest of the
/internal/* surface uses.

Route:
    POST /internal/trading-plan/dispatch

Body:
    {
      "user_id":          "<auth user id>",
      "balance":          50000.0,
      "balance_currency": "USD",
      "balance_source":   "broker" | "fallback",
      "profile_version":  <int>,
      "profile":          { ... raw trading-system profile ... }
    }

Responses:
    202 Accepted        - dispatched (or suppressed by the coordinator's
                          per-user cooldown, which is the success path
                          when a duplicate dispatch arrives within the
                          window).
    400 Bad Request     - malformed body.
    503 Service Unavail - generator could not be constructed (gateway
                          URL or internal secret missing).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from engine.dependencies import Container
from engine.processor.trading_plan import (
    GenerationRequest,
    TradingPlanGenerator,
)
from engine.shared.internal_auth import verify_internal_auth
from engine.shared.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class DispatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., min_length=1, max_length=64)
    balance: float = Field(..., ge=0.0)
    balance_currency: str = Field(..., min_length=3, max_length=8)
    balance_source: str = Field(..., min_length=1, max_length=16)
    profile_version: int = Field(..., ge=0)
    profile: dict
    # Identity fields forwarded by the gateway so the engine can apply
    # the platform-key fallback policy (admin / pro_managed) without a
    # separate identity lookup. Optional on the wire because a slightly
    # older gateway deploy may not yet send them; the engine then
    # defaults to the conservative BYOK posture below.
    role: str = Field(default="", max_length=32)
    tier: str = Field(default="", max_length=32)


# Cooldown chosen so a runaway client cannot trigger duplicate LLM
# calls within the same minute. Independent of the gateway's per-user
# rate limit; this is defense-in-depth at the engine layer.
_COOLDOWN_S = 60.0
# Timeout per job: the LLM call typically completes in 10-30s; we
# allow 5x headroom for slow providers.
_TIMEOUT_S = 150.0


async def _resolve_generator(container: Container) -> TradingPlanGenerator | None:
    """Lazily build (and cache on the container) the generator instance.

    The generator depends on the platform LLM client which is built
    by Container.build_processor() during the FastAPI lifespan, so we
    cannot build it inside Container.__init__. Caching the result on
    the container keeps the construction cost (httpx client setup) a
    one-time event per process.

    Concurrency: two simultaneous dispatch requests arriving before
    the cache is populated would otherwise both build a generator;
    one wins the final assignment and the other leaks an httpx pool.
    We guard the build with an asyncio.Lock attached to the container
    (created lazily on first call) so the second arrival awaits the
    first and reuses its result. The lock is cheap (~0 cost after the
    first build) and avoids the resource leak under cold-start bursts.
    """
    gen = getattr(container, "_trading_plan_generator", None)
    if gen is not None:
        return gen

    # Attach the lock on first access. We do NOT need a meta-lock on
    # the attribute assignment because Python's GIL guarantees the
    # check-and-set sequence below is atomic at the bytecode level
    # for a simple attribute write; the worst case is two coroutines
    # creating two locks in the same tick, after which one is GC'd.
    lock: asyncio.Lock = getattr(container, "_trading_plan_generator_lock", None)
    if lock is None:
        lock = asyncio.Lock()
        container._trading_plan_generator_lock = lock  # type: ignore[attr-defined]

    async with lock:
        # Re-check inside the lock so the loser of the race does not
        # rebuild after the winner already cached.
        gen = getattr(container, "_trading_plan_generator", None)
        if gen is not None:
            return gen
        gen = TradingPlanGenerator.from_container(container)
        # Always assign (even when None) so we do not retry the
        # env-var lookup on every request.
        container._trading_plan_generator = gen  # type: ignore[attr-defined]
        return gen


@router.post("/internal/trading-plan/dispatch", status_code=202)
async def dispatch_trading_plan_generation(
    request: Request,
    body: DispatchBody,
    _: None = Depends(verify_internal_auth),
) -> dict:
    container: Container = request.app.state.container

    generator = await _resolve_generator(container)
    if generator is None:
        logger.warning(
            "trading_plan_dispatch_generator_unavailable",
            extra={"user_id": body.user_id},
        )
        raise HTTPException(
            status_code=503,
            detail="trading plan generator is not configured",
        )

    # Resolve identity: body wins, then header, then conservative
    # defaults. Centralising the resolution here keeps the generator
    # signature minimal and ensures both call sites (HTTP dispatch
    # and any future caller) populate the GenerationRequest the same
    # way.
    role = (body.role.strip() or request.headers.get("X-User-Role", "").strip() or "etradie").lower()
    tier = (body.tier.strip() or request.headers.get("X-User-Tier", "").strip() or "free").lower()

    gen_req = GenerationRequest(
        user_id=body.user_id,
        balance=body.balance,
        balance_currency=body.balance_currency.upper(),
        balance_source=body.balance_source.lower(),
        profile_version=body.profile_version,
        profile=body.profile,
        role=role,
        tier=tier,
    )

    # schedule_once gives us:
    #   - per-user cooldown (defense-in-depth vs runaway clients),
    #   - single-flight (a concurrent dispatch for the same user
    #     coalesces onto the first),
    #   - bounded timeout per job.
    # A False return means the dispatch was suppressed by an
    # in-flight or cooldown-active wave; that is still the success
    # path because the original wave will eventually post the
    # callback. Returning 202 in both cases keeps the gateway path
    # uniform.
    key = f"trading_plan:{body.user_id}"
    spawned = await container.background_tasks.schedule_once(
        key,
        lambda: generator.run(gen_req),
        cooldown_s=_COOLDOWN_S,
        timeout_s=_TIMEOUT_S,
    )

    logger.info(
        "trading_plan_dispatch_accepted",
        extra={
            "user_id": body.user_id,
            "spawned": spawned,
            "balance_source": gen_req.balance_source,
            "profile_version": gen_req.profile_version,
        },
    )

    return {
        "dispatched": True,
        "spawned": spawned,
    }
