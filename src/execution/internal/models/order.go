package models

import (
	"sync"
	"time"

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
	UserID    string // Owner of this order (auth user ID from JWT "sub" claim)
	AuthToken string // JWT token for authenticated downstream calls

	// Broker reference (populated after placement).
	BrokerOrderID string
}

// Lock acquires the write lock.
func (o *Order) Lock() { o.mu.Lock() }

// Unlock releases the write lock.
func (o *Order) Unlock() { o.mu.Unlock() }

// RLock acquires the read lock.
func (o *Order) RLock() { o.mu.RLock() }

// RUnlock releases the read lock.
func (o *Order) RUnlock() { o.mu.RUnlock() }
