
---

#### Module B Implementation Plan - `src/execution/`

**Language:** Go (blazing fast, zero-GC-pause goroutines, gRPC native)
**Location:** `src/execution/`
**Communication:** gRPC from gateway, gRPC to broker bridge, gRPC to Module C

---

#### What Module B receives (via gRPC from gateway)

The gateway's `ProcessorOutput` already carries everything. Module B receives exactly: `symbol`, `direction`, `entry_zone_low`, `entry_zone_high`, `stop_loss`, `tp1_price/pct`, `tp2_price/pct`, `tp3_price/pct`, `rr_ratio`, `grade`, `risk_percentage`, `trading_style`, `session`, `confluence_score`, `analysis_id`, `confidence`.

#### What Module B does NOT do (belongs elsewhere)

- **Does NOT re-analyze** (Module A's job)
- **Does NOT manage open trades** (Module C's job: trailing, partial closes, BE triggers, EOD protocols, invalidation, journaling)
- **Does NOT repeat gateway guard checks** (news proximity MR-REJECT-001, counter-trend MR-REJECT-006, weekend gap MR-REJECT-008, low liquidity MR-REJECT-009 are already done)

#### Sub-modules and directory structure

```
src/execution/
├── cmd/
│   └── execution/
│       └── main.go                    # gRPC server entry point
├── internal/
│   ├── config/
│   │   └── config.go                  # All configurable params (dashboard-driven)
│   ├── constants/
│   │   └── constants.go               # Enums, thresholds, correlated pair groups
│   ├── models/
│   │   ├── order.go                   # Unified Order Object (the core model)
│   │   ├── execution.go               # ExecutionRequest/Response, validation result
│   │   └── broker.go                  # Broker account info, position, tick models
│   ├── validator/
│   │   ├── validator.go               # Pre-execution validator (orchestrates all checks)
│   │   ├── checks.go                  # Individual check functions (10 checks Module B owns)
│   │   └── result.go                  # ValidationResult with fail reason, check ID
│   ├── sizing/
│   │   └── engine.go                  # Position sizing: lot calculation, floor/ceiling
│   ├── builder/
│   │   └── order_builder.go           # Builds Unified Order Object from validated input + sizing
│   ├── executor/
│   │   ├── executor.go                # Execution orchestrator (limit vs instant dispatch)
│   │   ├── limit.go                   # Limit mode: place order at broker via bridge
│   │   └── instant.go                 # Instant mode: arm Module C goroutine via gRPC
│   ├── broker/
│   │   ├── port.go                    # BrokerPort interface (abstracted)
│   │   ├── mt5/
│   │   │   └── bridge.go             # MT5 gRPC bridge client (calls Python MT5 service)
│   │   └── mock/
│   │       └── broker.go             # Mock broker for testing/demo
│   ├── state/
│   │   ├── manager.go                 # In-memory state: open positions, pending orders, daily P&L
│   │   └── correlations.go            # Correlated pair group lookups
│   ├── audit/
│   │   └── logger.go                  # Immutable execution audit log to PostgreSQL
│   ├── notify/
│   │   └── notifier.go                # Pop-up notification dispatcher (WebSocket push to dashboard)
│   ├── observability/
│   │   ├── logger.go                  # Structured zerolog
│   │   └── metrics.go                 # Prometheus metrics for execution
│   └── server/
│       └── grpc_server.go             # gRPC service implementation (receives from gateway)
├── go.mod
└── go.sum
```

#### B1: Pre-Execution Validator (10 checks Module B owns)

The gateway already handles checks 1, 2, 3 (confluence score, grade, HTF alignment) via the processor + guards. Module B owns these 10:

| # | Check | Action on Fail | Data Source |
|---|-------|---------------|-------------|
| 4 | News lockout (30 min / 45 min scalping) | REJECT | Gateway already does this, but Module B **re-validates** at execution time since time has passed since analysis |
| 5 | Session filter (full, not just Asian) | REJECT | Config (dashboard settings) + current UTC time |
| 6 | No existing position on same pair | REJECT | State manager (in-memory + broker query) |
| 7 | Correlated pair exposure | REJECT | State manager + correlation map |
| 8 | Max concurrent trades | QUEUE | State manager (open position count) |
| 9 | Daily loss limit 3% | LOCK | State manager (daily P&L tracking) |
| 10 | Weekly drawdown 5% | PAUSE | State manager (weekly P&L tracking) |
| 11 | Spread check | REJECT | Live spread from broker bridge |
| 12 | Min R:R for style | REJECT | From ProcessorOutput.rr_ratio + style thresholds |
| 13 | Weekend/day filter (full style-specific cutoffs) | REJECT | Config + current UTC time + trading style |

Validator runs **sequentially, fail-fast**. First failure stops execution.

#### B2: Position Sizing Engine

```
Lot Size = (Live Balance × Risk%) ÷ (SL Distance in pips × Pip Value per lot)
```

- Live balance: fetched from broker via gRPC bridge at execution time
- Risk%: from `ProcessorOutput.RiskPercentage` (already grade-mapped: A+/A=1%, B=0.5%)
- SL distance: `|entry_price - stop_loss|` converted to pips (instrument-specific pip size)
- Pip value: fetched from broker (instrument-specific)
- Floor: 0.01 lots. Below floor = REJECT
- Ceiling: configurable per instrument via dashboard

#### B3: Execution Dispatch

Two modes, dashboard-selectable:

**Limit Mode:**
1. Build order object with entry at midpoint of entry zone (or OTE)
2. Attach SL + TP1/TP2/TP3 to order
3. Place limit order at broker via gRPC bridge
4. Set TTL (style-dependent: intraday=1 session, swing=3 days, etc.)
5. Log `LIMIT_ORDER_PLACED` audit event
6. Return broker order ID to gateway
7. Module C monitors for fill + structure break cancellation

**Instant Mode:**
1. Build order object with watch level at entry zone
2. Send arm request to Module C via gRPC with full order params
3. Module C goroutine watches ticks, fires market order on touch
4. Log `GOROUTINE_ARMED` audit event
5. Return goroutine ID to gateway

#### B4: Broker Port (abstracted interface)

```go
type BrokerPort interface {
    GetAccountInfo(ctx) (*AccountInfo, error)        // Balance, equity, margin
    GetPositions(ctx) ([]Position, error)             // Open positions
    GetPendingOrders(ctx) ([]PendingOrder, error)     // Pending limits
    GetSpread(ctx, symbol) (float64, error)           // Live spread
    GetPipValue(ctx, symbol) (float64, error)         // Pip value for lot calc
    GetPipSize(ctx, symbol) (float64, error)          // Pip size (0.0001 or 0.01)
    PlaceLimitOrder(ctx, order) (*OrderResult, error) // Limit with SL/TP
    PlaceMarketOrder(ctx, order) (*OrderResult, error)// Market with SL/TP
    CancelOrder(ctx, orderID) error                   // Cancel pending
    GetInstrumentInfo(ctx, symbol) (*InstrumentInfo, error) // Min/max lots, etc.
}
```

MT5 bridge is the primary implementation. Mock broker for testing.

#### B5: Execution Audit Log

Every action is an immutable row in `execution_audit_logs` table:

- `VALIDATION_PASSED` / `VALIDATION_REJECTED` (with which check failed)
- `LOT_SIZE_CALCULATED` (with full calculation breakdown)
- `LIMIT_ORDER_PLACED` / `GOROUTINE_ARMED`
- `ORDER_FILLED` / `ORDER_EXPIRED` / `ORDER_CANCELLED`
- All with: timestamp, symbol, direction, analysis_id, trace_id, full order details

#### B6: Notifications

Pop-up notifications via WebSocket push to the React dashboard:
- Order placed, filled, rejected
- Daily limit locked, weekly pause
- System errors

No Telegram. Dashboard-native notifications.

#### B7: State Manager

In-memory (with PostgreSQL backing) tracking of:
- Open positions (count, per-pair, per-correlation-group)
- Pending orders
- Daily realized P&L (resets at 00:00 UTC)
- Weekly realized P&L (resets Monday 00:00 UTC)
- This is what checks 6, 7, 8, 9, 10 query against

#### Execution Flow (end to end)

```
Gateway Router.Route() 
  → processorOutput.TradeValid == true 
  → guards pass 
  → router calls ExecutionPort.Execute(ctx, processorOutput)
    → [gRPC call to Module B service]
      → B1: Validator runs 10 checks sequentially (fail-fast)
      → B2: Sizing engine calculates lot size from live broker balance
      → B3: Order builder constructs Unified Order Object
      → B3: Executor dispatches (limit → broker, instant → arm Module C)
      → B5: Audit log written
      → B6: Notification pushed
      → Return result to gateway
```

#### Proto definition needed

A new proto file `proto/execution/v1/execution.proto` defining:
- `ExecutionService.Execute(ExecuteTradeRequest) returns (ExecuteTradeResponse)`
- `ExecuteTradeRequest` maps from `ProcessorOutput` fields
- `ExecuteTradeResponse` with order ID, status, lot size, risk amount, execution mode, rejection reason if any

---


GOOD!

NOW, FOR THE INSTANT AND LIMIT ORDER IN THE DASHBOARD"

1. USERS SELECT WHICH FROM THE DASHBOARD THE ONE THEY WANT IT AND GETS APPLIED

2. IF THEY SELECT LIMIT ORDER , THE SYSTEM AUTOMATICALLY PLACE THE LIMIT ORDER UPON COMPLETE ANALYSIS AND CONFIRMATION.

3. IF THEY SELECT INSTANT, THE SYSTEM MONITORS THOROUGHLY EVERY MINI SECS WAITING FOR THE EXACT CONFIRMATION PATTERN DETECT EARLEIR TO HAPPEN AROUND THE PRICE TARGET THEN PLACES ORDER INSTANTLY WHEN THAT HAPPENS



NOW WE ARE GOING TO START THE IMPLEMENTATION
PLEASE NOTE: ENSURE YOU FOLLOW THIS INSTRUCTIONS BELOW ORDERLY EXACTLY AS I GAVE IT:


1.   EXAMINE THE INSTRUCTIONS.md THOROUGHLY FROM THE BEGINNING TO THE END AND MAKE SURE YOU STRICTLY AND CAREFULLY FOLLOW ALL THE DIRECTIVES AND INSTRUCTIONS.

BECAUSE THIS IS VERY CRITICAL INFRASTRUCTURE AND YOU MUST LEVERAGE COMBINED EXPERTISE AND EXECUTE WITH 100% PRECISION AND ACCURACY FOLLOWING BEST PRACTICES, ENTERPRISE GRADE AND INDUSTRY STANDARD.

