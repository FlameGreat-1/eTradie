# Dashboard Integration

> Endpoint reference for the eTradie dashboard frontend. This document
> is the contract between the dashboard application and the platform
> (gateway + engine + execution + management). Previously committed at
> the repo root as `AUDIT.md`; renamed and moved here because the
> previous title misrepresented the content as a deployment audit.

---

## 1. AUTHENTICATION & PROFILE

User login, registration, and profile management for the frontend app.

### 1.1 Login & Tokens
- **Endpoint:** `POST /auth/login` (Gateway)
- **Request Body:** `username`, `password`
- **Response:** JWT Access Token + Refresh Token mapping.
- **Dashboard use:** Login page. Handles initial authentication.

### 1.2 Registration
- **Endpoint:** `POST /auth/register` (Gateway)
- **Request Body:** `username`, `email`, `password`
- **Dashboard use:** Sign-up page for new traders. Auto-logs the user in upon success.

### 1.3 Session Management
- **Endpoints:**
  - `POST /auth/refresh`: Silently refreshes expired access tokens.
  - `POST /auth/logout`: Revokes current active session.
  - `POST /auth/logout-all`: Revokes all devices logged into the account.
- **Dashboard use:** Interceptors for background token refresh, user logout buttons.

### 1.4 Profile Management
- **Endpoints:**
  - `GET /auth/me`: Loads current logged-in user details (ID, email, role, etc).
  - `PUT /auth/me/password`: Changes the user password (requires current password).
- **Dashboard use:** "My Profile" settings page.

---

## 2. SYSTEM CONFIGURATION

Settings panel where the user views and adjusts specific system runtime configurations.

### 2.1 Get System Config
- **Endpoint:** `GET /api/v1/config` (Gateway)
- **Dashboard use:** Settings panel to display active system configurations (Max limits, default symbols, current execution active toggle).

### 2.2 Set Cycle Interval
- **Endpoint:** `PUT /api/v1/config/interval` (Gateway)
- **Request Body:** `{"interval_seconds": 7200}`
- **Dashboard use:** Slider or input field to change how often automatic analysis runs.

---

## 3. SYMBOL MANAGEMENT

Symbol selector panel where the user chooses which currency pairs to analyze.

### 3.1 Handle Standard Symbols
- **Endpoints:**
  - `GET /api/v1/symbols`: Load tracked pairs.
  - `PUT /api/v1/symbols`: Save updated tracked pairs.
  - `POST /api/v1/symbols/reset`: Revert to standard system defaults.
- **Dashboard use:** Symbols configuration tab. Multi-select checkboxes to allow/disallow pairs.

---

## 4. ANALYSIS CYCLE CONTROL

Controls for triggering and monitoring analysis cycles dynamically without waiting for cron schedule.

### 4.1 On-Demand Generation
- **Endpoints:**
  - `POST /api/v1/cycle/run` (Gateway): Runs full orchestrator process on select pairs or all active pairs and fires to broker depending on guards.
  - `POST /api/analysis/rerun?symbol=EURUSD` (Engine): Re-analyzes a single explicitly requested symbol offline (no broker execution).
- **Dashboard use:** "Run full scan now" bulk button vs Individual "Re-analyze" chart button.

---

## 5. ANALYSIS HISTORY & DETAIL

View past and current analysis results from the AI processor.

### 5.1 Latest & History
- **Endpoints:**
  - `GET /api/analysis/latest?limit=20` (Engine): Fetches the immediate recent feed.
  - `GET /api/analysis/history` (Engine): Full paginated breakdown with `since`, `until`, `grade`, `status` filters.
  - `GET /api/analysis/stats` (Engine): Dashboard analytics aggregator for total/success counts over periods.
- **Dashboard use:** Analytics dashboard, recent signals feed, success rate widgets.

### 5.2 Deep Dive detail
- **Endpoint:** `GET /api/analysis/{analysis_id}` (Engine)
- **Dashboard use:** Detailed modal popup when clicking a specific AI Trade Plan signal (Shows TA/Macro summaries, grade, reasoning, stop loss placements).

---

## 6. LLM CONNECTION MANAGEMENT

Users bring their own keys. Can have multiple saved AI connections (Anthropic, OpenAI, Self-Hosted Local).

### 6.1 Provider Support Lookup
- **Endpoint:** `GET /api/llm/providers` (Engine)
- **Dashboard use:** Populates the provider dropdown/model strings exactly as the backend expects.

