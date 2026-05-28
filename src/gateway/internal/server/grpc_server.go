package server

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"strings"
	"sync/atomic"
	"time"

	"github.com/rs/zerolog"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/health"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"
	"google.golang.org/grpc/status"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/management"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/pipeline"
	"github.com/flamegreat-1/etradie/src/gateway/internal/settingsstore"
	"github.com/flamegreat-1/etradie/src/gateway/internal/symbolstore"

	gatewayv1 "github.com/flamegreat-1/etradie/proto/gateway/v1"
	managementv1 "github.com/flamegreat-1/etradie/proto/management/v1"
)

// GRPCServer serves the gateway gRPC API.
type GRPCServer struct {
	gatewayv1.UnimplementedGatewayServiceServer
	server        *grpc.Server
	healthServer  *health.Server
	serving       atomic.Bool
	orchestrator  *pipeline.Orchestrator
	symbolStore   *symbolstore.Store
	settingsStore *settingsstore.Store
	scheduler     *pipeline.Scheduler
	redis         *infra.RedisClient
	engine        *infra.EngineHTTPClient
	transport     *alertredis.Transport
	mgmtClient    *management.Client
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
	mgmtClient *management.Client,
	tokenService *auth.TokenService,
) *GRPCServer {
	s := &GRPCServer{
		orchestrator:  orchestrator,
		symbolStore:   symbolStore,
		settingsStore: settingsStore,
		scheduler:     scheduler,
		redis:         redis,
		engine:        engine,
		transport:     transport,
		mgmtClient:    mgmtClient,
		cfg:           cfg,
		port:          cfg.GRPCPort,
		log:           observability.Logger("grpc_server"),
	}

	// gRPC methods that bypass authentication (health checks).
	skipAuth := map[string]bool{
		"/grpc.health.v1.Health/Check": true,
		"/grpc.health.v1.Health/Watch": true,
	}

	grpcServer := grpc.NewServer(
		grpc.StatsHandler(otelgrpc.NewServerHandler()),
		grpc.ChainUnaryInterceptor(
			panicRecoveryInterceptor(s.log),
			auth.UnaryAuthInterceptor(tokenService, skipAuth),
		),
	)

	gatewayv1.RegisterGatewayServiceServer(grpcServer, s)

	// Wire the health server but DO NOT flip status to SERVING here.
	// Status is flipped immediately before grpcServer.Serve() inside
	// Start() so /readiness reports not-ready until the listener is
	// actually accepting. Audit ref: G-C4.
	healthServer := health.NewServer()
	healthServer.SetServingStatus("", healthpb.HealthCheckResponse_NOT_SERVING)
	healthpb.RegisterHealthServer(grpcServer, healthServer)
	s.healthServer = healthServer

	reflection.Register(grpcServer)

	s.server = grpcServer
	return s
}

// IsServing reports true once the gRPC listener has been bound AND the
// embedded health server has been flipped to SERVING. The HTTP server's
// /readiness handler consults this so a pod is not advertised Ready
// to Kubernetes (and therefore not added to the Service endpoints)
// until the gRPC surface can actually accept dials. Audit ref: G-C4.
func (s *GRPCServer) IsServing() bool {
	return s.serving.Load()
}

// Start begins serving gRPC. Blocks until the server stops.
//
// Order of operations matters for readiness correctness:
//
//  1. bind the TCP listener (so subsequent dials succeed),
//  2. flip the embedded health server + IsServing() flag to SERVING,
//  3. call Serve() which blocks until Stop / GracefulStop.
//
// Step 2 is performed AFTER the listener succeeds; if Listen fails the
// pod never reports Ready. Audit ref: G-C4.
func (s *GRPCServer) Start() error {
	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", s.port))
	if err != nil {
		return fmt.Errorf("grpc_server: listen on port %d: %w", s.port, err)
	}
	s.healthServer.SetServingStatus("", healthpb.HealthCheckResponse_SERVING)
	s.serving.Store(true)
	s.log.Info().Int("port", s.port).Msg("grpc_server_starting")
	return s.server.Serve(lis)
}

// GracefulStop gracefully stops the gRPC server.
//
// Flips IsServing() to false BEFORE GracefulStop so a draining pod
// fails readiness during connection draining. New dials are refused
// at the Service-endpoint level once readiness flips; in-flight RPCs
// continue to completion under GracefulStop's normal semantics.
// Audit ref: G-C4.
func (s *GRPCServer) GracefulStop() {
	s.log.Info().Msg("grpc_server_shutting_down")
	s.serving.Store(false)
	if s.healthServer != nil {
		s.healthServer.SetServingStatus("", healthpb.HealthCheckResponse_NOT_SERVING)
	}
	s.server.GracefulStop()
}

