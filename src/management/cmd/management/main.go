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
	"github.com/redis/go-redis/v9"
	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"

	managementv1 "github.com/flamegreat/etradie/proto/management/v1"
	"github.com/flamegreat/etradie/src/alert"
	alertredis "github.com/flamegreat/etradie/src/alert/redis"
	"github.com/flamegreat/etradie/src/management/internal/analytics"
	"github.com/flamegreat/etradie/src/management/internal/broker"
	"github.com/flamegreat/etradie/src/management/internal/config"
	"github.com/flamegreat/etradie/src/management/internal/constants"
	"github.com/flamegreat/etradie/src/management/internal/eod"
	mhttp "github.com/flamegreat/etradie/src/management/internal/http"
	"github.com/flamegreat/etradie/src/management/internal/invalidator"
	"github.com/flamegreat/etradie/src/management/internal/journal"
	"github.com/flamegreat/etradie/src/management/internal/monitoring"
	"github.com/flamegreat/etradie/src/management/internal/observability"
	"github.com/flamegreat/etradie/src/management/internal/server"
	"github.com/flamegreat/etradie/src/management/internal/stoploss"
	"github.com/flamegreat/etradie/src/management/internal/takeprofit"
	"github.com/flamegreat/etradie/src/management/pkg/types"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		fmt.Fprintf(os.Stderr, "management: config: %v\n", err)
		os.Exit(1)
	}

	observability.SetLevel(cfg.LogLevel)
	log := observability.Logger("main")

	log.Info().
		Int("grpc_port", cfg.GRPCPort).
		Int("http_port", cfg.HTTPPort).
		Str("broker_mode", cfg.BrokerMode).
		Msg("management_engine_starting")

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

	// Create management tables (journal, events).
	if _, err := pool.Exec(ctx, journal.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("schema_creation_failed")
	}

	// ── Broker implementation ─────────────────────────────────────────
	var bp broker.Port
	if cfg.IsMT5Mode() {
		bp = broker.NewMT5Broker(cfg.BrokerBridgeURL, cfg.BrokerTimeoutMs)
		log.Info().Str("url", cfg.BrokerBridgeURL).Msg("broker_mt5_bridge_configured")
	} else {
		// Mock logic is omitted for clean structure. Can be re-injected later.
		log.Fatal().Msg("mock_broker_not_supported_in_this_build_flavor")
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

	// ── Shared alert transport ────────────────────────────────────────
	alertHub := alert.NewHub()
	defer alertHub.Close()

	alertTransport := alertredis.NewTransport(rdb, alertHub, alertredis.TransportConfig{})
	alertTransport.Start(ctx)
	defer alertTransport.Close()

	// ── Stores ────────────────────────────────────────────────────────
	journalRepo := journal.NewRepository(pool)

	// ── Sub-engines (dependency order) ────────────────────────────────
	beEngine := stoploss.NewBreakevenEngine(bp, journalRepo)
	trailEngine := stoploss.NewTrailingEngine(bp, journalRepo)
	tpExecutor := takeprofit.NewExecutor(bp, journalRepo)

	// ── Monitoring manager ────────────────────────────────────────────
	mgr := monitoring.NewManager(
		bp, beEngine, trailEngine, tpExecutor,
		journalRepo, alertTransport, cfg.TickPollIntervalMs,
	)

	// ── Invalidation Engines ──────────────────────────────────────────
	structuralEngine := invalidator.NewStructuralEngine(bp, journalRepo, alertTransport)
	macroEngine := invalidator.NewMacroEngine(bp, journalRepo, alertTransport)

	// Subscribe to internal hub for engine signals
	go func() {
		sub := alertHub.Subscribe()
		defer alertHub.Unsubscribe(sub)

		for evt := range sub.C {
			switch evt.Type {
			case alert.TypeCandleClosed:
				trades := mgr.GetAllTrades()
				for _, t := range trades {
					if t.Symbol == evt.Symbol && t.Status == constants.StatusOpen {
						price, err := mgr.GetPriceForSymbol(ctx, evt.Symbol)
						if err == nil {
							structuralEngine.EvaluateStructuralBreak(ctx, t, evt.Direction, price)
						}
					}
				}
			case alert.TypeCOTFlip:
				trades := mgr.GetAllTrades()
				for _, t := range trades {
					if t.Symbol == evt.Symbol && t.Status == constants.StatusOpen {
						price, err := mgr.GetPriceForSymbol(ctx, evt.Symbol)
						if err == nil {
							macroEngine.EvaluateCOTFlip(ctx, t, evt.Direction, price)
						}
					}
				}
			}
		}
	}()

	// ── EOD scheduler (runs temporal checks every minute) ─────────────
	eodScheduler := eod.NewScheduler(
		bp,
		journalRepo,
		alertTransport,
		mgr.GetAllTrades,
		func(ctx context.Context, symbol string) (float64, error) {
			return mgr.GetPriceForSymbol(ctx, symbol)
		},
	)
	eodScheduler.Start()

	// ── Analytics ─────────────────────────────────────────────────────
	metricsEngine := analytics.NewMetrics(pool)

	// ── Restore active trades from database on restart ────────────────
	activeTrades, err := journalRepo.GetActiveTrades(ctx)
	if err != nil {
		log.Error().Err(err).Msg("active_trades_restore_failed")
	} else if len(activeTrades) > 0 {
		log.Info().Int("count", len(activeTrades)).Msg("restoring_active_trades")
		for _, rec := range activeTrades {
			trade := restoreTradeFromRecord(rec)
			mgr.RegisterTrade(trade)
		}
	}

	// ── gRPC server ───────────────────────────────────────────────────
	mgmtServer := server.NewManagementServer(mgr, journalRepo, metricsEngine)

	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", cfg.GRPCPort))
	if err != nil {
		log.Fatal().Err(err).Int("port", cfg.GRPCPort).Msg("grpc_listen_failed")
	}

	grpcServer := grpc.NewServer()
	managementv1.RegisterManagementServiceServer(grpcServer, mgmtServer)
	reflection.Register(grpcServer)

	go func() {
		log.Info().Int("port", cfg.GRPCPort).Msg("management_grpc_server_started")
		if err := grpcServer.Serve(lis); err != nil {
			log.Fatal().Err(err).Msg("grpc_serve_failed")
		}
	}()

	// ── HTTP server (Dashboard REST API) ──────────────────────────────
	httpServer := mhttp.NewServer(cfg.HTTPPort, mgr, journalRepo, metricsEngine)
	go func() {
		if err := httpServer.Start(); err != nil {
			log.Fatal().Err(err).Msg("http_serve_failed")
		}
	}()

	// ── Publish service started event ─────────────────────────────────
	alertTransport.Publish(ctx,
		alert.NewEvent(alert.SourceTradeManager, alert.TypeServiceStarted, alert.SeverityInfo,
			"Trade Management engine started").
			WithDetails(map[string]interface{}{
				"grpc_port":     cfg.GRPCPort,
				"broker_mode":   cfg.BrokerMode,
				"active_trades": len(activeTrades),
			}),
	)

	log.Info().
		Int("grpc_port", cfg.GRPCPort).
		Int("active_trades", len(activeTrades)).
		Msg("management_engine_ready")

	// ── Graceful shutdown ────────────────────────────────────────────
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	log.Info().Msg("shutdown_signal_received")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	alertTransport.Publish(shutdownCtx,
		alert.NewEvent(alert.SourceTradeManager, alert.TypeServiceStopping, alert.SeverityInfo,
			"Trade Management engine shutting down"),
	)

	// Shutdown order: HTTP -> gRPC → EOD scheduler → monitoring → alerts → DB.
	httpServer.Shutdown(shutdownCtx)
	grpcServer.GracefulStop()
	eodScheduler.Shutdown()
	mgr.Shutdown()
	alertTransport.Close()
	pool.Close()

	log.Info().Msg("management_engine_stopped")
}

