package container

import (
	"context"
	"fmt"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/billing/store"
	"github.com/flamegreat-1/etradie/src/consent"
	"github.com/flamegreat-1/etradie/src/gateway/internal/collectors"
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	ctxpkg "github.com/flamegreat-1/etradie/src/gateway/internal/context"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/management"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/pipeline"
	"github.com/flamegreat-1/etradie/src/gateway/internal/ports"
	"github.com/flamegreat-1/etradie/src/gateway/internal/querybuilder"
	"github.com/flamegreat-1/etradie/src/gateway/internal/routing"
	"github.com/flamegreat-1/etradie/src/gateway/internal/server"
	"github.com/flamegreat-1/etradie/src/gateway/internal/settingsstore"
	"github.com/flamegreat-1/etradie/src/gateway/internal/symbolstore"
	"github.com/flamegreat-1/etradie/src/mails"
	"github.com/flamegreat-1/etradie/src/performancereview"
	"github.com/flamegreat-1/etradie/src/support"
	"github.com/flamegreat-1/etradie/src/tradingplan"
	"github.com/flamegreat-1/etradie/src/tradingsystem"
)

// Container holds all gateway components and manages their lifecycle.
type Container struct {
	Cfg              *config.Config
	Redis            *infra.RedisClient
	Engine           *infra.EngineHTTPClient
	Execution        *infra.ExecutionGRPCAdapter
	UsageStore       *store.UsageStore
	SubStore         *store.SubscriptionStore
	QuotaPolicyStore *store.QuotaPolicyStore
	PortalAuditStore *store.PortalAuditStore
	SymbolStore      *symbolstore.Store
	SettingsStore    *settingsstore.Store
	Orchestrator     *pipeline.Orchestrator
	Scheduler        *pipeline.Scheduler
	HTTPServer       *server.HTTPServer
	GRPCServer       *server.GRPCServer
	Management       *management.Client
	AlertHub         *alert.Hub
	AlertTransport   *alertredis.Transport
	ConsentHandler   *consent.Handler
	SupportNotifier  *support.Notifier
	log              zerolog.Logger
}

