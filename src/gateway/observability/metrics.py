"""Gateway-specific Prometheus metrics.

Follows RED/USE methodology consistent with engine.shared.metrics.
All metrics are namespaced under ``etradie_gateway_`` to avoid collisions.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# -- Cycle-level metrics -----------------------------------------------------

GATEWAY_CYCLE_TOTAL = Counter(
    "etradie_gateway_cycle_total",
    "Total gateway analysis cycles",
    ["status", "outcome"],
)

GATEWAY_CYCLE_DURATION = Histogram(
    "etradie_gateway_cycle_duration_seconds",
    "Full gateway analysis cycle latency",
    buckets=(5.0, 10.0, 30.0, 60.0, 120.0, 180.0, 300.0),
)

GATEWAY_ACTIVE_CYCLES = Gauge(
    "etradie_gateway_active_cycles",
    "Number of currently running analysis cycles",
)

# -- Phase-level metrics -----------------------------------------------------

GATEWAY_PHASE_DURATION = Histogram(
    "etradie_gateway_phase_duration_seconds",
    "Duration of individual pipeline phases",
    ["phase"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

# -- Collector metrics -------------------------------------------------------

GATEWAY_TA_COLLECT_DURATION = Histogram(
    "etradie_gateway_ta_collect_duration_seconds",
    "TA collection phase latency",
    ["symbol"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

GATEWAY_MACRO_COLLECT_DURATION = Histogram(
    "etradie_gateway_macro_collect_duration_seconds",
    "Macro collection phase latency",
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

GATEWAY_TA_CANDIDATES_PER_CYCLE = Histogram(
    "etradie_gateway_ta_candidates_per_cycle",
    "Number of TA candidates detected per cycle",
    ["framework"],
    buckets=(0, 1, 2, 5, 10, 20, 50),
)

# -- RAG metrics -------------------------------------------------------------

GATEWAY_RAG_DURATION = Histogram(
    "etradie_gateway_rag_duration_seconds",
    "RAG retrieval latency as seen by the gateway",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

# -- Processor metrics -------------------------------------------------------

GATEWAY_PROCESSOR_DURATION = Histogram(
    "etradie_gateway_processor_duration_seconds",
    "Processor LLM call latency as seen by the gateway",
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

# -- Guard metrics -----------------------------------------------------------

GATEWAY_GUARD_REJECTIONS = Counter(
    "etradie_gateway_guard_rejections_total",
    "Guard rejection count by rule",
    ["rule"],
)

GATEWAY_GUARD_DURATION = Histogram(
    "etradie_gateway_guard_duration_seconds",
    "Guard evaluation latency",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
)

# -- Routing metrics ---------------------------------------------------------

GATEWAY_TRADE_ROUTED = Counter(
    "etradie_gateway_trade_routed_total",
    "Trades routed to execution engine",
    ["symbol", "direction"],
)

GATEWAY_NO_SETUP_TOTAL = Counter(
    "etradie_gateway_no_setup_total",
    "Cycles that ended with NO SETUP",
    ["reason"],
)

# -- Error metrics -----------------------------------------------------------

GATEWAY_STAGE_ERRORS = Counter(
    "etradie_gateway_stage_errors_total",
    "Errors by pipeline stage",
    ["stage", "error_type"],
)
