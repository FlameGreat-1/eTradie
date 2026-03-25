# DASHBOARD INTEGRATION AUDIT

> Only what needs to be integrated into the dashboard.
> No internal system-to-system endpoints. No automatic pipelines.
> Organized by where each item belongs in the dashboard UI.

---

## 1. SYSTEM HEALTH & STATUS

Top bar / header area showing whether the system is alive and connected.

### 1.1 Gateway Health
- **Endpoint:** `GET /api/v1/health` (Gateway HTTP, port 8080)
- **Response:**
  - `status` (string): `"ok"` or `"degraded"`
  - `redis_connected` (bool)
  - `engine_connected` (bool)
  - `active_cycles` (int): Currently running analysis cycles
- **Dashboard use:** Health indicator badge in header. Green/yellow/red based on status. Returns 503 when degraded.

### 1.2 Gateway Readiness (REST)
- **Endpoint:** `GET /readiness` (Gateway HTTP, port 8080)
- **Response:** `{"status": "ready"|"not_ready", "redis": bool, "engine": bool}`
- **Dashboard use:** Startup readiness check. Shows which dependencies are connected.

### 1.3 RAG Knowledge Base Health
- **Endpoint:** `GET /health/rag` (Engine HTTP, port 8000)
- **Response:**
  - `status`: `"healthy"`, `"degraded"`, or `"disabled"`
  - `vectorstore_connected` (bool)
  - `database_connected` (bool)
  - `embedding_ready` (bool)
  - `documents_count` (int)
  - `scenarios_count` (int)
- **Dashboard use:** Knowledge base status card. Shows if the AI has access to the trading rulebook.

### 1.4 Management Service Health
- **Endpoint:** `GET /health` (Management HTTP, port 8083)
- **Response:** `{"status": "ok"}`
- **Dashboard use:** Trade management liveness indicator.

### 1.5 Execution Health
- **Endpoint:** `GET /health` (Execution HTTP, port 8080)
- **Response:** `{"status": "ok"}`
- **Dashboard use:** Execution engine liveness indicator.

---

## 2. GATEWAY CONFIGURATION

Settings panel where the user views and adjusts runtime config.

### 2.1 Get Gateway Config
- **Endpoint:** `GET /api/v1/config` (Gateway HTTP, port 8080)
- **Response:**
  - `enabled` (bool): Master switch
  - `cycle_interval_seconds` (int): How often analysis runs (default 14400 = 4 hours)
  - `cycle_timeout_seconds` (int): Max time per cycle (default 300)
  - `max_concurrent_symbols` (int): Parallel symbol limit (default 4)
  - `ta_cache_ttl_seconds` (int): TA cache duration (default 300)
  - `macro_cache_ttl_seconds` (int): Macro cache duration (default 600)
  - `max_cycle_retries` (int): Retry count on failure (default 1)
  - `default_symbols` (string[]): Config-defined default symbols
  - `active_symbols` (string[]): Currently active symbols
  - `active_symbols_source` (string): `"redis"` or `"gateway_config"`
  - `execution_enabled` (bool): Whether trade execution is on
- **Dashboard use:** Settings panel. Display all current config values.

### 2.2 Set Cycle Interval
- **Endpoint:** `PUT /api/v1/config/interval` (Gateway HTTP, port 8080)
- **Request Body:** `{"interval_seconds": 7200}`
- **Validation:** Must be 60-86400
- **Response:** `{"success": true, "current_interval_seconds": 7200, "message": "..."}`
- **Dashboard use:** Slider or input field to change how often analysis runs. Takes effect immediately. Persisted in Redis (survives restarts).

---

## 3. SYMBOL MANAGEMENT

Symbol selector panel where the user chooses which currency pairs to analyze.

### 3.1 Get Active Symbols
- **Endpoint:** `GET /api/v1/symbols` (Gateway HTTP, port 8080)
- **Response:** `{"symbols": [...], "source": "redis"}`
- **Dashboard use:** Shows which pairs are currently being analyzed.

