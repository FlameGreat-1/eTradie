package models

import (
	"context"
	"sync"
	"time"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/execution/internal/constants"
)

// Order is the Unified Order Object per TechSpec B.4.
// Built by the order builder after validation and sizing pass.
// Mutable fields (AuthToken, BrokerOrderID) are protected by the
// embedded mutex for concurrent access from the watcher goroutine
// and the gRPC server / token refresh operations.
type Order struct {
	mu sync.RWMutex

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

	// Candidate structural parameters for lightweight LTF confirmation.
	// Carried from the TA candidate through ProcessorOutput → TradeRequest → Order.
	OBUpper      float64
	OBLower      float64
	LTFTimeframe string
	HTFTimeframe string // The HTF timeframe the OB was detected on (e.g. "H4")

	// TimeoutOverride, when > 0, overrides the style-specific watcher
	// timeout. Used when restoring watchers after a service restart:
	// the remaining time (original timeout minus elapsed) is set here
	// so the restored watcher expires at the correct absolute time,
	// not with a fresh full-duration timeout.
	TimeoutOverride time.Duration

	// Timestamps.
	CreatedAt time.Time

	// Auth context (for background watcher goroutines).
	// AuthToken is mutable: refreshed by RefreshUserOrderTokens when
	// the user authenticates or when service tokens are renewed.
	//
	// Identity fields (UserID + Username + Role + Tier + Status) flow
	// top-down from the trust boundary (TokenService). They are stamped
	// once when the Order is created or restored and read from context
	// thereafter; no JWT parsing happens in hot paths.
	UserID    string // Owner of this order (auth user ID from JWT "sub" claim)
	Username  string // Owner's username (JWT "username" claim)
	Role      string // Owner's role ("admin" / "etradie")
	Tier      string // Owner's tier ("free" / "pro_byok" / "pro_managed")
	StatusJWT string // Owner's subscription status ("active" / "past_due" / ...)
	AuthToken string // JWT token for authenticated downstream calls

	// Broker reference (populated after placement).
	BrokerOrderID string
}

// IdentityCtx returns a context derived from `parent` with the
// order's owner identity injected as parsed *auth.Claims AND with
// the raw JWT injected for back-compat with any callee that still
// reads RawTokenFromContext.
//
// The caller is expected to take a snapshot of the identity fields
// under RLock (or be on the construction path where no concurrent
// access exists) before calling this helper. The struct mutex is
// NOT acquired internally, matching the rest of this package's
// concurrency convention.
func (o *Order) IdentityCtx(parent context.Context) context.Context {
	ctx := auth.InjectIdentity(
		parent,
		o.UserID, o.Username, auth.Role(o.Role), o.Tier, o.StatusJWT,
	)
	if o.AuthToken != "" {
		ctx = auth.InjectTokenIntoContext(ctx, o.AuthToken)
	}
	return ctx
}

// Lock acquires the write lock.
func (o *Order) Lock() { o.mu.Lock() }

// Unlock releases the write lock.
func (o *Order) Unlock() { o.mu.Unlock() }

// RLock acquires the read lock.
func (o *Order) RLock() { o.mu.RLock() }

// RUnlock releases the read lock.
func (o *Order) RUnlock() { o.mu.RUnlock() }
