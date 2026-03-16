package server

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"strings"
	"time"

	"github.com/prometheus/client_golang/prometheus/testutil"
	"github.com/rs/zerolog"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/health"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"
	"google.golang.org/grpc/status"

	"github.com/flamegreat/etradie/src/alert"
	alertredis "github.com/flamegreat/etradie/src/alert/redis"
	"github.com/flamegreat/etradie/src/gateway/internal/config"
	"github.com/flamegreat/etradie/src/gateway/internal/infra"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
	"github.com/flamegreat/etradie/src/gateway/internal/pipeline"
	"github.com/flamegreat/etradie/src/gateway/internal/settingsstore"
	"github.com/flamegreat/etradie/src/gateway/internal/symbolstore"

	gatewayv1 "github.com/flamegreat/etradie/proto/gateway/v1"
)

// GRPCServer serves the gateway gRPC API.
type GRPCServer struct {
	gatewayv1.UnimplementedGatewayServiceServer
	server        *grpc.Server
	orchestrator  *pipeline.Orchestrator
	symbolStore   *symbolstore.Store
	settingsStore *settingsstore.Store
	scheduler     *pipeline.Scheduler
	redis         *infra.RedisClient
	engine        *infra.EngineHTTPClient
	transport     *alertredis.Transport
	cfg           *config.Config
	port          int
	log           zerolog.Logger
}

// NewGRPCServer creates the gateway gRPC server.
func NewGRPCServer(
	cfg *config.Config,
	orchestrator *pipeline.Orchestrator,
	symbolStore *symbolstore.Store,
	settingsStore *settingsstore.Store,
	scheduler *pipeline.Scheduler,
	redis *infra.RedisClient,
	engine *infra.EngineHTTPClient,
	transport *alertredis.Transport,
) *GRPCServer {
	s := &GRPCServer{
		orchestrator:  orchestrator,
		symbolStore:   symbolStore,
		settingsStore: settingsStore,
		scheduler:     scheduler,
		redis:         redis,
		engine:        engine,
		transport:     transport,
		cfg:           cfg,
		port:          cfg.GRPCPort,
		log:           observability.Logger("grpc_server"),
	}

	grpcServer := grpc.NewServer(
		grpc.StatsHandler(otelgrpc.NewServerHandler()),
		grpc.ChainUnaryInterceptor(panicRecoveryInterceptor(s.log)),
	)

	gatewayv1.RegisterGatewayServiceServer(grpcServer, s)

	healthServer := health.NewServer()
	healthServer.SetServingStatus("", healthpb.HealthCheckResponse_SERVING)
	healthpb.RegisterHealthServer(grpcServer, healthServer)

	reflection.Register(grpcServer)

	s.server = grpcServer
	return s
}

// Start begins serving gRPC. Blocks until the server stops.
func (s *GRPCServer) Start() error {
	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", s.port))
	if err != nil {
		return fmt.Errorf("grpc_server: listen on port %d: %w", s.port, err)
	}
	s.log.Info().Int("port", s.port).Msg("grpc_server_starting")
	return s.server.Serve(lis)
}

// GracefulStop gracefully stops the gRPC server.
func (s *GRPCServer) GracefulStop() {
	s.log.Info().Msg("grpc_server_shutting_down")
	s.server.GracefulStop()
}

// ---------------------------------------------------------------------------
// Cycle Management
// ---------------------------------------------------------------------------

