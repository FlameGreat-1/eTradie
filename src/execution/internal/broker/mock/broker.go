package mock

import (
	"context"
	"fmt"
	"math/rand"
	"time"

	"github.com/flamegreat/etradie/src/execution/internal/models"
)

// Broker is a mock broker implementation for development and testing.
// Returns realistic but simulated data. Implements broker.Port.
type Broker struct {
	balance float64
}

// NewBroker creates a mock broker with the given starting balance.
func NewBroker(balance float64) *Broker {
	return &Broker{balance: balance}
}

func (b *Broker) GetAccountInfo(_ context.Context) (*models.AccountInfo, error) {
	return &models.AccountInfo{
		Balance:    b.balance,
		Equity:     b.balance,
		Margin:     0,
		FreeMargin: b.balance,
		Currency:   "USD",
	}, nil
}

func (b *Broker) GetPositions(_ context.Context) ([]models.Position, error) {
	return nil, nil
}

func (b *Broker) GetPendingOrders(_ context.Context) ([]models.BrokerPendingOrder, error) {
	return nil, nil
}

func (b *Broker) GetInstrumentInfo(_ context.Context, symbol string) (*models.InstrumentInfo, error) {
	pipSize := 0.0001
	pipValue := 10.0
	digits := int32(5)

	if len(symbol) >= 6 && symbol[3:6] == "JPY" {
		pipSize = 0.01
		pipValue = 7.5
		digits = 3
	}

	if symbol == "XAUUSD" {
		pipSize = 0.01
		pipValue = 1.0
		digits = 2
	}

	return &models.InstrumentInfo{
		Symbol:       symbol,
		PipSize:      pipSize,
		PipValue:     pipValue,
		MinLotSize:   0.01,
		MaxLotSize:   100.0,
		LotStep:      0.01,
		Spread:       pipSize * 1.5,
		AvgSpread:    pipSize * 1.2,
		Digits:       digits,
		ContractSize: 100000,
	}, nil
}

func (b *Broker) PlaceLimitOrder(_ context.Context, order *models.OrderPlacement) (*models.OrderResult, error) {
	return &models.OrderResult{
		BrokerOrderID: fmt.Sprintf("MOCK_%d", time.Now().UnixNano()),
		FillPrice:     order.Price,
		Slippage:      0,
		Status:        "PLACED",
	}, nil
}

func (b *Broker) PlaceMarketOrder(_ context.Context, order *models.OrderPlacement) (*models.OrderResult, error) {
	slippage := (rand.Float64() - 0.5) * 0.00002
	return &models.OrderResult{
		BrokerOrderID: fmt.Sprintf("MOCK_%d", time.Now().UnixNano()),
		FillPrice:     order.Price + slippage,
		Slippage:      slippage,
		Status:        "FILLED",
	}, nil
}

func (b *Broker) CancelOrder(_ context.Context, _ string) error {
	return nil
}