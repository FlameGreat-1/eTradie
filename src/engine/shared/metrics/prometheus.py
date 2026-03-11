"""
Prometheus metric definitions for the eTradie engine.

Metrics follow RED/USE methodology:
- Rate (requests/operations per second)
- Errors (error counts by type)
- Duration (latency histograms)
- Utilization / Saturation for resource-oriented metrics

All metrics are namespaced under ``etradie_`` to avoid collisions.

Cardinality Warning:
- Avoid high-cardinality labels (user IDs, timestamps, UUIDs)
- Use bounded label sets (status, operation type, error category)
- Monitor metric cardinality in production

Usage Example:
    >>> from engine.shared.metrics.prometheus import PROVIDER_FETCH_TOTAL
    >>> PROVIDER_FETCH_TOTAL.labels(
    ...     provider="fred",
    ...     category="economic",
    ...     status="success"
    ... ).inc()
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Info

# ══════════════════════════════════════════════════════════════
# Application Info
# ══════════════════════════════════════════════════════════════

APP_INFO = Info(
    "etradie_engine",
    "eTradie engine build information",
)

# ══════════════════════════════════════════════════════════════
# Provider / HTTP Client Metrics
# ══════════════════════════════════════════════════════════════

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

PROVIDER_RESPONSE_SIZE = Histogram(
    "etradie_provider_response_size_bytes",
    "Provider response size in bytes",
    ["provider", "category"],
    buckets=(100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000),
)

ACTIVE_PROVIDERS = Gauge(
    "etradie_active_providers",
    "Number of currently active (healthy) providers",
    ["category"],
)

# ══════════════════════════════════════════════════════════════
# Collector Metrics
# ══════════════════════════════════════════════════════════════

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

# ══════════════════════════════════════════════════════════════
# Processor Metrics
# ══════════════════════════════════════════════════════════════

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

# ══════════════════════════════════════════════════════════════
# Pipeline Metrics
# ══════════════════════════════════════════════════════════════

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

# ══════════════════════════════════════════════════════════════
# Cache Metrics
# ══════════════════════════════════════════════════════════════

CACHE_OPERATIONS_TOTAL = Counter(
    "etradie_cache_operations_total",
    "Cache get/set/delete operations",
    ["operation", "status"],
)

CACHE_OPERATION_DURATION = Histogram(
    "etradie_cache_operation_duration_seconds",
    "Cache operation latency",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

CACHE_VALUE_SIZE = Histogram(
    "etradie_cache_value_size_bytes",
    "Cache value size in bytes",
    ["operation"],
    buckets=(100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000),
)

CACHE_HIT_RATIO = Gauge(
    "etradie_cache_hit_ratio",
    "Rolling cache hit ratio",
    ["namespace"],
)

# ══════════════════════════════════════════════════════════════
# Database Metrics
# ══════════════════════════════════════════════════════════════

DB_QUERY_DURATION = Histogram(
    "etradie_db_query_duration_seconds",
    "Database query latency by repository and operation",
    ["repository", "operation"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

DB_OPERATION_DURATION = Histogram(
    "etradie_db_operation_duration_seconds",
    "Database operation duration (read/write sessions)",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

DB_OPERATION_ERRORS = Counter(
    "etradie_db_operation_errors_total",
    "Database operation errors by type",
    ["operation", "error_type"],
)

DB_QUERY_ERRORS = Counter(
    "etradie_db_query_errors_total",
    "Database query errors by repository and operation",
    ["repository", "operation", "error_type"],
)

DB_QUERY_ROWS = Histogram(
    "etradie_db_query_rows",
    "Number of rows affected by database operations",
    ["repository", "operation"],
    buckets=(1, 10, 50, 100, 500, 1_000, 5_000, 10_000),
)

DB_CONNECTION_POOL_SIZE = Gauge(
    "etradie_db_connection_pool_size",
    "Current database connection pool size",
    ["state"],
)

# ══════════════════════════════════════════════════════════════
# Scheduler Metrics
# ══════════════════════════════════════════════════════════════

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

SCHEDULER_PENDING_JOBS = Gauge(
    "etradie_scheduler_pending_jobs",
    "Number of pending scheduled jobs",
)

SCHEDULER_ACTIVE_JOBS = Gauge(
    "etradie_scheduler_active_jobs",
    "Number of currently executing jobs",
)

# ══════════════════════════════════════════════════════════════
# Tracing Metrics
# ══════════════════════════════════════════════════════════════

TRACING_SPANS_CREATED = Counter(
    "etradie_tracing_spans_created_total",
    "Total tracing spans created",
    ["span_name"],
)

TRACING_SPANS_ERRORS = Counter(
    "etradie_tracing_spans_errors_total",
    "Total tracing span errors",
    ["span_name", "error_type"],
)

# ══════════════════════════════════════════════════════════════
# Generic Provider Request Metrics (broker-agnostic)
# ══════════════════════════════════════════════════════════════

PROVIDER_REQUEST_DURATION = Histogram(
    "etradie_provider_request_duration_seconds",
    "Provider request latency (broker-agnostic)",
    ["provider", "operation"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

PROVIDER_REQUEST_ERRORS = Counter(
    "etradie_provider_request_errors_total",
    "Provider request error count (broker-agnostic)",
    ["provider", "operation", "error_type"],
)

# ══════════════════════════════════════════════════════════════
# Logging Metrics
# ══════════════════════════════════════════════════════════════

LOG_ENTRIES_TOTAL = Counter(
    "etradie_log_entries_total",
    "Total log entries by level and logger",
    ["level", "logger"],
)

# ══════════════════════════════════════════════════════════════
# Technical Analysis (TA) Metrics
# ══════════════════════════════════════════════════════════════

TA_BROKER_FETCH_TOTAL = Counter(
    "etradie_ta_broker_fetch_total",
    "Total TA broker candle fetch attempts",
    ["broker", "symbol", "timeframe", "status"],
)

TA_BROKER_FETCH_DURATION = Histogram(
    "etradie_ta_broker_fetch_duration_seconds",
    "TA broker fetch latency",
    ["broker", "symbol", "timeframe"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

TA_BROKER_ERRORS_TOTAL = Counter(
    "etradie_ta_broker_errors_total",
    "TA broker error count by type",
    ["broker", "error_type"],
)

TA_DETECTION_DURATION = Histogram(
    "etradie_ta_detection_duration_seconds",
    "TA detection execution latency",
    ["framework", "detector"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

TA_CANDIDATES_DETECTED = Counter(
    "etradie_ta_candidates_detected_total",
    "Total TA pattern candidates detected",
    ["framework", "pattern", "direction"],
)

TA_SNAPSHOT_BUILD_DURATION = Histogram(
    "etradie_ta_snapshot_build_duration_seconds",
    "TA snapshot build latency",
    ["symbol", "timeframe"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
)

TA_VALIDATION_FAILURES = Counter(
    "etradie_ta_validation_failures_total",
    "TA validation failures by framework and validator",
    ["framework", "validator", "reason"],
)

# ══════════════════════════════════════════════════════════════
# RAG (Retrieval-Augmented Generation) Metrics
# ══════════════════════════════════════════════════════════════

RAG_QUERY_TOTAL = Counter(
    "etradie_rag_query_total",
    "Total RAG retrieval queries",
    ["collection", "status"],
)

RAG_QUERY_DURATION = Histogram(
    "etradie_rag_query_duration_seconds",
    "RAG query latency",
    ["collection"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

RAG_DOCUMENTS_RETRIEVED = Histogram(
    "etradie_rag_documents_retrieved",
    "Number of documents retrieved per query",
    ["collection"],
    buckets=(1, 5, 10, 20, 50, 100),
)

RAG_EMBEDDING_DURATION = Histogram(
    "etradie_rag_embedding_duration_seconds",
    "Document embedding generation latency",
    ["model"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
)

RAG_EMBEDDING_TOTAL = Counter(
    "etradie_rag_embedding_total",
    "Total embedding generation requests",
    ["model", "status"],
)

RAG_EMBEDDING_BATCH_SIZE = Histogram(
    "etradie_rag_embedding_batch_size",
    "Chunks per embedding batch",
    ["model"],
    buckets=(1, 8, 16, 32, 64, 128, 256),
)

RAG_INGEST_TOTAL = Counter(
    "etradie_rag_ingest_total",
    "Total document ingest operations",
    ["doc_type", "status"],
)

RAG_INGEST_DURATION = Histogram(
    "etradie_rag_ingest_duration_seconds",
    "End-to-end ingest pipeline latency",
    ["doc_type"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

RAG_CHUNKS_GENERATED = Counter(
    "etradie_rag_chunks_generated_total",
    "Total chunks produced by chunking pipeline",
    ["doc_type", "chunker"],
)

RAG_VECTORSTORE_OPS_TOTAL = Counter(
    "etradie_rag_vectorstore_ops_total",
    "Vector store operations",
    ["operation", "collection", "status"],
)

RAG_VECTORSTORE_OPS_DURATION = Histogram(
    "etradie_rag_vectorstore_ops_duration_seconds",
    "Vector store operation latency",
    ["operation", "collection"],
    buckets=(0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

RAG_RERANK_DURATION = Histogram(
    "etradie_rag_rerank_duration_seconds",
    "Reranking stage latency",
    ["strategy"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25),
)

RAG_COVERAGE_CHECKS_TOTAL = Counter(
    "etradie_rag_coverage_checks_total",
    "Coverage check outcomes",
    ["result"],
)

RAG_CONFLICT_DETECTIONS_TOTAL = Counter(
    "etradie_rag_conflict_detections_total",
    "Conflict detection outcomes",
    ["result"],
)

RAG_ACTIVE_DOCUMENTS = Gauge(
    "etradie_rag_active_documents",
    "Number of active documents in knowledge base",
    ["doc_type"],
)

RAG_ACTIVE_CHUNKS = Gauge(
    "etradie_rag_active_chunks",
    "Total active chunks in vector store",
    ["collection"],
)

# ══════════════════════════════════════════════════════════════
# LLM / Processor (Module A) Metrics
# ══════════════════════════════════════════════════════════════

LLM_REQUEST_TOTAL = Counter(
    "etradie_llm_request_total",
    "Total LLM API requests",
    ["provider", "model", "status"],
)

LLM_REQUEST_DURATION = Histogram(
    "etradie_llm_request_duration_seconds",
    "LLM API request latency",
    ["provider", "model"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

LLM_TOKENS_USED = Counter(
    "etradie_llm_tokens_used_total",
    "Total LLM tokens consumed",
    ["provider", "model", "token_type"],
)

LLM_ERRORS_TOTAL = Counter(
    "etradie_llm_errors_total",
    "LLM API error count by type",
    ["provider", "model", "error_type"],
)

TRADE_PLAN_GENERATED_TOTAL = Counter(
    "etradie_trade_plan_generated_total",
    "Total trade plans generated by Module A",
    ["status"],
)

TRADE_PLAN_VALIDATION_FAILURES = Counter(
    "etradie_trade_plan_validation_failures_total",
    "Trade plan validation failures by rule",
    ["rule"],
)

# ══════════════════════════════════════════════════════════════
# System Resource Metrics
# ══════════════════════════════════════════════════════════════

SYSTEM_CPU_USAGE = Gauge(
    "etradie_system_cpu_usage_percent",
    "System CPU usage percentage",
)

SYSTEM_MEMORY_USAGE = Gauge(
    "etradie_system_memory_usage_bytes",
    "System memory usage in bytes",
    ["type"],  # used, available, total
)

SYSTEM_DISK_USAGE = Gauge(
    "etradie_system_disk_usage_bytes",
    "System disk usage in bytes",
    ["mount_point", "type"],  # used, available, total
)

# ══════════════════════════════════════════════════════════════
# Rate Limiting Metrics
# ══════════════════════════════════════════════════════════════

RATE_LIMIT_HITS_TOTAL = Counter(
    "etradie_rate_limit_hits_total",
    "Total rate limit hits by endpoint/resource",
    ["resource", "limit_type"],
)

RATE_LIMIT_REMAINING = Gauge(
    "etradie_rate_limit_remaining",
    "Remaining rate limit quota",
    ["resource", "limit_type"],
)
