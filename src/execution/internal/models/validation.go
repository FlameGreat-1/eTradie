package models

import "github.com/flamegreat-1/etradie/src/execution/internal/constants"

// ValidationResult holds the outcome of the pre-execution validator.
// On success, all fields except Passed are zero-valued.
type ValidationResult struct {
	Passed       bool
	FailedCheck  constants.ValidationCheck
	Outcome      constants.ValidationOutcome
	Reason       string
}

// TradeRequest is the internal representation of an incoming execution
// request, parsed from the gRPC ExecuteTradeRequest. Used throughout
// the validation and sizing pipeline.
type TradeRequest struct {
	Symbol          string
	Direction       constants.Direction
	EntryZoneLow    float64
	EntryZoneHigh   float64
	StopLoss        float64
	TP1Price        float64
	TP1Pct          int32
	TP2Price        float64
	TP2Pct          int32
	TP3Price        float64
	TP3Pct          int32
	RRRatio         float64
	Grade           string
	RiskPercentage  float64
	TradingStyle    constants.TradingStyle
	Session         string
	ConfluenceScore float64
	Confidence      float64
	AnalysisID      string
	TraceID         string
	ExecutionMode   string
	LTFConfirmed    bool
	SetupType       string
}

// EntryPrice returns the midpoint of the entry zone (OTE approximation).
func (r *TradeRequest) EntryPrice() float64 {
	return (r.EntryZoneLow + r.EntryZoneHigh) / 2
}

// EntryZoneWidth returns the width of the entry zone in price units.
func (r *TradeRequest) EntryZoneWidth() float64 {
	w := r.EntryZoneHigh - r.EntryZoneLow
	if w < 0 {
		w = -w
	}
	return w
}