// restoreTradeFromRecord reconstructs an in-memory Trade from a DB record.
// Used on service restart to resume monitoring of active trades.
func restoreTradeFromRecord(rec *journal.TradeRecord) *types.Trade {
	return &types.Trade{
		TradeID:          rec.TradeID,
		Symbol:           rec.Symbol,
		Direction:        constants.Direction(rec.Direction),
		BrokerOrderID:    rec.BrokerOrderID,
		AnalysisID:       rec.AnalysisID,
		TradingStyle:     constants.TradingStyle(rec.TradingStyle),
		Grade:            rec.Grade,
		Session:          rec.Session,
		SetupType:        rec.SetupType,
		ExecutionMode:    rec.ExecutionMode,
		ConfluenceScore:  rec.ConfluenceScore,
		EntryPrice:       rec.EntryPrice,
		StopLoss:         rec.StopLoss,
		InitialSL:        rec.InitialSL,
		TP1Price:         rec.TP1Price,
		TP2Price:         rec.TP2Price,
		TP3Price:         rec.TP3Price,
		TotalLotSize:     rec.TotalLotSize,
		RemainingLotSize: rec.TotalLotSize,
		RiskAmount:       rec.RiskAmount,
		RiskPercent:      rec.RiskPercent,
		Slippage:         rec.Slippage,
		Status:           constants.TradeStatus(rec.Status),
		OpenedAt:         rec.OpenedAt,
	}
}
