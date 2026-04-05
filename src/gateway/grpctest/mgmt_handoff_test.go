package gateway_grpc

import (
	"context"
	"net"
	"sync"
	"testing"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"
	"google.golang.org/grpc/test/bufconn"

	gatewayv1 "github.com/flamegreat-1/etradie/proto/gateway/v1"
	managementv1 "github.com/flamegreat-1/etradie/proto/management/v1"
	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/gateway/internal/collectors"
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	ctxpkg "github.com/flamegreat-1/etradie/src/gateway/internal/context"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/management"
	"github.com/flamegreat-1/etradie/src/gateway/internal/pipeline"
	"github.com/flamegreat-1/etradie/src/gateway/internal/querybuilder"
	"github.com/flamegreat-1/etradie/src/gateway/internal/routing"
	"github.com/flamegreat-1/etradie/src/gateway/internal/server"
	"github.com/flamegreat-1/etradie/src/gateway/internal/settingsstore"
	"github.com/flamegreat-1/etradie/src/gateway/internal/symbolstore"

	e2e "github.com/flamegreat-1/etradie/src/gateway/e2etest"
)

// ---------------------------------------------------------------------------
// Mock Management gRPC Server
// ---------------------------------------------------------------------------

// mockManagementServer implements managementv1.ManagementServiceServer.
// Records RegisterFilledTrade calls and returns configurable responses.
type mockManagementServer struct {
	managementv1.UnimplementedManagementServiceServer

	mu    sync.Mutex
	calls []*managementv1.RegisterFilledTradeRequest

	// Configurable response.
	TradeID   string
	Success   bool
	Message   string
	ReturnErr error
}

func (m *mockManagementServer) RegisterFilledTrade(
	_ context.Context,
	req *managementv1.RegisterFilledTradeRequest,
) (*managementv1.RegisterFilledTradeResponse, error) {
	m.mu.Lock()
	m.calls = append(m.calls, req)
	m.mu.Unlock()

	if m.ReturnErr != nil {
		return nil, m.ReturnErr
	}

	return &managementv1.RegisterFilledTradeResponse{
		Success: m.Success,
		TradeId: m.TradeID,
		Message: m.Message,
	}, nil
}

func (m *mockManagementServer) getCalls() []*managementv1.RegisterFilledTradeRequest {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]*managementv1.RegisterFilledTradeRequest, len(m.calls))
	copy(out, m.calls)
	return out
}

// ---------------------------------------------------------------------------
// Harness with real management.Client wired to mock Management server
// ---------------------------------------------------------------------------

// mgmtHandoffHarness builds a Gateway gRPC server with a real
// management.Client connected to a mock Management gRPC server.
type mgmtHandoffHarness struct {
	t        *testing.T
	gwClient gatewayv1.GatewayServiceClient
	mgmtMock *mockManagementServer
	engine   *e2e.MockEngineServer

	// Resources to close.
	gwLis       *bufconn.Listener
	gwServer    *grpc.Server
	gwConn      *grpc.ClientConn
	mgmtServer  *grpc.Server
	hub         *alert.Hub
	transport   *alertredis.Transport
	redisClient *redis.Client
}

