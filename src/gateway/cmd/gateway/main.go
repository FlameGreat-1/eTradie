package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/billing/store"
	"github.com/flamegreat-1/etradie/src/consent"
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	"github.com/flamegreat-1/etradie/src/gateway/internal/container"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/ports"
	"github.com/flamegreat-1/etradie/src/mails"
	"github.com/flamegreat-1/etradie/src/support"
	"github.com/flamegreat-1/etradie/src/tradingsystem"
)

func main() {
	// Load and validate configuration. Fail fast on invalid config.
	cfg, err := config.Load()
	if err != nil {
		// Logger not yet initialized; write to stderr and exit.
		os.Stderr.WriteString("FATAL: " + err.Error() + "\n")
		os.Exit(1)
	}

	// Initialize structured logging.
	observability.InitLogger(cfg.LogLevel, cfg.LogJSON)
	log := observability.Logger("main")

	log.Info().Msg("gateway_starting")

	// ── Auth configuration ─────────────────────────────────────────────
	authCfg, err := auth.LoadConfig()
	if err != nil {
		log.Fatal().Err(err).Msg("auth_config_load_failed")
	}

	// ── Auth database ──────────────────────────────────────────────────
	// Auth uses the same PostgreSQL instance as Execution/Management.
	// If AUTH_DATABASE_URL is not set, fall back to the gateway's Redis-
	// adjacent DB URL pattern. We construct it from POSTGRES_ env vars.
	authDBURL := authCfg.DatabaseURL
	if authDBURL == "" {
		// Build from standard POSTGRES_ env vars (same as .env.example).
		pgUser := envOrDefault("POSTGRES_USER", "etradie")
		pgPass := envOrDefault("POSTGRES_PASSWORD", "")
		pgHost := envOrDefault("POSTGRES_HOST", "postgres")
		pgPort := envOrDefault("POSTGRES_PORT", "5432")
		pgDB := envOrDefault("POSTGRES_DB", "etradie")
		authDBURL = fmt.Sprintf("postgres://%s:%s@%s:%s/%s?sslmode=disable",
			pgUser, pgPass, pgHost, pgPort, pgDB)
	}

	ctx := context.Background()

	authPool, err := pgxpool.New(ctx, authDBURL)
	if err != nil {
		log.Fatal().Err(err).Msg("auth_database_pool_create_failed")
	}
	defer authPool.Close()

	if err := authPool.Ping(ctx); err != nil {
		log.Fatal().Err(err).Msg("auth_database_ping_failed")
	}

	// Create auth tables.
	if _, err := authPool.Exec(ctx, auth.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("auth_schema_creation_failed")
	}

	// Create billing tables (subscriptions + usage tracking).
	if _, err := authPool.Exec(ctx, store.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("billing_schema_creation_failed")
	}

	// Build auth components.
	userStore := auth.NewUserStore(authPool)
	sessionStore := auth.NewSessionStore(authPool)
	oauthFlowStore := auth.NewOAuthFlowStore(authPool)
	oauthIdentityStore := auth.NewOAuthIdentityStore(authPool)
	passwordResetStore := auth.NewPasswordResetStore(authPool)
	tokenService := auth.NewTokenService(authCfg)
	authHandler := auth.NewHandler(userStore, sessionStore, tokenService, authCfg)
	// Inject a structured logger so the password-reset endpoints can
	// emit silent-skip telemetry without weakening the non-enumeration
	// contract on the wire. The auth handler defaults to zerolog.Nop()
	// when this is not called; that path is used by unit tests.
	authHandler.WithLogger(observability.Logger("auth"))

	// Wire Google OAuth only when explicitly enabled. The provider
	// builds an HTTP client with a bounded timeout and an empty JWKS
	// cache; the first sign-in attempt populates the cache.
	if authCfg.GoogleOAuthEnabled {
		googleProvider := auth.NewGoogleOAuthProvider(authCfg)
		authHandler.WithOAuth(oauthFlowStore, oauthIdentityStore, googleProvider)
		log.Info().
			Str("redirect_uri", authCfg.GoogleRedirectURI).
			Int("flow_ttl_seconds", authCfg.OAuthFlowTTLSeconds).
			Int("hosted_domains", len(authCfg.GoogleAllowedHostedDomains)).
			Msg("auth_google_oauth_enabled")
	} else {
		log.Info().Msg("auth_google_oauth_disabled")
	}

	// Seed admin user on first startup.
	if err := auth.SeedAdminUser(ctx, userStore, authCfg); err != nil {
		log.Error().Err(err).Msg("auth_admin_seed_failed")
	} else {
		log.Info().Str("admin_username", authCfg.AdminUsername).Msg("auth_admin_seed_checked")
	}

	log.Info().Msg("auth_service_initialized")

	// ── Waitlist / Mails module ───────────────────────────────────────
	smtpCfg, err := mails.LoadConfig()
	if err != nil {
		log.Fatal().Err(err).Msg("smtp_config_load_failed")
	}

	// Create waitlist table (idempotent, same pool as auth).
	if _, err := authPool.Exec(ctx, mails.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("waitlist_schema_creation_failed")
	}

	waitlistStore := mails.NewWaitlistStore(authPool)
	emailSender := mails.NewSender(smtpCfg, observability.Logger("email_sender"))
	waitlistHandler := mails.NewHandler(waitlistStore, emailSender, observability.Logger("waitlist"))

	// Wire forgot/reset-password into the auth handler. The mailer is
	// the same *mails.Sender used by the waitlist (it satisfies the
	// auth.Mailer interface). When SMTP is not configured the sender's
	// SendWithRetry logs a warning and returns; the handler still
	// records the reset row so audit trails are intact.
	authHandler.WithPasswordReset(passwordResetStore, emailSender)
	log.Info().
		Int("token_ttl_seconds", authCfg.PasswordResetTokenTTLSeconds).
		Bool("frontend_base_url_set", authCfg.FrontendBaseURL != "").
		Msg("auth_password_reset_initialized")

	// ── Cookie consent (GDPR / ePrivacy audit trail) ─────────────
	// Same pool, same idempotent-DDL pattern as every other store.
	// The consent service is independent of execution / engine /
	// realtime so it has no fan-out wiring; only DB + IP resolver.
	if _, err := authPool.Exec(ctx, consent.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("consent_schema_creation_failed")
	}
	consentStore := consent.NewStore(authPool)
	consentIPSalt := []byte(os.Getenv("CONSENT_IP_HASH_SALT"))
	// Layered rate limiters for the public POST /api/v1/consent endpoint:
	//
	//   ipLimiter   -- 60 writes / minute / resolved client IP. Generous
	//                  for a legitimate user (who will only ever issue a
	//                  handful of decisions in their lifetime) while
	//                  making a volumetric DB-fill attack uneconomical.
	//   anonLimiter -- 10 writes / minute / anonymous_id. Defeats a
	//                  single attacker rotating across many residential
	//                  IPs (botnet) who would slip under ipLimiter but
	//                  collectively inflate one target's history.
	consentIPLimiter := auth.NewRateLimiter(60, time.Minute)
	consentAnonLimiter := auth.NewRateLimiter(10, time.Minute)
	consentHandler := consent.NewHandlerWithLimiters(
		consentStore,
		authCfg.IPResolver(),
		consentIPSalt,
		consentIPLimiter,
		consentAnonLimiter,
		observability.Logger("consent"),
	)
	defer consentIPLimiter.Close()
	defer consentAnonLimiter.Close()
	log.Info().
		Bool("ip_hash_salt_configured", len(consentIPSalt) > 0).
		Int("rate_limit_ip_per_minute", 60).
		Int("rate_limit_anon_per_minute", 10).
		Msg("consent_service_initialized")

	if smtpCfg.IsConfigured() {
		log.Info().Str("host", smtpCfg.Host).Int("port", smtpCfg.Port).Msg("smtp_configured")
	} else {
		log.Warn().Msg("smtp_not_configured_waitlist_emails_will_be_skipped")
	}

	// ── Support & Contact Us module ───────────────────────────────────
	//
	// Persists customer-facing tickets and fans new events out to the
	// configured channels (email, Discord webhook, Telegram bot,
	// WhatsApp Cloud API). The schema is idempotent and lives in the
	// same auth pool as every other persisted feature.
	supportCfg, err := support.LoadConfig()
	if err != nil {
		log.Fatal().Err(err).Msg("support_config_load_failed")
	}
	if _, err := authPool.Exec(ctx, support.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("support_schema_creation_failed")
	}
	supportStore := support.NewStore(authPool)
	supportNotifier := support.NewNotifier(supportCfg, emailSender, observability.Logger("support_notifier"))
	// Layered rate limiters for the public contact endpoint:
	//
	//   supportIPLimiter    -- 60 writes/minute per resolved client IP.
	//                          Defends against volumetric abuse.
	//   supportEmailLimiter -- 15 writes/minute per validated email.
	//                          Defends against a botnet rotating IPs to
	//                          flood a single mailbox.
	supportIPLimiter := auth.NewRateLimiter(60, time.Minute)
	supportEmailLimiter := auth.NewRateLimiter(15, time.Minute)
	supportHandler := support.NewHandlerWithLimiters(
		supportStore,
		supportNotifier,
		supportCfg,
		userStore,
		authCfg.IPResolver(),
		supportIPLimiter,
		supportEmailLimiter,
		observability.Logger("support"),
	)
	defer supportIPLimiter.Close()
	defer supportEmailLimiter.Close()
	log.Info().
		Bool("email_enabled", supportCfg.EmailEnabled()).
		Bool("discord_enabled", supportCfg.DiscordEnabled()).
		Bool("telegram_enabled", supportCfg.TelegramEnabled()).
		Bool("whatsapp_enabled", supportCfg.WhatsAppEnabled()).
		Bool("community_links_configured", supportCfg.HasCommunityLinks()).
		Bool("auto_close_enabled", supportCfg.AutoCloseEnabled()).
		Dur("auto_close_after", supportCfg.AutoCloseAfter).
		Msg("support_service_initialized")

	// Initialize OpenTelemetry tracing. When GATEWAY_OTEL_ENDPOINT is
	// empty (default), InitTracing returns (nil, nil) which we treat as
	// "tracing explicitly disabled". Any non-empty endpoint that fails
	// to dial is surfaced as a warning but does not abort startup; the
	// gateway continues with a no-op tracer.
	var shutdownTracing func(context.Context) error
	if cfg.OTELEndpoint != "" {
		shutdownTracing, err = observability.InitTracing(ctx, cfg.OTELServiceName, cfg.OTELEndpoint)
		if err != nil {
			log.Warn().Err(err).Msg("tracing_init_failed_continuing_without_tracing")
		}
	} else {
		log.Info().Msg("tracing_disabled_via_empty_otel_endpoint")
	}

	// Build execution adapter if enabled.
	var execPort ports.ExecutionPort
	var execAdapter *infra.ExecutionGRPCAdapter
	if cfg.ExecutionEnabled {
		adapter, err := infra.NewExecutionGRPCAdapter(cfg.ExecutionAddr, cfg.ExecutionTimeoutMs)
		if err != nil {
			log.Warn().Err(err).Str("addr", cfg.ExecutionAddr).Msg("execution_adapter_connect_failed_running_without_execution")
		} else {
			execPort = adapter
			execAdapter = adapter
			log.Info().Str("addr", cfg.ExecutionAddr).Msg("execution_engine_connected")
		}
	} else {
		log.Info().Msg("execution_engine_disabled")
	}

	usageStore := store.NewUsageStore(authPool)
	subStore := store.NewSubscriptionStore(authPool)
	portalAudStore := store.NewPortalAuditStore(authPool)

	// ── Trading System (PRACTICE.md user personalization layer) ────────
	// Same authPool: keeps every per-user feature in one Postgres
	// instance with one connection budget. The store DDL is idempotent
	// so a fresh database boots without any external migration step.
	if _, err := authPool.Exec(ctx, tradingsystem.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("trading_system_schema_creation_failed")
	}
	tradingSystemStore := tradingsystem.NewStore(authPool)
	// Build the invalidation publisher. When Redis is available (which
	// it always is in production since the container already requires
	// it), profile mutations publish a cache-bust event to the engine
	// via Redis pub/sub so the engine's in-process + Redis cache for
	// the affected user is invalidated immediately rather than waiting
	// for the 1-hour positive-cache TTL.
	//
	// The container builds its own Redis client further down, but the
	// tradingSystemHandler must be constructed *before* container.New
	// because it is one of its inputs. We therefore build a dedicated
	// Redis client here pointing at the same Redis instance; pub/sub
	// events from this client are received by every subscriber
	// (including the engine), so a second connection does not change
	// semantics. On failure we degrade gracefully to nil, which the
	// InvalidationPublisher tolerates as a documented no-op path.
	var tradingSystemRedis tradingsystem.RedisPublisher
	if tsRedisClient, tsRedisErr := infra.NewRedisClient(cfg.RedisURL, cfg.RedisMaxConnections); tsRedisErr != nil {
		log.Warn().Err(tsRedisErr).Msg("tradingsystem_invalidation_redis_unavailable_continuing_without_pubsub")
	} else {
		tradingSystemRedis = tsRedisClient
	}
	tradingSystemInvalidation := tradingsystem.NewInvalidationPublisher(
		tradingSystemRedis,
		observability.Logger("tradingsystem_invalidation"),
	)
	tradingSystemHandler := tradingsystem.NewHandler(
		tradingSystemStore,
		cfg.EngineInternalSharedSecret,
		observability.Logger("tradingsystem"),
		tradingSystemInvalidation,
	)
	// Reap the per-user rate-limiter background goroutines on
	// graceful shutdown. Mirrors the pattern used by every other
	// rate-limited handler in the gateway (auth, consent, support).
	defer tradingSystemHandler.Close()
	log.Info().
		Int("schema_version", tradingsystem.CurrentSchemaVersion).
		Bool("internal_secret_configured", cfg.EngineInternalSharedSecret != "").
		Msg("trading_system_initialized")

	c, err := container.New(cfg, execPort, execAdapter, tokenService, authHandler, authCfg, userStore, waitlistHandler, consentHandler, supportHandler, supportNotifier, emailSender, usageStore, subStore, portalAudStore, tradingSystemHandler)
	if err != nil {
		log.Fatal().Err(err).Msg("gateway_container_build_failed")
	}

	// Health check at startup.
	redisOK := c.Redis.HealthCheck(ctx)
	engineOK := c.Engine.HealthCheck(ctx)
	executionOK := false
	if c.Execution != nil {
		executionOK = c.Execution.HealthCheck(ctx)
	}
	log.Info().
		Bool("redis", redisOK).
		Bool("engine", engineOK).
		Bool("execution", executionOK).
		Bool("execution_enabled", cfg.ExecutionEnabled).
		Msg("startup_health")

	// Start servers and scheduler concurrently.
	errCh := make(chan error, 3)

	go func() {
		errCh <- c.HTTPServer.Start()
	}()

	go func() {
		errCh <- c.GRPCServer.Start()
	}()

	schedulerCtx, schedulerCancel := context.WithCancel(ctx)
	go func() {
		c.Scheduler.Start(schedulerCtx)
	}()

	// Periodic janitor (every hour) for expired auth state. Runs in a
	// single goroutine so the schedule and shutdown semantics stay
	// simple; each cleanup is independent and a failure in one path
	// does not block the other.
	go func() {
		ticker := time.NewTicker(1 * time.Hour)
		defer ticker.Stop()
		for {
			select {
			case <-schedulerCtx.Done():
				return
			case <-ticker.C:
				cleanupCtx, cancel := context.WithTimeout(context.Background(), 1*time.Minute)
				deleted, err := sessionStore.CleanupExpiredSessions(cleanupCtx)
				if err != nil {
					log.Error().Err(err).Msg("auth_session_cleanup_failed")
				} else if deleted > 0 {
					log.Info().Int64("deleted", deleted).Msg("auth_expired_sessions_cleaned")
				}
				oauthDeleted, err := oauthFlowStore.CleanupExpiredOAuthFlows(cleanupCtx)
				if err != nil {
					log.Error().Err(err).Msg("auth_oauth_flows_cleanup_failed")
				} else if oauthDeleted > 0 {
					log.Info().Int64("deleted", oauthDeleted).Msg("auth_expired_oauth_flows_cleaned")
				}
				resetDeleted, err := passwordResetStore.DeleteExpiredTokens(cleanupCtx)
				if err != nil {
					log.Error().Err(err).Msg("auth_password_reset_cleanup_failed")
				} else if resetDeleted > 0 {
					log.Info().Int64("deleted", resetDeleted).Msg("auth_expired_password_resets_cleaned")
				}
				// GDPR Art. 5(1)(e): delete consent rows older than the
				// configured retention window, preserving the latest row
				// per anonymous_id and per user_id as legally-required
				// proof of consent. CutoffFromNow is calendar-aware so
				// the 24-month boundary aligns with the Privacy Policy
				// text rather than drifting via 24*30*24h arithmetic.
				cutoff := consent.CutoffFromNow(time.Now().UTC())
				consentDeleted, err := consentStore.DeleteExpired(cleanupCtx, cutoff)
				if err != nil {
					log.Error().Err(err).Msg("consent_retention_cleanup_failed")
				} else if consentDeleted > 0 {
					log.Info().Int64("deleted", consentDeleted).Msg("consent_expired_rows_cleaned")
				}
				// Auto-close resolved support tickets that have been
				// inactive for longer than SUPPORT_AUTO_CLOSE_AFTER.
				// Only runs when the feature is enabled (duration > 0).
				// Each closed ticket gets an audit row with actor='system'
				// and action='auto_closed' for compliance traceability.
				if supportCfg.AutoCloseEnabled() {
					autoCloseCutoff := time.Now().UTC().Add(-supportCfg.AutoCloseAfter)
					autoClosed, err := supportStore.AutoCloseInactiveTickets(cleanupCtx, autoCloseCutoff)
					if err != nil {
						log.Error().Err(err).Msg("support_auto_close_failed")
					} else if autoClosed > 0 {
						support.SupportTicketsAutoClosedTotal.Add(float64(autoClosed))
						log.Info().Int64("closed", autoClosed).Dur("after", supportCfg.AutoCloseAfter).Msg("support_tickets_auto_closed")
					}
				}
				cancel()
			}
		}
	}()

	log.Info().
		Int("http_port", cfg.HTTPPort).
		Int("grpc_port", cfg.GRPCPort).
		Int("cycle_interval_seconds", cfg.CycleIntervalSeconds).
		Msg("gateway_started")

	// Wait for shutdown signal or server error.
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	select {
	case sig := <-sigCh:
		log.Info().Str("signal", sig.String()).Msg("shutdown_signal_received")
	case err := <-errCh:
		if err != nil {
			log.Error().Err(err).Msg("server_error")
		}
	}

	// Graceful shutdown with 30-second deadline.
	log.Info().Msg("gateway_shutting_down")
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer shutdownCancel()

	schedulerCancel()
	c.Shutdown(shutdownCtx)

	// Close auth DB pool.
	authPool.Close()

	if shutdownTracing != nil {
		if err := shutdownTracing(shutdownCtx); err != nil {
			log.Error().Err(err).Msg("tracing_shutdown_error")
		}
	}

	log.Info().Msg("gateway_stopped")
}

// envOrDefault reads an environment variable with a fallback default.
func envOrDefault(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
