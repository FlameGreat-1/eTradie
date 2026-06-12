"""APScheduler jobs for Weekly + Monthly Performance Review cron.

Weekly  - Monday 06:00 UTC. Window: previous Monday 00:00 .. previous
          Sunday 23:59:59 UTC (inclusive).
Monthly - 1st of every month 06:00 UTC. Window: previous calendar
          month, [00:00 UTC of day 1 .. 23:59:59 UTC of last day].

For each tick the job:
  1. Calls gateway /internal/performance-review/active-users to get
     the list of users with a Trading System in status='active'.
  2. For every user, schedules a review-generation job IN-PROCESS via
     the same dispatch_generation() the HTTP endpoint uses. No
     HTTP-to-self round-trip; the cron and the HTTP endpoint share
     the same single-flight + cooldown + timeout policy on the same
     container.background_tasks coordinator.

Individual user failures do not abort the cron run.

The profile_version field in the dispatched GenerationRequest is 0
because the scheduler does not enumerate per-user trading-system
versions; the generator's _fetch_profile resolves the authoritative
version from the gateway at job execution time and overrides this
sentinel. See engine.processor.performance_review.generator.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException

from engine.processor.performance_review import GenerationRequest
from engine.routers.performance_review import dispatch_generation
from engine.shared.logging import get_logger
from engine.shared.scheduler.apscheduler import SchedulerManager

logger = get_logger(__name__)

_INTERNAL_AUTH_HEADER = "X-Internal-Auth"
_ACTIVE_USERS_TIMEOUT_S = 15.0


def _compute_weekly_window(now: datetime) -> tuple[datetime, datetime]:
    """Trailing 7 days ending at the start of today (UTC)."""
    now = now.astimezone(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=7)
    end = today - timedelta(microseconds=1)
    return start, end


def _compute_monthly_window(now: datetime) -> tuple[datetime, datetime]:
    """Last full calendar month (UTC)."""
    now = now.astimezone(timezone.utc)
    first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Last day of previous month at 23:59:59.999999.
    last_day_prev = first_of_this_month - timedelta(microseconds=1)
    first_of_prev_month = last_day_prev.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    return first_of_prev_month, last_day_prev


async def _fetch_active_users(
    gateway_url: str,
    secret: str,
) -> list[tuple[str, str, str]]:
    """Enumerate every user with status='active' on the gateway.

    Returns a list of (user_id, role, tier) tuples. Reads the new
    'users' field first (rich identity tuples) and falls back to the
    legacy 'user_ids' string array (with conservative
    role='etradie' / tier='free' defaults) for the one-release
    backward-compatibility window. Returns an empty list on any
    error so individual cron ticks never abort the engine.
    """
    url = f"{gateway_url.rstrip('/')}/internal/performance-review/active-users"
    headers = {
        _INTERNAL_AUTH_HEADER: secret,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(
        timeout=_ACTIVE_USERS_TIMEOUT_S,
        headers=headers,
    ) as client:
        try:
            resp = await client.get(url)
        except Exception as exc:
            logger.error(
                "performance_review_cron_active_users_transport_error",
                extra={"error": str(exc)},
            )
            return []
    if resp.status_code != 200:
        logger.error(
            "performance_review_cron_active_users_non_200",
            extra={
                "status": resp.status_code,
                "body_preview": resp.text[:300],
            },
        )
        return []
    try:
        data = resp.json()
    except Exception:
        logger.error("performance_review_cron_active_users_bad_json")
        return []
    if not isinstance(data, dict):
        logger.error("performance_review_cron_active_users_unexpected_shape")
        return []

    out: list[tuple[str, str, str]] = []

    # Preferred path: rich identity tuples.
    users = data.get("users")
    if isinstance(users, list):
        for u in users:
            if not isinstance(u, dict):
                continue
            uid = u.get("user_id")
            if not isinstance(uid, str) or not uid:
                continue
            role = u.get("role") if isinstance(u.get("role"), str) else ""
            tier = u.get("tier") if isinstance(u.get("tier"), str) else ""
            out.append((uid, role or "etradie", tier or "free"))
        return out

    # Compatibility path: legacy user_ids array.
    ids = data.get("user_ids")
    if isinstance(ids, list):
        for uid in ids:
            if isinstance(uid, str) and uid:
                out.append((uid, "etradie", "free"))
        return out

    logger.error("performance_review_cron_active_users_unexpected_shape")
    return []


async def _run_period_cron(app: FastAPI, period: str) -> None:
    """Iterate every active user and dispatch a review-generation job
    IN-PROCESS via dispatch_generation().

    Config is read from environment variables only for the active-users
    enumeration (which is a real HTTP call to the gateway). The
    in-process dispatch reuses the engine's container, so no separate
    self-URL is required.
    """
    gateway_url = (
        os.environ.get("ENGINE_GATEWAY_URL") or os.environ.get("GATEWAY_HTTP_URL") or ""
    ).strip()
    secret = (
        os.environ.get("ENGINE_INTERNAL_SHARED_SECRET")
        or os.environ.get("GATEWAY_ENGINE_INTERNAL_SHARED_SECRET")
        or ""
    ).strip()
    if not gateway_url or not secret:
        logger.warning(
            "performance_review_cron_skipped",
            extra={
                "period": period,
                "reason": "gateway_url_or_secret_missing",
                "gateway_url_set": bool(gateway_url),
                "secret_set": bool(secret),
            },
        )
        return

    container = getattr(app.state, "container", None)
    if container is None:
        logger.error(
            "performance_review_cron_container_missing",
            extra={"period": period},
        )
        return

    now = datetime.now(timezone.utc)
    if period == "weekly":
        period_start, period_end = _compute_weekly_window(now)
    elif period == "monthly":
        period_start, period_end = _compute_monthly_window(now)
    else:
        logger.error(
            "performance_review_cron_invalid_period",
            extra={"period": period},
        )
        return

    logger.info(
        "performance_review_cron_started",
        extra={
            "period": period,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        },
    )

    users = await _fetch_active_users(gateway_url, secret)
    if not users:
        logger.info(
            "performance_review_cron_no_active_users",
            extra={"period": period},
        )
        return

    logger.info(
        "performance_review_cron_dispatching",
        extra={"period": period, "users": len(users)},
    )

    dispatched = 0
    coalesced = 0
    errored = 0
    for uid, role, tier in users:
        for jmode in ("system", "manual"):
            gen_req = GenerationRequest(
                user_id=uid,
                period=period,
                period_start=period_start,
                period_end=period_end,
                # Sentinel value; the generator self-heals via _fetch_profile.
                profile_version=0,
                journal_mode=jmode,
                role=role,
                tier=tier,
            )
            try:
                result = await dispatch_generation(container, gen_req)
            except HTTPException as exc:
                # 503 = generator not configured; same answer every user
                # would give, so abort the cron run rather than spam logs.
                logger.error(
                    "performance_review_cron_generator_unavailable",
                    extra={
                        "period": period,
                        "status": exc.status_code,
                        "detail": str(exc.detail),
                    },
                )
                return
            except Exception as exc:  # noqa: BLE001
                errored += 1
                logger.warning(
                    "performance_review_cron_dispatch_error",
                    extra={
                        "user_id": uid,
                        "period": period,
                        "journal_mode": jmode,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
                continue
            if result.get("spawned"):
                dispatched += 1
            else:
                # The job was coalesced by the single-flight slot (a
                # previous manual /generate or the same cron tick from a
                # race-prone deploy). Expected; not an error.
                coalesced += 1

    logger.info(
        "performance_review_cron_completed",
        extra={
            "period": period,
            "total_users": len(users),
            "dispatched": dispatched,
            "coalesced": coalesced,
            "errored": errored,
        },
    )


def register_performance_review_jobs(
    app: FastAPI,
    scheduler: SchedulerManager,
) -> None:
    """Mount the weekly + monthly cron jobs on the given scheduler.

    The app reference is captured at registration time and resolved
    lazily at fire time via app.state.container. This is required
    because the container is not fully constructed when the lifespan
    starts registering jobs; the scheduler.start() call later in the
    lifespan is what actually runs the triggers.
    """
    scheduler.add_cron_job(
        _run_period_cron,
        job_id="performance_review_weekly",
        cron_expression="0 6 * * 1",
        kwargs={"app": app, "period": "weekly"},
    )
    scheduler.add_cron_job(
        _run_period_cron,
        job_id="performance_review_monthly",
        cron_expression="0 6 1 * *",
        kwargs={"app": app, "period": "monthly"},
    )
    logger.info(
        "performance_review_jobs_registered",
        extra={
            "weekly_cron": "mon 06:00 UTC",
            "monthly_cron": "1st 06:00 UTC",
        },
    )
