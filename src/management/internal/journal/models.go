package journal

import "time"

// Trade provenance values for the management_trades.origin column.
// origin is a TYPED discriminator, distinct from Grade (which is the
// LLM setup-quality label). The trading-plan Daily Execution Journal
// auto-populate selects on origin, never on a Grade string.
const (
	// OriginSystem is a trade the platform executed end-to-end
	// (gateway -> execution -> RegisterFilledTrade).
	OriginSystem = "SYSTEM"
	// OriginManualReconciled is a live broker position the trader
	// opened manually and the reconciler adopted with REAL
	// entry/SL/TP/volume, then managed to a real close. This is the
	// ONLY origin the manual journal view consumes.
	OriginManualReconciled = "MANUAL_RECONCILED"
	// OriginManualRestored is a rough history-import row from the
	// broker deal history (entry/SL/TP are zeroed placeholders). Used
	// by the PnL calendar only; EXCLUDED from the journal view.
	OriginManualRestored = "MANUAL_RESTORED"
)

// TradeRecord is the PostgreSQL model for a completed or active trade.
// Maps to the TRADE JOURNAL ENTRY schema. Every record is owned by a
// specific user (multi-tenant isolation via user_id).
type TradeRecord struct {
	ID               int64   `db:"id"`
	UserID           string  `db:"user_id"` // Owner of this trade (auth user ID)
	TradeID          string  `db:"trade_id"`
	Symbol           string  `db:"symbol"`
	Direction        string  `db:"direction"`
	EntryPrice       float64 `db:"entry_price"`
	ExitPrice        float64 `db:"exit_price"`
	StopLoss         float64 `db:"stop_loss"`
	InitialSL        float64 `db:"initial_sl"`
	TP1Price         float64 `db:"tp1_price"`
	TP1Pct           int32   `db:"tp1_pct"`
	TP2Price         float64 `db:"tp2_price"`
	TP2Pct           int32   `db:"tp2_pct"`
	TP3Price         float64 `db:"tp3_price"`
	TP3Pct           int32   `db:"tp3_pct"`
	TotalLotSize     float64 `db:"total_lot_size"`
	RemainingLotSize float64 `db:"remaining_lot_size"`
	GrossPnL         float64 `db:"gross_pnl"`
	RMultiple        float64 `db:"r_multiple"`
	RiskAmount       float64 `db:"risk_amount"`
	RiskPercent      float64 `db:"risk_percent"`
	RRRatio          float64 `db:"rr_ratio"`
	Point            float64 `db:"point"`
	Digits           int     `db:"digits"`
	// Origin is the typed provenance discriminator (see OriginSystem /
	// OriginManualReconciled / OriginManualRestored). It is the
	// authoritative manual-vs-system signal for the trading-plan
	// journal auto-populate; never derive provenance from Grade.
	Origin          string     `db:"origin"`
	TP1Hit          bool       `db:"tp1_hit"`
	TP2Hit          bool       `db:"tp2_hit"`
	TP3Hit          bool       `db:"tp3_hit"`
	BreakevenSet    bool       `db:"breakeven_set"`
	ConfluenceScore float64    `db:"confluence_score"`
	Grade           string     `db:"grade"`
	SetupType       string     `db:"setup_type"`
	TradingStyle    string     `db:"trading_style"`
	Session         string     `db:"session"`
	ExecutionMode   string     `db:"execution_mode"`
	Slippage        float64    `db:"slippage"`
	Outcome         string     `db:"outcome"` // WIN, LOSS, BREAKEVEN
	Status          string     `db:"status"`  // ACTIVE, CLOSED
	AnalysisID      string     `db:"analysis_id"`
	BrokerOrderID   string     `db:"broker_order_id"`
	OpenedAt        time.Time  `db:"opened_at"`
	ClosedAt        *time.Time `db:"closed_at"`
	DurationMinutes int        `db:"duration_minutes"`
	SLAdjustments   int        `db:"sl_adjustments"`
	PartialCloses   int        `db:"partial_closes"`
	CreatedAt       time.Time  `db:"created_at"`
	UpdatedAt       time.Time  `db:"updated_at"`
}

// TradeEvent is the PostgreSQL model for individual trade events
// (SL moves, partial closes, TP hits, etc.). Every action on a
// managed trade is recorded as an immutable event for full audit.
// Events inherit the user_id from their parent trade for tenant isolation.
type TradeEvent struct {
	ID           int64     `db:"id"`
	UserID       string    `db:"user_id"` // Owner of this event (auth user ID)
	TradeID      string    `db:"trade_id"`
	EventType    string    `db:"event_type"`
	Symbol       string    `db:"symbol"`
	Price        float64   `db:"price"`
	NewSL        float64   `db:"new_sl"`
	ClosedVolume float64   `db:"closed_volume"`
	RealizedPnL  float64   `db:"realized_pnl"`
	RMultiple    float64   `db:"r_multiple"`
	Reason       string    `db:"reason"`
	Timestamp    time.Time `db:"timestamp"`
}
