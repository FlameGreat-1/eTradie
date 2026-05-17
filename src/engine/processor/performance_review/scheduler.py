"""APScheduler jobs for Weekly + Monthly Performance Review cron.

Weekly  - Monday 06:00 UTC. Window: previous Monday 00:00 .. previous
          Sunday 23:59:59 UTC (inclusive).
Monthly - 1st of every month 06:00 UTC. Window: previous calendar
          month, [00:00 UTC of day 1 .. 23:59:59 UTC of last day].

For each tick the job:
  1. Calls gateway /internal/performance-review/active-users to get
     the list of users with a Trading System in status='active'.
  2. For every user, POSTs to the local engine
     /internal/performance-review/dispatch which schedules the LLM
     job on the same background-task coordinator the manual
     /generate path uses. Cooldown + single-flight + timeout policy
     is enforced inside the dispatch endpoint, so retries are safe.

Individual user failures do not abort the cron run.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from engine.shared.logging import get_logger

logger = get_logger(__name__)

_INTERNAL_AUTH_HEADER = "X-Internal-Auth"
_INTERNAL_USER_ID_HEADER = "X-User-Id"
_CRON_TIMEOUT_S = 15.0


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
    first_of_this_month = now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    # Last day of previous month at 23:59:59.999999.
    last_day_prev = first_of_this_month - timedelta(microseconds=1)
    first_of_prev_month = last_day_prev.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return first_of_prev_month, last_day_prev


async def _run_period_cron(period: str) -> None:
    """Iterate every active user and dispatch a review-generation job.

    Configuration is read from environment variables, identical to the
    generator's from_container() so the cron and the manual /generate
    path agree on URLs and secrets.
    """
    gateway_url = (
        os.environ.get("ENGINE_GATEWAY_URL")
        or os.environ.get("GATEWAY_HTTP_URL")
        or ""
    ).strip()
    engine_self_url = (
        os.environ.get("ENGINE_SELF_HTTP_URL")
        or os.environ.get("ENGINE_HTTP_URL")
        or "http://127.0.0.1:8000"
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

    now = datetime.now(timezone.utc)
    if period == "weekly":
        period_start, period_end = _compute_weekly_window(now)
    elif period == "monthly":
        period_start, period_end = _compute_monthly_window(now)
    else:
        logger.error("performance_review_cron_invalid_period", extra={"period": period})
        return

    logger.info(
        "performance_review_cron_started",
        extra={
            "period": period,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        },
    )

    headers = {
        _INTERNAL_AUTH_HEADER: secret,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=_CRON_TIMEOUT_S, headers=headers) as client:
        # Step 1: enumerate active users.
        try:
            resp = await client.get(
                f"{gateway_url.rstrip('/')}/internal/performance-review/active-users"
            )
        except Exception as exc:
            logger.error(
                "performance_review_cron_active_users_transport_error",
                extra={"period": period, "error": str(exc)},
            )
            return
        if resp.status_code != 200:
            logger.error(
                "performance_review_cron_active_users_non_200",
                extra={
                    "period": period,
                    "status": resp.status_code,
                    "body_preview": resp.text[:300],
                },
            )
            return
        try:
            data = resp.json()
        except Exception:
            logger.error("performance_review_cron_active_users_bad_json", extra={"period": period})
            return
        user_ids = data.get("user_ids") or []
        if not isinstance(user_ids, list):
            logger.error(
                "performance_review_cron_active_users_unexpected_shape",
                extra={"period": period},
            )
            return
        if not user_ids:
            logger.info("performance_review_cron_no_active_users", extra={"period": period})
            return

        logger.info(
            "performance_review_cron_dispatching",
            extra={"period": period, "users": len(user_ids)},
        )

        # Step 2: dispatch a job per user via the engine's own internal
        # dispatch endpoint. We post directly to the local engine so the
        # cooldown + single-flight + timeout policy lives in one place.
        dispatched = 0
        for uid in user_ids:
            if not isinstance(uid, str) or not uid:
                continue
            body: dict[str, Any] = {
                "user_id": uid,
                "period": period,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                # profile_version 0 is a safe sentinel; the dispatch
                # endpoint passes it through to the generator which
                # never uses it for control flow (only for audit
                # metadata on the persisted review).
                "profile_version": 0,
            }
            try:
                disp = await client.post(
                    f"{engine_self_url.rstrip('/')}/internal/performance-review/dispatch",
                    json=body,
                    headers={**headers, _INTERNAL_USER_ID_HEADER: uid},
                )
            except Exception as exc:
                logger.warning(
                    "performance_review_cron_dispatch_transport_error",
                    extra={"user_id": uid, "period": period, "error": str(exc)},
                )
                continue
            if disp.status_code == 202:
                dispatched += 1
            else:
                logger.warning(
                    "performance_review_cron_dispatch_non_202",
                    extra={
                        "user_id": uid,
                        "period": period,
                        "status": disp.status_code,
                    },
                )

    logger.info(
        "performance_review_cron_completed",
        extra={
            "period": period,
            "total_users": len(user_ids),
            "dispatched": dispatched,
        },
    )


def register_performance_review_jobs(scheduler: AsyncIOScheduler) -> None:
    """Mount the weekly + monthly cron jobs on the given scheduler.

    Idempotent: replace_existing=True so a hot-reload does not
    double-mount the trigger. Times anchored at 06:00 UTC to land
    after the morning macro warmup and well before London opens.
    """
    scheduler.add_job(
        _run_period_cron,
        trigger=CronTrigger(day_of_week="mon", hour=6, minute=0, timezone="UTC"),
        kwargs={"period": "weekly"},
        id="performance_review_weekly",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _run_period_cron,
        trigger=CronTrigger(day=1, hour=6, minute=0, timezone="UTC"),
        kwargs={"period": "monthly"},
        id="performance_review_monthly",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    logger.info(
        "performance_review_jobs_registered",
        extra={
            "weekly_cron": "mon 06:00 UTC",
            "monthly_cron": "1st 06:00 UTC",
        },
    )
