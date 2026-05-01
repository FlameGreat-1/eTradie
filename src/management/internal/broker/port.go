package broker

import (
	"context"
	"errors"
)

// ErrNoBrokerConfigured is returned by StreamPositions when the Engine
// indicates that the user has no active broker connection (WebSocket
// close code 4004). Callers should apply exponential backoff rather
// than retrying at a fixed interval, since the user must configure a
// broker connection before streaming can succeed.
var ErrNoBrokerConfigured = errors.New("no broker connection configured for user")

// TickPrice holds the latest bid/ask for a symbol.
type TickPrice struct {
	Bid float64
	Ask float64
}

// PositionInfo holds broker-reported position state.
type PositionInfo struct {
	Symbol       string
	Direction    string
	EntryPrice   float64
	CurrentPrice float64
	StopLoss     float64
	TakeProfit   float64
	Volume       float64
	Profit       float64
	Ticket       string
}

// HistoryDealInfo holds a historical deal from the broker.
type HistoryDealInfo struct {
	Ticket      string
	PositionID  string
	Symbol      string
	Direction   string
	Volume      float64
	Price       float64
	Profit      float64
	Commission  float64
	Swap        float64
	Time        int64
	Comment     string
}

// Port is the abstraction layer for broker interactions needed by
// the Trade Management Engine (Module C). It provides price feeds,
// position modification (SL adjustments), and partial/full closes.
//
// Module C needs a subset of the full broker API — it never places
// new orders (that is Module B's responsibility). It ONLY modifies
// existing positions and closes them.
type Port interface {
	// GetTickPrice returns the latest bid/ask for a symbol.
	// Called on every tick poll cycle to evaluate SL/TP hits.
	GetTickPrice(ctx context.Context, symbol string) (*TickPrice, error)

	// GetPosition returns the current broker state of a specific position.
	// Used to verify position still exists and get current unrealized P&L.
	GetPosition(ctx context.Context, ticket string) (*PositionInfo, error)

	// GetPositions returns ALL open positions at the broker.
	// Used by the startup reconciler to discover orphaned positions
	// that the Management engine doesn't know about.
	GetPositions(ctx context.Context) ([]PositionInfo, error)

	// GetHistory returns historical closed deals from the broker.
	// Used by the startup reconciler to backfill missing closed trades.
	GetHistory(ctx context.Context, days int) ([]HistoryDealInfo, error)

	// StreamPositions opens a persistent WebSocket connection to the broker bridge
	// and streams real-time updates for all open positions.
	StreamPositions(ctx context.Context, ch chan<- []PositionInfo) error

	// ModifyPosition changes the SL and/or TP on an existing position.
	// Called for break-even moves, trailing stop adjustments, and
	// time-based SL tightening. The broker applies the change atomically.
	ModifyPosition(ctx context.Context, ticket string, newSL, newTP float64) error

	// ClosePartial closes a fraction of a position at market price.
	// Used for TP1/TP2 partial closes (e.g., close 40% at TP1).
	// volumeToClose is the lot size to close, not a percentage.
	ClosePartial(ctx context.Context, ticket string, volumeToClose float64) error

	// ClosePosition fully closes a position at market price.
	// Used for SL hits, EOD closures, invalidation exits, and TP3 runner.
	ClosePosition(ctx context.Context, ticket string) error
}

// MT5Broker acts as a union of the Stream and Client implementations
// to satisfy the comprehensive Port interface for the management engine.
type MT5Broker struct {
	*Client
	*Stream
}

// NewMT5Broker creates an MT5 broker connection composing action and stream clients.
func NewMT5Broker(baseURL string, timeoutMs int) *MT5Broker {
	return &MT5Broker{
		Client: NewClient(baseURL, timeoutMs),
		Stream: NewStream(baseURL, timeoutMs),
	}
}