// New builds all gateway components in correct dependency order.
// tokenService and authHandler are created in main.go from the auth
// package and passed here so the HTTP/gRPC servers can mount auth
// routes and apply auth middleware. consentHandler follows the exact
// same pattern: it owns its own DB-backed store and IP resolver, so
// the container only needs to pass it through to the HTTP server.
func New(
	cfg *config.Config,
	execution ports.ExecutionPort,
	execAdapter *infra.ExecutionGRPCAdapter,
	tokenService *auth.TokenService,
	authHandler *auth.Handler,
	authCfg *auth.Config,
	userStore *auth.UserStore,
	waitlistHandler *mails.Handler,
	consentHandler *consent.Handler,
	supportHandler *support.Handler,
	supportNotifier *support.Notifier,
	emailSender *mails.Sender,
	usageStore *store.UsageStore,
	subStore *store.SubscriptionStore,
	portalAudStore *store.PortalAuditStore,
	tradingSystemHandler *tradingsystem.Handler,
	tradingPlanHandler *tradingplan.Handler,
	perfReviewHandler *performancereview.Handler,
) (*Container, error) {
	log := observability.Logger("container")

	// Infrastructure.
	redisClient, err := infra.NewRedisClient(cfg.RedisURL, cfg.RedisMaxConnections)
	if err != nil {
		return nil, fmt.Errorf("container: redis: %w", err)
	}

	engineHTTP := infra.NewEngineHTTPClient(cfg.EngineHTTPURL, cfg.EngineInternalSharedSecret, cfg.CycleTimeoutSeconds)

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
	router := routing.NewRouter(guards, execution, transport, usageStore)

	// Management Client (Module C).
	var mgmtClient *management.Client
	if cfg.ManagementEnabled {
		mgmtClient, err = management.NewClient(cfg.ManagementAddr, cfg.ManagementTimeoutMs)
		if err != nil {
			log.Warn().Err(err).Msg("failed_to_connect_to_management_engine")
			// We don't fail container creation if management is down, Gateway can still route to Execution.
		}
	}

	// Pipeline Orchestrator.
	orchestrator := pipeline.NewOrchestrator(
		cfg, taCollector, macroCollector, qb, assembler,
		processor, router, engineHTTP, transport, execution,
		pipeline.WithRedisRaw(redisClient.RawClient()),
	)

	// Tier-quota policy store. Backs the tier_quota_policies table
	// (migration 0028) and is read by the metering handler on every
	// Reserve, by the admin quota handler for GET / PUT operations, by
	// the dashboard REST pre-flight in handleRunCycle, AND by the
	// scheduler's auto-path pre-flight in executeUserCycle. Same
	// *pgxpool.Pool as every other billing store, sourced via
	// subStore.Pool() so connection-pool lifecycle stays uniform.
	//
	// Constructed BEFORE the scheduler so the scheduler can hold the
	// shared instance directly (audit ref: ADMIN-QUOTA-7). Every other
	// consumer downstream of this point reads the same pointer.
	quotaPolicyStore := store.NewQuotaPolicyStore(subStore.Pool())

	// Scheduler (with SettingsStore for persisted interval overrides).
	// tokenService and userStore are passed so the scheduler can issue
	// service tokens for autonomous 24/7 operation without a logged-in user.
	//
	// quotaPolicyStore + usageStore power the auto-path pre-flight that
	// short-circuits an exhausted user's tick BEFORE symbol-fetch /
	// orchestrator cost. Both are the SAME shared instances every
	// other gateway consumer reads. Audit ref: ADMIN-QUOTA-7.
	scheduler := pipeline.NewScheduler(orchestrator, symStore, settStore, cfg, transport, tokenService, userStore, quotaPolicyStore, usageStore)

	// Billing service client. Used by the gateway billing handler to create
	// checkout URLs without ever holding provider API keys.
	billingClient, err := server.NewBillingClient(
		cfg.BillingServiceURL,
		cfg.BillingInternalSharedSecret,
		time.Duration(cfg.BillingClientTimeoutMs)*time.Millisecond,
	)
	if err != nil {
		return nil, fmt.Errorf("container: billing client: %w", err)
	}

	// LLM metering handler. The same engine shared-secret used by every
	// /internal/* call from gateway to engine is reused here in the
	// opposite direction (engine -> gateway). When the secret is empty
	// (dev) the handler refuses every internal call with 401, which is
	// the safe default.
	meteringHandler := server.NewMeteringHandler(
		usageStore,
		userStore,
		quotaPolicyStore,
		authCfg,
		cfg.EngineInternalSharedSecret,
	)

	// Wire the shared *mails.Sender (already used for waitlist and
	// password-reset emails) into the metering handler so the
	// soft-cap warning email reuses the same SMTP configuration with
	// zero extra env vars. The dashboard URL is built from the
	// already-validated AUTH_FRONTEND_BASE_URL so the email button
	// links to the same SPA origin every other auth email uses; an
	// empty FrontendBaseURL (dev) leaves the URL empty and the
	// template gracefully degrades the CTA button.
	dashboardURL := ""
	if authCfg.FrontendBaseURL != "" {
		dashboardURL = authCfg.FrontendBaseURL + "/settings/billing"
	}
	meteringHandler.WithSoftCapMailer(emailSender, dashboardURL)

	// Admin billing handler. Reads-only views over billing_subscriptions,
	// billing_subscription_events, and billing_usage joined with
	// auth_users. Used by the admin dashboard's Transactions and
	// AI-Token-Usage pages. The queries surface is a thin wrapper over
	// the same *pgxpool.Pool every other billing store uses so it
	// inherits the connection-pool lifecycle automatically.
	adminQueries := store.NewAdminQueries(subStore.Pool())
	adminBillingHandler := server.NewAdminBillingHandler(adminQueries)

	// Admin quota policy handler. Reads / writes tier_quota_policies
	// rows. Same chain as the billing admin handler:
	// auth -> RequireAdmin -> CSRF inside the handler's RegisterRoutes.
	adminQuotaHandler := server.NewAdminQuotaHandler(quotaPolicyStore)

	// User billing handler. Read-only, user-scoped views over
	// billing_subscriptions (card snapshot) and billing_subscription_events
	// (per-user financial history) for the dashboard's Payment Methods
	// and Invoice History panels. Same pool, same lifecycle, separate
	// query surface so the user-facing fast path is not polluted with
	// admin-only joins and the SQL stays trivially user_id-bound.
	userQueries := store.NewUserQueries(subStore.Pool())
	userBillingHandler := server.NewUserBillingHandler(userQueries)

	// Build the gRPC server FIRST so the HTTP server's readiness handler
	// can ask it whether the gRPC surface is bound and serving. Without
	// this ordering the kubelet would mark the pod Ready before the
	// gRPC goroutine reached net.Listen, causing transient ECONNREFUSED
	// at every rollout. Audit ref: G-C4.
	grpcServer := server.NewGRPCServer(cfg, orchestrator, symStore, settStore, scheduler, redisClient, engineHTTP, transport, mgmtClient, tokenService)

	// Servers (now with auth + consent support + metering + tradingsystem + admin billing + user billing).
	//
	// quotaPolicyStore + usageStore are forwarded here so the dashboard
	// REST handler (APIHandler.handleRunCycle) can run the LLM-quota
	// pre-flight before TA / Macro / RAG resource burn. Both are the
	// SAME instances every other consumer in this container already
	// shares: usageStore is the argument passed to New() above, and
	// quotaPolicyStore was built once a few lines up and is also the
	// instance handed to meteringHandler and adminQuotaHandler. There
	// is only one of each in the gateway process. Audit ref:
	// ADMIN-QUOTA-7.
	httpServer, err := server.NewHTTPServer(cfg, redisClient, engineHTTP, hub, transport, orchestrator, symStore, settStore, scheduler, tokenService, authHandler, waitlistHandler, consentHandler, supportHandler, subStore, portalAudStore, billingClient, userStore, meteringHandler, quotaPolicyStore, usageStore, tradingSystemHandler, tradingPlanHandler, perfReviewHandler, adminBillingHandler, adminQuotaHandler, userBillingHandler, grpcServer)
	if err != nil {
		return nil, fmt.Errorf("container: http server: %w", err)
	}

	log.Info().
		Int("default_cycle_interval", scheduler.DefaultIntervalSeconds()).
		Int("cycle_timeout", cfg.CycleTimeoutSeconds).
		Bool("execution_available", execution != nil).
		Bool("management_available", mgmtClient != nil).
		Bool("auth_enabled", true).
		Msg("gateway_container_built")

	return &Container{
		Cfg:              cfg,
		Redis:            redisClient,
		Engine:           engineHTTP,
		Execution:        execAdapter,
		UsageStore:       usageStore,
		SubStore:         subStore,
		QuotaPolicyStore: quotaPolicyStore,
		PortalAuditStore: portalAudStore,
		SymbolStore:      symStore,
		SettingsStore:    settStore,
		Orchestrator:     orchestrator,
		Scheduler:        scheduler,
		HTTPServer:       httpServer,
		GRPCServer:       grpcServer,
		Management:       mgmtClient,
		AlertHub:         hub,
		AlertTransport:   transport,
		ConsentHandler:   consentHandler,
		SupportNotifier:  supportNotifier,
		log:              log,
	}, nil
}

