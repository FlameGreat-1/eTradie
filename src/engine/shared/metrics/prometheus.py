"""Prometheus metric definitions for the eTradie engine.

Metrics follow RED/USE methodology:
- Rate (requests/operations per second)
- Errors (error counts by type)
- Duration (latency histograms)
- Utilisation / Saturation for resource-oriented metrics

All metrics are namespaced under ``etradie_`` to avoid collisions.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Info

# ── Application Info ─────────────────────────────────────────

APP_INFO = Info(
    "etradie_engine",
    "eTradie engine build information",
)

# ── Provider Metrics ─────────────────────────────────────────

PROVIDER_FETCH_TOTAL = Counter(
    "etradie_provider_fetch_total",
    "Total provider fetch attempts",
    ["provider", "category", "status"],
)

PROVIDER_FETCH_DURATION = Histogram(
    "etradie_provider_fetch_duration_seconds",
    "Provider fetch latency",
    ["provider", "category"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

PROVIDER_ERRORS_TOTAL = Counter(
    "etradie_provider_errors_total",
    "Provider error count by type",
    ["provider", "category", "error_type"],
)

# ── Collector Metrics ────────────────────────────────────────

COLLECTOR_RUN_TOTAL = Counter(
    "etradie_collector_run_total",
    "Total collector executions",
    ["collector", "status"],
)

COLLECTOR_RUN_DURATION = Histogram(
    "etradie_collector_run_duration_seconds",
    "Collector execution latency",
    ["collector"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

COLLECTOR_ITEMS_STORED = Counter(
    "etradie_collector_items_stored_total",
    "Items persisted by collectors",
    ["collector"],
)

# ── Processor Metrics ────────────────────────────────────────

PROCESSOR_RUN_TOTAL = Counter(
    "etradie_processor_run_total",
    "Total processor executions",
    ["processor", "status"],
)

PROCESSOR_RUN_DURATION = Histogram(
    "etradie_processor_run_duration_seconds",
    "Processor execution latency",
    ["processor"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ── Pipeline Metrics ─────────────────────────────────────────

PIPELINE_CYCLE_TOTAL = Counter(
    "etradie_pipeline_cycle_total",
    "Total macro pipeline analysis cycles",
    ["status"],
)

PIPELINE_CYCLE_DURATION = Histogram(
    "etradie_pipeline_cycle_duration_seconds",
    "Full analysis cycle latency",
    buckets=(5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

# ── Cache Metrics ────────────────────────────────────────────

CACHE_OPERATIONS_TOTAL = Counter(
    "etradie_cache_operations_total",
    "Cache get/set/delete operations",
    ["operation", "status"],
)

CACHE_HIT_RATIO = Gauge(
    "etradie_cache_hit_ratio",
    "Rolling cache hit ratio",
    ["namespace"],
)

# ── Database Metrics ─────────────────────────────────────────

DB_QUERY_DURATION = Histogram(
    "etradie_db_query_duration_seconds",
    "Database query latency",
    ["repository", "operation"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

DB_CONNECTION_POOL_SIZE = Gauge(
    "etradie_db_connection_pool_size",
    "Current database connection pool size",
    ["state"],
)

# ── Scheduler Metrics ────────────────────────────────────────

SCHEDULER_JOB_TOTAL = Counter(
    "etradie_scheduler_job_total",
    "Scheduled job executions",
    ["job_id", "status"],
)

SCHEDULER_JOB_DURATION = Histogram(
    "etradie_scheduler_job_duration_seconds",
    "Scheduled job execution latency",
    ["job_id"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)

# ── Active Providers Gauge ───────────────────────────────────

ACTIVE_PROVIDERS = Gauge(
    "etradie_active_providers",
    "Number of currently active (healthy) providers",
    ["category"],
)
