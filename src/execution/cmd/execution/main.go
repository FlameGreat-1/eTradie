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

	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"

	executionv1 "github.com/flamegreat-1/etradie/proto/execution/v1"
	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
	billingstore "github.com/flamegreat-1/etradie/src/billing/store"
	"github.com/flamegreat-1/etradie/src/execution/internal/audit"
	"github.com/flamegreat-1/etradie/src/execution/internal/broker"
	"github.com/flamegreat-1/etradie/src/execution/internal/broker/mt5"
	"github.com/flamegreat-1/etradie/src/execution/internal/config"
	"github.com/flamegreat-1/etradie/src/execution/internal/constants"
	"github.com/flamegreat-1/etradie/src/execution/internal/executor"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
	"github.com/flamegreat-1/etradie/src/execution/internal/server"
	"github.com/flamegreat-1/etradie/src/execution/internal/signing"
	"github.com/flamegreat-1/etradie/src/execution/internal/sizing"
	"github.com/flamegreat-1/etradie/src/execution/internal/state"
	"github.com/flamegreat-1/etradie/src/execution/internal/store"
	"github.com/flamegreat-1/etradie/src/execution/internal/validator"
	"github.com/flamegreat-1/etradie/src/execution/internal/watcher"
	"github.com/redis/go-redis/v9"
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
		Str("broker_bridge_url", cfg.BrokerBridgeURL).
		Str("execution_mode", cfg.DefaultExecutionMode).
		Int("max_concurrent", cfg.MaxConcurrentTrades).
		Msg("execution_engine_starting")

	// ── Auth configuration ─────────────────────────────────────────────────
	authCfg, err := auth.LoadConfig()
	if err != nil {
		log.Fatal().Err(err).Msg("auth_config_load_failed")
	}
	tokenService := auth.NewTokenService(authCfg)
	log.Info().Msg("auth_service_initialized")

	ctx := context.Background()

	// ── OpenTelemetry tracing ──────────────────────────────────────────────
	// Empty EXECUTION_OTEL_ENDPOINT -> clean no-op (tracing opt-in). A
	// non-empty endpoint that fails to dial is a warning, not fatal:
	// tracing must never block the order path. InitTracing also sets the
	// global W3C propagator so the otelgrpc server handler below continues
	// the gateway's trace rather than starting a disconnected root span.
	var shutdownTracing func(context.Context) error
	if cfg.OTELEndpoint != "" {
		shutdownTracing, err = observability.InitTracing(ctx, cfg.OTELServiceName, cfg.OTELEndpoint)
		if err != nil {
			log.Warn().Err(err).Msg("tracing_init_failed_continuing_without_tracing")
		}
	} else {
		log.Info().Msg("tracing_disabled_via_empty_otel_endpoint")
	}

	// ── Database connection pool ───────────────────────────────────────────
	poolCfg, err := pgxpool.ParseConfig(cfg.DatabaseURL)
	if err != nil {
		log.Fatal().Err(err).Msg("database_config_parse_failed")
	}
	poolCfg.MaxConns = int32(cfg.DatabaseMaxConns) // #nosec G115 -- max conns is reasonably small
	poolCfg.MinConns = int32(cfg.DatabaseMinConns) // #nosec G115
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

	// Create all execution tables (audit logs, pnl tracker, settings, pending watchers).
	if _, err := pool.Exec(ctx, store.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("schema_creation_failed")
	}

	// Ensure auth schema exists (idempotent). Execution needs read access
	// to auth_users for issuing service tokens on watcher restoration.
	if _, err := pool.Exec(ctx, auth.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("auth_schema_creation_failed")
	}
	userStore := auth.NewUserStore(pool)

	// Execution consumes long-lived service tokens (the gRPC auth
	// interceptor below verifies them). Attach the user store as the
	// epoch resolver so a revoked service token (token_epoch bumped via
	// UserStore.BumpTokenEpoch) is rejected at verify. User access
	// tokens are unaffected (only token_type=="svc" is epoch-checked).
	tokenService = tokenService.WithEpochResolver(userStore)

	// ── Broker implementation ──────────────────────────────────────────────
	// The mt5 bridge is the sole broker.Port implementation. Every call
	// is dispatched to the Python engine's /internal/broker/* surface,
	// which resolves the per-user MT4 or MT5 broker connection from the
	// database (see src/engine/ta/broker/mt5/factory.py).
	//
	// EngineInternalSecret is validated by Config.validate(): required
	// unconditionally in production / staging (>=32 chars); optional in
	// development where the bridge logs a warning at construction and
	// every call returns 401 until configured.
	var bp broker.Port = mt5.NewBridge(cfg.BrokerBridgeURL, cfg.BrokerTimeoutMs, cfg.EngineInternalSecret)
	log.Info().
		Str("url", cfg.BrokerBridgeURL).
		Bool("internal_auth_configured", cfg.EngineInternalSecret != "").
		Msg("broker_mt5_bridge_configured")

	// ── Redis Connection (for shared alerts) ───────────────────────────────
	opts, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		log.Fatal().Err(err).Msg("redis_url_parse_failed")
	}
	rdb := redis.NewClient(opts)
	defer rdb.Close()
	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Fatal().Err(err).Msg("redis_ping_failed")
	}

	// ── Shared alert transport (serves all modules) ────────────────────────
	alertHub := alert.NewHub()
	defer alertHub.Close()

	alertTransport := alertredis.NewTransport(rdb, alertHub, alertredis.TransportConfig{})
	alertTransport.Start(ctx)
	defer alertTransport.Close()

	// ── Stores ─────────────────────────────────────────────────────────────
	auditStore := store.NewAuditStore(pool)
	pnlStore := store.NewPnLStore(pool)
	settingsStore := store.NewSettingsStore(pool)

	// Section 7 (CHECKLIST): position snapshots. The store persists
	// the engine's post-reconcile view per user every cycle so the
	// reconciler can detect ghost positions across restarts and the
	// Step B replay endpoint can walk the history.
	snapshotStore := store.NewPositionSnapshotStore(pool)

	// ── Gateway gRPC client (for instant-mode confirmation callbacks) ──
	gwClient, err := watcher.NewGatewayGRPCClient(cfg.GatewayAddr)
	if err != nil {
		log.Fatal().Err(err).Str("addr", cfg.GatewayAddr).Msg("gateway_client_init_failed")
	}
	defer gwClient.Close()

	// ── Components (dependency order) ──────────────────────────────────────
	sm := state.NewManager(bp, pnlStore)
	v := validator.NewValidator(cfg, sm, bp)
	s := sizing.NewEngine(cfg, bp)
	al := audit.NewLogger(auditStore)

	watcherStore := store.NewWatcherStore(pool)

	// Section 3 (CHECKLIST): order-level idempotency store.
	idempotencyStore := store.NewIdempotencyStore(pool)

	// Section 3: reconciler identity adapter. The reconciler must call
	// the broker bridge under each user's identity so the bridge
	// resolves the correct per-user broker connection. We reuse
	// userStore + tokenService - the same building blocks the watcher
	// restoration path uses.
	reconcileIdentity := newReconcileIdentityProvider(userStore, tokenService)

	wm := watcher.NewManager(bp, gwClient, al, alertTransport, watcher.Config{
		PollIntervalMs:          cfg.WatcherPollIntervalMs,
		TimeoutMinutes:          cfg.WatcherTimeoutMinutes,
		ConfirmPollIntervalSecs: cfg.WatcherConfirmPollIntervalSecs,
	}, watcherStore)

	// Apply the billing schema (idempotent) so this binary is safe to start
	// against a fresh DB even if it boots before the gateway. Then wire the
	// per-user watcher_count tracker so billing_usage stays accurate.
	if _, err := pool.Exec(ctx, billingstore.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("billing_schema_apply_failed")
	}
	wm = wm.WithUsage(&watcherUsageAdapter{store: billingstore.NewUsageStore(pool)}).
		WithIdempotency(idempotencyStore).
		WithHaltReader(settingsStore)

	e := executor.NewExecutor(
		bp,
		wm,
		idempotencyStore,
		cfg.BrokerTimeoutMs,
		cfg.MaxOrderLatencyMs,
	)

	// Order intake gate: per-user fairness + global in-flight cap +
	// wait deadline. Enforced at the head of ExecuteTrade.
	bq := executor.NewBurstQueue(executor.QueueConfig{
		MaxConcurrent:   cfg.QueueMaxConcurrent,
		PerUserCap:      cfg.QueuePerUserCap,
		DefaultDeadline: time.Duration(cfg.QueueDeadlineMs) * time.Millisecond,
	})

	// ──────────────────────────────────────────────────────────────────────
	// CRITICAL BOOT ORDER:
	//
	// Restore pending watchers + seed tick-cache + start background
	// goroutines BEFORE the gRPC listener accepts traffic. Otherwise a
	// gateway call landing in the window between Serve(lis) and the
	// restoration block would observe a watcher.Manager with zero
	// pending watchers and could double-arm the same setup.
	//
	// Audit ref: CHECKLIST Section 3 'Trade state recovery after crash'.
	// ──────────────────────────────────────────────────────────────────────

	// -- Restore pending watchers from database on restart ----------------
	// Pending watchers are instant-mode orders waiting for price to enter
	// the entry zone. Without restoration, a service restart silently
	// kills all pending watchers and valid trade setups are lost.
	pendingWatchers, err := watcherStore.GetAllPending(ctx)
	if err != nil {
		log.Error().Err(err).Msg("pending_watchers_restore_failed")
	} else if len(pendingWatchers) > 0 {
		log.Info().Int("count", len(pendingWatchers)).Msg("restoring_pending_watchers")

		// Collect unique user IDs and issue service tokens.
		userIDs := make(map[string]bool)
		for _, rec := range pendingWatchers {
			if rec.UserID != "" {
				userIDs[rec.UserID] = true
			}
		}

		// Issue service tokens AND cache the User row for each owner
		// of a pending watcher. The User row drives the identity
		// fields stamped onto the restored Order so the watcher's
		// IdentityCtx works without a second DB round trip.
		serviceTokens := make(map[string]string)
		usersByID := make(map[string]*auth.User)
		for uid := range userIDs {
			user, err := userStore.GetUserByID(ctx, uid)
			if err != nil || user == nil {
				log.Error().Err(err).Str("user_id", uid).Msg("watcher_restore_user_lookup_failed")
				continue
			}
			if !user.Active {
				log.Warn().Str("user_id", uid).Msg("skipping_watcher_restore_for_deactivated_user")
				continue
			}
			svcToken, err := tokenService.IssueServiceToken(user.ID, user.Username, user.Role, user.Tier, user.Status, user.TokenEpoch)
			if err != nil {
				log.Error().Err(err).Str("user_id", uid).Msg("watcher_restore_service_token_failed")
				continue
			}
			serviceTokens[uid] = svcToken
			usersByID[uid] = user
			log.Info().Str("user_id", uid).Str("username", user.Username).Msg("service_token_issued_for_watcher_restoration")
		}

		now := time.Now()
		restoredCount := 0

		// Do not re-arm watchers while a platform-wide halt is engaged.
		// The PENDING rows are left intact and restored on the next
		// healthy start after the halt is released. Per-user halts are
		// enforced at fire time, so user-scoped orders still restore.
		globalHalted, ghErr := settingsStore.IsGlobalHalted(ctx)
		if ghErr != nil {
			log.Warn().Err(ghErr).Msg("watcher_restore_global_halt_read_failed_assuming_not_halted")
			globalHalted = false
		}
		if globalHalted {
			log.Warn().Int("pending", len(pendingWatchers)).Msg("global_kill_switch_engaged_skipping_watcher_restore")
		}

		for _, rec := range pendingWatchers {
			if globalHalted {
				break
			}
			// Calculate remaining timeout using the style-specific duration.
			// Each trading style has a different timeout aligned with its
			// analysis timeframe (e.g., swing = 16h, positional = 48h).
			style := constants.TradingStyle(rec.TradingStyle)
			timeoutMinutes := constants.WatcherTimeoutForStyle(style, cfg.WatcherTimeoutMinutes)
			timeoutDuration := time.Duration(timeoutMinutes) * time.Minute
			elapsed := now.Sub(rec.CreatedAt)
			remaining := timeoutDuration - elapsed
			if remaining <= 0 {
				log.Info().
					Str("watcher_id", rec.WatcherID).
					Str("symbol", rec.Symbol).
					Dur("elapsed", elapsed).
					Msg("stale_watcher_expired_deleting")
				_ = watcherStore.Delete(ctx, rec.WatcherID)
				continue
			}

			token := serviceTokens[rec.UserID]
			if token == "" {
				log.Warn().
					Str("watcher_id", rec.WatcherID).
					Str("user_id", rec.UserID).
					Msg("no_service_token_for_watcher_skipping")
				_ = watcherStore.Delete(ctx, rec.WatcherID)
				continue
			}

			order := restoreOrderFromRecord(rec, token, usersByID[rec.UserID])
			order.TimeoutOverride = remaining
			wm.Arm(order)
			restoredCount++

			log.Info().
				Str("watcher_id", rec.WatcherID).
				Str("symbol", rec.Symbol).
				Str("user_id", rec.UserID).
				Dur("remaining_timeout", remaining).
				Msg("watcher_restored")
		}

		// Arm the tick cache with the first available identity. The
		// cache needs a real parsed *auth.Claims (not just a token)
		// because the engine resolves the per-user broker from
		// X-User-Id. Both Claims and the raw token are stored.
		for uid, svcToken := range serviceTokens {
			u := usersByID[uid]
			if u == nil {
				continue
			}
			wm.TickCache().SetServiceIdentity(&auth.Claims{
				UserID:   u.ID,
				Username: u.Username,
				Role:     u.Role,
				Tier:     u.Tier,
				Status:   u.Status,
			}, svcToken)
			break
		}

		log.Info().
			Int("total_pending", len(pendingWatchers)).
			Int("restored", restoredCount).
			Int("users_with_tokens", len(serviceTokens)).
			Msg("pending_watchers_restoration_complete")
	}

	// ── Startup tick-cache token (fallback for zero-watcher cold starts) ──
	//
	// When no pending watchers exist at startup, the tick cache has no
	// identity and every tick_price request would 401 at the engine.
	// Seed the cache with the first active user's identity so it can
	// authenticate immediately. The token carries the user's real
	// tier/status (NOT a silent "free" default) so downstream tier
	// checks see correct claims.
	//
	// Caveat: the chosen user may not have a configured broker. In that
	// case the engine returns 503 "No broker connection configured" on
	// every poll until a watcher arms with a broker'd user via gRPC,
	// which then overwrites the identity (see Manager.Arm). This is
	// benign because nothing reads the cache before that point. We
	// deliberately do NOT scan broker_connections at startup to find a
	// broker'd user — that would push DB load onto the boot path for
	// marginal log-noise reduction.
	{
		users, userErr := userStore.ListActiveUsers(ctx)
		if userErr == nil && len(users) > 0 {
			for _, u := range users {
				startupToken, tokenErr := tokenService.IssueServiceToken(u.ID, u.Username, u.Role, u.Tier, u.Status, u.TokenEpoch)
				if tokenErr == nil {
					wm.TickCache().SetServiceIdentity(&auth.Claims{
						UserID:   u.ID,
						Username: u.Username,
						Role:     u.Role,
						Tier:     u.Tier,
						Status:   u.Status,
					}, startupToken)
					log.Info().
						Str("user_id", u.ID).
						Str("username", u.Username).
						Msg("startup_tick_cache_identity_issued")
					break
				}
			}
		}
	}

	// Section 3 (CHECKLIST): garbage-collect expired idempotency rows.
	// Keeps the table bounded - the idempotency window is finite
	// (24h default).
	gcCtx, gcCancel := context.WithCancel(context.Background())
	defer gcCancel()
	go idempotencyGCLoop(gcCtx, idempotencyStore, cfg.OrderIdempotencyTTLSecs)

	// Section 3 + Section 7 (CHECKLIST): reconciliation loop. Compares
	// broker positions + pending orders against the engine view, AND
	// (when enabled) writes a post-reconcile snapshot per cycle to
	// drive ghost-position detection across restarts.
	// Runs on the same gcCtx so it stops together with the idempotency
	// GC + snapshot retention sweeper at shutdown.
	reconciler := state.NewReconciler(
		bp,
		sm,
		reconcileIdentity,
		time.Duration(cfg.ReconcileIntervalSecs)*time.Second,
		snapshotStore,
		time.Duration(cfg.GhostPositionMinAgeSecs)*time.Second,
		cfg.PositionSnapshotEnabled,
	)
	go reconciler.Loop(gcCtx)

	// Watcher token-refresh loop. A live INSTANT watcher forwards the
	// user's JWT to the gateway ConfirmSetup RPC; that token is only
	// re-minted when the user makes an authenticated request. A watcher
	// can outlive the access-token TTL by a wide margin (default 45m
	// timeout, up to 7 days for positional, vs ~15m JWT TTL), so an idle
	// owner's watcher would start failing ConfirmSetup with "token is
	// expired". This loop proactively mints a fresh service token per
	// active watcher owner every ReconcileIntervalSecs (well under the
	// JWT TTL) using the same tokenService + RefreshUserOrderIdentity
	// machinery the reconciler and restore paths use. Runs on gcCtx so
	// it stops together with the other background loops at shutdown.
	go watcherTokenRefreshLoop(
		gcCtx,
		wm,
		userStore,
		tokenService,
		time.Duration(cfg.ReconcileIntervalSecs)*time.Second,
	)

	// Section 7 Step C (CHECKLIST): eager position preload on startup.
	//
	// Before the gRPC listener opens, eagerly call Refresh() for every
	// active user so the engine's in-memory position state is hot.
	// Without this, the engine's view is empty on restart and the
	// reconciler closes the gap lazily within 60s. During that window:
	//   - MaxConcurrentTrades guard sees 0 open positions -> may allow
	//     a trade that would be blocked if the engine knew the real count.
	//   - Ghost-position detection has no baseline to compare against.
	//
	// The preload runs AFTER the reconciler goroutine is started (so
	// the reconciler's first cycle does not race with the preload) and
	// BEFORE the gRPC listener opens (so no user request can land
	// before the state is warm).
	//
	// Gated by cfg.PreloadPositionsOnStart so dev/test environments
	// where the broker bridge is not available at startup can disable
	// it without code change.
	if cfg.PreloadPositionsOnStart {
		preloadCtx, preloadCancel := context.WithTimeout(ctx, 60*time.Second)
		preloadUsers, preloadErr := userStore.ListActiveUsers(preloadCtx)
		if preloadErr != nil {
			log.Warn().Err(preloadErr).Msg("preload_positions_user_list_failed")
		} else {
			preloaded := 0
			for _, u := range preloadUsers {
				// Build a per-user identity context the same way the
				// reconciler does: issue a service token, inject it.
				svcToken, tokenErr := tokenService.IssueServiceToken(
					u.ID, u.Username, u.Role, u.Tier, u.Status, u.TokenEpoch,
				)
				if tokenErr != nil {
					log.Warn().Err(tokenErr).Str("user_id", u.ID).Msg("preload_positions_token_failed")
					continue
				}
				identityCtx, identityErr := reconcileIdentity.IdentityContext(preloadCtx, u.ID)
				if identityErr != nil {
					log.Warn().Err(identityErr).Str("user_id", u.ID).Msg("preload_positions_identity_failed")
					continue
				}
				_ = svcToken // token is embedded in identityCtx via reconcileIdentity
				if err := sm.Refresh(identityCtx, u.ID); err != nil {
					log.Warn().Err(err).Str("user_id", u.ID).Msg("preload_positions_refresh_failed")
					continue
				}
				preloaded++
			}
			log.Info().
				Int("total_users", len(preloadUsers)).
				Int("preloaded", preloaded).
				Msg("preload_positions_complete")
		}
		preloadCancel()
	}

	// Section 7 (CHECKLIST): retention sweeper. Prunes snapshots older
	// than PositionSnapshotRetentionHours every 1h. Runs on gcCtx so it
	// shuts down together with the reconciler + idempotency GC.
	go snapshotRetentionLoop(
		gcCtx,
		snapshotStore,
		cfg.PositionSnapshotRetentionHours,
		cfg.PositionSnapshotEnabled,
	)

	// ──────────────────────────────────────────────────────────────────────
	// At this point, state is fully restored and background loops are
	// running. NOW it is safe to open the listener and accept traffic.
	// ──────────────────────────────────────────────────────────────────────

	// ── gRPC server ────────────────────────────────────────────────────────
	execServer := server.NewExecutionServer(cfg, v, s, e, sm, bp, al, alertTransport, settingsStore, wm, bq)

	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", cfg.GRPCPort))
	if err != nil {
		log.Fatal().Err(err).Int("port", cfg.GRPCPort).Msg("grpc_listen_failed")
	}

	// gRPC methods that bypass authentication (health checks).
	skipAuth := map[string]bool{
		"/grpc.health.v1.Health/Check": true,
		"/grpc.health.v1.Health/Watch": true,
	}

	// Order-integrity request signing (CHECKLIST Tier 8 F-1/F-2/F-5).
	// Build the verifier from the resolved HMAC key (dedicated override
	// or the shared ENGINE_INTERNAL_SHARED_SECRET) + freshness window.
	// When enforcement is on, config.validate() has already guaranteed a
	// usable key, so signingVerifier is non-nil there. In non-enforced
	// dev without a key, the verifier stays nil and the interceptor is a
	// clean passthrough.
	var signingVerifier *signing.Verifier
	if key := cfg.RequestSigningKey(); len(key) > 0 {
		signingVerifier, err = signing.NewVerifier(key, cfg.RequestSignatureMaxSkew())
		if err != nil {
			log.Fatal().Err(err).Msg("signing_verifier_init_failed")
		}
	}
	log.Info().
		Bool("signature_enforced", cfg.RequireSignedRequestsEnabled()).
		Bool("signature_verifier_active", signingVerifier != nil).
		Dur("signature_max_skew", cfg.RequestSignatureMaxSkew()).
		Msg("request_signing_configured")

	grpcServer := grpc.NewServer(
		// otelgrpc stats handler: extracts the inbound traceparent (set by
		// the gateway's otelgrpc client handler) and records a server span
		// as a child of the gateway span, so an order flows as ONE trace
		// gateway -> execution. No-op when tracing is disabled (the global
		// provider is then a no-op tracer).
		grpc.StatsHandler(otelgrpc.NewServerHandler()),
		grpc.ChainUnaryInterceptor(
			server.PanicRecoveryInterceptor(observability.Logger("grpc_panic")),
			auth.UnaryAuthInterceptor(tokenService, skipAuth),
			server.SigningVerifyInterceptor(signingVerifier, cfg.RequireSignedRequestsEnabled()),
		),
	)
	executionv1.RegisterExecutionServiceServer(grpcServer, execServer)
	// Reflection exposes the full service descriptor to any client that
	// reaches the port; keep it out of production and staging.
	if !cfg.IsProdLike() {
		reflection.Register(grpcServer)
	}

	go func() {
		log.Info().Int("port", cfg.GRPCPort).Msg("execution_grpc_server_started")
		if err := grpcServer.Serve(lis); err != nil {
			log.Fatal().Err(err).Msg("grpc_serve_failed")
		}
	}()

	// ── HTTP API server (REST + WebSocket + metrics + health) ─────────────
	// authCfg flows through so the HTTP server can build the CSRF
	// middleware (auth.RequireCSRF) AND emit the configured CSRF header
	// name in the CORS Allow-Headers preflight response. Without this,
	// renaming AUTH_CSRF_HEADER silently broke every mutating request.
	httpServer := server.NewHTTPServer(cfg.HTTPPort, sm, bp, settingsStore, al, alertTransport, tokenService, authCfg)

	go func() {
		if err := httpServer.Start(); err != nil {
			log.Fatal().Err(err).Msg("http_api_server_failed")
		}
	}()

	log.Info().
		Int("grpc_port", cfg.GRPCPort).
		Int("http_port", cfg.HTTPPort).
		Int("max_order_latency_ms", cfg.MaxOrderLatencyMs).
		Int("order_idempotency_ttl_secs", cfg.OrderIdempotencyTTLSecs).
		Msg("execution_engine_ready")

	// ── Graceful shutdown ──────────────────────────────────────────────────
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	log.Info().Msg("shutdown_signal_received")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	gcCancel()

	// Shutdown order: gRPC → watchers → HTTP → alerts → DB.
	grpcServer.GracefulStop()
	wm.Shutdown()
	_ = httpServer.Shutdown(shutdownCtx)
	_ = gwClient.Close()
	alertTransport.Close()
	pool.Close()

	if shutdownTracing != nil {
		if err := shutdownTracing(shutdownCtx); err != nil {
			log.Error().Err(err).Msg("tracing_shutdown_error")
		}
	}

	log.Info().Msg("execution_engine_stopped")
}

