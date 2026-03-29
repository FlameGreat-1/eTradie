package gateway_grpc

import (
	"context"
	"fmt"
	"net"
	"os"
	"testing"
	"time"

	"github.com/redis/go-redis/v9"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/test/bufconn"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/gateway/internal/collectors"
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	ctxpkg "github.com/flamegreat-1/etradie/src/gateway/internal/context"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/pipeline"
	"github.com/flamegreat-1/etradie/src/gateway/internal/querybuilder"
	"github.com/flamegreat-1/etradie/src/gateway/internal/routing"
	"github.com/flamegreat-1/etradie/src/gateway/internal/server"
	"github.com/flamegreat-1/etradie/src/gateway/internal/settingsstore"
	"github.com/flamegreat-1/etradie/src/gateway/internal/symbolstore"

	gatewayv1 "github.com/flamegreat-1/etradie/proto/gateway/v1"

	e2e "github.com/flamegreat-1/etradie/src/gateway/e2etest"
)

func testRedisURL() string {
	if url := os.Getenv("REDIS_URL"); url != "" {
		return url
	}
	pw := os.Getenv("REDIS_PASSWORD")
	if pw != "" {
		return fmt.Sprintf("redis://:%s@localhost:6379/0", pw)
	}
	return "redis://localhost:6379/0"
}

const bufSize = 1024 * 1024

// Harness provides an in-process gRPC test environment for the Gateway
// server. Uses bufconn so no real network ports are needed.
type Harness struct {
	T         *testing.T
	Client    gatewayv1.GatewayServiceClient
	Engine    *e2e.MockEngineServer
	Execution *e2e.MockExecutionPort
	Cfg       *config.Config

	lis         *bufconn.Listener
	grpcServer  *grpc.Server
	conn        *grpc.ClientConn
	hub         *alert.Hub
	transport   *alertredis.Transport
	redisClient *redis.Client
}

// NewHarness creates a fully wired in-process Gateway gRPC server
// and returns a harness with a connected client.
func NewHarness(t *testing.T) *Harness {
	t.Helper()

	// Mock Python engine HTTP server.
	engine := e2e.NewMockEngineServer()

	// Config matching the E2E harness.
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
		EngineHTTPURL:                 engine.URL(),
		RedisURL:                      testRedisURL(),
		RedisMaxConnections:           5,
		OTELEndpoint:                  "localhost:4317",
		OTELServiceName:               "etradie-gateway-integration",
		ExecutionEnabled:              true,
		ExecutionAddr:                 "localhost:50053",
		ExecutionTimeoutMs:            5000,
		ManagementEnabled:             false,
		ManagementAddr:                "localhost:50054",
		ManagementTimeoutMs:           5000,
		HTTPPort:                      19080,
		GRPCPort:                      19081,
	}

	// Real EngineHTTPClient pointing at mock.
	engineHTTP := infra.NewEngineHTTPClient(engine.URL(), 30)

	// Real Redis connection for alert transport and stores.
	redisOpts, err := redis.ParseURL(testRedisURL())
	if err != nil {
		t.Fatalf("failed to parse redis URL: %v", err)
	}
	redisOpts.ReadTimeout = 5 * time.Second
	redisOpts.WriteTimeout = 5 * time.Second
	redisOpts.DialTimeout = 5 * time.Second

	redisClient := redis.NewClient(redisOpts)

	// Alert hub + transport backed by real Redis.
	hub := alert.NewHub()
	transport := alertredis.NewTransport(redisClient, hub, alertredis.TransportConfig{})
	transport.Start(context.Background())

	// Build the real infra.RedisClient wrapper is needed by SymbolStore
	// and SettingsStore. Since we can't construct infra.RedisClient without
	// a real Redis URL parse, we pass nil to collectors (caching disabled)
	// and build the GRPCServer with nil redis/engine for health checks.
	// The GRPCServer's GetHealth will report degraded, which is fine for tests.

	// Collectors (no caching).
	taCollector := collectors.NewTACollector(engineHTTP, nil, cfg)
	macroCollector := collectors.NewMacroCollector(engineHTTP, nil, 0)

	// Pipeline components.
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

	// SymbolStore and SettingsStore backed by real Redis.
	redisWrapper, _ := infra.NewRedisClient(testRedisURL(), 5)

	var symStore *symbolstore.Store
	var settStore *settingsstore.Store
	if redisWrapper != nil {
		symStore = symbolstore.NewStore(redisWrapper, cfg)
		settStore = settingsstore.NewStore(redisWrapper)
	}

	// Scheduler (not started, just wired for SetCycleInterval).
	var scheduler *pipeline.Scheduler
	if symStore != nil && settStore != nil {
		scheduler = pipeline.NewScheduler(orchestrator, symStore, settStore, cfg, transport)
	}

	// Build the real GRPCServer. Pass nil for mgmtClient (tested separately).
	grpcSrv := server.NewGRPCServer(
		cfg, orchestrator, symStore, settStore, scheduler,
		redisWrapper, engineHTTP, transport, nil,
	)

	// Start in-process gRPC server via bufconn.
	lis := bufconn.Listen(bufSize)
	rawServer := grpc.NewServer()
	gatewayv1.RegisterGatewayServiceServer(rawServer, grpcSrv)

	go func() {
		if err := rawServer.Serve(lis); err != nil {
			// Server stopped, expected during cleanup.
		}
	}()

	// Create client connection via bufconn.
	conn, err := grpc.NewClient(
		"passthrough:///bufnet",
		grpc.WithContextDialer(func(ctx context.Context, _ string) (net.Conn, error) {
			return lis.DialContext(ctx)
		}),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		t.Fatalf("failed to create bufconn client: %v", err)
	}

	client := gatewayv1.NewGatewayServiceClient(conn)

	return &Harness{
		T:           t,
		Client:      client,
		Engine:      engine,
		Execution:   execPort,
		Cfg:         cfg,
		lis:         lis,
		grpcServer:  rawServer,
		conn:        conn,
		hub:         hub,
		transport:   transport,
		redisClient: redisClient,
	}
}

// Close tears down all test resources.
func (h *Harness) Close() {
	h.conn.Close()
	h.grpcServer.GracefulStop()
	h.lis.Close()
	h.transport.Close()
	h.hub.Close()
	h.redisClient.Close()
	h.Engine.Close()
}
