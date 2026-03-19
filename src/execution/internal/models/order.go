package models

import (
	"time"

	"github.com/flamegreat/etradie/src/execution/internal/constants"
)

// Order is the Unified Order Object per TechSpec B.4.
// Built by the order builder after validation and sizing pass.
// Immutable after construction.
type Order struct {
	// Identity.
	OrderID       string
	Symbol        string
	Direction     constants.Direction
	ExecutionMode constants.ExecutionMode

	// Execution levels.
	EntryPrice float64
	StopLoss   float64
	TP1Price   float64
	TP1Pct     int32
	TP2Price   float64
	TP2Pct     int32
	TP3Price   float64
	TP3Pct     int32

	// Risk.
	LotSize        float64
	RiskPercent    float64
	RiskAmount     float64
	RRRatio        float64
	AccountBalance float64
	SLDistancePips float64
	PipValue       float64

	// Context.
	AnalysisID   string
	TradingStyle constants.TradingStyle
	Session      string
	Grade        string
	Confluence   float64
	Confidence   float64
	SetupType    string

	// Limit mode specifics.
	TTLCandles int

	// Instant mode specifics.
	WatcherID          string
	OvershootTolerance float64
	LTFConfirmed       bool

	// Timestamps.
	CreatedAt time.Time

	// Broker reference (populated after placement).
	BrokerOrderID string
}