// snapshotRetentionLoop periodically prunes position snapshots older
// than the configured retention. Runs hourly. Exits when ctx is
// cancelled (engine shutdown).
//
// When enabled=false the loop returns immediately; the snapshot store
// is still constructed but no writes happen (the reconciler skips the
// write path under the same flag), so there is nothing to prune.
//
// Audit ref: CHECKLIST Section 7 'Recovery after full system restart'.
func snapshotRetentionLoop(
	ctx context.Context,
	st *store.PositionSnapshotStore,
	retentionHours int,
	enabled bool,
) {
	if !enabled || st == nil || retentionHours <= 0 {
		return
	}
	log := observability.Logger("snapshot_retention")
	ticker := time.NewTicker(1 * time.Hour)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			cutoff := time.Now().Add(-time.Duration(retentionHours) * time.Hour)
			sweepCtx, cancel := context.WithTimeout(ctx, 60*time.Second)
			pruned, err := st.PruneOlderThan(sweepCtx, cutoff)
			cancel()
			if err != nil {
				log.Warn().Err(err).Time("cutoff", cutoff).Msg("snapshot_retention_failed")
				continue
			}
			if pruned > 0 {
				log.Info().Int64("pruned", pruned).Time("cutoff", cutoff).Msg("snapshot_retention_ran")
			}
		}
	}
}