### 3.2 Set Active Symbols
- **Endpoint:** `PUT /api/v1/symbols` (Gateway HTTP, port 8080)
- **Request Body:** `{"symbols": ["EURUSD", "GBPUSD", "XAUUSD"]}`
- **Response:** `{"success": true, "active_symbols": [...]}`
- **Dashboard use:** Multi-select to add/remove trading pairs. Persisted in Redis.

### 3.3 Reset Active Symbols
- **Endpoint:** `POST /api/v1/symbols/reset` (Gateway HTTP, port 8080)
- **Request Body:** None required
- **Response:** `{"success": true, "active_symbols": [...]}`
- **Dashboard use:** "Reset to Defaults" button. Restores the 8 default pairs (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD, XAUUSD).

---

## 4. ANALYSIS CYCLE CONTROL

Controls for triggering and monitoring analysis cycles.

### 4.1 Run Cycle On Demand
- **Endpoint:** `POST /api/v1/cycle/run` (Gateway HTTP, port 8080)
- **Request Body:** `{"symbols": ["EURUSD"], "trace_id": "optional"}` (body is optional; if empty or no symbols, uses active symbols)
- **Response:** `{"outputs": [...]}`
  - Each output:
    - `cycle_status`: `RUNNING`, `COMPLETED`, `FAILED`, `TIMED_OUT`
    - `cycle_outcome`: `TRADE_APPROVED`, `NO_SETUP`, `REJECTED_BY_GUARD`, `INSUFFICIENT_DATA`, `PROCESSOR_ERROR`, `PIPELINE_ERROR`
    - `phase_reached`: Which pipeline stage was reached
    - `symbol`, `duration_ms`, `trace_id`, `error`, `error_stage`
    - `processor_output`: Full LLM decision object
    - `guard_result`: Guard evaluation result object
    - `execution_result`: Execution response object
- **Note:** This is a long-running request (can take up to cycle_timeout_seconds, default 300s). The server WriteTimeout is set to 120s to accommodate.
- **Dashboard use:** "Run Now" button. User triggers immediate analysis without waiting for the 4-hour scheduler. Shows results when complete.

### 4.2 Re-run Analysis (Single Symbol)
- **Endpoint:** `POST /api/analysis/rerun?symbol=EURUSD&trace_id=xxx` (Engine HTTP, port 8000)
- **Response:** `{"status": "completed", "symbol": str, "result": {...}}`
- **Dashboard use:** Per-symbol "Re-analyze" button. Runs the full TA + Macro + RAG + Processor pipeline for one symbol. Does NOT go through guards or execution (analysis only).

---

## 5. ANALYSIS HISTORY & DETAIL

View past and current analysis results from the AI processor.

### 5.1 Latest Analyses
- **Endpoint:** `GET /api/analysis/latest?pair=EURUSD&limit=20` (Engine HTTP, port 8000)
- **Response:** `{"analyses": [...], "count": int}`
- **Each analysis:**
  - `analysis_id`, `pair`, `direction` (LONG/SHORT)
  - `setup_grade` (A+, A, B, REJECT)
  - `confluence_score`, `confidence`
  - `proceed_to_module_b` (bool): Whether trade was valid
  - `rr_ratio`, `trading_style`, `session`
  - `llm_provider`, `llm_model`, `status`, `duration_ms`, `created_at`
  - `display.summary`: Human-readable summary
  - `display.analyzed_by`: Provider + model label
- **Dashboard use:** Analysis list/feed. Shows recent AI decisions.

### 5.2 Analysis History (Paginated + Filtered)
- **Endpoint:** `GET /api/analysis/history?pair=&status=&grade=&provider=&since=&until=&offset=0&limit=20` (Engine HTTP, port 8000)
- **Query Params:** `pair`, `status`, `grade`, `provider`, `since` (ISO 8601), `until` (ISO 8601), `offset`, `limit` (max 100)
- **Response:** `{"analyses": [...], "total_count": int, "offset": int, "limit": int}`
- **Dashboard use:** Analysis history table with pagination, filters, and date range.

