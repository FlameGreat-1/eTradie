package server_test

import (
	"context"
	"strings"
	"sync/atomic"
	"testing"

	managementv1 "github.com/flamegreat-1/etradie/proto/management/v1"
	"github.com/flamegreat-1/etradie/src/management/internal/analytics"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/server"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

// Mock objects
type mockJournal struct {
	existingTrade *journal.TradeRecord
	insertErr     error
	insertCount   int32
}

func (m *mockJournal) InsertTrade(ctx context.Context, t *journal.TradeRecord) error {
	atomic.AddInt32(&m.insertCount, 1)
	return m.insertErr
}

func (m *mockJournal) GetTradeByBrokerOrderID(ctx context.Context, brokerOrderID string) (*journal.TradeRecord, error) {
	if m.existingTrade != nil && m.existingTrade.BrokerOrderID == brokerOrderID {
		return m.existingTrade, nil
	}
	return nil, nil // not found
}

func (m *mockJournal) GetClosedTrades(ctx context.Context, limit, offset int, symbolFilter, styleFilter string) ([]*journal.TradeRecord, int, error) {
	return nil, 0, nil
}

type mockMonitor struct {
	registerCount int32
}

func (m *mockMonitor) RegisterTrade(t *types.Trade) {
	atomic.AddInt32(&m.registerCount, 1)
}

func (m *mockMonitor) GetAllTrades() []*types.Trade {
	return nil
}

func (m *mockMonitor) TradeCount() int {
	return 0
}

type mockMetrics struct{}

func (m *mockMetrics) Calculate(ctx context.Context, period string) (*analytics.PerformanceSummary, error) {
	return &analytics.PerformanceSummary{}, nil
}

func TestManagementServer_RegisterFilledTrade_Idempotent(t *testing.T) {
	mj := &mockJournal{
		existingTrade: &journal.TradeRecord{
			TradeID:       "existing-123",
			BrokerOrderID: "TKT-9999",
		},
	}
	mm := &mockMonitor{}
	mmx := &mockMetrics{}

	srv := server.NewManagementServer(mm, mj, mmx)

	req := &managementv1.RegisterFilledTradeRequest{
		Symbol:        "EURUSD",
		BrokerOrderId: "TKT-9999",
		FillPrice:     1.0500,
		StopLoss:      1.0450,
		LotSize:       1.0,
	}

	resp, err := srv.RegisterFilledTrade(context.Background(), req)
	if err != nil {
		t.Fatalf("expected success on idempotent request, got error: %v", err)
	}

	if resp.TradeId != "existing-123" {
		t.Errorf("expected to return existing trade ID 'existing-123', got '%s'", resp.TradeId)
	}

	if atomic.LoadInt32(&mj.insertCount) != 0 {
		t.Errorf("expected 0 db inserts for idempotent request, got %d", mj.insertCount)
	}
	if atomic.LoadInt32(&mm.registerCount) != 0 {
		t.Errorf("expected 0 monitor registrations for idempotent request, got %d", mm.registerCount)
	}

	if !strings.Contains(resp.Message, "idempotent") {
		t.Errorf("expected message to indicate idempotent behavior, got '%s'", resp.Message)
	}
}

func TestManagementServer_RegisterFilledTrade_NewTrade(t *testing.T) {
	mj := &mockJournal{} // no existing trade
	mm := &mockMonitor{}
	mmx := &mockMetrics{}

	srv := server.NewManagementServer(mm, mj, mmx)

	req := &managementv1.RegisterFilledTradeRequest{
		Symbol:        "GBPUSD",
		BrokerOrderId: "TKT-8888",
		FillPrice:     1.2000,
		StopLoss:      1.1950,
		LotSize:       2.0,
	}

	resp, err := srv.RegisterFilledTrade(context.Background(), req)
	if err != nil {
		t.Fatalf("expected success, got error: %v", err)
	}

	if resp.TradeId == "" {
		t.Errorf("expected generated trade ID, got empty string")
	}

	if atomic.LoadInt32(&mj.insertCount) != 1 {
		t.Errorf("expected exactly 1 db insert, got %d", mj.insertCount)
	}

	if atomic.LoadInt32(&mm.registerCount) != 1 {
		t.Errorf("expected exactly 1 monitor registration, got %d", mm.registerCount)
	}
}

func TestManagementServer_RegisterFilledTrade_Validation(t *testing.T) {
	mj := &mockJournal{}
	mm := &mockMonitor{}
	mmx := &mockMetrics{}

	srv := server.NewManagementServer(mm, mj, mmx)

	// Missing BrokerOrderId
	req := &managementv1.RegisterFilledTradeRequest{
		Symbol:    "GBPUSD",
		FillPrice: 1.2000,
		StopLoss:  1.1950,
		LotSize:   2.0,
	}

	_, err := srv.RegisterFilledTrade(context.Background(), req)
	if err == nil {
		t.Fatalf("expected error due to missing broker_order_id")
	}
	if !strings.Contains(err.Error(), "required") {
		t.Errorf("expected validation error mentioning required fields, got %v", err)
	}
}