// watcherTokenRefreshLoop proactively re-mints service tokens for the
// owners of live watchers so a watcher never fails its gateway
// ConfirmSetup call with an expired JWT.
//
// Every interval it enumerates the distinct user IDs of currently-armed
// watchers (Manager.ActiveUserIDs), looks each up, skips missing or
// inactive users, mints a fresh short-lived service token via
// tokenService.IssueServiceToken (identical to the reconciler + restore
// paths), and pushes the new identity onto every matching watcher via
// Manager.RefreshUserOrderIdentity. That method is a no-op when the
// token/tier/status are unchanged, and the watcher reads the latest
// token every tick through IdentityCtx, so the next confirmation after a
// refresh authenticates cleanly.
//
// interval is ReconcileIntervalSecs (default 60s), comfortably under the
// access-token TTL, so a live watcher's token is always refreshed before
// it expires. Exits when ctx is cancelled (engine shutdown).
func watcherTokenRefreshLoop(
	ctx context.Context,
	wm *watcher.Manager,
	users *auth.UserStore,
	tokens *auth.TokenService,
	interval time.Duration,
) {
	if wm == nil || users == nil || tokens == nil || interval <= 0 {
		return
	}
	log := observability.Logger("watcher_token_refresh")
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			userIDs := wm.ActiveUserIDs()
			if len(userIDs) == 0 {
				continue
			}
			for _, uid := range userIDs {
				lookupCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
				user, err := users.GetUserByID(lookupCtx, uid)
				cancel()
				if err != nil || user == nil {
					log.Warn().Err(err).Str("user_id", uid).Msg("watcher_token_refresh_user_lookup_failed")
					continue
				}
				if !user.Active {
					log.Warn().Str("user_id", uid).Msg("watcher_token_refresh_skipped_inactive_user")
					continue
				}
				token, err := tokens.IssueServiceToken(user.ID, user.Username, user.Role, user.Tier, user.Status, user.TokenEpoch)
				if err != nil {
					log.Warn().Err(err).Str("user_id", uid).Msg("watcher_token_refresh_issue_failed")
					continue
				}
				claims := &auth.Claims{
					UserID:   user.ID,
					Username: user.Username,
					Role:     user.Role,
					Tier:     user.Tier,
					Status:   user.Status,
				}
				// Refresh BOTH token consumers of a live INSTANT watcher:
				//   1. the Order's AuthToken (forwarded to the gateway
				//      ConfirmSetup RPC), and
				//   2. the TickCache's per-user identity (used by the
				//      tick poller's /internal/broker/tick_price calls).
				// The tick cache holds its own copy of the token set at
				// arm time; without this it would keep polling with the
				// expired arming JWT and the watcher would never see
				// price enter the entry zone.
				wm.RefreshUserOrderIdentity(claims, token)
				wm.TickCache().SetServiceIdentity(claims, token)
			}
		}
	}
}