### 5.3 Analysis Statistics
- **Endpoint:** `GET /api/analysis/stats?pair=&since=&until=` (Engine HTTP, port 8000)
- **Response:** Total count, success rate, grade distribution, average confluence score, average duration, breakdowns by provider and pair.
- **Dashboard use:** Analytics cards/charts. Success rates, grade distribution, performance by AI model.

### 5.4 Analysis Detail
- **Endpoint:** `GET /api/analysis/{analysis_id}` (Engine HTTP, port 8000)
- **Response:** Full analysis detail:
  - All fields from 5.1
  - `display.reasoning`: Full AI reasoning text
  - `display.macro_summary`: Macro environment summary
  - `display.technical_summary`: TA summary
  - `display.trade_plan`: Entry, SL, TP levels
  - `display.confluence_breakdown`: Score breakdown by factor
  - `display.risk_info`: Risk parameters
  - `display.event_warnings`: Upcoming high-impact events
  - `audit.llm_model`, `audit.llm_input_tokens`, `audit.llm_output_tokens`, `audit.llm_duration_ms`
  - `audit.retrieval_strategy`, `audit.retrieval_chunks_count`, `audit.retrieval_coverage`
  - `audit.citations`: Rule citations from knowledge base
  - `audit.validation_passed`, `audit.validation_errors`
- **Dashboard use:** Analysis detail view. Full reasoning, trade plan, audit trail.

---

## 6. LLM CONNECTION MANAGEMENT

User sets up their AI model: selects provider, picks model, enters API key, saves. Persisted in PostgreSQL. Can have multiple saved connections, activate/deactivate/delete them.

### 6.1 Get Available Providers & Models
- **Endpoint:** `GET /api/llm/providers` (Engine HTTP, port 8000)
- **Response:**
  - `providers`: Per-provider model lists with defaults and flags
    - `anthropic`: claude-sonnet-4, claude-opus-4, claude-3.5-sonnet, etc.
    - `openai`: gpt-4o, gpt-4o-mini, o3, o3-mini, o4-mini, etc.
    - `gemini`: gemini-2.5-pro, gemini-2.5-flash, etc.
    - `self_hosted`: Any custom model (requires base_url)
- **Dashboard use:** Populates the provider dropdown and model selector in the "Connect LLM" modal.

### 6.2 List Saved Connections
- **Endpoint:** `GET /api/llm/connections` (Engine HTTP, port 8000)
- **Response:** `{"connections": [...], "count": int}`
- **Each connection:** `id`, `provider`, `model_name`, `base_url`, `temperature`, `max_output_tokens`, `is_active`, `label`, `created_at`, `updated_at`
- **Note:** API keys are never returned in responses (stored encrypted in DB).
- **Dashboard use:** List of saved LLM connections. Shows which one is active.

### 6.3 Get Active Connection
- **Endpoint:** `GET /api/llm/connections/active` (Engine HTTP, port 8000)
- **Response:** `{"connection": {...}}` or `{"connection": null, "message": "No active LLM connection."}`
- **Dashboard use:** Shows the currently active AI model in the header/status bar.

### 6.4 Create New Connection (Connect LLM)
- **Endpoint:** `POST /api/llm/connections` (Engine HTTP, port 8000)
- **Request Body:**
  - `provider` (string, required): `anthropic`, `openai`, `gemini`, `self_hosted`
  - `model_name` (string, required): Model identifier from the provider's list
  - `api_key` (string, required): User's API key for the provider
  - `base_url` (string, optional): Required for `self_hosted` provider
  - `temperature` (float, optional): 0.0-2.0 (default 0.0)
  - `max_output_tokens` (int, optional): 1024-131072 (default 16384)
  - `label` (string, optional): Display name (auto-generated if empty)
  - `activate` (bool, optional): Whether to activate immediately (default true)
- **Response:** `{"id": "...", "provider": "...", "model_name": "...", "is_active": true, "message": "Connection created and activated."}`
- **Behavior:** API key is encrypted and stored in PostgreSQL. If `activate=true`, all other connections are deactivated and the processor is hot-swapped immediately.
- **Dashboard use:** "Connect LLM" modal. User selects provider from dropdown, picks model, enters API key, clicks Save.

