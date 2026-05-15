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

	managementv1 "github.com/flamegreat-1/etradie/proto/management/v1"
	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/management/internal/analytics"
	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/broker/mock"
	"github.com/flamegreat-1/etradie/src/management/internal/config"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/eod"
	mhttp "github.com/flamegreat-1/etradie/src/management/internal/http"
	"github.com/flamegreat-1/etradie/src/management/internal/invalidator"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/monitoring"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
	"github.com/flamegreat-1/etradie/src/management/internal/server"
	"github.com/flamegreat-1/etradie/src/management/internal/stoploss"
	"github.com/flamegreat-1/etradie/src/management/internal/takeprofit"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
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

	// -- Auth configuration -----------------------------------------------
	authCfg, err := auth.LoadConfig()
	if err != nil {
		log.Fatal().Err(err).Msg("auth_config_load_failed")
	}
	tokenService := auth.NewTokenService(authCfg)
	log.Info().Msg("auth_service_initialized")

	// -- Database connection pool ------------------------------------------
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

	// Create management tables (journal, events) with user_id columns.
	if _, err := pool.Exec(ctx, journal.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("schema_creation_failed")
	}

	// Ensure auth schema exists (idempotent). The auth tables live in the
	// same PostgreSQL instance. Management needs read access to auth_users
	// to look up user details when issuing service tokens on restart.
	if _, err := pool.Exec(ctx, auth.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("auth_schema_creation_failed")
	}
	userStore := auth.NewUserStore(pool)

	// -- Broker implementation ---------------------------------------------
	var bp broker.Port
	if cfg.IsMT5Mode() {
		bp = broker.NewMT5Broker(cfg.BrokerBridgeURL, cfg.BrokerTimeoutMs, cfg.EngineInternalSecret)
		log.Info().
			Str("url", cfg.BrokerBridgeURL).
			Bool("internal_auth_configured", cfg.EngineInternalSecret != "").
			Msg("broker_mt5_bridge_configured")
	} else {
		bp = mock.NewBroker()
		log.Info().Msg("broker_mock_configured")
	}

	// -- Redis Connection (for shared alerts) ------------------------------
	opts, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		log.Fatal().Err(err).Msg("redis_url_parse_failed")
	}
	rdb := redis.NewClient(opts)
	defer rdb.Close()
	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Fatal().Err(err).Msg("redis_ping_failed")
	}

	// -- Shared alert transport --------------------------------------------
	alertHub := alert.NewHub()
	defer alertHub.Close()

	alertTransport := alertredis.NewTransport(rdb, alertHub, alertredis.TransportConfig{})
	alertTransport.Start(ctx)
	defer alertTransport.Close()

	// -- Stores ------------------------------------------------------------
	journalRepo := journal.NewRepository(pool)

	// -- Sub-engines (dependency order) ------------------------------------
	beEngine := stoploss.NewBreakevenEngine(bp, journalRepo)
	trailEngine := stoploss.NewTrailingEngine(bp, journalRepo)
	tpExecutor := takeprofit.NewExecutor(bp, journalRepo)

	// -- Monitoring manager ------------------------------------------------
	mgr := monitoring.NewManager(
		bp, beEngine, trailEngine, tpExecutor,
		journalRepo, alertTransport, cfg.TickPollIntervalMs,
	)

	// -- Invalidation Engines ----------------------------------------------
	structuralEngine := invalidator.NewStructuralEngine(bp, journalRepo, alertTransport)
	macroEngine := invalidator.NewMacroEngine(bp, journalRepo, alertTransport)
	newsEngine := invalidator.NewNewsEngine(bp, journalRepo, alertTransport, rdb)
	exposureEngine := invalidator.NewExposureEngine(bp, journalRepo, alertTransport, rdb)

	// Subscribe to internal hub for engine signals.
	// This is a system-level background goroutine that reacts to events
	// across all users' trades. The invalidation engines operate on the
	// trade's own auth context (injected by the monitoring worker).
	go func() {
		sub := alertHub.Subscribe()
		defer alertHub.Unsubscribe(sub)

		for evt := range sub.C {
			switch evt.Type {
			case alert.TypeCandleClosed:
				trades := mgr.GetAllTrades()
				for _, t := range trades {
					t.RLock()
					sym := t.Symbol
					st := t.Status
					token := t.AuthToken
					t.RUnlock()

					if sym == evt.Symbol && st != constants.StatusClosed {
						tradeCtx := auth.InjectTokenIntoContext(ctx, token)
						price, err := mgr.GetPriceForSymbol(tradeCtx, evt.Symbol)
						if err == nil {
							structuralEngine.EvaluateStructuralBreak(tradeCtx, t, evt.Direction, price)
						}
					}
				}
			case alert.TypeCOTFlip:
				trades := mgr.GetAllTrades()
				for _, t := range trades {
					t.RLock()
					sym := t.Symbol
					st := t.Status
					token := t.AuthToken
					t.RUnlock()

					if sym == evt.Symbol && st != constants.StatusClosed {
						tradeCtx := auth.InjectTokenIntoContext(ctx, token)
						price, err := mgr.GetPriceForSymbol(tradeCtx, evt.Symbol)
						if err == nil {
							macroEngine.EvaluateCOTFlip(tradeCtx, t, evt.Direction, price)
						}
					}
				}
			case alert.TypeTradeClosed:
				// When a trade is closed, check for correlation shock.
				stoppedSymbol := evt.Symbol

				// Verify if it was an SL hit (loss) by checking outcome in details.
				isLoss := false
				if evt.Details != nil {
					if outcome, ok := evt.Details["outcome"].(string); ok && outcome == string(constants.OutcomeLoss) {
						isLoss = true
					}
				}

				if isLoss {
					trades := mgr.GetAllTrades()
					for _, t := range trades {
						t.RLock()
						st := t.Status
						sym := t.Symbol
						token := t.AuthToken
						t.RUnlock()

						if st != constants.StatusClosed {
							tradeCtx := auth.InjectTokenIntoContext(ctx, token)
							price, err := mgr.GetPriceForSymbol(tradeCtx, sym)
							if err == nil {
								exposureEngine.EvaluateCorrelationShock(tradeCtx, t, stoppedSymbol, price)
							}
						}
					}
				}
			}
		}
	}()

	// -- EOD scheduler (runs temporal checks every minute) -----------------
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

	// -- Pre-News Polling Engine (runs checks every minute) ----------------
	newsEngine.StartPolling(ctx, mgr.GetAllTrades, func(ctx context.Context, symbol string) (float64, error) {
		return mgr.GetPriceForSymbol(ctx, symbol)
	})

	// -- Analytics & Reporting ---------------------------------------------
	metricsEngine := analytics.NewMetrics(pool)
	reporter := analytics.NewReporter(metricsEngine, alertTransport)

	// Schedule weekly/monthly reporting goroutine.
	go func() {
		ticker := time.NewTicker(1 * time.Hour) // Check every hour to see if it's reporting time.
		defer ticker.Stop()

		for {
			select {
			case <-ctx.Done():
				return
			case t := <-ticker.C:
				// Friday 21:00 UTC = Weekly Report
				if t.Weekday() == time.Friday && t.Hour() == 21 {
					_ = reporter.GenerateWeeklyReport(ctx)
				}
				// Last day of month 23:00 UTC = Monthly Report
				if isLastDayOfMonth(t) && t.Hour() == 23 {
					_ = reporter.GenerateMonthlyReport(ctx)
				}
			}
		}
	}()

	// -- Restore active trades from database on restart -------------------
	// Use GetAllActiveTrades (cross-user) to restore monitoring for every
	// user's active trades. Each restored trade carries its UserID from
	// the database.
	//
	// CRITICAL: Issue long-lived service tokens for each user so that
	// background operations (monitoring, EOD, news, invalidation) can
	// make authenticated broker calls from second zero after restart.
	// The system must operate autonomously 24/7 without user presence.
	activeTrades, err := journalRepo.GetAllActiveTrades(ctx)
	if err != nil {
		log.Error().Err(err).Msg("active_trades_restore_failed")
	} else if len(activeTrades) > 0 {
		log.Info().Int("count", len(activeTrades)).Msg("restoring_active_trades")

		// Collect unique user IDs from restored trades.
		userIDs := make(map[string]bool)
		for _, rec := range activeTrades {
			if rec.UserID != "" && rec.UserID != "system" {
				userIDs[rec.UserID] = true
			}
		}

		// Issue a service token for each unique user. This token carries
		// the user's identity (sub, username, role) so the Python engine
		// resolves the correct broker connection identically to a session
		// token. The service token has a 30-day TTL for autonomous operation.
		//
		// We also cache the full *auth.User row keyed by ID so the
		// restoreTradeFromRecord call below can stamp Username/Role/Tier/
		// StatusJWT onto each Trade without re-fetching the row.
		serviceTokens := make(map[string]string)     // userID -> service JWT
		userByID := make(map[string]*auth.User)      // userID -> User row
		for userID := range userIDs {
			user, err := userStore.GetUserByID(ctx, userID)
			if err != nil || user == nil {
				log.Error().Err(err).Str("user_id", userID).Msg("service_token_user_lookup_failed")
				continue
			}
			if !user.Active {
				log.Warn().Str("user_id", userID).Str("username", user.Username).Msg("skipping_service_token_for_deactivated_user")
				continue
			}
			svcToken, err := tokenService.IssueServiceToken(user.ID, user.Username, user.Role, user.Tier, user.Status)
			if err != nil {
				log.Error().Err(err).Str("user_id", userID).Msg("service_token_issue_failed")
				continue
			}
			serviceTokens[userID] = svcToken
			userByID[userID] = user
			log.Info().
				Str("user_id", userID).
				Str("username", user.Username).
				Str("role", string(user.Role)).
				Msg("service_token_issued_for_trade_restoration")
		}

		// Restore trades with their service tokens AND identity fields
		// so background workers can build claims-bearing contexts.
		for _, rec := range activeTrades {
			authToken := serviceTokens[rec.UserID] // empty if lookup failed
			user := userByID[rec.UserID]           // nil if lookup failed
			trade := restoreTradeFromRecord(rec, authToken, user)
			mgr.RegisterTrade(trade)
		}

		// Set the tick cache auth token. Any valid service token works
		// since tick prices are not user-scoped.
		for _, svcToken := range serviceTokens {
			mgr.TickCache().SetAuthToken(svcToken)
			break // Only need one token.
		}

		log.Info().
			Int("trades_restored", len(activeTrades)).
			Int("users_with_service_tokens", len(serviceTokens)).
			Msg("active_trades_restoration_complete")
	}

	// ── Startup tick-cache token (fallback for zero-trade cold starts) ──
	// When no active trades exist at startup, the tick cache has no auth
	// token and every tick_price request gets 401 Unauthorized. Issue a
	// service token from any active user so the tick cache can authenticate
	// immediately. The token will be refreshed when the first trade arrives
	// (RegisterTrade sets it) or by the 24h renewal goroutine.
	{
		users, userErr := userStore.ListActiveUsers(ctx)
		if userErr == nil && len(users) > 0 {
			firstSet := false
			for _, u := range users {
				svcToken, tokenErr := tokenService.IssueServiceToken(u.ID, u.Username, u.Role, u.Tier, u.Status)
				if tokenErr == nil {
					if !firstSet {
						mgr.TickCache().SetAuthToken(svcToken)
						log.Info().
							Str("user_id", u.ID).
							Str("username", u.Username).
							Msg("startup_tick_cache_token_issued")
						firstSet = true
					}

					// Start the state reconciler for this user to import orphaned trades
					// and listen for real-time MT5 modifications.
					reconciler := monitoring.NewStateReconciler(mgr, bp, journalRepo, alertTransport, u.ID, svcToken)

					// Run startup sync asynchronously so it doesn't block boot
					go func(r *monitoring.StateReconciler) {
						// 1. Sync orphaned MT5 positions
						_ = r.RunStartupSync(context.Background())
						// 2. Fall into websocket listening loop
						r.RunStreamListener(context.Background())
					}(reconciler)
				}
			}
		}
	}

	// -- gRPC server (with auth interceptor) -------------------------------
	mgmtServer := server.NewManagementServer(mgr, journalRepo, metricsEngine)

	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", cfg.GRPCPort))
	if err != nil {
		log.Fatal().Err(err).Int("port", cfg.GRPCPort).Msg("grpc_listen_failed")
	}

	// gRPC methods that bypass authentication (health checks).
	skipAuth := map[string]bool{
		"/grpc.health.v1.Health/Check": true,
		"/grpc.health.v1.Health/Watch": true,
	}

	grpcServer := grpc.NewServer(
		grpc.ChainUnaryInterceptor(
			auth.UnaryAuthInterceptor(tokenService, skipAuth),
		),
	)
	managementv1.RegisterManagementServiceServer(grpcServer, mgmtServer)
	reflection.Register(grpcServer)

	go func() {
		log.Info().Int("port", cfg.GRPCPort).Msg("management_grpc_server_started")
		if err := grpcServer.Serve(lis); err != nil {
			log.Fatal().Err(err).Msg("grpc_serve_failed")
		}
	}()

	// -- HTTP server (Dashboard REST API with auth + CSRF) ----------------
	// authCfg flows through so the HTTP server can build the CSRF
	// middleware (auth.RequireCSRF) AND emit the configured CSRF header
	// name in the CORS Allow-Headers preflight response.
	httpServer := mhttp.NewServer(cfg.HTTPPort, mgr, journalRepo, metricsEngine, tokenService, authCfg)
	go func() {
		if err := httpServer.Start(); err != nil {
			log.Fatal().Err(err).Msg("http_serve_failed")
		}
	}()

	// -- Proactive service token renewal ----------------------------------
	// Service tokens have a 30-day TTL. For long-running trades (swing,
	// positional), the service must proactively renew tokens before they
	// expire. This goroutine runs every 24 hours and re-issues service
	// tokens for all users with active trades.
	go func() {
		// Check every 24 hours. Service tokens last 30 days, so daily
		// checks give ample margin for renewal.
		renewalTicker := time.NewTicker(24 * time.Hour)
		defer renewalTicker.Stop()

		renewalLog := observability.Logger("service_token_renewal")

		for {
			select {
			case <-ctx.Done():
				return
			case <-renewalTicker.C:
				trades := mgr.GetAllTrades()
				if len(trades) == 0 {
					continue
				}

				// Collect unique user IDs from active trades.
				uniqueUsers := make(map[string]bool)
				for _, t := range trades {
					t.RLock()
					uid := t.UserID
					t.RUnlock()
					if uid != "" && uid != "system" {
						uniqueUsers[uid] = true
					}
				}

				renewed := 0
				for uid := range uniqueUsers {
					user, err := userStore.GetUserByID(ctx, uid)
					if err != nil || user == nil {
						renewalLog.Error().Err(err).Str("user_id", uid).Msg("renewal_user_lookup_failed")
						continue
					}
					if !user.Active {
						renewalLog.Warn().Str("user_id", uid).Msg("skipping_renewal_for_deactivated_user")
						continue
					}

					svcToken, err := tokenService.IssueServiceToken(user.ID, user.Username, user.Role, user.Tier, user.Status)
					if err != nil {
						renewalLog.Error().Err(err).Str("user_id", uid).Msg("renewal_token_issue_failed")
						continue
					}

					// Also refresh the tick cache token.
					mgr.TickCache().SetAuthToken(svcToken)

					count := mgr.RefreshUserTradeTokens(uid, svcToken)
					if count > 0 {
						renewed += count
						renewalLog.Info().
							Str("user_id", uid).
							Str("username", user.Username).
							Int("trades_renewed", count).
							Msg("service_token_renewed")
					}
				}

				if renewed > 0 {
					renewalLog.Info().
						Int("total_trades_renewed", renewed).
						Int("unique_users", len(uniqueUsers)).
						Msg("service_token_renewal_cycle_complete")
				}
			}
		}
	}()

	log.Info().
		Int("grpc_port", cfg.GRPCPort).
		Int("active_trades", len(activeTrades)).
		Bool("auth_enabled", true).
		Msg("management_engine_ready")

	// -- Graceful shutdown ------------------------------------------------
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	log.Info().Msg("shutdown_signal_received")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	// Shutdown order: HTTP -> gRPC -> EOD scheduler -> monitoring -> alerts -> DB.
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
// UserID is restored from the database. The four extra identity fields
// (Username, Role, Tier, StatusJWT) come from the cached User row we
// already looked up to mint the service token, so no extra DB round
// trip is paid here.
func restoreTradeFromRecord(rec *journal.TradeRecord, authToken string, user *auth.User) *types.Trade {
	var username, role, tier, statusJWT string
	if user != nil {
		username = user.Username
		role = string(user.Role)
		tier = user.Tier
		statusJWT = user.Status
	}
	return &types.Trade{
		TradeID:          rec.TradeID,
		Symbol:           rec.Symbol,
		Direction:        constants.Direction(rec.Direction),
		BrokerOrderID:    rec.BrokerOrderID,
		AnalysisID:       rec.AnalysisID,
		UserID:           rec.UserID,
		Username:         username,
		Role:             role,
		Tier:             tier,
		StatusJWT:        statusJWT,
		AuthToken:        authToken,
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

// isLastDayOfMonth checks if the given time is the last day of its current month.
func isLastDayOfMonth(t time.Time) bool {
	// Add one day and check if the month changed.
	return t.AddDate(0, 0, 1).Month() != t.Month()
}