// RunCycle triggers an analysis cycle.
func (s *GRPCServer) RunCycle(ctx context.Context, req *gatewayv1.RunCycleRequest) (*gatewayv1.RunCycleResponse, error) {
	symbols := req.GetSymbols()
	if len(symbols) == 0 {
		symbols = s.symbolStore.GetActiveSymbols(ctx)
	}

	outputs := s.orchestrator.RunCycle(ctx, symbols, req.GetTraceId())

	var cycleOutputs []*gatewayv1.CycleOutput
	for _, out := range outputs {
		co := &gatewayv1.CycleOutput{
			CycleStatus:  string(out.CycleStatus),
			CycleOutcome: string(out.CycleOutcome),
			PhaseReached: string(out.PhaseReached),
			Symbol:       out.Symbol,
			DurationMs:   out.DurationMs,
			TraceId:      out.TraceID,
			Error:        out.Error,
			ErrorStage:   out.ErrorStage,
		}
		if out.ProcessorOutput != nil {
			co.ProcessorOutputJson, _ = json.Marshal(out.ProcessorOutput)
		}
		if out.GuardResult != nil {
			co.GuardResultJson, _ = json.Marshal(out.GuardResult)
		}
		if out.ExecutionResult != nil {
			co.ExecutionResultJson, _ = json.Marshal(out.ExecutionResult)
		}
		cycleOutputs = append(cycleOutputs, co)
	}

	return &gatewayv1.RunCycleResponse{Outputs: cycleOutputs}, nil
}

// SetCycleInterval changes the analysis cycle interval at runtime.
func (s *GRPCServer) SetCycleInterval(ctx context.Context, req *gatewayv1.SetCycleIntervalRequest) (*gatewayv1.SetCycleIntervalResponse, error) {
	newInterval := int(req.GetIntervalSeconds())

	if newInterval < 60 {
		return nil, status.Errorf(codes.InvalidArgument, "interval_seconds must be >= 60, got %d", newInterval)
	}
	if newInterval > 86400 {
		return nil, status.Errorf(codes.InvalidArgument, "interval_seconds must be <= 86400 (24h), got %d", newInterval)
	}

	oldInterval := s.scheduler.CurrentIntervalSeconds()

	if err := s.settingsStore.SetCycleInterval(ctx, newInterval); err != nil {
		s.log.Error().Err(err).Int("interval", newInterval).Msg("set_cycle_interval_persist_failed")
		return nil, status.Errorf(codes.Internal, "failed to persist interval: %v", err)
	}

	s.scheduler.UpdateInterval(time.Duration(newInterval) * time.Second)

	s.log.Info().
		Int("old_interval_seconds", oldInterval).
		Int("new_interval_seconds", newInterval).
		Msg("cycle_interval_updated_via_dashboard")

	// Publish notification.
	s.transport.Publish(ctx,
		alert.NewEvent(alert.SourceGateway, alert.TypeIntervalChanged, alert.SeverityInfo,
			fmt.Sprintf("Cycle interval changed from %ds to %ds", oldInterval, newInterval)).
			WithDetails(map[string]interface{}{
				"old_interval_seconds": oldInterval,
				"new_interval_seconds": newInterval,
			}),
	)

	return &gatewayv1.SetCycleIntervalResponse{
		Success:                true,
		CurrentIntervalSeconds: int32(newInterval),
		Message:                fmt.Sprintf("Cycle interval updated to %d seconds. Takes effect immediately.", newInterval),
	}, nil
}

// ---------------------------------------------------------------------------
// Symbol Management
// ---------------------------------------------------------------------------

// SetActiveSymbols updates the user's active symbol selection.
func (s *GRPCServer) SetActiveSymbols(ctx context.Context, req *gatewayv1.SetActiveSymbolsRequest) (*gatewayv1.SetActiveSymbolsResponse, error) {
	oldSymbols := s.symbolStore.GetActiveSymbols(ctx)
	ok := s.symbolStore.SetActiveSymbols(ctx, req.GetSymbols())
	active := s.symbolStore.GetActiveSymbols(ctx)

	if ok {
		s.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeSymbolsChanged, alert.SeverityInfo,
				fmt.Sprintf("Active symbols changed: %s", strings.Join(active, ", "))).
				WithDetails(map[string]interface{}{
					"old_symbols": oldSymbols,
					"new_symbols": active,
				}),
		)
	}

	return &gatewayv1.SetActiveSymbolsResponse{
		Success:       ok,
		ActiveSymbols: active,
	}, nil
}