### 6.5 Update Connection
- **Endpoint:** `PUT /api/llm/connections/{id}` (Engine HTTP, port 8000)
- **Request Body:** Any subset of: `provider`, `model_name`, `api_key`, `base_url`, `temperature`, `max_output_tokens`, `label`
- **Response:** Updated connection object
- **Dashboard use:** Edit an existing connection (change model, update API key, etc.).

### 6.6 Activate Connection
- **Endpoint:** `POST /api/llm/connections/{id}/activate` (Engine HTTP, port 8000)
- **Response:** `{"is_active": true, "message": "Connection activated. Processor now using anthropic/claude-sonnet-4."}`
- **Behavior:** Deactivates all other connections. Hot-swaps the processor immediately.
- **Dashboard use:** "Use This" button on a saved connection.

### 6.7 Deactivate Connection
- **Endpoint:** `POST /api/llm/connections/{id}/deactivate` (Engine HTTP, port 8000)
- **Response:** `{"is_active": false, "message": "Connection deactivated."}`
- **Dashboard use:** "Deactivate" button. Stops using this connection without deleting it.

### 6.8 Delete Connection
- **Endpoint:** `DELETE /api/llm/connections/{id}` (Engine HTTP, port 8000)
- **Response:** `{"deleted": true, "message": "Connection deleted."}`
- **Dashboard use:** "Delete" button. Permanently removes the saved connection and its encrypted API key.

---

## 7. EXECUTION SETTINGS & STATE

Execution engine settings, positions, orders, and account info.

### 7.1 Get Execution Settings
- **Endpoint:** `GET /api/v1/settings` (Execution HTTP, port 8080)
- **Response:**
  - `execution_mode` (string): `LIMIT` or `INSTANT`
  - `max_concurrent_trades` (int): 1-10 (default 3)
  - `daily_loss_limit_pct` (float): 0.5-10.0 (default 3.0%)
  - `weekly_drawdown_pct` (float): 1.0-20.0 (default 5.0%)
- **Dashboard use:** Execution settings panel. Shows current risk controls.

### 7.2 Update Execution Settings
- **Endpoint:** `PUT /api/v1/settings` (Execution HTTP, port 8080)
- **Request Body:**
  - `execution_mode`: `LIMIT` or `INSTANT`
  - `max_concurrent_trades`: 1-10
  - `daily_loss_limit_pct`: 0.5-10.0
  - `weekly_drawdown_pct`: 1.0-20.0
- **Response:** Updated settings object
- **Dashboard use:** Sliders/inputs for execution mode and risk controls. Changes take effect on the next trade immediately. Persisted in PostgreSQL.

### 7.3 Get Execution State
- **Endpoint:** `GET /api/v1/state` (Execution HTTP, port 8080)
- **Response:**
  - `open_position_count` (int)
  - `pending_order_count` (int)
  - `daily_realized_pnl` (float)
  - `weekly_realized_pnl` (float)
  - `account_balance` (float)
  - `account_equity` (float)
  - `open_positions` (array): Each has `symbol`, `direction`, `entry_price`, `current_price`, `stop_loss`, `lot_size`, `unrealized_pnl`, `order_id`, `analysis_id`, `trading_style`
  - `pending_orders` (array): Each has `symbol`, `direction`, `entry_price`, `stop_loss`, `lot_size`, `order_id`, `analysis_id`, `execution_mode` (LIMIT/INSTANT), `status` (PENDING/WATCHING)
- **Dashboard use:** Execution panel. Live positions table, pending orders table, P&L cards, account balance.

### 7.4 Get Account Info
- **Endpoint:** `GET /api/v1/account` (Execution HTTP, port 8080)
- **Response:** Live broker account (balance, equity, margin, free margin)
- **Dashboard use:** Account balance card.

