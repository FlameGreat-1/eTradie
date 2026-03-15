package main

import (
	"context"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/flamegreat/etradie/src/gateway/internal/config"
	"github.com/flamegreat/etradie/src/gateway/internal/container"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
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

	// Initialize OpenTelemetry tracing.
	ctx := context.Background()
	shutdownTracing, err := observability.InitTracing(ctx, cfg.OTELServiceName, cfg.OTELEndpoint)
	if err != nil {
		log.Warn().Err(err).Msg("tracing_init_failed_continuing_without_tracing")
	}

	// Build the gateway container (all dependency wiring).
	// Execution port is nil until Module B is implemented.
	// The gateway operates in "analysis-only" mode: it runs the full pipeline
	// but returns {status: pending} from the execution step.
	// The processor is wired internally via HTTPProcessorAdapter.
	c, err := container.New(cfg, nil)
	if err != nil {
		log.Fatal().Err(err).Msg("gateway_container_build_failed")
	}

	// Health check at startup.
	redisOK := c.Redis.HealthCheck(ctx)
	engineOK := c.Engine.HealthCheck(ctx)
	log.Info().
		Bool("redis", redisOK).
		Bool("engine", engineOK).
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

	if shutdownTracing != nil {
		if err := shutdownTracing(shutdownCtx); err != nil {
			log.Error().Err(err).Msg("tracing_shutdown_error")
		}
	}

	log.Info().Msg("gateway_stopped")
}
