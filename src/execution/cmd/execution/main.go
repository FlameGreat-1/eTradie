package main

import (
	"context"
	"fmt"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"

	executionv1 "github.com/flamegreat/etradie/proto/execution/v1"
	"github.com/flamegreat/etradie/src/alert"
	"github.com/flamegreat/etradie/src/alert/alertredis"
	"github.com/redis/go-redis/v9"
	"github.com/flamegreat/etradie/src/execution/internal/audit"
	"github.com/flamegreat/etradie/src/execution/internal/broker"
	mockbroker "github.com/flamegreat/etradie/src/execution/internal/broker/mock"
	"github.com/flamegreat/etradie/src/execution/internal/broker/mt5"
	"github.com/flamegreat/etradie/src/execution/internal/config"
	"github.com/flamegreat/etradie/src/execution/internal/executor"
	"github.com/flamegreat/etradie/src/execution/internal/observability"
	"github.com/flamegreat/etradie/src/execution/internal/server"
	"github.com/flamegreat/etradie/src/execution/internal/sizing"
	"github.com/flamegreat/etradie/src/execution/internal/state"
	"github.com/flamegreat/etradie/src/execution/internal/store"
	"github.com/flamegreat/etradie/src/execution/internal/validator"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		fmt.Fprintf(os.Stderr, "execution: config: %v\n", err)
		os.Exit(1)
	}

	observability.SetLevel(cfg.LogLevel)
	log := observability.Logger("main")

	log.Info().
		Int("grpc_port", cfg.GRPCPort).
		Int("http_port", cfg.HTTPPort).
		Str("broker_mode", cfg.BrokerMode).
		Str("execution_mode", cfg.DefaultExecutionMode).
		Int("max_concurrent", cfg.MaxConcurrentTrades).
		Msg("execution_engine_starting")

	// ── Database connection pool ──────────────────────────────────────
	ctx := context.Background()
	poolCfg, err := pgxpool.ParseConfig(cfg.DatabaseURL)
	if err != nil {
		log.Fatal().Err(err).Msg("database_config_parse_failed")
	}
	poolCfg.MaxConns = int32(cfg.DatabaseMaxConns)
	poolCfg.MinConns = int32(cfg.DatabaseMinConns)
	poolCfg.MaxConnIdleTime = time.Duration(cfg.DatabaseMaxIdleMs) * time.Millisecond
	poolCfg.MaxConnLifetime = time.Duration(cfg.DatabaseConnMaxLife) * time.Second

	pool, err := pgxpool.NewWithConfig(ctx, poolCfg)
	if err != nil {
		log.Fatal().Err(err).Msg("database_pool_create_failed")
	}
	defer pool.Close()

	if err := pool.Ping(ctx); err != nil {
		log.Fatal().Err(err).Msg("database_ping_failed")
	}

	// Create all execution tables (audit logs, pnl tracker, settings).
	if _, err := pool.Exec(ctx, store.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("schema_creation_failed")
	}

	// ── Broker implementation ─────────────────────────────────────────
	var bp broker.Port
	if cfg.IsMT5Mode() {
		bp = mt5.NewBridge(cfg.BrokerBridgeURL, cfg.BrokerTimeoutMs)
		log.Info().Str("url", cfg.BrokerBridgeURL).Msg("broker_mt5_bridge_configured")
	} else {
		bp = mockbroker.NewBroker(cfg.MockBrokerBalance)
		log.Info().Float64("balance", cfg.MockBrokerBalance).Msg("broker_mock_configured")
	}

	// ── Redis Connection (for shared alerts) ──────────────────────────
	opts, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		log.Fatal().Err(err).Msg("redis_url_parse_failed")
	}
	rdb := redis.NewClient(opts)
	defer rdb.Close()
	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Fatal().Err(err).Msg("redis_ping_failed")
	}

	// ── Shared alert transport (serves all modules) ───────────────────
	alertTransport, err := alertredis.NewTransport(ctx, rdb)
	if err != nil {
		log.Fatal().Err(err).Msg("alert_transport_init_failed")
	}
	defer alertTransport.Close()

	// ── Stores ────────────────────────────────────────────────────────
	auditStore := store.NewAuditStore(pool)
	pnlStore := store.NewPnLStore(pool)
	settingsStore := store.NewSettingsStore(pool)

	// ── Components (dependency order) ─────────────────────────────────
	sm := state.NewManager(bp, pnlStore)
	v := validator.NewValidator(cfg, sm, bp)
	s := sizing.NewEngine(cfg, bp)
	e := executor.NewExecutor(bp, cfg.BrokerTimeoutMs)
	al := audit.NewLogger(auditStore)

	// ── gRPC server ───────────────────────────────────────────────────
	execServer := server.NewExecutionServer(cfg, v, s, e, sm, bp, al, alertTransport, settingsStore)

	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", cfg.GRPCPort))
	if err != nil {
		log.Fatal().Err(err).Int("port", cfg.GRPCPort).Msg("grpc_listen_failed")
	}

	grpcServer := grpc.NewServer()
	executionv1.RegisterExecutionServiceServer(grpcServer, execServer)
	reflection.Register(grpcServer)

	go func() {
		log.Info().Int("port", cfg.GRPCPort).Msg("execution_grpc_server_started")
		if err := grpcServer.Serve(lis); err != nil {
			log.Fatal().Err(err).Msg("grpc_serve_failed")
		}
	}()

	// ── HTTP API server (REST + WebSocket + metrics + health) ─────────
	httpServer := server.NewHTTPServer(cfg.HTTPPort, sm, bp, settingsStore, al, alertTransport)

	go func() {
		if err := httpServer.Start(); err != nil {
			log.Fatal().Err(err).Msg("http_api_server_failed")
		}
	}()

	// ── Publish service started event ─────────────────────────────────
	alertTransport.Publish(ctx,
		alert.NewEvent(alert.SourceExecution, alert.TypeServiceStarted, alert.SeverityInfo,
			"Execution engine started").
			WithDetails(map[string]interface{}{
				"grpc_port":      cfg.GRPCPort,
				"http_port":      cfg.HTTPPort,
				"broker_mode":    cfg.BrokerMode,
				"execution_mode": cfg.DefaultExecutionMode,
			}),
	)

	log.Info().
		Int("grpc_port", cfg.GRPCPort).
		Int("http_port", cfg.HTTPPort).
		Msg("execution_engine_ready")

	// ── Graceful shutdown ────────────────────────────────────────────
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	log.Info().Msg("shutdown_signal_received")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	alertTransport.Publish(shutdownCtx,
		alert.NewEvent(alert.SourceExecution, alert.TypeServiceStopping, alert.SeverityInfo,
			"Execution engine shutting down"),
	)

	grpcServer.GracefulStop()
	execServer.Close()
	_ = httpServer.Shutdown(shutdownCtx)
	alertTransport.Close()
	pool.Close()

	log.Info().Msg("execution_engine_stopped")
}