### 7.5 Cancel Order (User Emergency Action)
- **Endpoint:** `POST /api/v1/orders/cancel` (Execution HTTP, port 8080)
- **Request Body:** `{"order_id": str, "symbol": str, "reason": str}`
- **Response:** `{"success": bool, "status": "CANCELLED"|"NOT_FOUND"}`
- **Dashboard use:** Cancel button on each pending order. User can manually cancel in emergencies. The system also cancels automatically (structure break, TTL expired, etc.) but the user needs this as a manual override.

### 7.6 Pre-Execution Validation Checks (Display Only)
These are the 10 checks the system runs automatically before placing any trade. The dashboard should display which check failed when a trade is rejected.

| Check # | Name | Outcome | What It Checks |
|---|---|---|---|
| 4 | News Lockout | REJECT | No entries within 30min (45min scalping) of high-impact news |
| 5 | Session Filter | REJECT | Only enabled sessions (LONDON_OPEN, LONDON_NY_OVERLAP, NEW_YORK) |
| 6 | Same Pair Position | REJECT | No duplicate positions on same symbol |
| 7 | Correlated Exposure | REJECT | Max 1 trade per correlated pair group |
| 8 | Max Concurrent Trades | REJECT | Max concurrent trades limit (dashboard-configurable) |
| 9 | Daily Loss Limit | LOCK | Locks execution when daily loss exceeds limit (dashboard-configurable) |
| 10 | Weekly Drawdown | PAUSE | Pauses execution when weekly drawdown exceeds limit (dashboard-configurable) |
| 11 | Spread Check | REJECT | Spread must be below threshold |
| 12 | Min R:R | REJECT | Minimum risk-reward by trading style |
| 13 | Weekend/Day Filter | REJECT | No entries Friday after cutoff, no Monday before 07:00 UTC |

### 7.7 Correlated Pair Groups (Display Only)
When check #7 rejects, show which group caused it.

| Group | Pairs |
|---|---|
| USD Quote (risk-on) | EURUSD, GBPUSD, AUDUSD, NZDUSD |
| USD Base | USDJPY, USDCHF, USDCAD |
| JPY Cross | EURJPY, GBPJPY, AUDJPY, NZDJPY |
| EUR Cross | EURGBP, EURAUD, EURNZD, EURCHF, EURCAD |
| Metals | XAUUSD, XAGUSD |

---

## 8. ACTIVE TRADE MANAGEMENT

Trades currently being managed by Module C (break-even, trailing, partial closes).

### 8.1 Get Active Managed Trades
- **Endpoint:** `GET /api/v1/management/trades` (Management HTTP, port 8083)
- **Response:** `{"trades": [...]}`
- **Each trade:**
  - `trade_id`, `symbol`, `direction`
  - `entry_price`, `current_price`, `stop_loss`
  - `tp1_price`, `tp2_price`, `tp3_price`
  - `total_lot_size`, `remaining_lot_size`
  - `unrealized_pnl`, `realized_pnl`
  - `trading_style`, `status` (ACTIVE, BREAKEVEN, TRAILING, CLOSING)
  - `breakeven_set` (bool), `tp1_hit` (bool), `tp2_hit` (bool)
  - `broker_order_id`, `analysis_id`, `opened_at`
- **Dashboard use:** Active trades table. Shows all trades under management with live P&L, SL status, TP progress.

---

## 9. TRADE JOURNAL

Closed trade history.

### 9.1 Get Trade Journal
- **Endpoint:** `GET /api/v1/management/journal?limit=50&offset=0&symbol=EURUSD&style=INTRADAY` (Management HTTP, port 8083)
- **Response:** `{"entries": [...], "total_count": int}`
- **Each entry:**
  - `trade_id`, `symbol`, `direction`
  - `entry_price`, `exit_price`, `stop_loss`, `lot_size`
  - `gross_pnl`, `r_multiple`
  - `confluence_score`, `grade`, `setup_type`
  - `trading_style`, `outcome` (WIN, LOSS, BREAKEVEN)
  - `duration_minutes`, `sl_adjustment_count`, `partial_close_count`
  - `analysis_id`, `opened_at`, `closed_at`
- **Dashboard use:** Trade journal table with pagination and filters (by symbol, by style).

