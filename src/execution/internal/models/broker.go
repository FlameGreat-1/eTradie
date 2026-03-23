package models

import "time"

// AccountInfo holds live broker account state.
type AccountInfo struct {
	Balance    float64
	Equity     float64
	Margin     float64
	FreeMargin float64
	Currency   string
}

// Position represents an open broker position.
type Position struct {
	Symbol        string
	Direction     string
	EntryPrice    float64
	CurrentPrice  float64
	StopLoss      float64
	TakeProfit    float64
	LotSize       float64
	UnrealizedPnL float64
	OrderID       string
	AnalysisID    string
	TradingStyle  string
	OpenTime      time.Time
}

// BrokerPendingOrder represents a pending limit order at the broker.
type BrokerPendingOrder struct {
	Symbol        string
	Direction     string
	EntryPrice    float64
	StopLoss      float64
	TakeProfit    float64
	LotSize       float64
	OrderID       string
	AnalysisID    string
	ExecutionMode string
	Status        string
	CreatedAt     time.Time
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