### 6.2 Connection Management
- **Endpoints:**
  - `GET /api/llm/connections` (Engine): List saved profiles.
  - `GET /api/llm/connections/active` (Engine): Identify current in-use profile.
  - `POST /api/llm/connections` (Engine): Add a new AI connection configuration.
  - `PUT /api/llm/connections/{id}` (Engine): Update Key/Temperature settings.
  - `POST /api/llm/connections/{id}/activate`: Switch processing to this connection immediately.
  - `POST /api/llm/connections/{id}/deactivate`: Pause a connection.
  - `DELETE /api/llm/connections/{id}`: Delete an AI key permanently.
- **Dashboard use:** "AI Engine Settings" integrations page.

---

## 7. BROKER CONNECTION MANAGEMENT

User sets up MT4/MT5 connections. The platform dynamically provisions a MetaTrader container via Kubernetes for the selected platform, or supports manual local EA connection as a fallback.

### 7.1 Connection Management
- **Endpoints:**
  - `POST /api/broker/connections` (Engine): Create a new connection configuration (requires `platform="mt4"` or `platform="mt5"`).
  - `GET /api/broker/connections` (Engine): See all saved broker credentials.
  - `GET /api/broker/connections/active` (Engine): Check active used broker.
  - `PUT /api/broker/connections/{id}`: Modify terminal details.
  - `POST /api/broker/connections/{id}/activate`: Spawns a dedicated Kubernetes Pod (`etradie-mt-node`) for this connection and routes all Engine traffic to it.
  - `POST /api/broker/connections/{id}/deactivate`: Terminates the Kubernetes Pod.
  - `POST /api/broker/connections/{id}/test`: Pre-ping broker API endpoint to see if the terminal is online.
  - `DELETE /api/broker/connections/{id}`: Drop the connection entirely.
- **Dashboard use:** "My Broker" integration page.

---

## 8. EXECUTION SETTINGS & STATE

Execution risk settings, positions, orders, and account financials.

### 8.1 Settings & Account Values
- **Endpoints:**
  - `GET /api/v1/settings`: Fetch current max concurrent limit scaling, daily loss %.
  - `PUT /api/v1/settings`: Update limits.
  - `GET /api/v1/account`: Live Broker account equity, balance, used margin.
- **Dashboard use:** Risk Management sub-panel and global top-bar financial balance.

### 8.2 Execution State Tracking
- **Endpoints:**
  - `GET /api/v1/state`: Full snapshot. Current PnL, pending limit orders array, open order structs.
  - `POST /api/v1/orders/cancel`: Emergency user override to kill a pending limit order.
- **Dashboard use:** "Active Positions" and "Pending Limit Trades" tables.

---

## 9. ACTIVE TRADE MANAGEMENT & JOURNAL

Trades currently passed the pending phase and being managed dynamically (trailing stops, partial closures).

### 9.1 Live Active Break-Even Tracking
- **Endpoint:** `GET /api/v1/management/trades` (Management)
- **Dashboard use:** Specific table view that illustrates the progression of live TP partial hits and Breakeven adjustments.

### 9.2 History & Aggregation Statistics
- **Endpoints:**
  - `GET /api/v1/management/journal?limit=50&offset=0` (Management): Historical closed ledger.
  - `GET /api/v1/management/metrics?period=ALL_TIME` (Management): Advanced analytics (expectancy, R:R average, Winrate %).
- **Dashboard use:** Dedicated Trade Journal page and overall Pnl/Winrate chart metric view.

---

## 10. REAL-TIME NOTIFICATIONS

Live event stream updating the layout natively without page refreshes.

### 10.1 WebSockets & Feeds
- **Endpoints:**
  - `WS ws://gateway/ws/notifications?severity=WARNING`: Main socket. Pushes events directly to the browser.
  - `GET /events/recent`: Load previous unread events initially while drawing the layout.
  - `GET /events/since`: Used on WS reconnect dropouts to backfill missing notifications without downloading massive payloads.
- **Dashboard use:** Bottom left notification toaster, notification slide-over tab, and header context badges.

---

## 11. ADMIN PANEL (SYSTEM LEVEL MANAGEMENT)

Privileged endpoints specifically for administrative (superuser) users. Regular users cannot access these.

### 11.1 Platform User Management
- **Endpoints:**
  - `GET /auth/admin/users`: See all platform users.
  - `POST /auth/admin/users`: Pre-register/spawn users via email manual insert.
  - `PUT /auth/admin/users/{id}/activate`: Lift ban/unpause accounts.
  - `PUT /auth/admin/users/{id}/deactivate`: Freeze accounts.
- **Dashboard use:** Admin "Users" Datatable.

### 11.2 Platform Global AI Fallback Settings
- **Endpoints:**
  - `GET /api/processor/models`: List raw available system model list.
  - `GET /api/processor/config`: Global configured default fallback model for core services.
  - `PUT /api/processor/config`: Modify the base system fallback model parameters without impacting user-tied keys.
- **Dashboard use:** Admin "System Environment" Core settings pane.
