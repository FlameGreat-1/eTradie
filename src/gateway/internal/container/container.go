package container

import (
	"context"
	"fmt"

	"github.com/rs/zerolog"

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
	"github.com/flamegreat/etradie/src/gateway/internal/symbolstore"
)

// Container holds all gateway components and manages their lifecycle.
type Container struct {
	Cfg          *config.Config
	Redis        *infra.RedisClient
	EngineHTTP   *infra.EngineHTTPClient
	SymbolStore  *symbolstore.Store
	Orchestrator *pipeline.Orchestrator
	Scheduler    *pipeline.Scheduler
	HTTPServer   *server.HTTPServer
	GRPCServer   *server.GRPCServer
	log          zerolog.Logger
}

// New builds all gateway components in correct dependency order.
func New(cfg *config.Config, execution ports.ExecutionPort) (*Container, error) {
	log := observability.Logger("container")

	// Infrastructure.
	redisClient, err := infra.NewRedisClient(cfg.RedisURL, cfg.RedisMaxConnections)
	if err != nil {
		return nil, fmt.Errorf("container: redis: %w", err)
	}

	engineHTTP := infra.NewEngineHTTPClient(cfg.EngineHTTPURL, cfg.CycleTimeoutSeconds)

	// Processor adapter: calls Python engine via HTTP.
	processor := infra.NewHTTPProcessorAdapter(engineHTTP)

	// Symbol Store.
	symStore := symbolstore.NewStore(redisClient, cfg)

	// Collectors.
	taCollector := collectors.NewTACollector(engineHTTP, cfg)
	macroCollector := collectors.NewMacroCollector(engineHTTP)

	// Query Builder.
	qb := querybuilder.NewBuilder()

	// Context Assembler.
	assembler := ctxpkg.NewAssembler()

	// Guard Evaluator.
	guards := routing.NewGuardEvaluator()

	// Decision Router.
	router := routing.NewRouter(guards, execution)

	// Pipeline Orchestrator.
	orchestrator := pipeline.NewOrchestrator(
		cfg, taCollector, macroCollector, qb, assembler,
		processor, router, engineHTTP,
	)

	// Scheduler.
	scheduler := pipeline.NewScheduler(orchestrator, symStore, cfg)

	// Servers.
	httpServer := server.NewHTTPServer(cfg, redisClient, engineHTTP)
	grpcServer := server.NewGRPCServer(cfg, orchestrator, symStore, redisClient, engineHTTP)

	log.Info().
		Int("cycle_interval", cfg.CycleIntervalSeconds).
		Int("cycle_timeout", cfg.CycleTimeoutSeconds).
		Bool("execution_available", execution != nil).
		Msg("gateway_container_built")

	return &Container{
		Cfg:          cfg,
		Redis:        redisClient,
		EngineHTTP:   engineHTTP,
		SymbolStore:  symStore,
		Orchestrator: orchestrator,
		Scheduler:    scheduler,
		HTTPServer:   httpServer,
		GRPCServer:   grpcServer,
		log:          log,
	}, nil
}

// Shutdown gracefully closes all resources in reverse dependency order.
func (c *Container) Shutdown(ctx context.Context) {
	c.log.Info().Msg("gateway_container_shutting_down")

	c.GRPCServer.GracefulStop()

	if err := c.HTTPServer.Shutdown(ctx); err != nil {
		c.log.Error().Err(err).Msg("http_server_shutdown_error")
	}

	c.EngineHTTP.Close()

	if err := c.Redis.Close(); err != nil {
		c.log.Error().Err(err).Msg("redis_close_error")
	}

	c.log.Info().Msg("gateway_container_stopped")
}