// InternalServer returns the underlying grpc.Server. Used by test
// harnesses to serve on bufconn while preserving the auth interceptor
// chain wired during NewGRPCServer construction.
func (s *GRPCServer) InternalServer() *grpc.Server {
	return s.server
}

// ---------------------------------------------------------------------------
// Cycle Management
// ---------------------------------------------------------------------------

// RunCycle triggers an analysis cycle.
func (s *GRPCServer) RunCycle(ctx context.Context, req *gatewayv1.RunCycleRequest) (*gatewayv1.RunCycleResponse, error) {
	userID := auth.UserIDFromContext(ctx)
	symbols := req.GetSymbols()
	if len(symbols) == 0 {
		symbols = s.symbolStore.GetActiveSymbols(ctx, userID)
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

// ConfirmSetup runs a targeted TA-only confirmation pulse for an
// instant-mode watcher. Called by Module B's Execution watcher when
// live price enters the POI zone. Bypasses Macro, RAG, and Processor.
func (s *GRPCServer) ConfirmSetup(ctx context.Context, req *gatewayv1.ConfirmSetupRequest) (*gatewayv1.ConfirmSetupResponse, error) {
	symbol := req.GetSymbol()
	analysisID := req.GetAnalysisId()
	traceID := req.GetTraceId()

	if symbol == "" || analysisID == "" {
		return nil, status.Errorf(codes.InvalidArgument, "symbol and analysis_id are required")
	}

	s.log.Info().
		Str("symbol", symbol).
		Str("analysis_id", analysisID).
		Str("trace_id", traceID).
		Msg("confirm_setup_received")

	// Extract optional LTF params for lightweight confirmation path
	var ltfParams *pipeline.LTFConfirmParams
	if req.GetObUpper() > 0 && req.GetObLower() > 0 {
		ltfParams = &pipeline.LTFConfirmParams{
			Symbol:       symbol,
			Direction:    req.GetDirection(),
			LTFTimeframe: req.GetLtfTimeframe(),
			OBUpper:      req.GetObUpper(),
			OBLower:      req.GetObLower(),
			EntryPrice:   req.GetEntryPrice(),
			StopLoss:     req.GetStopLoss(),
			HTFTimeframe: req.GetHtfTimeframe(),
		}
	}

	result := s.orchestrator.RunConfirmationPulseWithParams(ctx, symbol, analysisID, traceID, ltfParams)

	s.log.Info().
		Str("symbol", symbol).
		Str("analysis_id", analysisID).
		Bool("confirmed", result.Confirmed).
		Str("reason", result.Reason).
		Str("trace_id", traceID).
		Msg("confirm_setup_completed")

	return &gatewayv1.ConfirmSetupResponse{
		Confirmed:       result.Confirmed,
		LtfConfirmation: result.LTFConfirmation,
		Reason:          result.Reason,
		TraceId:         traceID,
	}, nil
}

// NotifyExecutionCompleted is called by Module B when a market order is filled.
// This is Step 7 of the architecture: Gateway orchestrates handoff to Module C.
func (s *GRPCServer) NotifyExecutionCompleted(ctx context.Context, req *gatewayv1.NotifyExecutionCompletedRequest) (*gatewayv1.NotifyExecutionCompletedResponse, error) {
	s.log.Info().
		Str("symbol", req.GetSymbol()).
		Str("broker_order_id", req.GetBrokerOrderId()).
		Float64("fill_price", req.GetFillPrice()).
		Float64("lot_size", req.GetLotSize()).
		Str("analysis_id", req.GetAnalysisId()).
		Str("trace_id", req.GetTraceId()).
		Msg("execution_handoff_received_from_module_b")

	// Emit an alert event for dashboard visibility.
	s.transport.Publish(ctx,
		alert.NewEvent(alert.SourceGateway, alert.TypeExecutionHandoff, alert.SeverityInfo,
			fmt.Sprintf("Trade filled for %s — handing off to Module C for management.", req.GetSymbol())).
			WithUserID(auth.UserIDFromContext(ctx)).
			WithSymbol(req.GetSymbol()).
			WithTraceID(req.GetTraceId()).
			WithDetails(map[string]interface{}{
				"broker_order_id": req.GetBrokerOrderId(),
				"fill_price":      req.GetFillPrice(),
				"slippage":        req.GetSlippage(),
				"lot_size":        req.GetLotSize(),
				"analysis_id":     req.GetAnalysisId(),
			}),
	)

	if s.mgmtClient == nil {
		s.log.Warn().
			Str("symbol", req.GetSymbol()).
			Msg("management_client_not_configured_skipping_handoff")
		return &gatewayv1.NotifyExecutionCompletedResponse{Success: true}, nil
	}

	// Best-effort: fetch symbol metadata (point size, digits) from the
	// engine's broker bridge. The Management service needs these for
	// dynamic pip calculations (breakeven buffer, trailing stop). If
	// the call fails, Management falls back to a safe default (0.0001).
	var symbolPoint float64
	var symbolDigits int32
	symbolInfoPath := fmt.Sprintf("/internal/broker/symbol_info?symbol=%s", req.GetSymbol())
	if symbolInfo, err := s.engine.GetJSON(ctx, symbolInfoPath); err == nil {
		if p, ok := symbolInfo["point"].(float64); ok {
			symbolPoint = p
		}
		if d, ok := symbolInfo["digits"].(float64); ok {
			symbolDigits = int32(d)
		}
	} else {
		s.log.Warn().
			Err(err).
			Str("symbol", req.GetSymbol()).
			Msg("symbol_info_fetch_failed_using_defaults")
	}

	mgmtReq := &managementv1.RegisterFilledTradeRequest{
		Symbol:          req.GetSymbol(),
		Direction:       req.GetDirection(),
		BrokerOrderId:   req.GetBrokerOrderId(),
		FillPrice:       req.GetFillPrice(),
		StopLoss:        req.GetStopLoss(),
		Tp1Price:        req.GetTp1Price(),
		Tp1Pct:          req.GetTp1Pct(),
		Tp2Price:        req.GetTp2Price(),
		Tp2Pct:          req.GetTp2Pct(),
		Tp3Price:        req.GetTp3Price(),
		Tp3Pct:          req.GetTp3Pct(),
		LotSize:         req.GetLotSize(),
		RiskAmount:      req.GetRiskAmount(),
		RiskPercent:     req.GetRiskPercent(),
		RrRatio:         req.GetRrRatio(),
		Grade:           req.GetGrade(),
		TradingStyle:    req.GetTradingStyle(),
		Session:         req.GetSession(),
		SetupType:       req.GetSetupType(), // Threaded completely from Module A
		ExecutionMode:   req.GetExecutionMode(),
		ConfluenceScore: req.GetConfluenceScore(),
		Slippage:        req.GetSlippage(),
		AnalysisId:      req.GetAnalysisId(),
		TraceId:         req.GetTraceId(),
		Point:           symbolPoint,
		Digits:          symbolDigits,
	}

	tradeID, err := s.mgmtClient.RegisterFilledTrade(ctx, mgmtReq)
	if err != nil {
		s.log.Error().Err(err).
			Str("symbol", req.GetSymbol()).
			Str("broker_order_id", req.GetBrokerOrderId()).
			Msg("failed_to_register_trade_with_management_engine")

		s.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeManagementHandoffFailed, alert.SeverityError,
				fmt.Sprintf("Failed to handoff filled trade %s to Management: %v", req.GetSymbol(), err)).
				WithUserID(auth.UserIDFromContext(ctx)).
				WithSymbol(req.GetSymbol()).
				WithTraceID(req.GetTraceId()),
		)

		return nil, status.Errorf(codes.Internal, "failed to handoff to management: %v", err)
	}

	s.log.Info().
		Str("symbol", req.GetSymbol()).
		Str("management_trade_id", tradeID).
		Msg("successfully_handed_off_trade_to_module_c")

	return &gatewayv1.NotifyExecutionCompletedResponse{
		Success:           true,
		ManagementTradeId: tradeID,
	}, nil
}

