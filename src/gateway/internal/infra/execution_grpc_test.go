package infra_test

import (
	"context"
	"net"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"

	executionv1 "github.com/flamegreat-1/etradie/proto/execution/v1"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
)

type mockExecutionServer struct {
	executionv1.UnimplementedExecutionServiceServer
	callCount      int32
	lastIdempotency string
	failFirstCalls int32
}

func (m *mockExecutionServer) ExecuteTrade(ctx context.Context, req *executionv1.ExecuteTradeRequest) (*executionv1.ExecuteTradeResponse, error) {
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

	return &executionv1.ExecuteTradeResponse{
		Success: true,
		Message: "Trade Executed",
		BrokerOrderId: "mock-broker-id",
	}, nil
}

func (m *mockExecutionServer) GetExecutionState(ctx context.Context, req *executionv1.GetStateRequest) (*executionv1.GetStateResponse, error) {
	return &executionv1.GetStateResponse{}, nil
}

func startMockGRPCServer(t *testing.T, failFirst int32) (*grpc.Server, *mockExecutionServer, string) {
	lis, err := net.Listen("tcp", "127.0.0.1:0") // Random available port
	if err != nil {
		t.Fatalf("failed to listen: %v", err)
	}

	srv := grpc.NewServer()
	mockSrv := &mockExecutionServer{failFirstCalls: failFirst}
	executionv1.RegisterExecutionServiceServer(srv, mockSrv)

	go func() {
		if err := srv.Serve(lis); err != nil {
			// Ignore closing errors
		}
	}()

	return srv, mockSrv, lis.Addr().String()
}

func TestExecutionGRPCAdapter_Execute_RetryAndIdempotency(t *testing.T) {
	// Start mock gRPC server that fails the FIRST call with Unavailable.
	srv, mockSrv, addr := startMockGRPCServer(t, 1)
	defer srv.Stop()

	// Wait briefly for server to be ready
	time.Sleep(50 * time.Millisecond)

	adapter, err := infra.NewExecutionGRPCAdapter(addr, 5000)
	if err != nil {
		t.Fatalf("failed to create adapter: %v", err)
	}

	// Provide a decision output. We expect AnalysisId to be used as idempotency key.
	decision := &models.ProcessorOutput{
		Symbol:     "EURUSD",
		Direction:  "BUY",
		AnalysisID: "test-analysis-1234",
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	result, err := adapter.Execute(ctx, decision)
	if err != nil {
		t.Fatalf("execute failed: %v", err)
	}

	if mockSrv.lastIdempotency != "test-analysis-1234" {
		t.Errorf("expected idempotency key 'test-analysis-1234', got '%s'", mockSrv.lastIdempotency)
	}

	if atomic.LoadInt32(&mockSrv.callCount) != 2 {
		t.Errorf("expected 2 calls due to 1 retry, got %d", atomic.LoadInt32(&mockSrv.callCount))
	}

	if result["success"] != true {
		t.Errorf("expected success=true in result map, got %v", result["success"])
	}
	if result["broker_order_id"] != "mock-broker-id" {
		t.Errorf("expected broker_order_id='mock-broker-id', got %v", result["broker_order_id"])
	}
}

}
