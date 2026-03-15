package main

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"

	executionv1 "github.com/flamegreat/etradie/proto/execution/v1"
	"github.com/flamegreat/etradie/src/execution/internal/audit"
	"github.com/flamegreat/etradie/src/execution/internal/broker"
	mockbroker "github.com/flamegreat/etradie/src/execution/internal/broker/mock"
	"github.com/flamegreat/etradie/src/execution/internal/broker/mt5"
	"github.com/flamegreat/etradie/src/execution/internal/config"
	"github.com/flamegreat/etradie/src/execution/internal/executor"
	"github.com/flamegreat/etradie/src/execution/internal/notify"
	"github.com/flamegreat/etradie/src/execution/internal/observability"
	"github.com/flamegreat/etradie/src/execution/internal/server"
	"github.com/flamegreat/etradie/src/execution/internal/sizing"
	"github.com/flamegreat/etradie/src/execution/internal/state"
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
		Str("broker_mode", cfg.BrokerMode).
		Str("execution_mode", cfg.DefaultExecutionMode).
		Int("max_concurrent", cfg.MaxConcurrentTrades).
		Msg("execution_engine_starting")

	// Database connection pool.
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

	if _, err := pool.Exec(ctx, audit.CreateTableSQL()); err != nil {
		log.Fatal().Err(err).Msg("audit_table_creation_failed")
	}

	// Select broker implementation.
	var bp broker.Port
	if cfg.IsMT5Mode() {
		bp = mt5.NewBridge(cfg.BrokerBridgeURL, cfg.BrokerTimeoutMs)
		log.Info().Str("url", cfg.BrokerBridgeURL).Msg("broker_mt5_bridge_configured")
	} else {
		bp = mockbroker.NewBroker(cfg.MockBrokerBalance)
		log.Info().Float64("balance", cfg.MockBrokerBalance).Msg("broker_mock_configured")
	}

	// Build components in dependency order.
	sm := state.NewManager(bp)
	v := validator.NewValidator(cfg, sm, bp)
	s := sizing.NewEngine(cfg, bp)
	e := executor.NewExecutor(bp, cfg.BrokerTimeoutMs)
	auditStore := audit.NewStore(pool)
	al := audit.NewLogger(auditStore)
	n := notify.NewNotifier()

	execServer := server.NewExecutionServer(cfg, v, s, e, sm, bp, al, n)

	// Start metrics + health HTTP server.
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	mux.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	})

	httpServer := &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.MetricsPort),
		Handler:      mux,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	go func() {
		log.Info().Int("port", cfg.MetricsPort).Msg("metrics_http_server_started")
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal().Err(err).Msg("metrics_http_server_failed")
		}
	}()

	// Start gRPC server.
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

	// Graceful shutdown.
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	log.Info().Msg("shutdown_signal_received")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	grpcServer.GracefulStop()
	_ = httpServer.Shutdown(shutdownCtx)
	pool.Close()

	log.Info().Msg("execution_engine_stopped")
}
