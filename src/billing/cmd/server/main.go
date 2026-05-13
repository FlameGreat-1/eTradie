// Command billing is the standalone billing microservice.
//
//	Endpoints (public):  /webhooks/paddle, /webhooks/lemonsqueezy,
//	                     /health, /readiness, /metrics
//	Endpoints (internal, X-Internal-Auth): /internal/checkout
//
// In-process background work:
//	- service.Reconciler runs every BILLING_RECONCILER_INTERVAL_SECONDS
//	  to demote subscriptions whose tentative-loss status (paused, past_due,
//	  canceled, refunded) has outlived current_period_end, and to prune
//	  processed_webhook_events older than BILLING_IDEMPOTENCY_RETENTION_DAYS.
package main

import (
	"context"
	"errors"
	"fmt"
	"net"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	goredis "github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/billing/config"
	"github.com/flamegreat-1/etradie/src/billing/lemonsqueezy"
	"github.com/flamegreat-1/etradie/src/billing/paddle"
	"github.com/flamegreat-1/etradie/src/billing/server"
	"github.com/flamegreat-1/etradie/src/billing/service"
	"github.com/flamegreat-1/etradie/src/billing/store"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		fmt.Fprintln(os.Stderr, "FATAL: "+err.Error())
		os.Exit(1)
	}

	log := newLogger(cfg.LogLevel, cfg.LogJSON)

	// Surface operator-relevant configuration at startup so the runbook can
	// be validated against the running process. PublicBaseURL in particular
	// is the value operators register in the Paddle and Lemon Squeezy
	// dashboards; a mismatch between this and the dashboard is the most
	// common cause of "webhooks not arriving" incidents.
	log.Info().
		Int("port", cfg.HTTPPort).
		Str("public_base_url", cfg.PublicBaseURL).
		Dur("reconciler_interval", cfg.ReconcilerInterval).
		Int("idempotency_retention_days", cfg.IdempotencyRetentionDays).
		Dur("webhook_replay_window", cfg.WebhookReplayWindow).
		Int64("webhook_max_body_bytes", cfg.WebhookMaxBodyBytes).
		Msg("billing_starting")

	ctx := context.Background()

	pool, err := pgxpool.New(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatal().Err(err).Msg("billing_db_pool_create_failed")
	}
	defer pool.Close()

	pingCtx, pingCancel := context.WithTimeout(ctx, 30*time.Second)
	if err := pool.Ping(pingCtx); err != nil {
		pingCancel()
		log.Fatal().Err(err).Msg("billing_db_ping_failed")
	}
	pingCancel()

	if _, err := pool.Exec(ctx, store.SchemaSQL()); err != nil {
		log.Fatal().Err(err).Msg("billing_schema_apply_failed")
	}

	subStore := store.NewSubscriptionStore(pool)
	processedStore := store.NewProcessedEventStore(pool)
	auditStore := store.NewSubscriptionEventStore(pool)
	intentStore := store.NewCheckoutIntentStore(pool)

	// Redis client: required for the cross-service alert transport that
	// pushes SUBSCRIPTION_* events to the gateway's WebSocket subscribers.
	// The gateway runs its own subscriber on the same channel; we only
	// PUBLISH from this process.
	redisURL := cfg.RedisURL
	if redisURL == "" {
		log.Fatal().Msg("billing_redis_url_required_for_alert_publish")
	}
	redisOpts, err := goredis.ParseURL(redisURL)
	if err != nil {
		log.Fatal().Err(err).Msg("billing_redis_url_parse_failed")
	}
	redisClient := goredis.NewClient(redisOpts)
	defer redisClient.Close()
	pingRedisCtx, pingRedisCancel := context.WithTimeout(ctx, 5*time.Second)
	if err := redisClient.Ping(pingRedisCtx).Err(); err != nil {
		pingRedisCancel()
		log.Fatal().Err(err).Msg("billing_redis_ping_failed")
	}
	pingRedisCancel()

	// Local hub is publish-only here — the billing process does NOT
	// terminate WebSocket connections. The gateway subscribes to the
	// same Redis channel and fans events out to its own connected
	// clients.
	alertHub := alert.NewHub()
	defer alertHub.Close()
	alertTransport := alertredis.NewTransport(redisClient, alertHub, alertredis.TransportConfig{})
	alertTransport.Start(ctx)
	defer alertTransport.Close()

	// SessionRevoker + SubscriptionEventPublisher composed into a single
	// type. The Service treats it as a SessionRevoker; the post-commit
	// code path in subscription.go type-asserts for the publisher
	// behaviour so this wiring requires no service-constructor changes.
	revoker := &service.AlertRedisPublisher{
		Revoker:   auth.NewSessionStore(pool),
		Publisher: alertTransport,
		Log:       log.With().Str("component", "billing_event_publisher").Logger(),
	}

	subSvc := service.NewService(subStore, processedStore, auditStore, revoker, log.With().Str("component", "billing_service").Logger())
	checkoutSvc, err := service.NewCheckoutService(cfg.CheckoutConfig(), log.With().Str("component", "billing_checkout").Logger())
	if err != nil {
		log.Fatal().Err(err).Msg("billing_checkout_service_init_failed")
	}

	// Wire the checkout-intent idempotency cache into the checkout
	// service. A repeat call with the same (user, provider, tier) within
	// the TTL returns the cached provider URL instead of creating a
	// second checkout session on the provider side. The reconciler's
	// janitor pass below prunes expired rows.
	checkoutSvc.WithIntentCache(
		func(ctx context.Context, userID, provider, tier string) (string, string, string, string, time.Time, bool, error) {
			rec, err := intentStore.Get(ctx, userID, provider, tier)
			if err != nil {
				if errors.Is(err, store.ErrCheckoutIntentNotFound) {
					return "", "", "", "", time.Time{}, false, nil
				}
				return "", "", "", "", time.Time{}, false, err
			}
			return rec.UserID, rec.Provider, rec.Tier, rec.CheckoutURL, rec.ExpiresAt, true, nil
		},
		func(ctx context.Context, userID, provider, tier, url string, expiresAt time.Time) error {
			return intentStore.Record(ctx, &store.CheckoutIntent{
				UserID:      userID,
				Provider:    provider,
				Tier:        tier,
				CheckoutURL: url,
				ExpiresAt:   expiresAt,
			})
		},
	)

	paddleVerifier, err := paddle.NewVerifier(cfg.PaddleWebhookSecret, cfg.WebhookReplayWindow, cfg.WebhookMaxBodyBytes)
	if err != nil {
		log.Fatal().Err(err).Msg("paddle_verifier_init_failed")
	}
	lsVerifier, err := lemonsqueezy.NewVerifier(cfg.LSWebhookSecret, cfg.WebhookMaxBodyBytes)
	if err != nil {
		log.Fatal().Err(err).Msg("lemonsqueezy_verifier_init_failed")
	}

	metrics := server.NewMetrics()

	// Wire the metric pack as the circuit-breaker observer so every
	// closed/half_open/open transition emits a counter increment and a
	// state-gauge update. Must happen before the first provider call.
	checkoutSvc.SetBreakerObserver(metrics)

	// Period-end reconciler + idempotency janitor. Constructed before the
	// listener so a misconfig fails fast.
	reconciler, err := service.NewReconciler(
		subStore, processedStore, auditStore, revoker,
		metrics,
		log.With().Str("component", "billing_reconciler").Logger(),
		service.ReconcilerConfig{
			Interval:                 cfg.ReconcilerInterval,
			IdempotencyRetentionDays: cfg.IdempotencyRetentionDays,
		},
	)
	if err != nil {
		log.Fatal().Err(err).Msg("billing_reconciler_init_failed")
	}

	// Janitor: prune expired billing_checkout_intents on every tick.
	reconciler.WithCheckoutIntents(intentStore)

	// Janitor: reap stale LLM reservations (held + TTL elapsed) and
	// reset monthly token counters on period-end renewal. The usage
	// store shares the same pool as every other billing store.
	usageStore := store.NewUsageStore(pool)
	reconciler.WithUsageStore(usageStore)

	srv := server.New(server.Options{
		DB:                  pool,
		Log:                 log.With().Str("component", "billing_http").Logger(),
		Metrics:             metrics,
		InternalSecret:      cfg.InternalSharedSecret,
		PaddleVerifier:      paddleVerifier,
		PaddlePrices:        cfg.PriceTierMap(),
		LSVerifier:          lsVerifier,
		LSVariants:          cfg.VariantTierMap(),
		SubscriptionService: subSvc,
		CheckoutService:     checkoutSvc,
	})

	// Bind the listener FIRST so a port-bind failure (EADDRINUSE) terminates
	// the process cleanly before any background goroutines spin up against
	// a dead HTTP path. The listener is owned by main; defer Close ensures
	// the OS port is released on every exit path.
	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", cfg.HTTPPort))
	if err != nil {
		log.Fatal().Err(err).Int("port", cfg.HTTPPort).Msg("billing_http_listen_failed")
	}
	log.Info().Str("addr", lis.Addr().String()).Msg("billing_http_listener_bound")

	// Background work is driven by a cancellable context so SIGTERM stops
	// the reconciler cleanly before HTTP shutdown. Run blocks until ctx is
	// cancelled and returns; main waits on the done channel during graceful
	// shutdown so a half-finished tick can complete.
	bgCtx, bgCancel := context.WithCancel(context.Background())
	reconcilerDone := make(chan struct{})
	go func() {
		reconciler.Run(bgCtx)
		close(reconcilerDone)
	}()

	errCh := make(chan error, 1)
	go func() { errCh <- srv.Start(lis) }()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	select {
	case sig := <-sigCh:
		log.Info().Str("signal", sig.String()).Msg("billing_shutdown_signal")
	case err := <-errCh:
		if err != nil {
			log.Error().Err(err).Msg("billing_http_error")
		}
	}

	// Cancel the reconciler first so its current tick finishes before we
	// drop the DB pool. Wait up to 10s for it to drain; the reconciler's
	// inner steps are bounded so this is generous.
	bgCancel()
	select {
	case <-reconcilerDone:
	case <-time.After(10 * time.Second):
		log.Warn().Msg("billing_reconciler_shutdown_timeout")
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Error().Err(err).Msg("billing_shutdown_error")
	}
	log.Info().Msg("billing_stopped")
}

func newLogger(level string, jsonOutput bool) zerolog.Logger {
	lvl, err := zerolog.ParseLevel(strings.ToLower(level))
	if err != nil || level == "" {
		lvl = zerolog.InfoLevel
	}
	zerolog.SetGlobalLevel(lvl)
	var logger zerolog.Logger
	if jsonOutput {
		logger = zerolog.New(os.Stdout).With().Timestamp().Logger()
	} else {
		logger = zerolog.New(zerolog.ConsoleWriter{Out: os.Stderr, TimeFormat: time.RFC3339}).
			With().Timestamp().Logger()
	}
	return logger
}