func newMgmtHandoffHarness(t *testing.T, mgmtSuccess bool, mgmtTradeID string, mgmtErr error) *mgmtHandoffHarness {
	t.Helper()

	// 1. Start mock Management gRPC server on an ephemeral TCP port.
	// management.Client creates its own internal gRPC connection, so
	// we use real TCP (not bufconn) for the management mock.
	mgmtMock := &mockManagementServer{
		Success:   mgmtSuccess,
		TradeID:   mgmtTradeID,
		Message:   "Trade registered",
		ReturnErr: mgmtErr,
	}

	tcpLis, err := net.Listen("tcp", "localhost:0")
	if err != nil {
		t.Fatalf("failed to listen on TCP: %v", err)
	}
	mgmtAddr := tcpLis.Addr().String()

	mgmtGrpcServer := grpc.NewServer()
	managementv1.RegisterManagementServiceServer(mgmtGrpcServer, mgmtMock)
	go mgmtGrpcServer.Serve(tcpLis)

	// 2. Create real management.Client pointing at the mock server.
	mgmtClient, err := management.NewClient(mgmtAddr, 5000)
	if err != nil {
		t.Fatalf("failed to create management client: %v", err)
	}

	// 3. Build the Gateway gRPC server with the real mgmtClient.
	mockEngine := e2e.NewMockEngineServer()

	cfg := &config.Config{
		Enabled:                       true,
		DefaultSymbols:                []string{"EURUSD", "GBPUSD"},
		CycleIntervalSeconds:          60,
		CycleTimeoutSeconds:           300,
		MaxConcurrentSymbols:          4,
		TAMacroParallelTimeoutSeconds: 120,
		RAGTimeoutSeconds:             30,
		ProcessorTimeoutSeconds:       60,
		GuardTimeoutSeconds:           10,
		TACacheTTLSeconds:             0,
		MacroCacheTTLSeconds:          0,
		MaxCycleRetries:               1,
		RetryBackoffBaseSeconds:       0.5,
		LogLevel:                      "ERROR",
		LogJSON:                       false,
		EngineHTTPURL:                 mockEngine.URL(),
		RedisURL:                      testRedisURL(),
		RedisMaxConnections:           5,
		OTELEndpoint:                  "localhost:4317",
		OTELServiceName:               "etradie-gateway-mgmt-test",
		ExecutionEnabled:              true,
		ExecutionAddr:                 "localhost:50053",
		ExecutionTimeoutMs:            5000,
		ManagementEnabled:             true,
		ManagementAddr:                mgmtAddr,
		ManagementTimeoutMs:           5000,
		HTTPPort:                      19180,
		GRPCPort:                      19181,
	}

	engineHTTP := infra.NewEngineHTTPClient(mockEngine.URL(), 30)
	redisOpts, err := redis.ParseURL(testRedisURL())
	if err != nil {
		t.Fatalf("failed to parse redis URL: %v", err)
	}
	redisOpts.ReadTimeout = 5 * time.Second
	redisOpts.WriteTimeout = 5 * time.Second
	redisOpts.DialTimeout = 5 * time.Second

	redisClient := redis.NewClient(redisOpts)
	hub := alert.NewHub()
	transport := alertredis.NewTransport(redisClient, hub, alertredis.TransportConfig{})
	transport.Start(context.Background())

	taCollector := collectors.NewTACollector(engineHTTP, nil, cfg)
	macroCollector := collectors.NewMacroCollector(engineHTTP, nil, 0)
	qb := querybuilder.NewBuilder()
	assembler := ctxpkg.NewAssembler()
	guards := routing.NewGuardEvaluator()
	execPort := &e2e.MockExecutionPort{}
	router := routing.NewRouter(guards, execPort, transport)
	processor := infra.NewHTTPProcessorAdapter(engineHTTP)

	orchestrator := pipeline.NewOrchestrator(
		cfg, taCollector, macroCollector, qb, assembler,
		processor, router, engineHTTP, transport,
	)

	redisWrapper, _ := infra.NewRedisClient(testRedisURL(), 5)
	var symStore *symbolstore.Store
	var settStore *settingsstore.Store
	if redisWrapper != nil {
		symStore = symbolstore.NewStore(redisWrapper, cfg)
		settStore = settingsstore.NewStore(redisWrapper)
	}
	var scheduler *pipeline.Scheduler
	if symStore != nil && settStore != nil {
		scheduler = pipeline.NewScheduler(orchestrator, symStore, settStore, cfg, transport)
	}

	// Build GRPCServer WITH the real mgmtClient.
	grpcSrv := server.NewGRPCServer(
		cfg, orchestrator, symStore, settStore, scheduler,
		redisWrapper, engineHTTP, transport, mgmtClient, nil,
	)

	// Start Gateway gRPC server via bufconn.
	gwLis := bufconn.Listen(bufSize)
	gwRawServer := grpc.NewServer()
	gatewayv1.RegisterGatewayServiceServer(gwRawServer, grpcSrv)
	go gwRawServer.Serve(gwLis)

	gwConn, err := grpc.NewClient(
		"passthrough:///bufnet-gw",
		grpc.WithContextDialer(func(ctx context.Context, _ string) (net.Conn, error) {
			return gwLis.DialContext(ctx)
		}),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		t.Fatalf("failed to create gw bufconn client: %v", err)
	}

	return &mgmtHandoffHarness{
		t:           t,
		gwClient:    gatewayv1.NewGatewayServiceClient(gwConn),
		mgmtMock:    mgmtMock,
		engine:      mockEngine,
		gwLis:       gwLis,
		gwServer:    gwRawServer,
		gwConn:      gwConn,
		mgmtServer:  mgmtGrpcServer,
		hub:         hub,
		transport:   transport,
		redisClient: redisClient,
	}
}

