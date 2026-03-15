package broker

import (
	"context"

	"github.com/flamegreat/etradie/src/execution/internal/models"
)

// Port is the abstracted broker interface. Module B depends on this
// abstraction per Dependency Inversion. Concrete implementations
// (MT5 bridge, OANDA, mock) are injected at startup.
type Port interface {
	// GetAccountInfo returns live account balance, equity, margin.
	GetAccountInfo(ctx context.Context) (*models.AccountInfo, error)

	// GetPositions returns all open positions at the broker.
	GetPositions(ctx context.Context) ([]models.Position, error)

	// GetPendingOrders returns all pending limit orders at the broker.
	GetPendingOrders(ctx context.Context) ([]models.BrokerPendingOrder, error)

	// GetInstrumentInfo returns instrument metadata (pip size, pip value,
	// lot constraints, current spread, average spread).
	GetInstrumentInfo(ctx context.Context, symbol string) (*models.InstrumentInfo, error)

	// PlaceLimitOrder places a limit order with SL/TP at the broker.
	PlaceLimitOrder(ctx context.Context, order *models.OrderPlacement) (*models.OrderResult, error)

	// PlaceMarketOrder places a market order with SL/TP at the broker.
	PlaceMarketOrder(ctx context.Context, order *models.OrderPlacement) (*models.OrderResult, error)

	// CancelOrder cancels a pending order by broker order ID.
	CancelOrder(ctx context.Context, brokerOrderID string) error
}