---

## 10. PERFORMANCE ANALYTICS

Trading performance metrics and breakdowns.

### 10.1 Get Performance Metrics
- **Endpoint:** `GET /api/v1/management/metrics?period=ALL_TIME` (Management HTTP, port 8083)
- **Query Params:** `period`: `DAILY`, `WEEKLY`, `MONTHLY`, `ALL_TIME`
- **Response:**
  - `win_rate`, `avg_r_multiple`, `expectancy`
  - `total_trades`, `wins`, `losses`, `breakevens`
  - `total_pnl`
  - `max_consecutive_wins`, `max_consecutive_losses`
  - `max_drawdown_pct`
  - `best_trade_r`, `worst_trade_r`
  - `win_rate_by_symbol` (map)
  - `win_rate_by_style` (map)
  - `win_rate_by_setup` (map)
  - `win_rate_by_session` (map)
- **Dashboard use:** Performance cards and charts. Win rate, expectancy, drawdown, breakdowns by symbol/style/setup/session. Period selector (daily/weekly/monthly/all-time).

---

## 11. REAL-TIME NOTIFICATIONS

Live event stream the dashboard subscribes to.

### 11.1 WebSocket Connection
- **Endpoint:** `ws://host:8080/ws/notifications?severity=WARNING` (Gateway HTTP, port 8080)
- **Query Params:** `severity` (optional): Minimum severity filter. Values: `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Default: all events.
- **Event Payload (JSON):**
  - `id`: Unique event ID
  - `source`: `GATEWAY`, `EXECUTION`, `TRADE_MANAGER`, `SYSTEM`
  - `type`: Event type (see catalog below)
  - `severity`: `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - `timestamp`: RFC3339Nano
  - `symbol` (optional)
  - `direction` (optional)
  - `message`: Human-readable description
  - `trace_id` (optional)
  - `details` (optional): Key-value metadata
- **Dashboard use:** Real-time notification feed/toast system. Every significant event streams here.

### 11.2 Event History (Page Load)
- **Endpoint:** `GET /events/recent?count=50&severity=WARNING` (Gateway HTTP, port 8080)
- **Response:** `{"events": [...], "count": int}`
- **Dashboard use:** Load recent events when the page opens.

### 11.3 Event Catch-up (After Reconnect)
- **Endpoint:** `GET /events/since?last_event_id=xxx&count=100` (Gateway HTTP, port 8080)
- **Response:** `{"events": [...], "count": int}`
- **Dashboard use:** After WebSocket reconnect, fetch events missed during disconnect.

### 11.4 Event Type Catalog

All event types the dashboard should handle/display:

#### Gateway Events (source: GATEWAY)
| Type | Severity | What to Show |
|---|---|---|
| `CYCLE_STARTED` | INFO | "Analysis cycle started" with symbols |
| `CYCLE_COMPLETED` | INFO | "Cycle completed" with outcome and duration |
| `CYCLE_FAILED` | ERROR | "Cycle failed" with error and phase reached |
| `CYCLE_RETRYING` | WARNING | "Retrying" with attempt number |
| `ANALYSIS_COMPLETE` | INFO | "Analysis complete for EURUSD" with trade_valid, grade, confidence |
| `GUARD_REJECTED` | WARNING | "Trade blocked" with which rules rejected |
| `GUARD_WARNING` | WARNING | "Guard warning" with flagged concern |
| `TRADE_ROUTED` | INFO | "Trade sent to execution" with symbol, direction, grade |
| `INTERVAL_CHANGED` | INFO | "Cycle interval changed" with old/new values |
| `SYMBOLS_CHANGED` | INFO | "Active symbols changed" with old/new lists |
| `TA_COLLECTION_FAILED` | ERROR | "TA failed" with error |
| `MACRO_COLLECTION_FAILED` | ERROR | "Macro failed" with error |
| `RAG_RETRIEVAL_FAILED` | ERROR | "RAG failed" with error |
| `PROCESSOR_LLM_FAILED` | ERROR | "AI processor failed" with error |
| `EXECUTION_CALL_FAILED` | ERROR | "Execution call failed" with error |
| `EXECUTION_HANDOFF` | INFO | "Trade filled, handed to management" |
| `MANAGEMENT_HANDOFF_FAILED` | ERROR | "Failed to hand off to management" |

