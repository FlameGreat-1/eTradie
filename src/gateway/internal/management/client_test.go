package management_test

import (
	"context"
	"net"
	"sync/atomic"
	"testing"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"

	managementv1 "github.com/flamegreat-1/etradie/proto/management/v1"
	"github.com/flamegreat-1/etradie/src/gateway/internal/management"
)

type mockManagementServer struct {
	managementv1.UnimplementedManagementServiceServer
	callCount       int32
	lastIdempotency string
	failFirstCalls  int32
}

func (m *mockManagementServer) RegisterFilledTrade(ctx context.Context, req *managementv1.RegisterFilledTradeRequest) (*managementv1.RegisterFilledTradeResponse, error) {
	atomic.AddInt32(&m.callCount, 1)

	// Extract idempotency key
	md, ok := metadata.FromIncomingContext(ctx)
	if ok {
		vals := md.Get("x-idempotency-key")
		if len(vals) > 0 {
			m.lastIdempotency = vals[0]
		}
	}

	// Fail the specified number of times to trigger retry
	if atomic.LoadInt32(&m.callCount) <= m.failFirstCalls {
		return nil, status.Error(codes.Unavailable, "service temporarily down")
	}

	return &managementv1.RegisterFilledTradeResponse{
		Success: true,
		TradeId: "mock-trade-id-123",
		Message: "Registered",
	}, nil
}

func startMockGRPCServer(t *testing.T, failFirst int32) (*grpc.Server, *mockManagementServer, string) {
	lis, err := net.Listen("tcp", "127.0.0.1:0") // Random available port
	if err != nil {
		t.Fatalf("failed to listen: %v", err)
	}

	srv := grpc.NewServer()
	mockSrv := &mockManagementServer{failFirstCalls: failFirst}
	managementv1.RegisterManagementServiceServer(srv, mockSrv)

	go func() {
		if err := srv.Serve(lis); err != nil {
			// Ignore closing errors
		}
	}()

	return srv, mockSrv, lis.Addr().String()
}

func TestManagementClient_RegisterFilledTrade_RetryAndIdempotency(t *testing.T) {
	// Start mock gRPC server that fails the FIRST call with Unavailable.
	srv, mockSrv, addr := startMockGRPCServer(t, 1)
	defer srv.Stop()

	time.Sleep(50 * time.Millisecond)

	client, err := management.NewClient(addr, 5000)
	if err != nil {
		t.Fatalf("failed to create management client: %v", err)
	}
	defer client.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	req := &managementv1.RegisterFilledTradeRequest{
		BrokerOrderId: "MT5-TICKET-9999",
		Symbol:        "EURUSD",
		Direction:     "BUY",
	}

	tradeID, err := client.RegisterFilledTrade(ctx, req)
	if err != nil {
		t.Fatalf("register filled trade failed: %v", err)
	}

	if tradeID != "mock-trade-id-123" {
		t.Errorf("expected tradeID 'mock-trade-id-123', got '%s'", tradeID)
	}

	if mockSrv.lastIdempotency != "MT5-TICKET-9999" {
		t.Errorf("expected idempotency key 'MT5-TICKET-9999', got '%s'", mockSrv.lastIdempotency)
	}

	if atomic.LoadInt32(&mockSrv.callCount) != 2 {
		t.Errorf("expected 2 calls due to 1 retry, got %d", atomic.LoadInt32(&mockSrv.callCount))
	}
}

func TestManagementClient_RegisterFilledTrade_GeneratedIdempotencyKey(t *testing.T) {
	srv, mockSrv, addr := startMockGRPCServer(t, 0)
	defer srv.Stop()
	time.Sleep(50 * time.Millisecond)

	client, _ := management.NewClient(addr, 5000)
	defer client.Close()

	ctx := context.Background()

	// Missing BrokerOrderId should trigger automatic UUID generation for idempotency
	req := &managementv1.RegisterFilledTradeRequest{
		Symbol:    "GBPUSD",
		Direction: "SELL",
	}

	_, err := client.RegisterFilledTrade(ctx, req)
	if err != nil {
		t.Fatalf("expected success, got error: %v", err)
	}

	if mockSrv.lastIdempotency == "" {
		t.Errorf("expected generated uuid for idempotency key when broker_order_id is missing, got empty string")
	}
	if len(mockSrv.lastIdempotency) < 10 {
		t.Errorf("expected a valid uuid, got '%s'", mockSrv.lastIdempotency)
	}
}
