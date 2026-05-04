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
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	"github.com/flamegreat-1/etradie/src/gateway/internal/container"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/ports"
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

	// Build auth components.
	userStore := auth.NewUserStore(authPool)
	sessionStore := auth.NewSessionStore(authPool)
	oauthFlowStore := auth.NewOAuthFlowStore(authPool)
	oauthIdentityStore := auth.NewOAuthIdentityStore(authPool)
	tokenService := auth.NewTokenService(authCfg)
	authHandler := auth.NewHandler(userStore, sessionStore, tokenService, authCfg)

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

	c, err := container.New(cfg, execPort, execAdapter, tokenService, authHandler, userStore)
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