// GetActiveSymbols returns the current active symbol selection.
func (s *GRPCServer) GetActiveSymbols(ctx context.Context, _ *gatewayv1.GetActiveSymbolsRequest) (*gatewayv1.GetActiveSymbolsResponse, error) {
	symbols := s.symbolStore.GetActiveSymbols(ctx)
	return &gatewayv1.GetActiveSymbolsResponse{
		Symbols: symbols,
		Source:  "redis",
	}, nil
}

// ResetActiveSymbols resets symbol selection to config defaults.
func (s *GRPCServer) ResetActiveSymbols(ctx context.Context, _ *gatewayv1.ResetActiveSymbolsRequest) (*gatewayv1.ResetActiveSymbolsResponse, error) {
	oldSymbols := s.symbolStore.GetActiveSymbols(ctx)
	ok := s.symbolStore.ResetToDefaults(ctx)
	active := s.symbolStore.GetActiveSymbols(ctx)

	if ok {
		s.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeSymbolsChanged, alert.SeverityInfo,
				fmt.Sprintf("Symbols reset to defaults: %s", strings.Join(active, ", "))).
				WithDetails(map[string]interface{}{
					"old_symbols": oldSymbols,
					"new_symbols": active,
					"source":      "reset_to_defaults",
				}),
		)
	}

	return &gatewayv1.ResetActiveSymbolsResponse{
		Success:       ok,
		ActiveSymbols: active,
	}, nil
}

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

// GetGatewayConfig returns the current runtime-configurable settings.
func (s *GRPCServer) GetGatewayConfig(ctx context.Context, _ *gatewayv1.GetGatewayConfigRequest) (*gatewayv1.GetGatewayConfigResponse, error) {
	activeSymbols := s.symbolStore.GetActiveSymbols(ctx)

	source := "gateway_config"
	persisted := s.settingsStore.Load(ctx)
	if persisted.CycleIntervalSeconds > 0 {
		source = "redis"
	}

	return &gatewayv1.GetGatewayConfigResponse{
		Enabled:              s.cfg.Enabled,
		CycleIntervalSeconds: int32(s.scheduler.CurrentIntervalSeconds()),
		CycleTimeoutSeconds:  int32(s.cfg.CycleTimeoutSeconds),
		MaxConcurrentSymbols: int32(s.cfg.MaxConcurrentSymbols),
		TaCacheTtlSeconds:    int32(s.cfg.TACacheTTLSeconds),
		MacroCacheTtlSeconds: int32(s.cfg.MacroCacheTTLSeconds),
		MaxCycleRetries:      int32(s.cfg.MaxCycleRetries),
		DefaultSymbols:       s.cfg.DefaultSymbols,
		ActiveSymbols:        activeSymbols,
		ActiveSymbolsSource:  source,
		ExecutionEnabled:     s.cfg.ExecutionEnabled,
	}, nil
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

// GetHealth returns the gateway's health status.
func (s *GRPCServer) GetHealth(ctx context.Context, _ *gatewayv1.GetHealthRequest) (*gatewayv1.GetHealthResponse, error) {
	redisOK := s.redis.HealthCheck(ctx)
	engineOK := s.engine.HealthCheck(ctx)

	healthStatus := "ok"
	if !redisOK || !engineOK {
		healthStatus = "degraded"
	}

	activeCycles := int32(testutil.ToFloat64(observability.GatewayActiveCycles))

	return &gatewayv1.GetHealthResponse{
		Status:          healthStatus,
		RedisConnected:  redisOK,
		EngineConnected: engineOK,
		ActiveCycles:    activeCycles,
	}, nil
}

func panicRecoveryInterceptor(log zerolog.Logger) grpc.UnaryServerInterceptor {
	return func(
		ctx context.Context,
		req interface{},
		info *grpc.UnaryServerInfo,
		handler grpc.UnaryHandler,
	) (resp interface{}, err error) {
		defer func() {
			if r := recover(); r != nil {
				observability.LogPanicRecovery(log, r, info.FullMethod)
				err = fmt.Errorf("internal server error")
			}
		}()
		return handler(ctx, req)
	}
}
