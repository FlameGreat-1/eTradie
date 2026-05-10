// Command billing is the standalone billing microservice.
//
//	Endpoints (public): /webhooks/paddle, /webhooks/lemonsqueezy, /health, /readiness, /metrics
//	Endpoints (internal, X-Internal-Auth): /internal/checkout
package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"

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
	log.Info().Int("port", cfg.HTTPPort).Msg("billing_starting")

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

	// SessionRevoker is satisfied by *auth.SessionStore directly; the billing
	// service only depends on the SessionRevoker interface.
	var revoker service.SessionRevoker = auth.NewSessionStore(pool)

	subSvc := service.NewService(subStore, processedStore, auditStore, revoker, log.With().Str("component", "billing_service").Logger())
	checkoutSvc, err := service.NewCheckoutService(cfg.CheckoutConfig(), log.With().Str("component", "billing_checkout").Logger())
	if err != nil {
		log.Fatal().Err(err).Msg("billing_checkout_service_init_failed")
	}

	paddleVerifier, err := paddle.NewVerifier(cfg.PaddleWebhookSecret, cfg.WebhookReplayWindow, cfg.WebhookMaxBodyBytes)
	if err != nil {
		log.Fatal().Err(err).Msg("paddle_verifier_init_failed")
	}
	lsVerifier, err := lemonsqueezy.NewVerifier(cfg.LSWebhookSecret, cfg.WebhookMaxBodyBytes)
	if err != nil {
		log.Fatal().Err(err).Msg("lemonsqueezy_verifier_init_failed")
	}

	metrics := server.NewMetrics()

	srv := server.New(server.Options{
		HTTPPort:            cfg.HTTPPort,
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

	errCh := make(chan error, 1)
	go func() { errCh <- srv.Start() }()

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