func (h *mgmtHandoffHarness) close() {
	h.gwConn.Close()
	h.gwServer.GracefulStop()
	h.gwLis.Close()
	h.mgmtServer.GracefulStop()
	h.transport.Close()
	h.hub.Close()
	h.redisClient.Close()
	h.engine.Close()
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

// TestGRPC_NotifyExecutionCompleted_FullHandoff tests the complete
// Module B → Gateway → Module C handoff path:
//
//	Module B calls Gateway.NotifyExecutionCompleted
//	  → Gateway maps fields to RegisterFilledTradeRequest
//	  → Gateway calls management.Client.RegisterFilledTrade
//	  → management.Client calls mock Module C gRPC server
//	  → mock returns trade_id
//	  → Gateway returns management_trade_id to Module B
//
// This is the most critical integration test: it validates that a
// filled trade at the broker is correctly handed off to Module C.
func TestGRPC_NotifyExecutionCompleted_FullHandoff(t *testing.T) {
	h := newMgmtHandoffHarness(t, true, "MGMT-TRADE-001", nil)
	defer h.close()

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	resp, err := h.gwClient.NotifyExecutionCompleted(ctx, &gatewayv1.NotifyExecutionCompletedRequest{
		Symbol:          "EURUSD",
		BrokerOrderId:   "TKT-55555",
		FillPrice:       1.10000,
		Slippage:        0.00003,
		LotSize:         0.15,
		AnalysisId:      "SMC-EURUSD-H4-001",
		TraceId:         "trace-handoff-full-001",
		Direction:       "BUY",
		StopLoss:        1.09500,
		Tp1Price:        1.10500,
		Tp1Pct:          40,
		Tp2Price:        1.11000,
		Tp2Pct:          30,
		Tp3Price:        1.11500,
		Tp3Pct:          30,
		RiskAmount:      150.0,
		RiskPercent:     1.0,
		RrRatio:         3.0,
		Grade:           "A",
		TradingStyle:    "INTRADAY",
		Session:         "LONDON_NY_OVERLAP",
		ConfluenceScore: 8.5,
		ExecutionMode:   "LIMIT",
		SetupType:       "TURTLE_SOUP",
	})

	require.NoError(t, err, "handoff should succeed")
	require.NotNil(t, resp)
	assert.True(t, resp.Success)
	assert.Equal(t, "MGMT-TRADE-001", resp.ManagementTradeId,
		"management trade ID should be returned to caller")

	// ---------------------------------------------------------------
	// Assert: Mock Management server received the correct request.
	// ---------------------------------------------------------------
	mgmtCalls := h.mgmtMock.getCalls()
	require.Len(t, mgmtCalls, 1, "Module C should receive exactly 1 call")

	mgmtReq := mgmtCalls[0]
	assert.Equal(t, "EURUSD", mgmtReq.Symbol)
	assert.Equal(t, "BUY", mgmtReq.Direction)
	assert.Equal(t, "TKT-55555", mgmtReq.BrokerOrderId)
	assert.InDelta(t, 1.10000, mgmtReq.FillPrice, 0.00001)
	assert.InDelta(t, 0.00003, mgmtReq.Slippage, 0.000001)
	assert.InDelta(t, 0.15, mgmtReq.LotSize, 0.001)
	assert.Equal(t, "SMC-EURUSD-H4-001", mgmtReq.AnalysisId)
	assert.Equal(t, "trace-handoff-full-001", mgmtReq.TraceId)
	assert.InDelta(t, 1.09500, mgmtReq.StopLoss, 0.00001)
	assert.InDelta(t, 1.10500, mgmtReq.Tp1Price, 0.00001)
	assert.Equal(t, int32(40), mgmtReq.Tp1Pct)
	assert.InDelta(t, 1.11000, mgmtReq.Tp2Price, 0.00001)
	assert.Equal(t, int32(30), mgmtReq.Tp2Pct)
	assert.InDelta(t, 1.11500, mgmtReq.Tp3Price, 0.00001)
	assert.Equal(t, int32(30), mgmtReq.Tp3Pct)
	assert.InDelta(t, 150.0, mgmtReq.RiskAmount, 0.01)
	assert.InDelta(t, 1.0, mgmtReq.RiskPercent, 0.01)
	assert.InDelta(t, 3.0, mgmtReq.RrRatio, 0.01)
	assert.Equal(t, "A", mgmtReq.Grade)
	assert.Equal(t, "INTRADAY", mgmtReq.TradingStyle)
	assert.Equal(t, "LONDON_NY_OVERLAP", mgmtReq.Session)
	assert.InDelta(t, 8.5, mgmtReq.ConfluenceScore, 0.01)
	assert.Equal(t, "LIMIT", mgmtReq.ExecutionMode)
	assert.Equal(t, "TURTLE_SOUP", mgmtReq.SetupType)
}

// TestGRPC_NotifyExecutionCompleted_MgmtReturnsError verifies that
// when Module C returns a gRPC error, the Gateway propagates it
// back to the caller.
func TestGRPC_NotifyExecutionCompleted_MgmtReturnsError(t *testing.T) {
	h := newMgmtHandoffHarness(t, false, "",
		status.Errorf(codes.Unavailable, "management service unavailable"))
	defer h.close()

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	_, err := h.gwClient.NotifyExecutionCompleted(ctx, &gatewayv1.NotifyExecutionCompletedRequest{
		Symbol:        "EURUSD",
		BrokerOrderId: "TKT-66666",
		FillPrice:     1.10000,
		Slippage:      0.0,
		LotSize:       0.10,
		AnalysisId:    "SMC-EURUSD-H4-002",
		TraceId:       "trace-handoff-err-001",
		Direction:     "BUY",
		StopLoss:      1.09500,
	})

	// The Gateway should propagate the error.
	require.Error(t, err, "should return error when Module C fails")
	st, ok := status.FromError(err)
	require.True(t, ok)
	assert.Equal(t, codes.Internal, st.Code(),
		"Gateway wraps management errors as Internal")
	assert.Contains(t, st.Message(), "management")
}

// TestGRPC_NotifyExecutionCompleted_MgmtRejectsRegistration verifies
// that when Module C returns success=false, the Gateway treats it
// as an error and propagates it.
func TestGRPC_NotifyExecutionCompleted_MgmtRejectsRegistration(t *testing.T) {
	h := newMgmtHandoffHarness(t, false, "", nil)
	h.mgmtMock.Message = "duplicate broker_order_id"
	defer h.close()

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	_, err := h.gwClient.NotifyExecutionCompleted(ctx, &gatewayv1.NotifyExecutionCompletedRequest{
		Symbol:        "EURUSD",
		BrokerOrderId: "TKT-77777",
		FillPrice:     1.10000,
		Slippage:      0.0,
		LotSize:       0.10,
		AnalysisId:    "SMC-EURUSD-H4-003",
		TraceId:       "trace-handoff-reject-001",
		Direction:     "BUY",
		StopLoss:      1.09500,
	})

	// management.Client checks resp.Success and returns error if false.
	require.Error(t, err, "should return error when Module C rejects")
	st, ok := status.FromError(err)
	require.True(t, ok)
	assert.Equal(t, codes.Internal, st.Code())
}