// SetCycleInterval changes the analysis cycle interval at runtime.
func (s *GRPCServer) SetCycleInterval(ctx context.Context, req *gatewayv1.SetCycleIntervalRequest) (*gatewayv1.SetCycleIntervalResponse, error) {
	userID := auth.UserIDFromContext(ctx)
	newInterval := int(req.GetIntervalSeconds())

	if newInterval < 60 {
		return nil, status.Errorf(codes.InvalidArgument, "interval_seconds must be >= 60, got %d", newInterval)
	}
	if newInterval > 86400 {
		return nil, status.Errorf(codes.InvalidArgument, "interval_seconds must be <= 86400 (24h), got %d", newInterval)
	}

	// Free tier users do not get automated scheduling — block interval changes.
	claims := auth.ClaimsFromContext(ctx)
	if claims != nil && claims.Role != "admin" && claims.Tier == "free" {
		return nil, status.Errorf(codes.PermissionDenied, "Automated scheduling is not available on the Free tier. Upgrade to Pro to configure cycle intervals.")
	}

	oldInterval := s.scheduler.CurrentIntervalForUser(ctx, userID)

	// Persist and update this user's interval only. Other users are unaffected.
	// The user's goroutine periodically re-reads from Redis.
	s.scheduler.UpdateUserInterval(ctx, userID, time.Duration(newInterval)*time.Second)

	s.log.Info().
		Str("user_id", userID).
		Int("old_interval_seconds", oldInterval).
		Int("new_interval_seconds", newInterval).
		Msg("cycle_interval_updated_via_dashboard")

	// Publish notification.
	s.transport.Publish(ctx,
		alert.NewEvent(alert.SourceGateway, alert.TypeIntervalChanged, alert.SeverityInfo,
			fmt.Sprintf("Cycle interval changed from %ds to %ds", oldInterval, newInterval)).
			WithUserID(userID).
			WithDetails(map[string]interface{}{
				"old_interval_seconds": oldInterval,
				"new_interval_seconds": newInterval,
			}),
	)

	return &gatewayv1.SetCycleIntervalResponse{
		Success:                true,
		CurrentIntervalSeconds: int32(newInterval),
		Message:                fmt.Sprintf("Cycle interval updated to %d seconds. Your scheduler goroutine will pick up the change within 5 minutes.", newInterval),
	}, nil
}

