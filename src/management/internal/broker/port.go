package broker

import (
	"context"
	"errors"
	"time"
)

// ErrNoBrokerConfigured is emitted on the errors channel of
// WatchPositions when the engine responds with HTTP 503 and a body
// indicating that the user has no active broker connection (see the
// engine's `_resolve_user_broker` helper). Callers should apply
// exponential backoff rather than retrying at a fixed interval,
// since the user must configure a broker connection before the
// watcher can produce data.
var ErrNoBrokerConfigured = errors.New("no broker connection configured for user")

// TickPrice holds the latest bid/ask for a symbol.
type TickPrice struct {
	Bid float64
	Ask float64
}

// AccountInfo holds the live account balance.
type AccountInfo struct {
	Balance    float64
	Equity     float64
	Margin     float64
	FreeMargin float64
	Currency   string
}

// SymbolInfo holds the instrument metadata the management engine needs
// for pip-scale math (break-even buffer, trailing). Sourced from the
// engine's /internal/broker/symbol_info endpoint — the SAME source the
// execution sizing engine uses — so the pip model stays consistent
// across modules.
type SymbolInfo struct {
	Symbol         string
	Point          float64
	Digits         int
	TradeTickValue float64 // value of one tick movement for 1 lot in deposit currency
	TradeTickSize  float64 // size of one tick in price terms
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
	Commission   float64
	Swap         float64
	Ticket       string
}

// HistoryDealInfo holds a historical deal from the broker.
type HistoryDealInfo struct {
	Ticket     string
	PositionID string
	Symbol     string
	Direction  string
	Volume     float64
	Price      float64
	Profit     float64
	Commission float64
	Swap       float64
	Time       int64
	Comment    string
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

	// GetAccountInfo returns live account balance, equity, margin.
	GetAccountInfo(ctx context.Context) (*AccountInfo, error)

	// GetPosition returns the current broker state of a specific position.
	// Used to verify position still exists and get current unrealized P&L.
	GetPosition(ctx context.Context, ticket string) (*PositionInfo, error)

	// GetSymbolInfo returns instrument metadata (point, digits) for a
	// symbol. Used to self-heal a managed trade whose broker point was
	// not captured at registration (reconciler-imported / pre-migration
	// rows) so break-even / trailing pip math runs on the correct scale.
	GetSymbolInfo(ctx context.Context, symbol string) (*SymbolInfo, error)

	// GetPositions returns ALL open positions at the broker.
	// Used by the startup reconciler to discover orphaned positions
	// that the Management engine doesn't know about.
	GetPositions(ctx context.Context) ([]PositionInfo, error)

	// GetHistory returns historical closed deals from the broker.
	// Used by the startup reconciler to backfill missing closed trades.
	GetHistory(ctx context.Context, days int) ([]HistoryDealInfo, error)

	// WatchPositions returns two channels driven by a background
	// goroutine that polls GetPositions at the supplied interval and
	// emits a new snapshot ONLY when it differs from the previous one.
	//
	// Channels:
	//   positions  - structurally-changed position snapshots. Size-1
	//                with coalescing semantics: if the consumer falls
	//                behind, an older unconsumed snapshot is dropped
	//                and replaced by the newer one. The consumer
	//                therefore always sees the LATEST state, never a
	//                stale backlog.
	//   errors     - fatal errors from the watcher. Receiving on this
	//                channel ends the watch. ErrNoBrokerConfigured
	//                signals "user has no active broker connection"
	//                and the consumer should apply exponential backoff
	//                before re-arming the watcher. Other errors are
	//                transient broker / network failures.
	//
	// Both channels are closed when ctx is cancelled or a fatal error
	// occurs. The goroutine is leak-free under shutdown.
	//
	// This is the architecturally correct shape for MT5 / MetaAPI
	// position data: the broker API is request/response with no
	// server-initiated push, so polling at the system boundary is
	// the truthful design. A future broker that exposes a real
	// streaming API can be added by writing a new Port implementation
	// without touching the consumer.
	WatchPositions(ctx context.Context, interval time.Duration) (<-chan []PositionInfo, <-chan error)

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

// NewMT5Broker creates an MT5 broker connection composing action and
// stream clients. internalSecret must match the engine's
// ENGINE_INTERNAL_SHARED_SECRET; an empty value is allowed for
// development but every /internal/broker/* call will 401 at the
// engine, which surfaces the misconfiguration in the operator's logs.
func NewMT5Broker(baseURL string, timeoutMs int, internalSecret string) *MT5Broker {
	return &MT5Broker{
		Client: NewClient(baseURL, timeoutMs, internalSecret),
		Stream: NewStream(baseURL, timeoutMs, internalSecret),
	}
}
