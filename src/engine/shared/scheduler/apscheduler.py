"""
Production-grade async job scheduler with APScheduler.

Provides:
- Interval and cron-based job scheduling
- Automatic metrics instrumentation
- Panic recovery and error handling
- Trace context propagation
- Job timeout enforcement
- Graceful shutdown with job cancellation

Usage Example:
    >>> scheduler = SchedulerManager(max_concurrent_jobs=10)
    >>> 
    >>> async def my_job(param: str):
    ...     logger.info("job_running", param=param)
    >>> 
    >>> scheduler.add_interval_job(
    ...     my_job,
    ...     job_id="my_periodic_job",
    ...     seconds=60,
    ...     kwargs={"param": "value"},
    ...     timeout_seconds=30,
    ... )
    >>> 
    >>> scheduler.start()
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from typing import Any, Optional

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
    JobExecutionEvent,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from engine.shared.exceptions import SchedulerError, SchedulerValidationError
from engine.shared.logging import (
    bind_trace_id,
    clear_contextvars,
    get_logger,
    log_panic_recovery,
)
from engine.shared.metrics.prometheus import (
    SCHEDULER_JOB_DURATION,
    SCHEDULER_JOB_TOTAL,
    SCHEDULER_PENDING_JOBS,
    SCHEDULER_ACTIVE_JOBS,
)

logger = get_logger(__name__)

# Default job timeout (5 minutes)
DEFAULT_JOB_TIMEOUT = 300


class SchedulerManager:
    """
    Production-grade async job scheduler.
    
    Provides:
    - Interval and cron-based scheduling
    - Automatic metrics and logging
    - Panic recovery with context preservation
    - Job timeout enforcement
    - Graceful shutdown
    """

    def __init__(
        self,
        *,
        max_concurrent_jobs: int = 10,
        misfire_grace_time: int = 300,
        coalesce: bool = True,
    ) -> None:
        """
        Initialize scheduler manager.
        
        Args:
            max_concurrent_jobs: Maximum number of concurrent job instances
            misfire_grace_time: Seconds to allow for late job execution
            coalesce: Whether to coalesce missed runs into single execution
        """
        self._max_concurrent_jobs = max_concurrent_jobs
        self._scheduler = AsyncIOScheduler(
            job_defaults={
                "coalesce": coalesce,
                "max_instances": 1,  # Per-job instance limit
                "misfire_grace_time": misfire_grace_time,
            },
        )
        
        self._job_start_times: dict[str, float] = {}
        self._job_timeouts: dict[str, int] = {}
        self._active_jobs: set[str] = set()
        
        # Register event listeners
        self._scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self._scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)
        self._scheduler.add_listener(self._on_job_missed, EVENT_JOB_MISSED)
        
        logger.info(
            "scheduler_manager_initialized",
            extra={
                "max_concurrent_jobs": max_concurrent_jobs,
                "misfire_grace_time": misfire_grace_time,
                "coalesce": coalesce,
            },
        )

    def _on_job_executed(self, event: JobExecutionEvent) -> None:
        """Handle successful job execution."""
        job_id = event.job_id
        
        # Remove from active jobs
        self._active_jobs.discard(job_id)
        SCHEDULER_ACTIVE_JOBS.set(len(self._active_jobs))
        
        # Record duration
        start = self._job_start_times.pop(job_id, None)
        if start is not None:
            duration = time.monotonic() - start
            SCHEDULER_JOB_DURATION.labels(job_id=job_id).observe(duration)
            
            logger.debug(
                "scheduler_job_completed",
                extra={
                    "job_id": job_id,
                    "duration_seconds": round(duration, 2),
                },
            )
        
        SCHEDULER_JOB_TOTAL.labels(job_id=job_id, status="success").inc()

    def _on_job_error(self, event: JobExecutionEvent) -> None:
        """Handle job execution error."""
        job_id = event.job_id
        
        # Remove from active jobs
        self._active_jobs.discard(job_id)
        SCHEDULER_ACTIVE_JOBS.set(len(self._active_jobs))
        
        # Record duration
        start = self._job_start_times.pop(job_id, None)
        if start is not None:
            duration = time.monotonic() - start
            SCHEDULER_JOB_DURATION.labels(job_id=job_id).observe(duration)
        
        SCHEDULER_JOB_TOTAL.labels(job_id=job_id, status="error").inc()
        
        logger.error(
            "scheduler_job_failed",
            extra={
                "job_id": job_id,
                "exception_type": type(event.exception).__name__,
                "exception_message": str(event.exception),
            },
            exc_info=event.exception,
        )

    def _on_job_missed(self, event: JobExecutionEvent) -> None:
        """Handle missed job execution."""
        job_id = event.job_id
        
        SCHEDULER_JOB_TOTAL.labels(job_id=job_id, status="missed").inc()
        
        logger.warning(
            "scheduler_job_missed",
            extra={
                "job_id": job_id,
                "scheduled_run_time": event.scheduled_run_time.isoformat() if event.scheduled_run_time else None,
            },
        )

    @staticmethod
    def _validate_interval(seconds: int) -> None:
        """Validate interval job configuration."""
        if seconds <= 0:
            raise SchedulerValidationError("Interval must be positive")
        
        if seconds < 1:
            raise SchedulerValidationError("Interval must be at least 1 second")

    @staticmethod
    def _validate_cron(cron_expression: str) -> None:
        """Validate cron expression."""
        if not cron_expression or not cron_expression.strip():
            raise SchedulerValidationError("Cron expression cannot be empty")
        
        try:
            # Validate by attempting to create trigger
            CronTrigger.from_crontab(cron_expression)
        except Exception as e:
            raise SchedulerValidationError(
                f"Invalid cron expression '{cron_expression}': {e}"
            ) from e

    def _create_job_wrapper(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        job_id: str,
        timeout_seconds: Optional[int],
    ) -> Callable[..., Coroutine[Any, Any, None]]:
        """
        Create job wrapper with panic recovery, timeout, and tracing.
        
        Args:
            func: Original async job function
            job_id: Job identifier
            timeout_seconds: Optional timeout in seconds
            
        Returns:
            Wrapped job function
        """
        async def _wrapper(**kwargs: Any) -> None:
            trace_id = bind_trace_id()
            
            try:
                # Check concurrent job limit
                if len(self._active_jobs) >= self._max_concurrent_jobs:
                    logger.warning(
                        "scheduler_max_concurrent_jobs_reached",
                        extra={
                            "job_id": job_id,
                            "active_jobs": len(self._active_jobs),
                            "max_concurrent": self._max_concurrent_jobs,
                            "trace_id": trace_id,
                        },
                    )
                    return
                
                # Mark job as active
                self._active_jobs.add(job_id)
                SCHEDULER_ACTIVE_JOBS.set(len(self._active_jobs))
                
                # Record start time
                self._job_start_times[job_id] = time.monotonic()
                
                logger.info(
                    "scheduler_job_started",
                    extra={
                        "job_id": job_id,
                        "trace_id": trace_id,
                    },
                )
                
                # Execute with timeout
                timeout = timeout_seconds or self._job_timeouts.get(job_id, DEFAULT_JOB_TIMEOUT)
                
                try:
                    async with asyncio.timeout(timeout):
                        await func(**kwargs)
                        
                except asyncio.TimeoutError:
                    logger.error(
                        "scheduler_job_timeout",
                        extra={
                            "job_id": job_id,
                            "timeout_seconds": timeout,
                            "trace_id": trace_id,
                        },
                    )
                    SCHEDULER_JOB_TOTAL.labels(job_id=job_id, status="timeout").inc()
                    raise
                
            except Exception as e:
                # Panic recovery
                log_panic_recovery(
                    logger,
                    e,
                    operation="scheduler_job",
                    job_id=job_id,
                    trace_id=trace_id,
                )
                raise
                
            finally:
                # Always clean up context
                clear_contextvars()
                
                # Remove from active jobs if still present
                self._active_jobs.discard(job_id)
                SCHEDULER_ACTIVE_JOBS.set(len(self._active_jobs))
        
        return _wrapper

    def add_interval_job(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *,
        job_id: str,
        seconds: int,
        kwargs: dict[str, Any] | None = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        """
        Add interval-based job.
        
        Args:
            func: Async function to execute
            job_id: Unique job identifier
            seconds: Interval in seconds
            kwargs: Optional job arguments
            timeout_seconds: Optional job timeout (default: 300s)
            
        Raises:
            SchedulerValidationError: On invalid configuration
        """
        self._validate_interval(seconds)
        
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise SchedulerValidationError("Timeout must be positive")
        
        # Store timeout for this job
        if timeout_seconds:
            self._job_timeouts[job_id] = timeout_seconds
        
        wrapped_func = self._create_job_wrapper(func, job_id, timeout_seconds)
        
        self._scheduler.add_job(
            wrapped_func,
            trigger=IntervalTrigger(seconds=seconds),
            id=job_id,
            kwargs=kwargs or {},
            replace_existing=True,
        )
        
        logger.info(
            "scheduler_interval_job_registered",
            extra={
                "job_id": job_id,
                "interval_seconds": seconds,
                "timeout_seconds": timeout_seconds or DEFAULT_JOB_TIMEOUT,
            },
        )

    def add_cron_job(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *,
        job_id: str,
        cron_expression: str,
        kwargs: dict[str, Any] | None = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        """
        Add cron-based job.
        
        Args:
            func: Async function to execute
            job_id: Unique job identifier
            cron_expression: Cron expression (e.g., "0 */4 * * *")
            kwargs: Optional job arguments
            timeout_seconds: Optional job timeout (default: 300s)
            
        Raises:
            SchedulerValidationError: On invalid configuration
        """
        self._validate_cron(cron_expression)
        
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise SchedulerValidationError("Timeout must be positive")
        
        # Store timeout for this job
        if timeout_seconds:
            self._job_timeouts[job_id] = timeout_seconds
        
        wrapped_func = self._create_job_wrapper(func, job_id, timeout_seconds)
        
        self._scheduler.add_job(
            wrapped_func,
            trigger=CronTrigger.from_crontab(cron_expression),
            id=job_id,
            kwargs=kwargs or {},
            replace_existing=True,
        )
        
        logger.info(
            "scheduler_cron_job_registered",
            extra={
                "job_id": job_id,
                "cron_expression": cron_expression,
                "timeout_seconds": timeout_seconds or DEFAULT_JOB_TIMEOUT,
            },
        )

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job.
        
        Args:
            job_id: Job identifier to remove
            
        Returns:
            True if job was removed, False if not found
        """
        try:
            self._scheduler.remove_job(job_id)
            self._job_timeouts.pop(job_id, None)
            
            logger.info(
                "scheduler_job_removed",
                extra={"job_id": job_id},
            )
            return True
            
        except Exception:
            logger.warning(
                "scheduler_job_not_found",
                extra={"job_id": job_id},
            )
            return False

    def start(self) -> None:
        """Start the scheduler."""
        if not self._scheduler.running:
            self._scheduler.start()
            
            # Update pending jobs metric
            pending = len(self._scheduler.get_jobs())
            SCHEDULER_PENDING_JOBS.set(pending)
            
            logger.info(
                "scheduler_started",
                extra={"pending_jobs": pending},
            )

    def shutdown(self, wait: bool = True) -> None:
        """
        Gracefully shutdown the scheduler.
        
        Args:
            wait: If True, wait for running jobs to complete
        """
        if self._scheduler.running:
            active_count = len(self._active_jobs)
            
            logger.info(
                "scheduler_shutting_down",
                extra={
                    "wait_for_jobs": wait,
                    "active_jobs": active_count,
                },
            )
            
            self._scheduler.shutdown(wait=wait)
            
            # Clear metrics
            SCHEDULER_ACTIVE_JOBS.set(0)
            SCHEDULER_PENDING_JOBS.set(0)
            
            logger.info("scheduler_stopped")

    @property
    def running(self) -> bool:
        """Check if scheduler is running."""
        return self._scheduler.running

    @property
    def active_jobs_count(self) -> int:
        """Get count of currently executing jobs."""
        return len(self._active_jobs)

    @property
    def pending_jobs_count(self) -> int:
        """Get count of pending scheduled jobs."""
        return len(self._scheduler.get_jobs())
