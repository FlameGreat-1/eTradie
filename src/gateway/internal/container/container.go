package container

import (
	"context"
	"fmt"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/alert"
	alertredis "github.com/flamegreat/etradie/src/alert/redis"
	"github.com/flamegreat/etradie/src/gateway/internal/collectors"
	"github.com/flamegreat/etradie/src/gateway/internal/config"
	ctxpkg "github.com/flamegreat/etradie/src/gateway/internal/context"
	"github.com/flamegreat/etradie/src/gateway/internal/infra"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
	"github.com/flamegreat/etradie/src/gateway/internal/pipeline"
	"github.com/flamegreat/etradie/src/gateway/internal/ports"
	"github.com/flamegreat/etradie/src/gateway/internal/querybuilder"
	"github.com/flamegreat/etradie/src/gateway/internal/routing"
	"github.com/flamegreat/etradie/src/gateway/internal/server"
	"github.com/flamegreat/etradie/src/gateway/internal/settingsstore"
	"github.com/flamegreat/etradie/src/gateway/internal/symbolstore"
)

// Container holds all gateway components and manages their lifecycle.
type Container struct {
	Cfg            *config.Config
	Redis          *infra.RedisClient
	Engine         *infra.EngineHTTPClient
	Execution      *infra.ExecutionGRPCAdapter
	SymbolStore    *symbolstore.Store
	SettingsStore  *settingsstore.Store
	Orchestrator   *pipeline.Orchestrator
	Scheduler      *pipeline.Scheduler
	HTTPServer     *server.HTTPServer
	GRPCServer     *server.GRPCServer
	AlertHub       *alert.Hub
	AlertTransport *alertredis.Transport
	log            zerolog.Logger
}

// New builds all gateway components in correct dependency order.
func New(cfg *config.Config, execution ports.ExecutionPort, execAdapter *infra.ExecutionGRPCAdapter) (*Container, error) {
	log := observability.Logger("container")

	// Infrastructure.
	redisClient, err := infra.NewRedisClient(cfg.RedisURL, cfg.RedisMaxConnections)
	if err != nil {
		return nil, fmt.Errorf("container: redis: %w", err)
	}

	engineHTTP := infra.NewEngineHTTPClient(cfg.EngineHTTPURL, cfg.CycleTimeoutSeconds)

	// Processor adapter: calls Python engine via HTTP.
	processor := infra.NewHTTPProcessorAdapter(engineHTTP)

	// Symbol Store (Redis-backed, survives restarts).
	symStore := symbolstore.NewStore(redisClient, cfg)

	// Settings Store (Redis-backed, survives restarts).
	settStore := settingsstore.NewStore(redisClient)

	// Alert Hub + Redis Transport (Option B: cross-service notifications).
	hub := alert.NewHub()
	transport := alertredis.NewTransport(redisClient.RawClient(), hub, alertredis.TransportConfig{})
	transport.Start(context.Background())

	// Collectors (with Redis caching).
	taCollector := collectors.NewTACollector(engineHTTP, redisClient, cfg)
	macroCollector := collectors.NewMacroCollector(engineHTTP, redisClient, cfg.MacroCacheTTLSeconds)

	// Query Builder.
	qb := querybuilder.NewBuilder()

	// Context Assembler.
	assembler := ctxpkg.NewAssembler()

	// Guard Evaluator.
	guards := routing.NewGuardEvaluator()

	// Decision Router.
	router := routing.NewRouter(guards, execution, transport)

	// Pipeline Orchestrator.
	orchestrator := pipeline.NewOrchestrator(
		cfg, taCollector, macroCollector, qb, assembler,
		processor, router, engineHTTP, transport,
	)

	// Scheduler (with SettingsStore for persisted interval overrides).
	scheduler := pipeline.NewScheduler(orchestrator, symStore, settStore, cfg, transport)

	// Load any dashboard-set interval override from Redis before starting.
	scheduler.LoadPersistedInterval(context.Background())

	// Servers.
	httpServer := server.NewHTTPServer(cfg, redisClient, engineHTTP, hub, transport)
	grpcServer := server.NewGRPCServer(cfg, orchestrator, symStore, settStore, scheduler, redisClient, engineHTTP, transport)

	log.Info().
		Int("cycle_interval", scheduler.CurrentIntervalSeconds()).
		Int("cycle_timeout", cfg.CycleTimeoutSeconds).
		Bool("execution_available", execution != nil).
		Msg("gateway_container_built")

	return &Container{
		Cfg:            cfg,
		Redis:          redisClient,
		Engine:         engineHTTP,
		Execution:      execAdapter,
		SymbolStore:    symStore,
		SettingsStore:  settStore,
		Orchestrator:   orchestrator,
		Scheduler:      scheduler,
		HTTPServer:     httpServer,
		GRPCServer:     grpcServer,
		AlertHub:       hub,
		AlertTransport: transport,
		log:            log,
	}, nil
}

// Shutdown gracefully closes all resources in reverse dependency order.
func (c *Container) Shutdown(ctx context.Context) {
	c.log.Info().Msg("gateway_container_shutting_down")

	c.GRPCServer.GracefulStop()

	if err := c.HTTPServer.Shutdown(ctx); err != nil {
		c.log.Error().Err(err).Msg("http_server_shutdown_error")
	}

	c.Engine.Close()

	if c.Execution != nil {
		if err := c.Execution.Close(); err != nil {
			c.log.Error().Err(err).Msg("execution_adapter_close_error")
		}
	}

	// Close alert transport before Redis (transport uses Redis).
	c.AlertTransport.Close()
	c.AlertHub.Close()

	if err := c.Redis.Close(); err != nil {
		c.log.Error().Err(err).Msg("redis_close_error")
	}

	c.log.Info().Msg("gateway_container_stopped")
}
