from __future__ import annotations

import time
from collections.abc import Callable, Coroutine
from typing import Any

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobExecutionEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import SCHEDULER_JOB_DURATION, SCHEDULER_JOB_TOTAL

logger = get_logger(__name__)


class SchedulerManager:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            },
        )
        self._job_start_times: dict[str, float] = {}
        self._scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self._scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)

    def _on_job_executed(self, event: JobExecutionEvent) -> None:
        job_id = event.job_id
        start = self._job_start_times.pop(job_id, None)
        if start is not None:
            SCHEDULER_JOB_DURATION.labels(job_id=job_id).observe(time.monotonic() - start)
        SCHEDULER_JOB_TOTAL.labels(job_id=job_id, status="success").inc()

    def _on_job_error(self, event: JobExecutionEvent) -> None:
        job_id = event.job_id
        start = self._job_start_times.pop(job_id, None)
        if start is not None:
            SCHEDULER_JOB_DURATION.labels(job_id=job_id).observe(time.monotonic() - start)
        SCHEDULER_JOB_TOTAL.labels(job_id=job_id, status="error").inc()
        logger.error(
            "scheduler_job_failed",
            job_id=job_id,
            exception=str(event.exception),
        )

    def add_interval_job(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *,
        job_id: str,
        seconds: int,
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        original_func = func

        async def _wrapper(**kw: Any) -> Any:
            self._job_start_times[job_id] = time.monotonic()
            return await original_func(**kw)

        self._scheduler.add_job(
            _wrapper,
            trigger=IntervalTrigger(seconds=seconds),
            id=job_id,
            kwargs=kwargs or {},
            replace_existing=True,
        )
        logger.info("scheduler_job_registered", job_id=job_id, interval_seconds=seconds)

    def add_cron_job(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *,
        job_id: str,
        cron_expression: str,
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        original_func = func

        async def _wrapper(**kw: Any) -> Any:
            self._job_start_times[job_id] = time.monotonic()
            return await original_func(**kw)

        self._scheduler.add_job(
            _wrapper,
            trigger=CronTrigger.from_crontab(cron_expression),
            id=job_id,
            kwargs=kwargs or {},
            replace_existing=True,
        )
        logger.info("scheduler_job_registered", job_id=job_id, cron=cron_expression)

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("scheduler_started")

    def shutdown(self, wait: bool = True) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("scheduler_stopped")

    @property
    def running(self) -> bool:
        return self._scheduler.running
