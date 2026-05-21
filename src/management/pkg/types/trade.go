package types

import (
	"context"
	"sync"
	"time"

	"github.com/flamegreat-1/etradie/src/auth"
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
	Point         float64 // Broker point size (e.g., 0.00001 or 0.01)
	Digits        int     // Broker price digits
	Direction     constants.Direction
	BrokerOrderID string
	AnalysisID    string
	TraceID       string

	// Auth context (for background monitoring worker goroutines).
	// Set when the trade is registered via gRPC and used by the worker
	// to make authenticated calls to the Python engine broker endpoints.
	//
	// All five fields originate at the trust boundary (TokenService
	// in src/auth) and flow top-down. They are NEVER derived from the
	// JWT inside hot paths; whoever mints the service token / receives
	// the user request stamps them onto the Trade once.
	UserID    string // Owner of this trade (auth user ID from JWT "sub" claim)
	Username  string // Owner's username (auth user username from JWT "username" claim)
	Role      string // Owner's role ("admin" / "etradie") from JWT "role" claim
	Tier      string // Owner's tier ("free" / "pro_byok" / "pro_managed")
	StatusJWT string // Owner's subscription status ("active" / "past_due" / ...). Named StatusJWT to avoid collision with Trade.Status (trade-state machine).
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

// IdentityCtx returns a context derived from `parent` with the
// trade's owner identity injected as parsed *auth.Claims AND with
// the raw JWT injected for back-compat with any callee that still
// reads RawTokenFromContext.
//
// The caller must already hold (or not need) the read lock — this
// helper does not lock the struct internally, matching the pattern
// used by IsLong / IsSLHit / etc. across this package. In practice
// every call site already takes a snapshot of the identity fields
// under RLock and then calls IdentityCtx with those local copies
// expanded — see runWorker in monitoring/worker.go.
func (t *Trade) IdentityCtx(parent context.Context) context.Context {
	ctx := auth.InjectIdentity(
		parent,
		t.UserID, t.Username, auth.Role(t.Role), t.Tier, t.StatusJWT,
	)
	if t.AuthToken != "" {
		ctx = auth.InjectTokenIntoContext(ctx, t.AuthToken)
	}
	return ctx
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
// A StopLoss of 0 means "not set" — the check always returns false.
func (t *Trade) IsSLHit(checkPrice float64) bool {
	if t.StopLoss <= 0 {
		return false // No SL set; can't be hit.
	}
	if t.IsLong() {
		return checkPrice <= t.StopLoss
	}
	return checkPrice >= t.StopLoss
}

// IsTP1Hit returns true if the current check price has reached TP1.
// A TP1Price of 0 means "not set" — the check always returns false.
func (t *Trade) IsTP1Hit(checkPrice float64) bool {
	if t.TP1Price <= 0 {
		return false
	}
	if t.IsLong() {
		return checkPrice >= t.TP1Price
	}
	return checkPrice <= t.TP1Price
}

// IsTP2Hit returns true if the current check price has reached TP2.
// A TP2Price of 0 means "not set" — the check always returns false.
func (t *Trade) IsTP2Hit(checkPrice float64) bool {
	if t.TP2Price <= 0 {
		return false
	}
	if t.IsLong() {
		return checkPrice >= t.TP2Price
	}
	return checkPrice <= t.TP2Price
}

// IsTP3Hit returns true if the current check price has reached TP3.
// A TP3Price of 0 means "not set" — the check always returns false.
func (t *Trade) IsTP3Hit(checkPrice float64) bool {
	if t.TP3Price <= 0 {
		return false
	}
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
