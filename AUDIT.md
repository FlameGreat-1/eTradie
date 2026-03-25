# DASHBOARD INTEGRATION AUDIT

> Full audit of every API endpoint, gRPC service, WebSocket channel, and data model across all modules.
> Organized by dashboard section in the order they would appear in the UI.

---

## 1. SYSTEM HEALTH & STATUS (Top Bar / Header)

The first thing the dashboard shows: is the system alive and connected?

### 1.1 Gateway Health
- **Endpoint:** `GET /health` (HTTP)
- **Source:** `src/gateway/internal/server/http_server.go`
- **Returns:** `{"status": "ok"}`
- **Purpose:** Simple liveness probe. Always returns 200 if the gateway process is running.

### 1.2 Gateway Readiness
- **Endpoint:** `GET /readiness` (HTTP)
- **Source:** `src/gateway/internal/server/http_server.go`
- **Returns:** `{"status": "ready"|"not_ready", "redis": bool, "engine": bool}`
- **Purpose:** Deep health check. Verifies Redis and Python Engine connectivity. Returns 503 if either is down.

### 1.3 Gateway Health (gRPC)
- **RPC:** `GatewayService.GetHealth`
- **Proto:** `proto/gateway/v1/gateway.proto`
- **Source:** `src/gateway/internal/server/grpc_server.go`
- **Request:** `GetHealthRequest{}` (empty)
- **Response:**
  - `status` (string): `"ok"` or `"degraded"`
  - `redis_connected` (bool): Redis connectivity
  - `engine_connected` (bool): Python engine connectivity
  - `active_cycles` (int32): Number of currently running analysis cycles
- **Purpose:** Dashboard header status indicator. Shows system health at a glance.

### 1.4 Engine Health
- **Endpoint:** `GET /health` (HTTP)
- **Source:** `src/engine/main.py`
- **Returns:** `{"status": "ok"}`
- **Purpose:** Python engine liveness.

### 1.5 RAG Health
- **Endpoint:** `GET /health/rag` (HTTP)
- **Source:** `src/engine/main.py`
- **Returns:**
  - `status` (string): `"healthy"`, `"degraded"`, or `"disabled"`
  - `vectorstore_connected` (bool)
  - `database_connected` (bool)
  - `embedding_ready` (bool)
  - `documents_count` (int)
  - `scenarios_count` (int)
- **Purpose:** RAG knowledge base health. Shows if the LLM has access to the rulebook.

### 1.6 Management Service Health (gRPC)
- **RPC:** `ManagementService.GetHealth`
- **Proto:** `proto/management/v1/management.proto`
- **Source:** `src/management/internal/server/`
- **Response:**
  - `status` (string): `"ok"` or `"degraded"`
  - `db_connected` (bool)
  - `broker_connected` (bool)
  - `active_trades` (int32)
- **Purpose:** Module C health. Shows if trade management is operational.

### 1.7 Prometheus Metrics
- **Endpoint:** `GET /metrics` (HTTP)
- **Source:** `src/gateway/internal/server/http_server.go` (Go), `src/engine/main.py` (Python)
- **Purpose:** Prometheus scrape endpoint. Feeds Grafana dashboards. Contains all counters, gauges, histograms.

---

## 2. GATEWAY CONFIGURATION (Settings Panel)

Runtime-configurable settings the user can view and modify.

### 2.1 Get Gateway Config
- **RPC:** `GatewayService.GetGatewayConfig`
- **Proto:** `proto/gateway/v1/gateway.proto`
- **Source:** `src/gateway/internal/server/grpc_server.go`
- **Request:** `GetGatewayConfigRequest{}` (empty)
- **Response:**
  - `enabled` (bool): Master switch
  - `cycle_interval_seconds` (int32): Current cycle interval (default 14400 = 4 hours)
  - `cycle_timeout_seconds` (int32): Max time per cycle (default 300)
  - `max_concurrent_symbols` (int32): Parallel symbol processing limit (default 4)
  - `ta_cache_ttl_seconds` (int32): TA result cache TTL (default 300)
  - `macro_cache_ttl_seconds` (int32): Macro result cache TTL (default 600)
  - `max_cycle_retries` (int32): Retry count on failure (default 1)
  - `default_symbols` (string[]): Config-defined default symbols
  - `active_symbols` (string[]): Currently active symbols (may differ from defaults)
  - `active_symbols_source` (string): `"redis"` or `"gateway_config"`
  - `execution_enabled` (bool): Whether Module B execution is enabled
- **Purpose:** Dashboard settings panel. Shows all runtime config values.

### 2.2 Set Cycle Interval
- **RPC:** `GatewayService.SetCycleInterval`
- **Proto:** `proto/gateway/v1/gateway.proto`
- **Source:** `src/gateway/internal/server/grpc_server.go`
- **Request:** `interval_seconds` (int32): New interval, must be 60-86400
- **Response:**
  - `success` (bool)
  - `current_interval_seconds` (int32)
  - `message` (string)
- **Purpose:** Dashboard slider/input to change how often analysis runs. Takes effect immediately. Persisted in Redis.