#### Execution Events (source: EXECUTION)
| Type | Severity | What to Show |
|---|---|---|
| `ORDER_PLACED` | INFO | "Limit order placed" or "Watcher armed" with details |
| `ORDER_FILLED` | INFO | "Order filled" with price and lot size |
| `ORDER_CANCELLED` | INFO | "Order cancelled" with reason |
| `ORDER_EXPIRED` | WARNING | "Order expired" (TTL) |
| `EXECUTION_REJECTED` | WARNING | "Trade rejected" with which check failed |
| `WATCHER_ARMED` | INFO | "Price watcher started" for instant mode |
| `WATCHER_TRIGGERED` | INFO | "Price entered zone" |
| `DAILY_LIMIT_LOCKED` | CRITICAL | "Execution locked - daily loss limit reached" |
| `WEEKLY_PAUSED` | CRITICAL | "Execution paused - weekly drawdown limit reached" |
| `SIZING_CALCULATED` | INFO | "Position size calculated" with lot size |
| `EXECUTION_ERROR` | ERROR | "Execution error" with details |
| `EXECUTION_MODE_CHANGED` | INFO | "Mode switched" LIMIT/INSTANT |
| `SETTINGS_UPDATED` | INFO | "Settings updated" with new values |

#### Trade Manager Events (source: TRADE_MANAGER)
| Type | Severity | What to Show |
|---|---|---|
| `TRAILING_SL_MOVED` | INFO | "Trailing stop adjusted" with new SL |
| `PARTIAL_CLOSE` | INFO | "Partial close" at TP level with P&L |
| `BREAKEVEN_SET` | INFO | "Stop loss moved to break-even" |
| `TRADE_CLOSED` | INFO | "Trade closed" with outcome and P&L |
| `PERFORMANCE_REPORT` | INFO | Periodic performance summary |

#### System Events (source: SYSTEM)
| Type | Severity | What to Show |
|---|---|---|
| `SERVICE_STARTED` | INFO | "Gateway started" / "Service started" |
| `SERVICE_STOPPING` | INFO | "Shutting down" |
| `BROKER_DISCONNECTED` | ERROR | "Broker connection lost" (red alert) |
| `BROKER_RECONNECTED` | INFO | "Broker connection restored" |

---

## 12. GUARD RULES (Display Only)

Post-processor safety rules. The dashboard shows these when a trade is rejected or warned.

| Rule ID | Name | Type | What It Does |
|---|---|---|---|
| `MR-REJECT-001` | News Proximity | REJECT | Blocks entries within 30 minutes of high-impact news |
| `MR-REJECT-002` | Session Restriction | REJECT | Blocks non-Asian pairs during Asian session (00:00-07:00 UTC) |
| `MR-REJECT-006` | Counter-Trend No CHoCH | REJECT/WARN | Counter-trend trades need CHoCH. WARN if exists, REJECT if not |
| `MR-REJECT-008` | Weekend Gap Risk | REJECT | Blocks entries after Friday 20:00 UTC and on weekends |
| `MR-REJECT-009` | Low Liquidity Hours | WARN | Warning during 21:00-01:00 UTC |

---

## 13. PIPELINE PHASES (Display Only)

When showing cycle progress or errors, these are the phases:

| Phase | Description |
|---|---|
| `INITIALIZING` | Cycle starting |
| `COLLECTING_PARALLEL` | TA + Macro running in parallel |
| `BUILDING_QUERY` | RAG query construction |
| `RETRIEVING_RAG` | Knowledge base retrieval |
| `ASSEMBLING_CONTEXT` | Combining TA + Macro + RAG |
| `PROCESSING_LLM` | AI decision making |
| `EVALUATING_GUARDS` | Safety guard checks |
| `ROUTING_DECISION` | Routing to execution |
| `COMPLETED` | Done |
| `FAILED` | Failed |

