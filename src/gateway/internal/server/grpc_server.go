package server

import (
	"context"
	"encoding/json"
	"fmt"
	"net"

	"github.com/rs/zerolog"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"google.golang.org/grpc"
	"google.golang.org/grpc/health"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"

	"github.com/flamegreat/etradie/src/gateway/internal/config"
	"github.com/flamegreat/etradie/src/gateway/internal/infra"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
	"github.com/flamegreat/etradie/src/gateway/internal/pipeline"
	"github.com/flamegreat/etradie/src/gateway/internal/symbolstore"

	gatewayv1 "github.com/flamegreat/etradie/proto/gateway/v1"
)

// GRPCServer serves the gateway gRPC API.
type GRPCServer struct {
	gatewayv1.UnimplementedGatewayServiceServer
	server       *grpc.Server
	orchestrator *pipeline.Orchestrator
	symbolStore  *symbolstore.Store
	redis        *infra.RedisClient
	engine       *infra.EngineClient
	port         int
	log          zerolog.Logger
}

// NewGRPCServer creates the gateway gRPC server.
func NewGRPCServer(
	cfg *config.Config,
	orchestrator *pipeline.Orchestrator,
	symbolStore *symbolstore.Store,
	redis *infra.RedisClient,
	engine *infra.EngineClient,
) *GRPCServer {
	s := &GRPCServer{
		orchestrator: orchestrator,
		symbolStore:  symbolStore,
		redis:        redis,
		engine:       engine,
		port:         cfg.GRPCPort,
		log:          observability.Logger("grpc_server"),
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
		cycleOutputs = append(cycleOutputs, co)
	}

	return &gatewayv1.RunCycleResponse{Outputs: cycleOutputs}, nil
}

// SetActiveSymbols updates the user's active symbol selection.
func (s *GRPCServer) SetActiveSymbols(ctx context.Context, req *gatewayv1.SetActiveSymbolsRequest) (*gatewayv1.SetActiveSymbolsResponse, error) {
	ok := s.symbolStore.SetActiveSymbols(ctx, req.GetSymbols())
	active := s.symbolStore.GetActiveSymbols(ctx)
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

// GetHealth returns the gateway's health status.
func (s *GRPCServer) GetHealth(ctx context.Context, _ *gatewayv1.GetHealthRequest) (*gatewayv1.GetHealthResponse, error) {
	redisOK := s.redis.HealthCheck(ctx)
	engineOK := s.engine.HealthCheck(ctx)

	status := "ok"
	if !redisOK || !engineOK {
		status = "degraded"
	}

	return &gatewayv1.GetHealthResponse{
		Status:          status,
		RedisConnected:  redisOK,
		EngineConnected: engineOK,
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