### 2.3 Gateway Config Environment Variables
- **Source:** `src/gateway/internal/config/config.go`
- **Prefix:** `GATEWAY_`
- **All variables (set at deploy time, not runtime):**
  - `GATEWAY_ENABLED` (bool, default: true)
  - `GATEWAY_DEFAULT_SYMBOLS` (string[], default: EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,NZDUSD,USDCAD,XAUUSD)
  - `GATEWAY_CYCLE_INTERVAL_SECONDS` (int, default: 14400)
  - `GATEWAY_CYCLE_TIMEOUT_SECONDS` (int, default: 300, range: 30-600)
  - `GATEWAY_MAX_CONCURRENT_SYMBOLS` (int, default: 4, range: 1-16)
  - `GATEWAY_TA_MACRO_PARALLEL_TIMEOUT_SECONDS` (int, default: 120, range: 10-300)
  - `GATEWAY_RAG_TIMEOUT_SECONDS` (int, default: 30, range: 5-120)
  - `GATEWAY_PROCESSOR_TIMEOUT_SECONDS` (int, default: 60, range: 10-180)
  - `GATEWAY_GUARD_TIMEOUT_SECONDS` (int, default: 10, range: 2-30)
  - `GATEWAY_TA_CACHE_TTL_SECONDS` (int, default: 300, range: 0-3600)
  - `GATEWAY_MACRO_CACHE_TTL_SECONDS` (int, default: 600, range: 0-3600)
  - `GATEWAY_MAX_CYCLE_RETRIES` (int, default: 1, range: 0-3)
  - `GATEWAY_RETRY_BACKOFF_BASE_SECONDS` (float, default: 2.0, range: 0.5-30.0)
  - `GATEWAY_EXECUTION_ENABLED` (bool, default: true)
  - `GATEWAY_EXECUTION_ADDR` (string, default: localhost:50053)
  - `GATEWAY_EXECUTION_TIMEOUT_MS` (int, default: 5000)
  - `GATEWAY_MANAGEMENT_ENABLED` (bool, default: true)
  - `GATEWAY_MANAGEMENT_ADDR` (string, default: localhost:50054)
  - `GATEWAY_MANAGEMENT_TIMEOUT_MS` (int, default: 5000)
  - `GATEWAY_ENGINE_HTTP_URL` (string, default: http://localhost:8000)
  - `GATEWAY_REDIS_URL` (string, default: redis://localhost:6379/0)
  - `GATEWAY_HTTP_PORT` (int, default: 8080)
  - `GATEWAY_GRPC_PORT` (int, default: 50052)
  - `GATEWAY_LOG_LEVEL` (string, default: INFO)
  - `GATEWAY_LOG_JSON` (bool, default: true)

---

## 3. SYMBOL MANAGEMENT (Symbol Selector Panel)

Controls which currency pairs the system analyzes.

### 3.1 Get Active Symbols
- **RPC:** `GatewayService.GetActiveSymbols`
- **Proto:** `proto/gateway/v1/gateway.proto`
- **Source:** `src/gateway/internal/server/grpc_server.go`
- **Request:** `GetActiveSymbolsRequest{}` (empty)
- **Response:**
  - `symbols` (string[]): Currently active symbols
  - `source` (string): `"redis"` (always, since symbol store uses Redis)
- **Purpose:** Dashboard symbol selector. Shows which pairs are being analyzed.

### 3.2 Set Active Symbols
- **RPC:** `GatewayService.SetActiveSymbols`
- **Proto:** `proto/gateway/v1/gateway.proto`
- **Source:** `src/gateway/internal/server/grpc_server.go`
- **Request:** `symbols` (string[]): New symbol list
- **Response:**
  - `success` (bool)
  - `active_symbols` (string[]): Confirmed active symbols after update
- **Purpose:** Dashboard multi-select to add/remove trading pairs. Persisted in Redis. Publishes `SYMBOLS_CHANGED` alert.

### 3.3 Reset Active Symbols
- **RPC:** `GatewayService.ResetActiveSymbols`
- **Proto:** `proto/gateway/v1/gateway.proto`
- **Source:** `src/gateway/internal/server/grpc_server.go`
- **Request:** `ResetActiveSymbolsRequest{}` (empty)
- **Response:**
  - `success` (bool)
  - `active_symbols` (string[]): Default symbols now active
- **Purpose:** Dashboard "Reset to Defaults" button. Restores the 8 default pairs.

---

## 4. ANALYSIS CYCLE CONTROL (Cycle Panel)

Trigger and monitor analysis cycles.

### 4.1 Run Cycle (Manual Trigger)
- **RPC:** `GatewayService.RunCycle`
- **Proto:** `proto/gateway/v1/gateway.proto`
- **Source:** `src/gateway/internal/server/grpc_server.go`
- **Request:**
  - `symbols` (string[]): Optional. If empty, uses active symbols.
  - `trace_id` (string): Optional correlation ID.
- **Response:** `outputs` (CycleOutput[]): One per symbol processed.
  - Each `CycleOutput` contains:
    - `cycle_status` (string): `RUNNING`, `COMPLETED`, `FAILED`, `TIMED_OUT`
    - `cycle_outcome` (string): `TRADE_APPROVED`, `NO_SETUP`, `REJECTED_BY_GUARD`, `INSUFFICIENT_DATA`, `PROCESSOR_ERROR`, `PIPELINE_ERROR`
    - `phase_reached` (string): `INITIALIZING`, `COLLECTING_PARALLEL`, `BUILDING_QUERY`, `RETRIEVING_RAG`, `ASSEMBLING_CONTEXT`, `PROCESSING_LLM`, `EVALUATING_GUARDS`, `ROUTING_DECISION`, `COMPLETED`, `FAILED`
    - `symbol` (string)
    - `duration_ms` (double)
    - `trace_id` (string)
    - `error` (string)
    - `error_stage` (string)
    - `processor_output_json` (bytes): Full LLM decision as JSON
    - `guard_result_json` (bytes): Guard evaluation as JSON
    - `execution_result_json` (bytes): Execution response as JSON
- **Purpose:** Dashboard "Run Now" button. Triggers immediate analysis. Shows results in real-time.

### 4.2 Re-run Analysis (Single Symbol, Python-side)
- **Endpoint:** `POST /api/analysis/rerun?symbol=EURUSD&trace_id=xxx`
- **Source:** `src/engine/main.py`
- **Returns:**
  - `status` (string): `"completed"`
  - `symbol` (string)
  - `result` (dict): Full processor output
- **Purpose:** Dashboard per-symbol re-analysis. Runs TA + Macro + RAG + Processor in sequence on the Python side. Does NOT go through Go gateway guards or execution routing.

### 4.3 Confirm Setup (Instant Mode)
- **RPC:** `GatewayService.ConfirmSetup`
- **Proto:** `proto/gateway/v1/gateway.proto`
- **Source:** `src/gateway/internal/server/grpc_server.go`
- **Request:**
  - `symbol` (string): e.g. "EURUSD"
  - `analysis_id` (string): Links to original TA candidate
  - `trace_id` (string)
- **Response:**
  - `confirmed` (bool): Whether LTF conditions are now met
  - `ltf_confirmation` (bool): Explicit LTF field from TA
  - `reason` (string): Human-readable explanation
  - `trace_id` (string)
- **Purpose:** Called by Module B's watcher when price enters POI zone. Runs targeted TA-only scan. Bypasses Macro, RAG, Processor. Fast path for instant execution.

---

## 5. ANALYSIS HISTORY & DETAIL (Analysis Panel)

View past and current analysis results from the Processor LLM.

### 5.1 Latest Analyses
- **Endpoint:** `GET /api/analysis/latest?pair=EURUSD&limit=20`
- **Source:** `src/engine/main.py`
- **Returns:** `{"analyses": [...], "count": int}`
- **Each analysis contains:**
  - `analysis_id` (string): Unique ID
  - `pair` (string): Symbol
  - `direction` (string): LONG/SHORT
  - `setup_grade` (string): A+, A, B, REJECT
  - `confluence_score` (float)
  - `confidence` (float)
  - `proceed_to_module_b` (bool): Whether trade was valid
  - `rr_ratio` (float): Risk-reward ratio
  - `trading_style` (string): SCALPING, INTRADAY, SWING, POSITIONAL
  - `session` (string): LONDON_OPEN, LONDON_NY_OVERLAP, etc.
  - `llm_provider` (string): anthropic, openai, gemini, self_hosted
  - `llm_model` (string): Model name used
  - `status` (string): success, no_setup, llm_error, etc.
  - `duration_ms` (float)
  - `created_at` (string): ISO 8601
  - `display.summary` (string): Human-readable summary
  - `display.analyzed_by` (string): Provider + model label
- **Purpose:** Dashboard analysis list. Shows recent decisions.

### 5.2 Analysis History (Paginated + Filtered)
- **Endpoint:** `GET /api/analysis/history?pair=&status=&grade=&provider=&since=&until=&offset=0&limit=20`
- **Source:** `src/engine/main.py`
- **Query Params:**
  - `pair` (string): Filter by symbol
  - `status` (string): Filter by status (success, no_setup, llm_error)
  - `grade` (string): Filter by grade (A+, A, B, REJECT)
  - `provider` (string): Filter by LLM provider
  - `since` (string): ISO 8601 lower bound
  - `until` (string): ISO 8601 upper bound
  - `offset` (int): Pagination offset
  - `limit` (int): Page size (max 100)
- **Returns:** `{"analyses": [...], "total_count": int, "offset": int, "limit": int}`
- **Purpose:** Dashboard analysis history table with pagination and filters.

### 5.3 Analysis Statistics
- **Endpoint:** `GET /api/analysis/stats?pair=&since=&until=`
- **Source:** `src/engine/main.py`
- **Returns:** Aggregate stats:
  - Total count, success rate, grade distribution
  - Average confluence score, average duration
  - Breakdowns by provider and pair
- **Purpose:** Dashboard analytics cards. Shows success rates, grade distribution, performance by provider.

### 5.4 Analysis Detail
- **Endpoint:** `GET /api/analysis/{analysis_id}`
- **Source:** `src/engine/main.py`
- **Returns:** Full analysis detail including:
  - All fields from 5.1 above
  - `display.reasoning` (string): Full LLM reasoning text
  - `display.macro_summary` (string): Macro environment summary
  - `display.technical_summary` (string): TA summary
  - `display.trade_plan` (dict): Entry, SL, TP levels
  - `display.confluence_breakdown` (dict): Score breakdown by factor
  - `display.risk_info` (dict): Risk parameters
  - `display.event_warnings` (list): Upcoming high-impact events
  - `audit.llm_model` (string): Exact model used
  - `audit.llm_input_tokens` (int): Token usage
  - `audit.llm_output_tokens` (int): Token usage
  - `audit.llm_duration_ms` (float): LLM call duration
  - `audit.retrieval_strategy` (string): RAG strategy used
  - `audit.retrieval_chunks_count` (int): Knowledge chunks retrieved
  - `audit.retrieval_coverage` (float): Coverage score
  - `audit.citations` (list): Rule citations from RAG
  - `audit.validation_passed` (bool): Schema validation result
  - `audit.validation_errors` (list): Any validation issues
- **Purpose:** Dashboard analysis detail view. Full reasoning, trade plan, audit trail.

---

## 6. PROCESSOR LLM CONFIGURATION (AI Model Panel)

Switch LLM providers and models at runtime.

### 6.1 Get Available Models
- **Endpoint:** `GET /api/processor/models`
- **Source:** `src/engine/main.py`
- **Returns:**
  - `current_provider` (string): Active provider
  - `current_model` (string): Active model
  - `providers` (dict): Per-provider model lists with defaults
  - `self_hosted` (dict): Self-hosted config with custom model support
- **Purpose:** Dashboard model selector dropdown. Shows all available providers and their models.

### 6.2 Get Processor Config
- **Endpoint:** `GET /api/processor/config`
- **Source:** `src/engine/main.py`
- **Returns:**
  - `llm_provider` (string)
  - `model_name` (string)
  - `temperature` (float)
  - `max_output_tokens` (int)
  - `supported_providers` (string[])
- **Purpose:** Dashboard current LLM config display.

### 6.3 Update Processor Config
- **Endpoint:** `PUT /api/processor/config`
- **Source:** `src/engine/main.py`
- **Request Body:**
  - `llm_provider` (string, optional): New provider
  - `model_name` (string, optional): New model
  - `temperature` (float, optional): 0.0-2.0
  - `max_output_tokens` (int, optional): 1024-131072
  - `api_key` (string, optional): API key for new provider
  - `api_base_url` (string, optional): Base URL for self-hosted
- **Returns:** `{"status": "updated", "llm_provider": ..., "model_name": ..., "temperature": ..., "max_output_tokens": ...}`
- **Purpose:** Dashboard model switcher. Hot-swaps the LLM at runtime. Takes effect on next analysis cycle.
- **Supported Providers:** anthropic, openai, gemini, self_hosted (from `src/engine/processor/constants.py`)

---

## 7. EXECUTION STATE (Module B - Trade Execution Panel)

Current open positions, pending orders, account state, and execution settings.

### 7.1 Get Execution State (gRPC)
- **RPC:** `ExecutionService.GetExecutionState`
- **Proto:** `proto/execution/v1/execution.proto`
- **Source:** `src/execution/internal/server/grpc_server.go`
- **Request:** `trace_id` (string)
- **Response:**
  - `open_position_count` (int32)
  - `pending_order_count` (int32)
  - `daily_realized_pnl` (double)
  - `weekly_realized_pnl` (double)
  - `account_balance` (double)
  - `account_equity` (double)
  - `open_positions` (OpenPosition[]): Each contains:
    - `symbol`, `direction`, `entry_price`, `current_price`, `stop_loss`, `lot_size`, `unrealized_pnl`, `order_id`, `analysis_id`, `trading_style`
  - `pending_orders` (PendingOrder[]): Each contains:
    - `symbol`, `direction`, `entry_price`, `stop_loss`, `lot_size`, `order_id`, `analysis_id`, `execution_mode` (LIMIT/INSTANT), `status` (PENDING/WATCHING)
  - `trace_id` (string)
- **Purpose:** Dashboard execution panel. Shows live positions, pending orders, P&L, account balance.

### 7.2 Get Execution State (REST)
- **Endpoint:** `GET /api/v1/state`
- **Source:** `src/execution/internal/server/http_server.go`
- **Returns:** Same data as gRPC GetExecutionState but as JSON:
  - `open_position_count`, `pending_order_count`, `daily_realized_pnl`, `weekly_realized_pnl`
  - `account_balance`, `account_equity`, `open_positions`, `pending_orders`
- **Purpose:** REST alternative for dashboard to get execution state without gRPC.

### 7.3 Get Execution Settings
- **Endpoint:** `GET /api/v1/settings`
- **Source:** `src/execution/internal/server/http_server.go`
- **Returns:**
  - `execution_mode` (string): `LIMIT` or `INSTANT`
  - `max_concurrent_trades` (int): 1-10 (default 3)
  - `daily_loss_limit_pct` (float): 0.5-10.0 (default 3.0)
  - `weekly_drawdown_pct` (float): 1.0-20.0 (default 5.0)
- **Purpose:** Dashboard execution settings panel. Shows current risk controls.

### 7.4 Update Execution Settings
- **Endpoint:** `PUT /api/v1/settings`
- **Source:** `src/execution/internal/server/http_server.go`
- **Request Body:**
  - `execution_mode` (string): `LIMIT` or `INSTANT`
  - `max_concurrent_trades` (int): 1-10
  - `daily_loss_limit_pct` (float): 0.5-10.0
  - `weekly_drawdown_pct` (float): 1.0-20.0
- **Returns:** Updated settings object
- **Persistence:** PostgreSQL `execution_settings` table (UPSERT)
- **Effect:** Takes effect on the NEXT trade (read on every ExecuteTrade call)
- **Alert:** Publishes `SETTINGS_UPDATED` event to all dashboards
- **Purpose:** Dashboard sliders/inputs for execution mode and risk controls. Changes are immediate.

### 7.5 Get Account Info (REST)
- **Endpoint:** `GET /api/v1/account`
- **Source:** `src/execution/internal/server/http_server.go`
- **Returns:** Live broker account info (balance, equity, margin, free margin)
- **Purpose:** Dashboard account balance card.

### 7.6 Cancel Pending Order (REST)
- **Endpoint:** `POST /api/v1/orders/cancel`
- **Source:** `src/execution/internal/server/http_server.go`
- **Request Body:** `{"order_id": str, "symbol": str, "reason": str}`
- **Returns:** `{"success": bool, "status": "CANCELLED"|"NOT_FOUND"}`
- **Purpose:** Dashboard cancel button on pending orders (REST alternative to gRPC).

### 7.7 Execution WebSocket Notifications
- **Endpoint:** `ws://host:8080/ws/notifications`
- **Source:** `src/execution/internal/server/http_server.go`
- **Purpose:** Module B's own WebSocket endpoint for execution-specific events. Uses the same alert hub.

### 7.8 Execute Trade (gRPC)
- **RPC:** `ExecutionService.ExecuteTrade`
- **Proto:** `proto/execution/v1/execution.proto`
- **Source:** `src/execution/internal/server/grpc_server.go`
- **Request:** Full trade parameters from processor output:
  - `symbol`, `direction` (LONG/SHORT), `entry_zone_low`, `entry_zone_high`, `stop_loss`
  - `tp1_price`, `tp1_pct`, `tp2_price`, `tp2_pct`, `tp3_price`, `tp3_pct`
  - `rr_ratio`, `grade`, `risk_percentage`, `trading_style`, `session`
  - `confluence_score`, `confidence`, `analysis_id`, `trace_id`
  - `execution_mode` (LIMIT/INSTANT), `ltf_confirmed` (bool), `setup_type`
- **Response:**
  - `accepted` (bool)
  - `status` (string): `LIMIT_ORDER_PLACED`, `WATCHER_ARMED`, `REJECTED`, `QUEUED`, `LOCKED`, `PAUSED`
  - `order_id` (string): Broker order ID or watcher ID
  - `rejection_reason` (string): Which check failed
  - `rejection_check` (int32): Check number 4-13
  - `lot_size`, `risk_amount`, `account_balance`, `sl_distance_pips`, `pip_value`
  - `execution_mode` (LIMIT/INSTANT), `entry_price`, `analysis_id`, `trace_id`
- **Pipeline:** Refresh state -> Validate (10 checks) -> Size position -> Resolve mode -> Execute -> Audit
- **Idempotency:** Duplicate `analysis_id` within 1 hour is rejected
- **Purpose:** Gateway calls this when guards pass. Dashboard shows execution result.

### 7.9 Cancel Pending Order (gRPC)
- **RPC:** `ExecutionService.CancelPendingOrder`
- **Proto:** `proto/execution/v1/execution.proto`
- **Source:** `src/execution/internal/server/grpc_server.go`
- **Request:**
  - `order_id` (string): Broker order ID or watcher ID
  - `symbol` (string)
  - `reason` (string): `STRUCTURE_BREAK`, `THESIS_CHANGED`, `MANUAL`, `TTL_EXPIRED`
  - `trace_id` (string)
- **Response:**
  - `success` (bool)
  - `status` (string): `CANCELLED`, `NOT_FOUND`, `ALREADY_FILLED`
  - `trace_id` (string)
- **Purpose:** Cancel pending orders via gRPC.

### 7.10 Pre-Execution Validation Checks (10 Checks)
**Source:** `src/execution/internal/validator/checks.go`, `src/execution/internal/constants/constants.go`

| Check # | Name | Outcome | Description |
|---|---|---|---|
| 4 | News Lockout | REJECT | No entries within 30min (45min for scalping) of high-impact news |
| 5 | Session Filter | REJECT | Only enabled sessions allowed (LONDON_OPEN, LONDON_NY_OVERLAP, NEW_YORK) |
| 6 | Same Pair Position | REJECT | No duplicate positions on same symbol |
| 7 | Correlated Exposure | REJECT | Max 1 trade per correlated pair group (5 groups defined) |
| 8 | Max Concurrent Trades | REJECT | Max concurrent trades limit (default 3, dashboard-configurable 1-10) |
| 9 | Daily Loss Limit | LOCK | Locks execution when daily loss exceeds limit (default 3%, configurable 0.5-10%) |
| 10 | Weekly Drawdown | PAUSE | Pauses execution when weekly drawdown exceeds limit (default 5%, configurable 1-20%) |
| 11 | Spread Check | REJECT | Spread must be below threshold (2x normal, 1.5x scalping) |
| 12 | Min R:R | REJECT | Minimum R:R by style (Scalping 2:1, Intraday/Swing 3:1, Positional 5:1) |
| 13 | Weekend/Day Filter | REJECT | No entries Friday after cutoff (12:00 scalping/intraday, 14:00 swing), no Monday before 07:00 |

### 7.11 Correlated Pair Groups
**Source:** `src/execution/internal/constants/constants.go`

| Group | Pairs |
|---|---|
| USD Quote (risk-on) | EURUSD, GBPUSD, AUDUSD, NZDUSD |
| USD Base | USDJPY, USDCHF, USDCAD |
| JPY Cross | EURJPY, GBPJPY, AUDJPY, NZDJPY |
| EUR Cross | EURGBP, EURAUD, EURNZD, EURCHF, EURCAD |
| Metals | XAUUSD, XAGUSD |

### 7.12 Execution Config Environment Variables
**Source:** `src/execution/internal/config/config.go`
**Prefix:** `EXECUTION_`

- `EXECUTION_GRPC_PORT` (int, default: 50053)
- `EXECUTION_HTTP_PORT` (int, default: 8080)
- `EXECUTION_BROKER_MODE` (string, default: mock, values: mock/mt5)
- `EXECUTION_BROKER_BRIDGE_URL` (string, default: http://localhost:8000)
- `EXECUTION_BROKER_TIMEOUT_MS` (int, default: 5000)
- `EXECUTION_MOCK_BROKER_BALANCE` (float, default: 10000.0)
- `EXECUTION_GATEWAY_ADDR` (string, default: localhost:50052)
- `EXECUTION_DEFAULT_EXECUTION_MODE` (string, default: LIMIT, values: LIMIT/INSTANT)
- `EXECUTION_MIN_LOT_SIZE` (float, default: 0.01)
- `EXECUTION_MAX_LOT_SIZE` (float, default: 10.0)
- `EXECUTION_MAX_CONCURRENT_TRADES` (int, default: 3, range: 1-10)
- `EXECUTION_DAILY_LOSS_LIMIT_PCT` (float, default: 3.0, range: 0.5-10.0)
- `EXECUTION_WEEKLY_DRAWDOWN_PCT` (float, default: 5.0, range: 1.0-20.0)
- `EXECUTION_SPREAD_MULTIPLIER_NORMAL` (float, default: 2.0)
- `EXECUTION_SPREAD_MULTIPLIER_SCALPING` (float, default: 1.5)
- `EXECUTION_NEWS_LOCKOUT_MINUTES` (int, default: 30)
- `EXECUTION_NEWS_LOCKOUT_MINUTES_SCALPING` (int, default: 45)
- `EXECUTION_ENABLED_SESSIONS` (string[], default: LONDON_OPEN,LONDON_NY_OVERLAP,NEW_YORK)
- `EXECUTION_OVERSHOOT_TOLERANCE_MULTIPLIER` (float, default: 1.5)
- `EXECUTION_WATCHER_POLL_INTERVAL_MS` (int, default: 500)
- `EXECUTION_WATCHER_TIMEOUT_MINUTES` (int, default: 45)
- `EXECUTION_WATCHER_CONFIRM_POLL_INTERVAL_SECS` (int, default: 300)
- `EXECUTION_DATABASE_URL` (string, required)
- `EXECUTION_REDIS_URL` (string, default: redis://localhost:6379/1)

---

## 8. TRADE MANAGEMENT (Module C - Active Trades Panel)

Managed trades with break-even, trailing, partial closes.

### 8.1 Get Managed Trades
- **RPC:** `ManagementService.GetManagedTrades`
- **Proto:** `proto/management/v1/management.proto`
- **Source:** `src/management/internal/server/`
- **Request:** `trace_id` (string)
- **Response:** `trades` (ManagedTrade[]): Each contains:
  - `trade_id` (string): Module C tracking ID
  - `symbol` (string)
  - `direction` (string): BUY/SELL
  - `entry_price` (double)
  - `current_price` (double)
  - `stop_loss` (double): Current SL (may have moved to BE or trailing)
  - `tp1_price`, `tp2_price`, `tp3_price` (double)
  - `total_lot_size` (double)
  - `remaining_lot_size` (double): After partial closes
  - `unrealized_pnl` (double)
  - `realized_pnl` (double): From partial closes
  - `trading_style` (string)
  - `status` (string): `ACTIVE`, `BREAKEVEN`, `TRAILING`, `CLOSING`
  - `breakeven_set` (bool)
  - `tp1_hit` (bool)
  - `tp2_hit` (bool)
  - `broker_order_id` (string)
  - `analysis_id` (string)
  - `opened_at` (string): RFC3339
- **Purpose:** Dashboard active trades table. Shows all trades under management with live P&L.

### 8.2 Register Filled Trade (Gateway -> Module C Handoff)
- **RPC:** `ManagementService.RegisterFilledTrade`
- **Proto:** `proto/management/v1/management.proto`
- **Source:** `src/management/internal/server/`
- **Request:** Full trade context:
  - `symbol`, `direction` (BUY/SELL), `broker_order_id`, `fill_price`, `stop_loss`
  - `tp1_price`, `tp1_pct`, `tp2_price`, `tp2_pct`, `tp3_price`, `tp3_pct`
  - `lot_size`, `rr_ratio`, `risk_amount`, `risk_percent`, `grade`
  - `trading_style`, `session`, `confluence_score`, `analysis_id`, `trace_id`
  - `slippage`, `setup_type`, `execution_mode`
- **Response:**
  - `success` (bool)
  - `trade_id` (string): Module C's internal tracking ID
  - `message` (string)
- **Purpose:** Step 7 of architecture. Gateway hands off filled trade to Module C. Dashboard sees the trade appear in managed trades.

### 8.3 Update Trade Status (Module C -> Gateway)
- **RPC:** `ManagementService.UpdateTradeStatus`
- **Proto:** `proto/management/v1/management.proto`
- **Source:** `src/management/internal/server/`
- **Request:**
  - `trade_id` (string)
  - `event_type` (string): `TP1_HIT`, `TP2_HIT`, `TP3_HIT`, `SL_HIT`, `BREAKEVEN_SET`, `TRAILING_SL_MOVED`, `PARTIAL_CLOSE`, `TRADE_CLOSED`, `EOD_CLOSURE`, `INVALIDATION_CLOSURE`
  - `symbol`, `current_price`, `new_stop_loss`, `closed_lot_size`, `realized_pnl`, `r_multiple`, `reason`, `trace_id`
- **Response:** `success` (bool)
- **Purpose:** Module C reports trade events. Dashboard updates trade status in real-time.

---

## 9. TRADE JOURNAL (Journal Panel)

Closed trade history with full detail.

### 9.1 Get Trade Journal
- **RPC:** `ManagementService.GetTradeJournal`
- **Proto:** `proto/management/v1/management.proto`
- **Source:** `src/management/internal/server/`
- **Request:**
  - `limit` (int32): Max entries (default 50)
  - `offset` (int32): Pagination offset
  - `symbol_filter` (string): Optional symbol filter
  - `style_filter` (string): Optional trading style filter
  - `trace_id` (string)
- **Response:**
  - `entries` (JournalEntry[]): Each contains:
    - `trade_id`, `symbol`, `direction`
    - `entry_price`, `exit_price`, `stop_loss`, `lot_size`
    - `gross_pnl` (double)
    - `r_multiple` (double): Realized R-multiple
    - `confluence_score` (double)
    - `grade` (string): A+, A, B
    - `setup_type` (string): OB, FVG, SND_ZONE, LIQUIDITY_SWEEP, etc.
    - `trading_style` (string)
    - `outcome` (string): `WIN`, `LOSS`, `BREAKEVEN`
    - `opened_at`, `closed_at` (string): RFC3339
    - `duration_minutes` (int32)
    - `sl_adjustment_count` (int32)
    - `partial_close_count` (int32)
    - `analysis_id` (string)
  - `total_count` (int32)
- **Purpose:** Dashboard trade journal. Full history of closed trades with outcomes.

---

## 10. PERFORMANCE ANALYTICS (Performance Panel)

Real-time trading performance metrics.

### 10.1 Get Performance Metrics
- **RPC:** `ManagementService.GetPerformanceMetrics`
- **Proto:** `proto/management/v1/management.proto`
- **Source:** `src/management/internal/server/`
- **Request:**
  - `period` (string): `DAILY`, `WEEKLY`, `MONTHLY`, `ALL_TIME`
  - `trace_id` (string)
- **Response:**
  - `win_rate` (double)
  - `avg_r_multiple` (double)
  - `expectancy` (double)
  - `total_trades` (int32)
  - `wins` (int32)
  - `losses` (int32)
  - `breakevens` (int32)
  - `total_pnl` (double)
  - `max_consecutive_wins` (int32)
  - `max_consecutive_losses` (int32)
  - `max_drawdown_pct` (double)
  - `best_trade_r` (double)
  - `worst_trade_r` (double)
  - `win_rate_by_symbol` (map<string, double>)
  - `win_rate_by_style` (map<string, double>)
  - `win_rate_by_setup` (map<string, double>)
  - `win_rate_by_session` (map<string, double>)
- **Purpose:** Dashboard performance cards and charts. Win rate, expectancy, drawdown, breakdowns by symbol/style/setup/session.

---

## 11. REAL-TIME NOTIFICATIONS (Notification Center / Event Feed)

Live event stream from all modules.

### 11.1 WebSocket Notifications
- **Endpoint:** `ws://host:8080/ws/notifications?severity=WARNING`
- **Source:** `src/alert/handler.go`
- **Protocol:** WebSocket (gorilla/websocket)
- **Query Params:**
  - `severity` (string, optional): Minimum severity filter. Values: `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Default: all events.
- **Event Payload (JSON):**
  - `id` (string): Unique event ID (format: `20060102150405-hexbytes`)
  - `source` (string): `GATEWAY`, `EXECUTION`, `TRADE_MANAGER`, `SYSTEM`
  - `type` (string): Event type (see full list below)
  - `severity` (string): `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - `timestamp` (string): RFC3339Nano
  - `symbol` (string, optional)
  - `direction` (string, optional)
  - `message` (string): Human-readable description
  - `trace_id` (string, optional): Correlation ID
  - `details` (dict, optional): Arbitrary key-value metadata
- **Purpose:** Dashboard real-time notification feed. Every significant event across all modules streams here.

### 11.2 Recent Events (REST)
- **Endpoint:** `GET /events/recent?count=50&severity=WARNING`
- **Source:** `src/alert/handler.go`
- **Returns:** `{"events": [...], "count": int}`
- **Purpose:** Dashboard event history on page load. Fetches last N events from Redis.

### 11.3 Events Since (Catch-up)
- **Endpoint:** `GET /events/since?last_event_id=xxx&count=100`
- **Source:** `src/alert/handler.go`
- **Returns:** `{"events": [...], "count": int}`
- **Purpose:** Dashboard reconnection catch-up. After WebSocket reconnect, fetches events missed during disconnect.

### 11.4 Complete Event Type Catalog

**Source:** `src/alert/event.go`

#### Gateway Events (source: GATEWAY)
| Event Type | Severity | Description |
|---|---|---|
| `CYCLE_STARTED` | INFO | Analysis cycle began |
| `CYCLE_COMPLETED` | INFO | Cycle finished successfully |
| `CYCLE_FAILED` | ERROR | Cycle failed (timeout or error) |
| `CYCLE_RETRYING` | WARNING | Cycle retrying after failure |
| `ANALYSIS_COMPLETE` | INFO | Processor returned decision for a symbol |
| `GUARD_REJECTED` | WARNING | Trade blocked by post-processor guards |
| `GUARD_WARNING` | WARNING | Guard passed but flagged a concern |
| `TA_COLLECTION_FAILED` | ERROR | Technical analysis collection failed |
| `MACRO_COLLECTION_FAILED` | ERROR | Macro data collection failed |
| `RAG_RETRIEVAL_FAILED` | ERROR | RAG knowledge retrieval failed |
| `PROCESSOR_LLM_FAILED` | ERROR | LLM processor call failed |
| `EXECUTION_CALL_FAILED` | ERROR | Call to Module B failed |
| `TRADE_ROUTED` | INFO | Trade approved and sent to execution |
| `EXECUTION_HANDOFF` | INFO | Filled trade handed off to Module C |
| `MANAGEMENT_HANDOFF_FAILED` | ERROR | Failed to hand off to Module C |
| `INTERVAL_CHANGED` | INFO | Cycle interval changed via dashboard |
| `SYMBOLS_CHANGED` | INFO | Active symbols changed via dashboard |

#### Execution Events (source: EXECUTION)
| Event Type | Severity | Description |
|---|---|---|
| `ORDER_PLACED` | INFO | Limit order placed at broker |
| `ORDER_FILLED` | INFO | Order filled at broker |
| `ORDER_CANCELLED` | INFO | Order cancelled |
| `ORDER_EXPIRED` | WARNING | Order expired (TTL) |
| `EXECUTION_REJECTED` | WARNING | Pre-execution check failed |
| `WATCHER_ARMED` | INFO | Instant-mode price watcher started |
| `WATCHER_TRIGGERED` | INFO | Price entered POI zone |
| `DAILY_LIMIT_LOCKED` | WARNING | Daily loss limit reached |
| `WEEKLY_PAUSED` | WARNING | Weekly loss limit reached |
| `SIZING_CALCULATED` | INFO | Position size calculated |
| `EXECUTION_ERROR` | ERROR | Execution engine error |
| `EXECUTION_MODE_CHANGED` | INFO | Execution mode switched |
| `SETTINGS_UPDATED` | INFO | Execution settings changed |

#### Trade Manager Events (source: TRADE_MANAGER)
| Event Type | Severity | Description |
|---|---|---|
| `TRAILING_SL_MOVED` | INFO | Trailing stop loss adjusted |
| `PARTIAL_CLOSE` | INFO | Partial position closed (TP hit) |
| `BREAKEVEN_SET` | INFO | Stop loss moved to break-even |
| `TRADE_CLOSED` | INFO | Trade fully closed |
| `PERFORMANCE_REPORT` | INFO | Periodic performance summary |

#### System Events (source: SYSTEM)
| Event Type | Severity | Description |
|---|---|---|
| `SERVICE_STARTED` | INFO | Service started |
| `SERVICE_STOPPING` | INFO | Service shutting down |
| `BROKER_DISCONNECTED` | ERROR | Broker connection lost |
| `BROKER_RECONNECTED` | INFO | Broker connection restored |

#### Market Events
| Event Type | Severity | Description |
|---|---|---|
| `CANDLE_CLOSED` | INFO | New candle closed on a timeframe |
| `COT_FLIP` | WARNING | COT positioning flipped |
| `MACRO_CALENDAR_UPDATE` | INFO | Economic calendar updated |

---

## 12. BROKER BRIDGE (Internal - Engine Proxies)

The Python engine proxies broker operations for Go services.

### 12.1 Account Info
- **Endpoint:** `GET /internal/broker/account_info`
- **Source:** `src/engine/main.py`
- **Returns:** `{"balance": float, "equity": float, "margin": float, "margin_free": float, "currency": string}`
- **Purpose:** Go Execution and Management services get live account data.

### 12.2 Open Positions
- **Endpoint:** `GET /internal/broker/positions`
- **Source:** `src/engine/main.py`
- **Returns:** Array of position objects with symbol, type, prices, volume, profit, ticket.
- **Purpose:** Go services query live broker positions.

### 12.3 Pending Orders
- **Endpoint:** `GET /internal/broker/pending_orders`
- **Source:** `src/engine/main.py`
- **Returns:** Array of pending order objects.
- **Purpose:** Go services query pending broker orders.

### 12.4 Symbol Info
- **Endpoint:** `GET /internal/broker/symbol_info?symbol=EURUSD`
- **Source:** `src/engine/main.py`
- **Returns:** Instrument metadata including tick_value, tick_size, digits, contract_size.
- **Purpose:** Go sizing engine uses this for pip value calculation.

### 12.5 Tick Price
- **Endpoint:** `GET /internal/broker/tick_price?symbol=EURUSD`
- **Source:** `src/engine/main.py`
- **Returns:** `{"bid": float, "ask": float, "time": string}`
- **Purpose:** Execution watcher and Management monitoring poll this for live prices.

### 12.6 Place Order
- **Endpoint:** `POST /internal/broker/place_order`
- **Source:** `src/engine/main.py`
- **Body:** `{"symbol": str, "direction": str, "order_type": str, "price": float, "stop_loss": float, "take_profit": float, "lot_size": float, "comment": str}`
- **Returns:** `{"order_id": str, "price": float, "status": str, "error": str}`
- **Purpose:** Module B places orders through this bridge.

### 12.7 Cancel Order
- **Endpoint:** `POST /internal/broker/cancel_order`
- **Source:** `src/engine/main.py`
- **Body:** `{"order_id": str}`
- **Returns:** `{"success": bool, "error": str}`
- **Purpose:** Module B cancels pending orders.

### 12.8 Get Single Position
- **Endpoint:** `GET /internal/broker/position?ticket=12345`
- **Source:** `src/engine/main.py`
- **Returns:** Single position object.
- **Purpose:** Module C queries individual positions.

### 12.9 Modify Position
- **Endpoint:** `POST /internal/broker/modify_position`
- **Source:** `src/engine/main.py`
- **Body:** `{"ticket": str, "stop_loss": float, "take_profit": float}`
- **Returns:** `{"success": bool, "error": str}`
- **Purpose:** Module C modifies SL/TP on open positions (break-even, trailing).

### 12.10 Close Partial
- **Endpoint:** `POST /internal/broker/close_partial`
- **Source:** `src/engine/main.py`
- **Body:** `{"ticket": str, "volume": float}`
- **Returns:** `{"success": bool, "close_price": float, "error": str}`
- **Purpose:** Module C partially closes positions at TP levels.

### 12.11 Close Position
- **Endpoint:** `POST /internal/broker/close_position`
- **Source:** `src/engine/main.py`
- **Body:** `{"ticket": str}`
- **Returns:** `{"success": bool, "close_price": float, "error": str}`
- **Purpose:** Module C fully closes positions (EOD, invalidation).

---

## 13. INTERNAL ENGINE ENDPOINTS (Gateway -> Engine)

These are called by the Go gateway, not directly by the dashboard.

### 13.1 TA Analysis
- **Endpoint:** `POST /internal/ta/analyze`
- **Source:** `src/engine/main.py`
- **Body:** `{"symbols": ["EURUSD"], "trace_id": "xxx"}`
- **Returns:** `{"symbol_results": [...]}`
- **Purpose:** Go gateway calls this for technical analysis.

### 13.2 Macro Collection
- **Endpoint:** `POST /internal/macro/collect`
- **Source:** `src/engine/main.py`
- **Body:** `{"trace_id": "xxx"}`
- **Returns:** 8 macro datasets (central_bank, cot, economic, news, calendar, dxy, intermarket, sentiment) + errors map.
- **Purpose:** Go gateway calls this for macro data collection.

### 13.3 RAG Retrieval
- **Endpoint:** `POST /internal/rag/retrieve`
- **Source:** `src/engine/main.py`
- **Body:** Full RAG query params (query_text, strategy, framework, setup_family, direction, timeframe, style, symbol, all signal flags).
- **Returns:** Context bundle with retrieved knowledge chunks.
- **Purpose:** Go gateway calls this for RAG knowledge retrieval.

### 13.4 Processor LLM
- **Endpoint:** `POST /internal/processor/process`
- **Source:** `src/engine/main.py`
- **Body:** `{"processor_input": {"symbol": ..., "ta_analysis": ..., "macro_analysis": ..., "retrieved_knowledge": ..., "metadata": ...}, "trace_id": "xxx"}`
- **Returns:** Full processor output (trade_valid, direction, confidence, grade, entry/SL/TP levels, etc.)
- **Purpose:** Go gateway calls this for LLM decision.

---

## 14. EXECUTION HANDOFF FLOW (Gateway Orchestration)

The complete flow when a trade is filled.

### 14.1 Notify Execution Completed
- **RPC:** `GatewayService.NotifyExecutionCompleted`
- **Proto:** `proto/gateway/v1/gateway.proto`
- **Source:** `src/gateway/internal/server/grpc_server.go`
- **Called by:** Module B (Execution) after order is FILLED at broker
- **Request:** Full trade context:
  - `symbol`, `broker_order_id`, `fill_price`, `slippage`, `lot_size`, `analysis_id`, `trace_id`
  - `direction`, `stop_loss`, `tp1_price`, `tp1_pct`, `tp2_price`, `tp2_pct`, `tp3_price`, `tp3_pct`
  - `risk_amount`, `risk_percent`, `rr_ratio`, `grade`, `trading_style`, `session`
  - `confluence_score`, `execution_mode`, `setup_type`
- **Response:**
  - `success` (bool)
  - `management_trade_id` (string): Module C's tracking ID
- **Purpose:** Step 7 of architecture. Module B tells Gateway the order filled. Gateway forwards to Module C for lifecycle management.

---

## 15. GUARD RULES (Post-Processor Safety)

Hard rejection rules evaluated after the LLM decision.

**Source:** `src/gateway/internal/routing/guards.go`

| Rule ID | Name | Type | Description |
|---|---|---|---|
| `MR-REJECT-001` | News Proximity | REJECT | No entries within 30 minutes of high-impact news events |
| `MR-REJECT-002` | Session Restriction | REJECT | No non-Asian pairs during Asian session (00:00-07:00 UTC) |
| `MR-REJECT-006` | Counter-Trend No CHoCH | REJECT/WARN | Counter-trend trades require CHoCH confirmation. WARN if CHoCH exists, REJECT if not |
| `MR-REJECT-008` | Weekend Gap Risk | REJECT | No entries after Friday 20:00 UTC or on weekends |
| `MR-REJECT-009` | Low Liquidity Hours | WARN | Warning during 21:00-01:00 UTC (low liquidity) |

---

## 16. PIPELINE PHASES & OBSERVABILITY

The analysis pipeline phases tracked by the orchestrator.

**Source:** `src/gateway/internal/constants/constants.go`

| Phase | Description |
|---|---|
| `INITIALIZING` | Cycle starting up |
| `COLLECTING_PARALLEL` | TA + Macro running in parallel |
| `BUILDING_QUERY` | RAG query construction from TA + Macro signals |
| `RETRIEVING_RAG` | Knowledge base retrieval |
| `ASSEMBLING_CONTEXT` | Combining TA + Macro + RAG into processor input |
| `PROCESSING_LLM` | LLM decision making |
| `EVALUATING_GUARDS` | Post-processor guard checks |
| `ROUTING_DECISION` | Routing to execution or rejection |
| `COMPLETED` | Pipeline finished |
| `FAILED` | Pipeline failed |

### Prometheus Metrics (Gateway)
**Source:** `src/gateway/internal/observability/metrics.go`
- `etradie_gateway_cycle_total` (counter, labels: status, outcome)
- `etradie_gateway_cycle_duration_seconds` (histogram)
- `etradie_gateway_active_cycles` (gauge)
- `etradie_gateway_phase_duration_seconds` (histogram, label: phase)
- `etradie_gateway_stage_errors_total` (counter, labels: stage, error_type)
- `etradie_gateway_no_setup_total` (counter, label: reason)
- `etradie_gateway_trade_routed_total` (counter, labels: symbol, direction)
- `etradie_gateway_guard_rejections_total` (counter, label: rule)
- `etradie_gateway_guard_duration_seconds` (histogram)
- `etradie_gateway_rag_duration_seconds` (histogram)
- `etradie_gateway_processor_duration_seconds` (histogram)

### Prometheus Metrics (Alert System)
**Source:** `src/alert/metrics.go`
- `etradie_alert_events_published_total` (counter, labels: source, type, severity)
- `etradie_alert_events_dropped_total` (counter, label: subscriber_id)
- `etradie_alert_active_subscribers` (gauge)
- `etradie_alert_redis_published_total` (counter)
- `etradie_alert_redis_received_total` (counter)
- `etradie_alert_redis_errors_total` (counter, label: operation)
- `etradie_alert_history_size` (gauge)

---

## 17. DATA MODELS REFERENCE

Key data structures the dashboard must understand.

### 17.1 ProcessorOutput (LLM Decision)
**Source:** `src/gateway/internal/models/processor.go`

| Field | Type | Description |
|---|---|---|
| `trade_valid` | bool | Whether the LLM approves the trade |
| `direction` | string | LONG or SHORT |
| `symbol` | string | Currency pair |
| `confidence` | float64 | 0.0-1.0 confidence score |
| `grade` | string | A+, A, B |
| `risk_percentage` | float64 | 1.0 or 0.5 |
| `reasoning` | string | Full LLM reasoning text |
| `entry_price` | float64 | Midpoint entry |
| `stop_loss` | float64 | Stop loss level |
| `take_profit` | float64 | Primary TP (backward compat) |
| `rejection_rules` | string[] | Rules that caused rejection |
| `entry_zone_low` | float64 | Entry zone lower bound |
| `entry_zone_high` | float64 | Entry zone upper bound |
| `tp1_price` | float64 | Take profit 1 |
| `tp1_pct` | int | TP1 position % (e.g. 40) |
| `tp2_price` | float64 | Take profit 2 |
| `tp2_pct` | int | TP2 position % (e.g. 30) |
| `tp3_price` | float64 | Take profit 3 |
| `tp3_pct` | int | TP3 position % (e.g. 30) |
| `trading_style` | string | SCALPING, INTRADAY, SWING, POSITIONAL |
| `session` | string | Trading session |
| `rr_ratio` | float64 | Risk-reward ratio |
| `confluence_score` | float64 | Confluence score |
| `analysis_id` | string | Unique analysis ID |
| `execution_mode` | string | LIMIT or INSTANT |
| `ltf_confirmed` | bool | LTF confirmation status |
| `setup_type` | string | OB, FVG, SND_ZONE, etc. |

### 17.2 MacroResult (8 Datasets)
**Source:** `src/gateway/internal/models/macro.go`

| Dataset | Description |
|---|---|
| `central_bank` | Fed, ECB, BOE, BOJ speeches and rate decisions |
| `cot` | CFTC Commitment of Traders positioning data |
| `economic` | GDP, CPI, NFP, unemployment, PMI releases |
| `news` | Bloomberg, Reuters, NewsAPI headlines |
| `calendar` | Upcoming economic events with impact ratings |
| `dxy` | US Dollar Index momentum and trend |
| `intermarket` | Cross-market correlations (bonds, commodities, equities) |
| `sentiment` | Market sentiment indicators |

### 17.3 TASymbolResult (Technical Analysis)
**Source:** `src/gateway/internal/models/ta.go`

| Field | Type | Description |
|---|---|---|
| `symbol` | string | Currency pair |
| `htf_timeframes` | string[] | Higher timeframes analyzed |
| `ltf_timeframes` | string[] | Lower timeframes analyzed |
| `status` | string | success, insufficient_data, error |
| `smc_candidates` | []map | Smart Money Concept trade candidates |
| `snd_candidates` | []map | Supply & Demand zone candidates |
| `snapshots` | map[tf]map | Per-timeframe market structure snapshots |
| `alignment` | map[tf]map | Multi-timeframe alignment data |
| `overall_trend` | string | BULLISH, BEARISH, NEUTRAL |

---

## 18. ALERT SYSTEM ARCHITECTURE

How events flow from services to the dashboard.

**Source:** `src/alert/` (event.go, hub.go, handler.go, metrics.go, redis/transport.go)

### Architecture:
1. **Any service** calls `transport.Publish(ctx, event)` to emit an event.
2. **Transport** does three things simultaneously:
   - Publishes to local Hub (immediate WebSocket delivery)
   - Publishes to Redis pub/sub channel `etradie:alerts` (cross-service delivery)
   - Stores in Redis sorted set `etradie:alert_history` (persistence, max 2000 events, 7-day TTL)
3. **Hub** fans out to all connected WebSocket subscribers (non-blocking, drops if buffer full).
4. **Background subscriber** listens on Redis channel and feeds remote events to local Hub.
5. **Dashboard** connects via WebSocket and receives all events in real-time.
6. **On reconnect**, dashboard calls `GET /events/since?last_event_id=xxx` to catch up.

### Key Constants:
- Redis channel: `etradie:alerts`
- Redis history key: `etradie:alert_history`
- Max history: 2000 events
- History TTL: 7 days
- Subscriber buffer: 128 events
- WebSocket ping interval: 30 seconds
- WebSocket pong timeout: 35 seconds

---

## 19. MACRO COLLECTORS (8 Data Sources)

All macro data collectors that feed into the analysis pipeline.

**Source:** `src/engine/macro/collectors/`

| Collector | File | Provider(s) | Data |
|---|---|---|---|
| Calendar | `calendar/collector.py` | Trading Economics | Upcoming economic events with impact ratings |
| Central Bank | `central_bank/collector.py` | Fed RSS, ECB RSS, BOE RSS, BOJ RSS | Central bank speeches, minutes, rate decisions |
| COT | `cot/collector.py` | CFTC | Commitment of Traders positioning data |
| DXY | `dxy/collector.py` | Trading Economics, Twelve Data | US Dollar Index price and momentum |
| Economic Data | `economic_data/collector.py` | FRED, Trading Economics | GDP, CPI, NFP, unemployment, PMI |
| Intermarket | `intermarket/collector.py` | Trading Economics, Twelve Data | Bond yields, commodity prices, equity indices |
| News | `news/collector.py` | Bloomberg RSS, Reuters RSS, NewsAPI | Market-moving headlines |
| Sentiment | `sentiment/collector.py` | Trading Economics | Market sentiment indicators |

### Macro Providers:
**Source:** `src/engine/macro/providers/`

| Provider | File | API |
|---|---|---|
| Trading Economics Calendar | `calendar/trading_economics.py` | Trading Economics API |
| Fed RSS | `central_bank/fed_rss.py` | Federal Reserve RSS feeds |
| ECB RSS | `central_bank/ecb_rss.py` | European Central Bank RSS |
| BOE RSS | `central_bank/boe_rss.py` | Bank of England RSS |
| BOJ RSS | `central_bank/boj_rss.py` | Bank of Japan RSS |
| CFTC COT | `cot/cftc.py` | CFTC public data |
| FRED | `economic_data/fred.py` | Federal Reserve Economic Data API |
| Trading Economics Economic | `economic_data/trading_economics.py` | Trading Economics API |
| Trading Economics Market Data | `market_data/trading_economics.py` | Trading Economics API |
| Twelve Data Market | `market_data/twelve_data.py` | Twelve Data API |
| Bloomberg RSS | `news/bloomberg_rss.py` | Bloomberg RSS feeds |
| Reuters RSS | `news/reuters_rss.py` | Reuters RSS feeds |
| NewsAPI | `news/newsapi.py` | NewsAPI.org |
| Trading Economics Sentiment | `sentiment/trading_economics.py` | Trading Economics API |

---

## 20. TECHNICAL ANALYSIS ENGINE

TA analysis components.

**Source:** `src/engine/ta/`

### Frameworks:
| Framework | Directory | Description |
|---|---|---|
| SMC (Smart Money Concepts) | `smc/` | Order blocks, fair value gaps, liquidity sweeps, CHoCH, BMS |
| SnD (Supply & Demand) | `snd/` | Supply/demand zones, Marubozu validation |

### SMC Components:
- `smc/builders/` - Candidate builders (AMD pattern builder)
- `smc/detectors/` - Structure detectors (CHoCH, BMS, liquidity)
- `smc/validators/` - LTF confirmation validators, zone validators
- `smc/zones/` - Zone identification and management

### SnD Components:
- `snd/builders/` - Zone candidate builders
- `snd/detectors/` - Zone detection algorithms
- `snd/validators/` - LTF validators, Marubozu validators

### Broker Integrations:
| Broker | Directory | Description |
|---|---|---|
| MT5 via MetaAPI | `broker/mt5/metaapi/` | Cloud-based MT5 access |
| MT5 via ZeroMQ | `broker/mt5/zmq/` | Direct MT5 bridge via ZMQ EA |
| TradingView | `broker/tradingview/webhook/` | TradingView webhook alerts |
| Twelve Data | `broker/twelve_data/` | Market data feed |

### Common Services:
- `common/analyzers/` - Shared analysis utilities
- `common/services/alignment/` - Multi-timeframe alignment
- `common/services/snapshot/` - Market structure snapshots
- `common/timeframe/` - Timeframe management
- `common/utils/price/` - Price utilities

---

## 21. RAG KNOWLEDGE BASE

Retrieval-Augmented Generation system.

**Source:** `src/engine/rag/`

### Components:
| Component | Directory | Description |
|---|---|---|
| Embeddings | `embeddings/` | OpenAI, Nomic, Sentence Transformers embedding providers |
| Ingest | `ingest/` | Document loading, chunking, normalization, validation |
| Knowledge | `knowledge/` | Bootstrap, manifest, policies, types |
| Retrieval | `retrieval/` | Retriever, reranker, assembler, citations, coverage, filters |
| Scenarios | `scenarios/` | Chart scenario matching and indexing |
| Services | `services/` | Bootstrap, health, sync, versioning, audit, re-embed |
| Storage | `storage/` | Chunk, document, citation, scenario repositories |
| VectorStore | `vectorstore/` | ChromaDB integration, collections, filters, upsert |

### Retrieval Strategies:
- `strategies/hybrid.py` - Hybrid semantic + keyword search
- `strategies/macro_bias.py` - Macro-biased retrieval
- `strategies/rule_first.py` - Rule-prioritized retrieval
- `strategies/scenario_first.py` - Scenario-prioritized retrieval

### Ingest Loaders:
- Markdown, DOCX, JSON, Text, Scenario Asset loaders

### Ingest Chunkers:
- Framework, Macro, Rulebook, Scenario, Metadata chunkers

---

## 22. PROCESSOR LLM

The AI decision engine.

**Source:** `src/engine/processor/`

### Components:
| Component | File | Description |
|---|---|---|
| Service | `service.py` | Main AnalysisProcessor orchestrator |
| Config | `config.py` | ProcessorConfig with all LLM settings |
| Constants | `constants.py` | Available models, default models, LLMProvider enum |
| LLM Client | `llm/client.py` | Abstract LLM client interface |
| LLM Factory | `llm/factory.py` | Creates provider-specific clients |
| Anthropic | `llm/providers/anthropic.py` | Claude integration |
| OpenAI | `llm/providers/openai_provider.py` | GPT integration |
| Gemini | `llm/providers/gemini.py` | Gemini integration |
| OpenAI Compatible | `llm/providers/openai_compatible.py` | Self-hosted (vLLM, Ollama, etc.) |
| Retry | `llm/retry.py` | Retry logic with exponential backoff |
| System Prompt | `prompts/system_prompt.py` | The master system prompt for the LLM |
| Response Parser | `parsing/response_parser.py` | Parses LLM JSON output |
| Validators | `parsing/validators.py` | Validates parsed output against schema |
| Output Mapper | `mapping/output_mapper.py` | Maps parsed output to ProcessorOutput |
| Dashboard Formatter | `mapping/dashboard_formatter.py` | Formats output for dashboard display |
| Audit Logger | `audit/logger.py` | Logs LLM calls with token usage |
| Models | `models/analysis.py`, `models/audit.py`, `models/io.py` | Data models |
| Analysis Repo | `storage/repositories/analysis_repository.py` | Persists analysis results |
| Audit Repo | `storage/repositories/audit_repository.py` | Persists audit logs |

---

## 23. SHARED INFRASTRUCTURE

**Source:** `src/engine/shared/`

| Component | Directory | Description |
|---|---|---|
| Cache | `cache/redis_cache.py` | Redis cache client |
| Database | `db/connection.py` | PostgreSQL async connection |
| Migrations | `db/migrations/` | Alembic migrations (7 versions) |
| Base Repository | `db/repositories/base_repository.py` | SQLAlchemy base repository |
| HTTP Client | `http/client.py` | Shared async HTTP client |
| Logging | `logging/logger.py` | Structured logging |
| Metrics | `metrics/prometheus.py` | Prometheus metrics |
| Models | `models/` | Base models, currency config, events |
| RSS Parser | `rss/parser.py` | RSS feed parser for central bank/news |
| Scheduler | `scheduler/apscheduler.py` | APScheduler for periodic jobs |
| Symbol Store | `store/symbol.py` | Redis-backed symbol reader |
| Tracing | `tracing/otel.py` | OpenTelemetry tracing |

---

## 24. SERVICE PORTS & ADDRESSES

| Service | Protocol | Default Port | Address Config |
|---|---|---|---|
| Gateway HTTP | HTTP | 8080 | `GATEWAY_HTTP_PORT` |
| Gateway gRPC | gRPC | 50052 | `GATEWAY_GRPC_PORT` |
| Engine HTTP | HTTP | 8000 | `GATEWAY_ENGINE_HTTP_URL` |
| Execution gRPC | gRPC | 50053 | `GATEWAY_EXECUTION_ADDR` |
| Management gRPC | gRPC | 50054 | `GATEWAY_MANAGEMENT_ADDR` |
| Redis | TCP | 6379 | `GATEWAY_REDIS_URL` |
| PostgreSQL | TCP | 5432 | Engine DB config |
| Prometheus | HTTP | 9090 | `docker/prometheus/prometheus.yml` |
| Grafana | HTTP | 3000 | `docker/grafana/datasources.yml` |
| OTEL Collector | gRPC | 4317 | `GATEWAY_OTEL_ENDPOINT` |

---

## 25. COMPLETE API ENDPOINT SUMMARY

### Gateway HTTP (port 8080)
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness probe |
| GET | `/readiness` | Deep health check |
| GET | `/metrics` | Prometheus metrics |
| WS | `/ws/notifications` | Real-time event stream |
| GET | `/events/recent` | Event history |
| GET | `/events/since` | Event catch-up |

### Gateway gRPC (port 50052)
| RPC | Purpose |
|---|---|
| `RunCycle` | Trigger analysis cycle |
| `ConfirmSetup` | TA-only confirmation pulse |
| `NotifyExecutionCompleted` | Filled trade handoff |
| `SetActiveSymbols` | Update symbol selection |
| `GetActiveSymbols` | Get current symbols |
| `ResetActiveSymbols` | Reset to defaults |
| `SetCycleInterval` | Change cycle interval |
| `GetGatewayConfig` | Get runtime config |
| `GetHealth` | Gateway health |

### Engine HTTP (port 8000)
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Engine liveness |
| GET | `/health/rag` | RAG health |
| POST | `/internal/ta/analyze` | TA analysis |
| POST | `/internal/macro/collect` | Macro collection |
| POST | `/internal/rag/retrieve` | RAG retrieval |
| POST | `/internal/processor/process` | LLM processing |
| GET | `/api/analysis/latest` | Recent analyses |
| GET | `/api/analysis/history` | Analysis history |
| GET | `/api/analysis/stats` | Analysis statistics |
| GET | `/api/analysis/{id}` | Analysis detail |
| POST | `/api/analysis/rerun` | Re-run analysis |
| GET | `/api/processor/models` | Available LLM models |
| GET | `/api/processor/config` | Current LLM config |
| PUT | `/api/processor/config` | Update LLM config |
| GET | `/internal/broker/account_info` | Broker account |
| GET | `/internal/broker/positions` | Open positions |
| GET | `/internal/broker/pending_orders` | Pending orders |
| GET | `/internal/broker/symbol_info` | Symbol metadata |
| GET | `/internal/broker/tick_price` | Live bid/ask |
| POST | `/internal/broker/place_order` | Place order |
| POST | `/internal/broker/cancel_order` | Cancel order |
| GET | `/internal/broker/position` | Single position |
| POST | `/internal/broker/modify_position` | Modify SL/TP |
| POST | `/internal/broker/close_partial` | Partial close |
| POST | `/internal/broker/close_position` | Full close |

### Execution gRPC (port 50053)
| RPC | Purpose |
|---|---|
| `ExecuteTrade` | Place trade |
| `CancelPendingOrder` | Cancel order |
| `GetExecutionState` | Positions + P&L |

### Management gRPC (port 50054)
| RPC | Purpose |
|---|---|
| `RegisterFilledTrade` | Accept filled trade |
| `UpdateTradeStatus` | Report trade events |
| `GetManagedTrades` | Active managed trades |
| `GetTradeJournal` | Closed trade history |
| `GetPerformanceMetrics` | Performance analytics |
| `GetHealth` | Management health |