// ---------------------------------------------------------------------------
// Symbol Management
// ---------------------------------------------------------------------------

// SetActiveSymbols updates the user's active symbol selection.
func (s *GRPCServer) SetActiveSymbols(ctx context.Context, req *gatewayv1.SetActiveSymbolsRequest) (*gatewayv1.SetActiveSymbolsResponse, error) {
	claims := auth.ClaimsFromContext(ctx)
	if claims != nil && claims.Role != "admin" && claims.Tier == "free" && len(req.GetSymbols()) > 1 {
		s.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeSymbolsChanged, alert.SeverityWarning,
				"Free tier is restricted to 1 active symbol. Upgrade to Pro for unlimited tracking.").
				WithUserID(claims.UserID).
				WithDetails(map[string]interface{}{
					"attempted_symbols": len(req.GetSymbols()),
				}),
		)
		return nil, status.Errorf(codes.PermissionDenied, "Free tier is restricted to 1 active symbol. Upgrade to Pro for unlimited tracking.")
	}

	userID := claims.UserID
	oldSymbols := s.symbolStore.GetActiveSymbols(ctx, userID)
	ok := s.symbolStore.SetActiveSymbols(ctx, userID, req.GetSymbols())
	active := s.symbolStore.GetActiveSymbols(ctx, userID)

	if ok {
		s.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeSymbolsChanged, alert.SeverityInfo,
				fmt.Sprintf("Active symbols changed: %s", strings.Join(active, ", "))).
				WithUserID(auth.UserIDFromContext(ctx)).
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
	userID := auth.UserIDFromContext(ctx)
	symbols := s.symbolStore.GetActiveSymbols(ctx, userID)
	return &gatewayv1.GetActiveSymbolsResponse{
		Symbols: symbols,
		Source:  "redis",
	}, nil
}

// ResetActiveSymbols resets symbol selection to config defaults.
func (s *GRPCServer) ResetActiveSymbols(ctx context.Context, _ *gatewayv1.ResetActiveSymbolsRequest) (*gatewayv1.ResetActiveSymbolsResponse, error) {
	userID := auth.UserIDFromContext(ctx)
	oldSymbols := s.symbolStore.GetActiveSymbols(ctx, userID)
	ok := s.symbolStore.ResetToDefaults(ctx, userID)
	active := s.symbolStore.GetActiveSymbols(ctx, userID)

	if ok {
		s.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeSymbolsChanged, alert.SeverityInfo,
				fmt.Sprintf("Symbols reset to defaults: %s", strings.Join(active, ", "))).
				WithUserID(auth.UserIDFromContext(ctx)).
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
	userID := auth.UserIDFromContext(ctx)
	activeSymbols := s.symbolStore.GetActiveSymbols(ctx, userID)

	// Read this user's interval (from Redis or config default).
	userInterval := s.scheduler.CurrentIntervalForUser(ctx, userID)

	source := "gateway_config"
	persisted := s.settingsStore.Load(ctx, userID)
	if persisted.CycleIntervalSeconds > 0 {
		source = "redis"
	}

	return &gatewayv1.GetGatewayConfigResponse{
		Enabled:              s.cfg.Enabled,
		CycleIntervalSeconds: int32(userInterval),
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

	activeCycles := int32(observability.ReadGaugeValue(observability.GatewayActiveCycles))

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
				err = status.Errorf(codes.Internal, "internal server error")
			}
		}()
		return handler(ctx, req)
	}
}