// Shutdown gracefully closes all resources in reverse dependency order.
func (c *Container) Shutdown(ctx context.Context) {
	c.log.Info().Msg("gateway_container_shutting_down")

	c.GRPCServer.GracefulStop()

	if err := c.HTTPServer.Shutdown(ctx); err != nil {
		c.log.Error().Err(err).Msg("http_server_shutdown_error")
	}

	// Drain in-flight support notifications AFTER the HTTP server has
	// stopped accepting new requests (so no new tickets can register
	// work) and BEFORE the DB pool is closed (the notifier itself does
	// not touch the DB, but ordering keeps the dependency graph honest).
	// A SIGTERM that arrives during a burst of new tickets now waits
	// for Discord / Telegram / WhatsApp / email deliveries to finish or
	// for the shutdown deadline to expire, whichever comes first.
	if c.SupportNotifier != nil {
		if err := c.SupportNotifier.Shutdown(ctx); err != nil {
			c.log.Warn().Err(err).Msg("support_notifier_shutdown_incomplete")
		} else {
			c.log.Info().Msg("support_notifier_drained")
		}
	}

	c.Engine.Close()

	if c.Execution != nil {
		if err := c.Execution.Close(); err != nil {
			c.log.Error().Err(err).Msg("execution_adapter_close_error")
		}
	}

	if c.Management != nil {
		if err := c.Management.Close(); err != nil {
			c.log.Error().Err(err).Msg("management_client_close_error")
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
