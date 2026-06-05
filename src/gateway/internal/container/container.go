package container

import (
	"context"
	"fmt"
	"os"
	"strings"
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
	"github.com/flamegreat-1/etradie/src/gateway/internal/tradingplanadapter"
	"github.com/flamegreat-1/etradie/src/mails"
	"github.com/flamegreat-1/etradie/src/performancereview"
	"github.com/flamegreat-1/etradie/src/support"
	"github.com/flamegreat-1/etradie/src/tradingplan"
	"github.com/flamegreat-1/etradie/src/tradingsystem"
)

// isProdLikeEnvContainer reports whether the runtime environment is
// production or staging, by the same APP_ENV/ENV/ENVIRONMENT precedence
// the gateway config and the Go services use. Used to enforce that the
// Redis-backed auth attempt limiter is mandatory in prod/staging.
func isProdLikeEnvContainer() bool {
	for _, k := range []string{"APP_ENV", "ENV", "ENVIRONMENT"} {
		switch strings.ToLower(strings.TrimSpace(os.Getenv(k))) {
		case "production", "prod", "staging":
			return true
		}
	}
	return false
}

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

	// Cluster-wide auth abuse control (login/register/refresh rate limit
	// + per-account lockout). Backed by Redis so the limit is shared
	// across every gateway replica instead of being per-pod.
	//
	// Fail-closed posture: in production/staging the Redis-backed
	// limiter is MANDATORY. We never fall back to a per-pod in-memory
	// limiter in a prod-like environment, because that silently
	// reintroduces the brute-force bypass this control exists to close.
	// redisClient is non-nil here (NewRedisClient returned no error
	// above), so the limiter is always wired in prod; the explicit
	// guard documents and enforces the invariant for any future
	// refactor that might make the client optional.
	if isProdLikeEnvContainer() {
		if redisClient == nil || redisClient.RawClient() == nil {
			return nil, fmt.Errorf(
				"container: a Redis-backed auth attempt limiter is required in production/staging; " +
					"refusing to start with a per-pod in-memory fallback that would bypass cluster-wide login rate limiting",
			)
		}
		authHandler.WithAttemptLimiter(server.NewRedisAttemptLimiter(redisClient.RawClient()))
		log.Info().Msg("auth_attempt_limiter_redis_backed_enabled")
	} else if redisClient != nil && redisClient.RawClient() != nil {
		// Dev/test with Redis available: still use the real limiter so
		// local behaviour matches production.
		authHandler.WithAttemptLimiter(server.NewRedisAttemptLimiter(redisClient.RawClient()))
		log.Info().Msg("auth_attempt_limiter_redis_backed_enabled_dev")
	} else {
		// Dev/test without Redis: explicit, loudly-logged in-memory
		// limiter. Never selected in prod-like environments (guarded
		// above).
		authHandler.WithAttemptLimiter(auth.NewDevAttemptLimiter())
		log.Warn().Msg("auth_attempt_limiter_in_memory_dev_only: per-pod limiter; NOT for production")
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

	// Inject the management-backed manual-trade reader that auto-populates
	// the trading-plan Daily Execution Journal's objective cells. Guarded
	// on BOTH the handler and the client being non-nil: NewManualTradeReader
	// returns a nil *ManualTradeReader when the client is nil, and boxing a
	// nil concrete pointer into the ManualTradeReader interface would defeat
	// the handler's nil-check (the interface would be non-nil). When
	// management is unavailable the reader is simply never set and the plan
	// still loads normally (the trader fills rows by hand).
	if tradingPlanHandler != nil && mgmtClient != nil {
		tradingPlanHandler.WithManualTradeReader(tradingplanadapter.NewManualTradeReader(mgmtClient))
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
		transport,
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

	// Kill-switch handler (CHECKLIST Section 8). Sole control plane for
	// the execution kill switch; delegates to the execution service via
	// the ExecutionPort. Constructed only when an execution engine is
	// wired (mirrors the execution_available guard) so a no-execution
	// build does not mount a surface that would 502 on every call.
	var killSwitchHandler *server.KillSwitchHandler
	if execution != nil {
		killSwitchHandler = server.NewKillSwitchHandler(execution, userStore, emailSender, authCfg.FrontendBaseURL)
	}

	// Service-token revocation on the gateway gRPC surface. Module B
	// (execution) calls the gateway gRPC (ConfirmSetup /
	// NotifyExecutionCompleted / ...) carrying the user's SERVICE token
	// (the watcher token-refresh loop mints these via
	// IssueServiceToken). Without an epoch resolver, VerifyAccessToken
	// skips the revocation check for those service tokens, leaving the
	// gateway as the only service-token-consuming surface that does NOT
	// honour a token_epoch bump (admin deactivate / password change /
	// reset) -- an asymmetry with execution + management, which both
	// wire the resolver. Attach it here for defence-in-depth.
	//
	// Zero cost on the user-auth HTTP path: VerifyAccessToken performs
	// the per-user epoch DB lookup ONLY for token_type=="svc"; user
	// ACCESS tokens skip the resolver and stay stateless. The gateway
	// shares one *auth.TokenService across HTTP + gRPC, so this single
	// call arms the check everywhere it matters. Audit ref: B3.
	tokenService = tokenService.WithEpochResolver(userStore)

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
	httpServer, err := server.NewHTTPServer(cfg, redisClient, engineHTTP, hub, transport, orchestrator, symStore, settStore, scheduler, tokenService, authHandler, waitlistHandler, consentHandler, supportHandler, subStore, portalAudStore, billingClient, userStore, meteringHandler, quotaPolicyStore, usageStore, tradingSystemHandler, tradingPlanHandler, perfReviewHandler, adminBillingHandler, adminQuotaHandler, userBillingHandler, killSwitchHandler, grpcServer)
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