// idempotencyGCLoop periodically prunes expired idempotency keys.
// Runs hourly with a cutoff of (now - ttl). Exits when ctx is
// cancelled (engine shutdown).
func idempotencyGCLoop(ctx context.Context, st *store.IdempotencyStore, ttlSecs int) {
	if st == nil || ttlSecs <= 0 {
		return
	}
	log := observability.Logger("idempotency_gc")
	ticker := time.NewTicker(1 * time.Hour)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			cutoff := time.Now().Add(-time.Duration(ttlSecs) * time.Second)
			gcCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
			deleted, err := st.GarbageCollect(gcCtx, cutoff)
			cancel()
			if err != nil {
				log.Warn().Err(err).Msg("idempotency_gc_failed")
				continue
			}
			if deleted > 0 {
				log.Info().Int64("deleted", deleted).Time("cutoff", cutoff).Msg("idempotency_gc_ran")
			}
		}
	}
}

// restoreOrderFromRecord reconstructs an Order from a persisted
// watcher record. Identity fields (Username, Role, Tier, StatusJWT)
// come from the cached *auth.User we already fetched to mint the
// service token, so no extra DB round trip is paid here.
func restoreOrderFromRecord(rec *store.PendingWatcherRecord, authToken string, user *auth.User) *models.Order {
	var username, role, tier, statusJWT string
	if user != nil {
		username = user.Username
		role = string(user.Role)
		tier = user.Tier
		statusJWT = user.Status
	}
	return &models.Order{
		OrderID:            rec.OrderID,
		Symbol:             rec.Symbol,
		Direction:          constants.Direction(rec.Direction),
		ExecutionMode:      constants.ExecutionMode(rec.ExecutionMode),
		EntryPrice:         rec.EntryPrice,
		StopLoss:           rec.StopLoss,
		TP1Price:           rec.TP1Price,
		TP1Pct:             rec.TP1Pct,
		TP2Price:           rec.TP2Price,
		TP2Pct:             rec.TP2Pct,
		TP3Price:           rec.TP3Price,
		TP3Pct:             rec.TP3Pct,
		LotSize:            rec.LotSize,
		RiskPercent:        rec.RiskPercent,
		RiskAmount:         rec.RiskAmount,
		RRRatio:            rec.RRRatio,
		AccountBalance:     rec.AccountBalance,
		SLDistancePips:     rec.SLDistancePips,
		PipValue:           rec.PipValue,
		OvershootTolerance: rec.OvershootTolerance,
		LTFConfirmed:       rec.LTFConfirmed,
		AnalysisID:         rec.AnalysisID,
		TradingStyle:       constants.TradingStyle(rec.TradingStyle),
		Session:            rec.Session,
		Grade:              rec.Grade,
		Confluence:         rec.Confluence,
		Confidence:         rec.Confidence,
		SetupType:          rec.SetupType,
		WatcherID:          rec.WatcherID,
		BrokerOrderID:      rec.BrokerOrderID,
		CreatedAt:          rec.CreatedAt,
		UserID:             rec.UserID,
		Username:           username,
		Role:               role,
		Tier:               tier,
		StatusJWT:          statusJWT,
		AuthToken:          authToken,
	}
}
