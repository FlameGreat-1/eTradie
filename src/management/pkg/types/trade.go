package types

import (
	"sync"
	"time"

	"github.com/flamegreat-1/etradie/src/management/internal/constants"
)

// Trade is the core in-memory representation of a managed trade.
// It is created when the Gateway calls RegisterFilledTrade and
// owned exclusively by Module C until the trade is fully closed.
// All fields are protected by the embedded mutex for concurrent
// access from the monitoring worker goroutine and the gRPC server.
type Trade struct {
	mu sync.RWMutex

	// Identity.
	TradeID       string
	Symbol        string
	Direction     constants.Direction
	BrokerOrderID string
	AnalysisID    string
	TraceID       string

	// Auth context (for background monitoring worker goroutines).
	// Set when the trade is registered via gRPC and used by the worker
	// to make authenticated calls to the Python engine broker endpoints.
	UserID    string // Owner of this trade (auth user ID from JWT "sub" claim)
	AuthToken string // Raw JWT token for authenticated downstream HTTP calls

	// Execution context.
	TradingStyle    constants.TradingStyle
	Grade           string
	Session         string
	SetupType       string
	ExecutionMode   string
	ConfluenceScore float64

	// Prices (SL is mutable — moved by BE/trailing logic).
	EntryPrice float64
	StopLoss   float64 // Current (mutable) stop loss
	InitialSL  float64 // Original SL at entry (immutable)

	// Take profit levels.
	TP1Price float64
	TP1Pct   int32
	TP2Price float64
	TP2Pct   int32
	TP3Price float64
	TP3Pct   int32

	// Risk.
	TotalLotSize     float64 // Original lot size at entry
	RemainingLotSize float64 // Current open volume
	RiskAmount       float64
	RiskPercent      float64
	RRRatio          float64
	Slippage         float64

	// State.
	Status       constants.TradeStatus
	BreakevenSet bool
	TP1Hit       bool
	TP2Hit       bool
	TP3Hit       bool

	// P&L.
	RealizedPnL   float64
	UnrealizedPnL float64
	CurrentPrice  float64
	Swap          float64
	Commission    float64

	// Tracking.
	OpenedAt time.Time
	ClosedAt time.Time
	SLMoves  int // Count of SL adjustments
	Partials int // Count of partial closes
}

// Lock acquires the write lock.
func (t *Trade) Lock() { t.mu.Lock() }

// Unlock releases the write lock.
func (t *Trade) Unlock() { t.mu.Unlock() }

// RLock acquires the read lock.
func (t *Trade) RLock() { t.mu.RLock() }

// RUnlock releases the read lock.
func (t *Trade) RUnlock() { t.mu.RUnlock() }

// IsLong returns true if this is a BUY position.
func (t *Trade) IsLong() bool {
	return t.Direction == constants.DirectionBuy
}

// SLDistanceFromEntry returns the absolute distance from entry to
// initial SL in price units. Used for R-multiple calculations.
func (t *Trade) SLDistanceFromEntry() float64 {
	d := t.EntryPrice - t.InitialSL
	if d < 0 {
		d = -d
	}
	return d
}

// RMultiple calculates the R-multiple for a given P&L amount.
// R = realized_pnl / risk_amount. Positive = profit, negative = loss.
func (t *Trade) RMultiple(pnl float64) float64 {
	if t.RiskAmount == 0 {
		return 0
	}
	return pnl / t.RiskAmount
}

// PriceForCheck returns the relevant price for SL/TP comparison.
// For BUY positions: use bid (the price we sell at to close).
// For SELL positions: use ask (the price we buy at to close).
func (t *Trade) PriceForCheck(bid, ask float64) float64 {
	if t.IsLong() {
		return bid
	}
	return ask
}

// IsSLHit returns true if the current check price has breached the stop loss.
func (t *Trade) IsSLHit(checkPrice float64) bool {
	if t.IsLong() {
		return checkPrice <= t.StopLoss
	}
	return checkPrice >= t.StopLoss
}

// IsTP1Hit returns true if the current check price has reached TP1.
func (t *Trade) IsTP1Hit(checkPrice float64) bool {
	if t.IsLong() {
		return checkPrice >= t.TP1Price
	}
	return checkPrice <= t.TP1Price
}

// IsTP2Hit returns true if the current check price has reached TP2.
func (t *Trade) IsTP2Hit(checkPrice float64) bool {
	if t.IsLong() {
		return checkPrice >= t.TP2Price
	}
	return checkPrice <= t.TP2Price
}

// IsTP3Hit returns true if the current check price has reached TP3.
func (t *Trade) IsTP3Hit(checkPrice float64) bool {
	if t.IsLong() {
		return checkPrice >= t.TP3Price
	}
	return checkPrice <= t.TP3Price
}

// LotSizeForTP calculates the lot size to close for a given TP
// percentage based on the total (original) lot size.
func (t *Trade) LotSizeForTP(pct int32) float64 {
	return t.TotalLotSize * float64(pct) / 100.0
}

// DurationMinutes returns how long the trade has been open.
func (t *Trade) DurationMinutes() int {
	end := t.ClosedAt
	if end.IsZero() {
		end = time.Now().UTC()
	}
	return int(end.Sub(t.OpenedAt).Minutes())
}
