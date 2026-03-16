
---

## COMPLETE NOTIFICATION AUDIT

#### How `src/alert/` Currently Works

The alert system is a **3-file in-process pub/sub hub**:

| File | What It Does | Production Ready? |
|------|-------------|-------------------|
| `event.go` | Event model with builder pattern (WithSymbol, WithTraceID, etc.) | **YES** - clean, well-designed |
| `hub.go` | Thread-safe pub/sub with buffered channels, non-blocking publish, subscriber management | **YES** - solid implementation |
| `handler.go` | WebSocket upgrade handler with ping/pong, read/write pumps, origin validation | **YES** - proper WS lifecycle |

**Verdict on `src/alert/`: This is NOT a demo. It's actually well-implemented.** The Hub is thread-safe, non-blocking (drops events if subscriber buffer is full rather than blocking the caller), has proper WebSocket lifecycle management with ping/pong keepalives, and origin validation. The execution service uses it extensively and correctly.

#### How Execution Uses Alerts (the reference pattern)

The execution service (`src/execution/`) publishes alerts for **every significant event**:

| Event | When | Severity |
|-------|------|----------|
| `ORDER_PLACED` | Trade accepted, order placed | INFO |
| `EXECUTION_REJECTED` | Validation check failed | WARNING |
| `DAILY_LIMIT_LOCKED` | Daily loss limit hit | CRITICAL |
| `WEEKLY_PAUSED` | Weekly drawdown hit | CRITICAL |
| `EXECUTION_ERROR` | Broker state refresh, sizing, or execution failed | ERROR |
| `ORDER_CANCELLED` | Order cancelled via gRPC or REST | INFO |
| `SETTINGS_UPDATED` | Dashboard changed settings | INFO |
| `SERVICE_STARTED` | Execution engine started | INFO |
| `SERVICE_STOPPING` | Shutdown signal received | INFO |

The dashboard connects via `ws://execution-host:port/ws/notifications` and receives ALL events in real-time.

---

#### What the GATEWAY Is Missing (Critical Gaps)

**The gateway has ZERO alert integration.** It doesn't import `src/alert`, doesn't have a Hub, and doesn't publish any events. Everything dies silently:

| What Happens | Current Behavior | What User Sees |
|-------------|-----------------|----------------|
| Scheduled cycle completes with TRADE_APPROVED | Logged, metric emitted | **NOTHING** |
| Scheduled cycle completes with NO_SETUP | Logged | **NOTHING** |
| Guard rejects a trade (news proximity, weekend, session, counter-trend) | Logged, metric emitted | **NOTHING** |
| Cycle fails/times out | Logged, metric emitted | **NOTHING** |
| TA collection fails | Logged | **NOTHING** |
| Macro collection fails | Logged | **NOTHING** |
| RAG retrieval fails | Logged | **NOTHING** |
| Processor LLM fails | Logged | **NOTHING** |
| Execution engine call fails | Logged | **NOTHING** |
| Gateway starts/stops | Logged | **NOTHING** |

**For a trading system handling real money, this is unacceptable.** The user has no idea what's happening unless they're staring at logs or Grafana dashboards.

---

#### What's Missing in `src/alert/` for Production

While the core is solid, there are **4 gaps**:

1. **No event persistence.** If the dashboard is disconnected when a CRITICAL event fires (daily limit locked, guard rejection), the event is lost forever. There's no replay mechanism. The hub is purely in-memory pub/sub.

2. **No event history endpoint.** The dashboard can only see events that arrive while it's connected. There's no REST endpoint to fetch recent events (e.g., "show me the last 50 events").

3. **No severity-based filtering.** The WebSocket sends ALL events. A dashboard that only wants CRITICAL/ERROR events still receives every INFO event.

4. **No metrics on the alert system itself.** No Prometheus counters for events published, events dropped, subscribers connected. If events are being silently dropped because subscriber buffers are full, nobody knows.

---

#### Complete List of Gateway Events That Need Notifications

| Event Type | When | Severity | Details |
|-----------|------|----------|---------|
| `CYCLE_STARTED` | Scheduled or on-demand cycle begins | INFO | symbols, interval, trace_id |
| `CYCLE_COMPLETED` | Cycle finishes successfully | INFO | outcome, duration_ms, symbols_processed |
| `ANALYSIS_COMPLETE` | Per-symbol: processor returned a decision | INFO | symbol, direction, confidence, grade, trade_valid |
| `GUARD_REJECTED` | Guard blocked a trade that processor approved | **WARNING** | symbol, blocking_rules, reasons, direction |
| `GUARD_WARNING` | Guard issued a warning (low liquidity, counter-trend with CHoCH) | WARNING | symbol, rule, reason |
| `CYCLE_FAILED` | Cycle failed or timed out | **ERROR** | error, phase_reached, duration_ms |
| `CYCLE_RETRYING` | Cycle is being retried after failure | WARNING | attempt, max_retries, backoff |
| `TA_COLLECTION_FAILED` | TA HTTP call failed | ERROR | error, trace_id |
| `MACRO_COLLECTION_FAILED` | Macro HTTP call failed | ERROR | error, trace_id |
| `RAG_RETRIEVAL_FAILED` | RAG retrieval failed for a symbol | ERROR | symbol, error |
| `PROCESSOR_LLM_FAILED` | Processor LLM call failed | ERROR | symbol, error |
| `EXECUTION_CALL_FAILED` | Call to Module B failed | **ERROR** | symbol, error |
| `TRADE_ROUTED` | Trade passed all guards and was sent to execution | INFO | symbol, direction, grade, confidence |
| `SERVICE_STARTED` | Gateway started | INFO | ports, interval, symbols |
| `SERVICE_STOPPING` | Gateway shutting down | INFO | - |
| `INTERVAL_CHANGED` | Dashboard changed cycle interval | INFO | old_interval, new_interval |
| `SYMBOLS_CHANGED` | Dashboard changed active symbols | INFO | old_symbols, new_symbols |

---

#### Architecture Decision: Shared Hub vs. Separate Hub

The execution service creates its own Hub and serves WebSocket on its HTTP port. The gateway needs the same pattern. Two options:

**Option A: Each service has its own Hub + WebSocket endpoint.** Dashboard connects to both `ws://execution/ws/notifications` and `ws://gateway/ws/notifications`. Simple, no coupling.

**Option B: Single shared Hub via Redis pub/sub.** All services publish to Redis, one WebSocket gateway serves everything. More complex but single connection for dashboard.

**Recommendation: Option A** for now. It matches the existing execution pattern, requires no new infrastructure, and the dashboard can easily merge two WebSocket streams. Option B is a future optimization.

---

That's the complete audit. The gateway needs the alert Hub wired in, all 17 event types published from the right places, and the 4 gaps in `src/alert/` addressed.

