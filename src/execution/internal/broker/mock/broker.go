package mock

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/flamegreat/etradie/src/execution/internal/models"
)

// Broker is a mock broker for development and testing.
// Thread-safe. Tracks positions and orders in memory.
type Broker struct {
	mu        sync.RWMutex
	balance   float64
	positions []models.Position
	pending   []models.BrokerPendingOrder
}

// NewBroker creates a mock broker with the given starting balance.
func NewBroker(balance float64) *Broker {
	return &Broker{balance: balance}
}

func (b *Broker) GetAccountInfo(_ context.Context) (*models.AccountInfo, error) {
	b.mu.RLock()
	defer b.mu.RUnlock()

	var unrealized float64
	for i := range b.positions {
		unrealized += b.positions[i].UnrealizedPnL
	}

	return &models.AccountInfo{
		Balance:    b.balance,
		Equity:     b.balance + unrealized,
		Margin:     0,
		FreeMargin: b.balance + unrealized,
		Currency:   "USD",
	}, nil
}

func (b *Broker) GetPositions(_ context.Context) ([]models.Position, error) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	out := make([]models.Position, len(b.positions))
	copy(out, b.positions)
	return out, nil
}

func (b *Broker) GetPendingOrders(_ context.Context) ([]models.BrokerPendingOrder, error) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	out := make([]models.BrokerPendingOrder, len(b.pending))
	copy(out, b.pending)
	return out, nil
}

func (b *Broker) GetInstrumentInfo(_ context.Context, symbol string) (*models.InstrumentInfo, error) {
	norm := strings.ToUpper(symbol)

	// Defaults for standard FX pairs (e.g. EURUSD, GBPUSD).
	info := &models.InstrumentInfo{
		Symbol:       norm,
		PipSize:      0.0001,
		PipValue:     10.0,
		MinLotSize:   0.01,
		MaxLotSize:   100.0,
		LotStep:      0.01,
		Spread:       0.00015,
		AvgSpread:    0.00012,
		Digits:       5,
		ContractSize: 100000,
	}

	// JPY pairs: pip size 0.01, different pip value.
	if len(norm) >= 6 && norm[3:6] == "JPY" {
		info.PipSize = 0.01
		info.PipValue = 6.7 // Approximate for 1 standard lot.
		info.Spread = 0.015
		info.AvgSpread = 0.012
		info.Digits = 3
	}

	// Gold.
	if norm == "XAUUSD" {
		info.PipSize = 0.01
		info.PipValue = 1.0
		info.Spread = 0.30
		info.AvgSpread = 0.25
		info.Digits = 2
	}

	// Silver.
	if norm == "XAGUSD" {
		info.PipSize = 0.001
		info.PipValue = 5.0
		info.Spread = 0.020
		info.AvgSpread = 0.015
		info.Digits = 3
	}

	return info, nil
}

func (b *Broker) PlaceLimitOrder(_ context.Context, order *models.OrderPlacement) (*models.OrderResult, error) {
	orderID := generateMockID()

	b.mu.Lock()
	b.pending = append(b.pending, models.BrokerPendingOrder{
		Symbol:        order.Symbol,
		Direction:     order.Direction,
		EntryPrice:    order.Price,
		StopLoss:      order.StopLoss,
		TakeProfit:    order.TakeProfit,
		LotSize:       order.LotSize,
		OrderID:       orderID,
		AnalysisID:    order.Comment,
		ExecutionMode: "LIMIT",
		Status:        "PENDING",
		CreatedAt:     time.Now().UTC(),
	})
	b.mu.Unlock()

	return &models.OrderResult{
		BrokerOrderID: orderID,
		FillPrice:     order.Price,
		Slippage:      0,
		Status:        "PLACED",
	}, nil
}

func (b *Broker) PlaceMarketOrder(_ context.Context, order *models.OrderPlacement) (*models.OrderResult, error) {
	orderID := generateMockID()

	b.mu.Lock()
	b.positions = append(b.positions, models.Position{
		Symbol:        order.Symbol,
		Direction:     order.Direction,
		EntryPrice:    order.Price,
		CurrentPrice:  order.Price,
		StopLoss:      order.StopLoss,
		TakeProfit:    order.TakeProfit,
		LotSize:       order.LotSize,
		UnrealizedPnL: 0,
		OrderID:       orderID,
		AnalysisID:    order.Comment,
		OpenTime:      time.Now().UTC(),
	})
	b.mu.Unlock()

	return &models.OrderResult{
		BrokerOrderID: orderID,
		FillPrice:     order.Price,
		Slippage:      0,
		Status:        "FILLED",
	}, nil
}

func (b *Broker) CancelOrder(_ context.Context, brokerOrderID string) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	for i := range b.pending {
		if b.pending[i].OrderID == brokerOrderID {
			b.pending = append(b.pending[:i], b.pending[i+1:]...)
			return nil
		}
	}
	return fmt.Errorf("order %s not found", brokerOrderID)
}

func generateMockID() string {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return fmt.Sprintf("MOCK_%s", hex.EncodeToString(b))
}
