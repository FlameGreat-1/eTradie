package journal

import "time"

// TradeRecord is the PostgreSQL model for a completed or active trade.
// Maps to the TRADE JOURNAL ENTRY schema in TradingSystem_TechSpec_v1_0.txt.
type TradeRecord struct {
	ID              int64     `db:"id"`
	TradeID         string    `db:"trade_id"`
	Symbol          string    `db:"symbol"`
	Direction       string    `db:"direction"`
	EntryPrice      float64   `db:"entry_price"`
	ExitPrice       float64   `db:"exit_price"`
	StopLoss        float64   `db:"stop_loss"`
	InitialSL       float64   `db:"initial_sl"`
	TP1Price        float64   `db:"tp1_price"`
	TP2Price        float64   `db:"tp2_price"`
	TP3Price        float64   `db:"tp3_price"`
	TotalLotSize    float64   `db:"total_lot_size"`
	GrossPnL        float64   `db:"gross_pnl"`
	RMultiple       float64   `db:"r_multiple"`
	RiskAmount      float64   `db:"risk_amount"`
	RiskPercent     float64   `db:"risk_percent"`
	ConfluenceScore float64   `db:"confluence_score"`
	Grade           string    `db:"grade"`
	SetupType       string    `db:"setup_type"`
	TradingStyle    string    `db:"trading_style"`
	Session         string    `db:"session"`
	ExecutionMode   string    `db:"execution_mode"`
	Slippage        float64   `db:"slippage"`
	Outcome         string    `db:"outcome"` // WIN, LOSS, BREAKEVEN
	Status          string    `db:"status"`  // ACTIVE, CLOSED
	AnalysisID      string    `db:"analysis_id"`
	BrokerOrderID   string    `db:"broker_order_id"`
	OpenedAt        time.Time `db:"opened_at"`
	ClosedAt        *time.Time `db:"closed_at"`
	DurationMinutes int       `db:"duration_minutes"`
	SLAdjustments   int       `db:"sl_adjustments"`
	PartialCloses   int       `db:"partial_closes"`
	CreatedAt       time.Time `db:"created_at"`
	UpdatedAt       time.Time `db:"updated_at"`
}

// TradeEvent is the PostgreSQL model for individual trade events
// (SL moves, partial closes, TP hits, etc.). Every action on a
// managed trade is recorded as an immutable event for full audit.
type TradeEvent struct {
	ID           int64     `db:"id"`
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
