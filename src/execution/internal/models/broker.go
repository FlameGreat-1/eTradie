package models

import "time"

// AccountInfo holds live broker account state.
//
// JSON tags match the dashboard's expected field names
// (balance, equity, margin, margin_free, currency). Without these
// tags, Go's default encoder emits the PascalCase Go field names
// ("Balance", "Equity", ...) and the dashboard displays NaN because
// account.balance etc. are undefined on the wire.
type AccountInfo struct {
	Balance    float64 `json:"balance"`
	Equity     float64 `json:"equity"`
	Margin     float64 `json:"margin"`
	FreeMargin float64 `json:"margin_free"`
	Currency   string  `json:"currency"`
}

// Position represents an open broker position.
//
// JSON tags use the MT5-style field names expected by the dashboard
// (price_open, sl, tp, volume, profit). Without these tags, Go emits
// PascalCase names and the dashboard renders NaN / empty values.
type Position struct {
	Symbol        string    `json:"symbol"`
	Direction     string    `json:"direction"`
	EntryPrice    float64   `json:"price_open"`
	CurrentPrice  float64   `json:"price_current"`
	StopLoss      float64   `json:"sl"`
	TakeProfit    float64   `json:"tp"`
	LotSize       float64   `json:"volume"`
	UnrealizedPnL float64   `json:"profit"`
	OrderID       string    `json:"order_id"`
	AnalysisID    string    `json:"analysis_id"`
	TradingStyle  string    `json:"trading_style"`
	OpenTime      time.Time `json:"open_time"`
}

// BrokerPendingOrder represents a pending limit order at the broker.
//
// JSON tags match the dashboard's expected field names. Same rationale
// as Position above — without tags the dashboard shows $0 / '-' for
// every column except Symbol.
type BrokerPendingOrder struct {
	Symbol        string    `json:"symbol"`
	Direction     string    `json:"direction"`
	EntryPrice    float64   `json:"price"`
	StopLoss      float64   `json:"sl"`
	TakeProfit    float64   `json:"tp"`
	LotSize       float64   `json:"volume"`
	OrderID       string    `json:"order_id"`
	AnalysisID    string    `json:"analysis_id"`
	ExecutionMode string    `json:"execution_mode"`
	Status        string    `json:"status"`
	CreatedAt     time.Time `json:"created_at"`
}

// InstrumentInfo holds broker-provided instrument metadata.
type InstrumentInfo struct {
	Symbol       string
	PipSize      float64 // 0.0001 for most FX, 0.01 for JPY pairs and metals
	PipValue     float64 // Dollar value per pip per standard lot
	MinLotSize   float64
	MaxLotSize   float64
	LotStep      float64 // e.g. 0.01
	Spread       float64 // Current spread in price units
	AvgSpread    float64 // Average spread for normality check
	Digits       int32
	ContractSize float64
}

// OrderPlacement is the request sent to the broker to place an order.
type OrderPlacement struct {
	Symbol     string
	Direction  string  // "BUY" or "SELL"
	OrderType  string  // "LIMIT" or "MARKET"
	Price      float64 // Entry price (limit) or 0 (market)
	StopLoss   float64
	TakeProfit float64 // TP1 for initial order; partials managed by Module C
	LotSize    float64
	Comment    string // analysis_id for traceability
}

// OrderResult is the broker's response after order placement.
type OrderResult struct {
	BrokerOrderID string
	FillPrice     float64
	Slippage      float64
	Status        string // "PLACED", "FILLED", "REJECTED"
	ErrorMessage  string
}

// TickPrice holds the latest bid/ask for a symbol. Used by the
// watcher engine to detect when price enters the POI zone.
type TickPrice struct {
	Bid       float64
	Ask       float64
	Timestamp time.Time
}
