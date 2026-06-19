package broker

import (
	"context"

	"github.com/flamegreat-1/etradie/src/execution/internal/models"
)

// Port is the abstracted broker interface. Module B depends on this
// abstraction per Dependency Inversion. The sole concrete
// implementation is the mt5 bridge (src/execution/internal/broker/mt5),
// which is injected at startup by cmd/execution/main.go.
//
// The mt5 bridge calls the Python engine's /internal/broker/* HTTP
// surface. The engine resolves the per-user MT4 or MT5 broker
// connection from the broker_connections table at request time, so
// the bridge itself is platform-agnostic. Module B extends the
// engine's TA broker with trading operations (account info,
// positions, order placement) that the TA layer doesn't expose.
type Port interface {
	// GetAccountInfo returns live account balance, equity, margin.
	GetAccountInfo(ctx context.Context) (*models.AccountInfo, error)

	// GetPositions returns all open positions at the broker.
	GetPositions(ctx context.Context) ([]models.Position, error)

	// GetPendingOrders returns all pending limit orders at the broker.
	GetPendingOrders(ctx context.Context) ([]models.BrokerPendingOrder, error)

	// GetInstrumentInfo returns instrument metadata (pip size, pip value,
	// lot constraints, current spread, average spread). Leverages the
	// same MT5 symbol_info data that src/engine/ta/broker/mt5/client.py
	// uses for get_symbol_info(), extended with spread and pip value.
	GetInstrumentInfo(ctx context.Context, symbol string) (*models.InstrumentInfo, error)

	// PlaceLimitOrder places a limit order with SL/TP at the broker.
	PlaceLimitOrder(ctx context.Context, order *models.OrderPlacement) (*models.OrderResult, error)

	// PlaceMarketOrder places a market order with SL/TP at the broker.
	PlaceMarketOrder(ctx context.Context, order *models.OrderPlacement) (*models.OrderResult, error)

	// CancelOrder cancels a pending order by broker order ID.
	CancelOrder(ctx context.Context, brokerOrderID string) error

	// GetTickPrice returns the latest bid/ask for a symbol.
	// Used by the watcher engine to detect POI zone touches.
	GetTickPrice(ctx context.Context, symbol string) (*models.TickPrice, error)
}
