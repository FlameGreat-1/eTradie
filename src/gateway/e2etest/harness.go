package e2e

import (
	"context"
	"fmt"
	"os"
	"sync"
	"testing"
	"time"

	"github.com/redis/go-redis/v9"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/gateway/internal/collectors"
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	ctxpkg "github.com/flamegreat-1/etradie/src/gateway/internal/context"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
	"github.com/flamegreat-1/etradie/src/gateway/internal/pipeline"
	"github.com/flamegreat-1/etradie/src/gateway/internal/querybuilder"
	"github.com/flamegreat-1/etradie/src/gateway/internal/routing"
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

// MockExecutionPort implements ports.ExecutionPort for E2E tests.
// Records every call and returns configurable responses.
type MockExecutionPort struct {
	mu    sync.Mutex
	calls []ExecutionCall

	// Response controls what Execute returns.
	Response map[string]interface{}
	Err      error
}

// ExecutionCall records a single call to the execution port.
type ExecutionCall struct {
	Decision *models.ProcessorOutput
}

// Execute implements ports.ExecutionPort.
func (m *MockExecutionPort) Execute(_ context.Context, decision *models.ProcessorOutput) (map[string]interface{}, error) {
	m.mu.Lock()
	m.calls = append(m.calls, ExecutionCall{Decision: decision})
	m.mu.Unlock()

	if m.Err != nil {
		return nil, m.Err
	}
	if m.Response != nil {
		return m.Response, nil
	}
	// Default successful execution response matching ExecuteTradeResponse fields.
	return map[string]interface{}{
		"accepted":         true,
		"status":           "LIMIT_ORDER_PLACED",
		"order_id":         "ORD-E2E-001",
		"rejection_reason": "",
		"lot_size":         0.10,
		"risk_amount":      100.0,
		"account_balance":  10000.0,
		"sl_distance_pips": 50.0,
		"pip_value":        10.0,
		"execution_mode":   "LIMIT",
		"entry_price":      1.10000,
		"analysis_id":      decision.AnalysisID,
		"trace_id":         decision.AnalysisID,
	}, nil
}

// GetCalls returns a copy of all recorded execution calls.
func (m *MockExecutionPort) GetCalls() []ExecutionCall {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]ExecutionCall, len(m.calls))
	copy(out, m.calls)
	return out
}

// Reset clears all recorded calls.
func (m *MockExecutionPort) Reset() {
	m.mu.Lock()
	m.calls = nil
	m.mu.Unlock()
}

// Harness wires the real Gateway Orchestrator with mock external services.
// It constructs the full production dependency chain, substituting only:
//   - The HTTP base URL (points to MockEngineServer instead of real Python engine)
//   - The ExecutionPort (uses MockExecutionPort instead of real gRPC adapter)
//   - Redis (nil, disabling caching so every call hits the mock server)
//   - Alert transport (uses a real Hub + Transport with a disconnected Redis client)
//
// Everything else is real production code: config validation, collectors,
// query builder, assembler, guard evaluator, router, orchestrator.
type Harness struct {
	T            *testing.T
	Cfg          *config.Config
	Engine       *MockEngineServer
	Execution    *MockExecutionPort
	Orchestrator *pipeline.Orchestrator
	Hub          *alert.Hub
	transport    *alertredis.Transport
	redisClient  *redis.Client
}

// NewHarness creates a fully wired E2E test harness.
// The mock engine server is started and the orchestrator is ready to run cycles.
func NewHarness(t *testing.T) *Harness {
	t.Helper()

	// Start mock Python engine HTTP server.
	engine := NewMockEngineServer()

	// Build a valid config that passes all validation.
	// Points the engine URL at our mock server.
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
		TACacheTTLSeconds:             0, // Disable caching: every call hits mock.
		MacroCacheTTLSeconds:          0, // Disable caching: every call hits mock.
		MaxCycleRetries:               1,
		RetryBackoffBaseSeconds:       0.5,
		LogLevel:                      "ERROR",
		LogJSON:                       false,
		EngineHTTPURL:                 engine.URL(),
		RedisURL:                      testRedisURL(),
		RedisMaxConnections:           5,
		OTELEndpoint:                  "localhost:4317",
		OTELServiceName:               "etradie-gateway-e2e",
		ExecutionEnabled:              true,
		ExecutionAddr:                 "localhost:50053",
		ExecutionTimeoutMs:            5000,
		ManagementEnabled:             false,
		ManagementAddr:                "localhost:50054",
		ManagementTimeoutMs:           5000,
		HTTPPort:                      18080,
		GRPCPort:                      18081,
	}

	// Real EngineHTTPClient pointing at mock server.
	// Timeout of 30s is generous for tests; the mock responds instantly.
	engineHTTP := infra.NewEngineHTTPClient(engine.URL(), 30)

	// Collectors with nil Redis (caching disabled).
	taCollector := collectors.NewTACollector(engineHTTP, nil, cfg)
	macroCollector := collectors.NewMacroCollector(engineHTTP, nil, 0)

	// Real query builder, assembler, guards.
	qb := querybuilder.NewBuilder()
	assembler := ctxpkg.NewAssembler()
	guards := routing.NewGuardEvaluator()

	// Mock execution port.
	execPort := &MockExecutionPort{}

	// Alert hub + Redis transport backed by the real Redis instance.
	// Redis is running in the container on localhost:6379. Using the real
	// connection exercises the full pub/sub and history code paths.
	hub := alert.NewHub()

	redisOpts, err := redis.ParseURL(testRedisURL())
	if err != nil {
		t.Fatalf("failed to parse redis URL: %v", err)
	}
	redisOpts.ReadTimeout = 5 * time.Second
	redisOpts.WriteTimeout = 5 * time.Second
	redisOpts.DialTimeout = 5 * time.Second

	redisClient := redis.NewClient(redisOpts)
	transport := alertredis.NewTransport(redisClient, hub, alertredis.TransportConfig{})
	transport.Start(context.Background())

	// Real router wired with mock execution and transport.
	router := routing.NewRouter(guards, execPort, transport)

	// Real processor adapter backed by the mock engine HTTP server.
	processor := infra.NewHTTPProcessorAdapter(engineHTTP)

	// Real orchestrator with the full production pipeline.
	orchestrator := pipeline.NewOrchestrator(
		cfg, taCollector, macroCollector, qb, assembler,
		processor, router, engineHTTP, transport,
	)

	return &Harness{
		T:            t,
		Cfg:          cfg,
		Engine:       engine,
		Execution:    execPort,
		Orchestrator: orchestrator,
		Hub:          hub,
		transport:    transport,
		redisClient:  redisClient,
	}
}

// Close tears down all test resources.
func (h *Harness) Close() {
	h.transport.Close()
	h.Hub.Close()
	h.redisClient.Close()
	h.Engine.Close()
}

// RunCycle executes a full pipeline cycle through the real orchestrator
// with the given symbols and returns the outputs.
func (h *Harness) RunCycle(symbols []string, traceID string) []*models.GatewayOutput {
	h.T.Helper()
	ctx := context.Background()
	return h.Orchestrator.RunCycle(ctx, symbols, traceID)
}