---

## 15. SERVICE PORTS

| Service | Protocol | Port | What Dashboard Connects To |
|---|---|---|---|
| Gateway HTTP | HTTP + WebSocket | 8080 | Health, readiness, metrics, WebSocket notifications, event history |
| Gateway gRPC | gRPC | 50052 | RunCycle, symbols, config, interval, health |
| Engine HTTP | HTTP | 8000 | Analysis history/detail/stats, rerun, AI model config, RAG health |
| Execution HTTP | HTTP | 8080 | Settings, state, account, cancel orders |
| Management HTTP | HTTP | 8083 | Active trades, journal, performance metrics |

---

## 16. COMPLETE DASHBOARD ENDPOINT SUMMARY

### Gateway HTTP (port 8080)
| Method | Path | Dashboard Action |
|---|---|---|
| POST | `/api/v1/cycle/run` | "Run Now" button |
| GET | `/api/v1/symbols` | Load current symbols |
| PUT | `/api/v1/symbols` | Update symbol selection |
| POST | `/api/v1/symbols/reset` | "Reset to Defaults" button |
| GET | `/api/v1/config` | Settings panel display |
| PUT | `/api/v1/config/interval` | Change cycle interval |
| GET | `/api/v1/health` | Detailed health status |
| GET | `/readiness` | Startup readiness check |
| WS | `/ws/notifications` | Real-time event stream |
| GET | `/events/recent` | Load event history on page open |
| GET | `/events/since` | Catch up after reconnect |

### Engine HTTP (port 8000)
| Method | Path | Dashboard Action |
|---|---|---|
| GET | `/health/rag` | RAG health status |
| GET | `/api/analysis/latest` | Recent analyses list |
| GET | `/api/analysis/history` | Analysis history with filters |
| GET | `/api/analysis/stats` | Analysis statistics |
| GET | `/api/analysis/{id}` | Analysis detail view |
| POST | `/api/analysis/rerun` | Re-run analysis for a symbol |
| GET | `/api/llm/providers` | Available LLM providers & models |
| GET | `/api/llm/connections` | List saved LLM connections |
| GET | `/api/llm/connections/active` | Get active LLM connection |
| POST | `/api/llm/connections` | Create new LLM connection |
| PUT | `/api/llm/connections/{id}` | Update LLM connection |
| POST | `/api/llm/connections/{id}/activate` | Activate LLM connection |
| POST | `/api/llm/connections/{id}/deactivate` | Deactivate LLM connection |
| DELETE | `/api/llm/connections/{id}` | Delete LLM connection |
| POST | `/api/broker/connections` | Create broker connection (EA or MetaAPI) |
| GET | `/api/broker/connections` | List all broker connections |
| GET | `/api/broker/connections/active` | Get active broker connection |
| GET | `/api/broker/connections/{id}` | Get broker connection by ID |
| PUT | `/api/broker/connections/{id}` | Update broker connection |
| POST | `/api/broker/connections/{id}/activate` | Activate broker connection |
| POST | `/api/broker/connections/{id}/deactivate` | Deactivate broker connection |
| POST | `/api/broker/connections/{id}/set-primary` | Set broker as primary |
| POST | `/api/broker/connections/{id}/test` | Test broker connection health |
| DELETE | `/api/broker/connections/{id}` | Delete broker connection |

### Execution HTTP (port 8080)
| Method | Path | Dashboard Action |
|---|---|---|
| GET | `/api/v1/settings` | Get execution settings |
| PUT | `/api/v1/settings` | Update execution settings |
| GET | `/api/v1/state` | Positions, orders, P&L |
| GET | `/api/v1/account` | Account balance |
| POST | `/api/v1/orders/cancel` | Cancel pending order |

### Management HTTP (port 8083)
| Method | Path | Dashboard Action |
|---|---|---|
| GET | `/api/v1/management/trades` | Active managed trades |
| GET | `/api/v1/management/journal` | Closed trade journal |
| GET | `/api/v1/management/metrics` | Performance analytics |
