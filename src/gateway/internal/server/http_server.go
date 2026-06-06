package server

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
	billingstore "github.com/flamegreat-1/etradie/src/billing/store"
	"github.com/flamegreat-1/etradie/src/consent"
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/pipeline"
	"github.com/flamegreat-1/etradie/src/gateway/internal/settingsstore"
	"github.com/flamegreat-1/etradie/src/gateway/internal/symbolstore"
	"github.com/flamegreat-1/etradie/src/mails"
	"github.com/flamegreat-1/etradie/src/performancereview"
	"github.com/flamegreat-1/etradie/src/support"
	"github.com/flamegreat-1/etradie/src/tradingplan"
	"github.com/flamegreat-1/etradie/src/tradingsystem"
)

// HTTPServer serves health, readiness, metrics, WebSocket notifications,
// event history, and the dashboard REST API.
//
// grpcServer is held only so handleReadiness can ask whether the gRPC
// surface is actually serving. The HTTP server never invokes any other
// method on it. Audit ref: G-C4.
type HTTPServer struct {
	server     *http.Server
	redis      *infra.RedisClient
	engine     *infra.EngineHTTPClient
	grpcServer *GRPCServer
	log        zerolog.Logger
}

// NewHTTPServer creates the HTTP server with all endpoints mounted.
// Auth routes are public; all dashboard API routes require authentication.
func NewHTTPServer(
	cfg *config.Config,
	redis *infra.RedisClient,
	engine *infra.EngineHTTPClient,
	hub *alert.Hub,
	transport *alertredis.Transport,
	orchestrator *pipeline.Orchestrator,
	symbolStore *symbolstore.Store,
	settingsStore *settingsstore.Store,
	scheduler *pipeline.Scheduler,
	tokenService *auth.TokenService,
	authHandler *auth.Handler,
	waitlistHandler *mails.Handler,
	consentHandler *consent.Handler,
	supportHandler *support.Handler,
	subStore *billingstore.SubscriptionStore,
	portalAudStore *billingstore.PortalAuditStore,
	billingClient *BillingClient,
	userStore *auth.UserStore,
	meteringHandler *MeteringHandler,
	quotaPolicyStore *billingstore.QuotaPolicyStore,
	usageStore *billingstore.UsageStore,
	tradingSystemHandler *tradingsystem.Handler,
	tradingPlanHandler *tradingplan.Handler,
	perfReviewHandler *performancereview.Handler,
	adminBillingHandler *AdminBillingHandler,
	adminQuotaHandler *AdminQuotaHandler,
	userBillingHandler *UserBillingHandler,
	killSwitchHandler *KillSwitchHandler,
	grpcServer *GRPCServer,
) (*HTTPServer, error) {
	s := &HTTPServer{
		redis:      redis,
		engine:     engine,
		grpcServer: grpcServer,
		log:        observability.Logger("http_server"),
	}

	mux := http.NewServeMux()

	// ---------------------------------------------------------------
	// Public ops endpoints (no auth required).
	// ---------------------------------------------------------------
	mux.HandleFunc("/health", s.handleHealth)
	mux.HandleFunc("/readiness", s.handleReadiness)
	mux.Handle("/metrics", promhttp.Handler())

	waitlistHandler.RegisterRoutes(mux)

	// ---------------------------------------------------------------
	// Auth endpoints (public: login, register, refresh, logout).
	// ---------------------------------------------------------------
	authHandler.RegisterRoutes(mux, tokenService)

	// ---------------------------------------------------------------
	// Protected endpoints (require valid JWT).
	//
	// authMiddleware accepts the JWT from Authorization header, WS
	// subprotocol, or access_token cookie (see auth/middleware.go).
	// csrfMiddleware enforces signed double-submit CSRF on every
	// state-changing method; safe methods bypass it (see auth/csrf.go).
	// The chain order is authMiddleware -> csrfMiddleware -> handler
	// so an unauthenticated request is rejected with 401, not 403,
	// AND so the user_id is in context for signed-CSRF verification.
	// ---------------------------------------------------------------
	authMiddleware := auth.RequireAuth(tokenService)
	csrfMiddleware := auth.RequireCSRF(authHandler.AuthConfig())

	mux.Handle("/ws/notifications", authMiddleware(http.HandlerFunc(alert.WebSocketHandler(hub))))

	mux.Handle("/events/recent", authMiddleware(csrfMiddleware(http.HandlerFunc(alert.RecentEventsHandler(transport)))))
	mux.Handle("/events/since", authMiddleware(csrfMiddleware(http.HandlerFunc(alert.EventsSinceHandler(transport)))))

	// quotaPolicyStore + usageStore power the LLM-quota pre-flight at
	// the top of POST /api/v1/cycle/run. Both are nil-tolerant on the
	// APIHandler side; passing nil cleanly disables the pre-flight
	// without breaking startup, which keeps test harnesses and any
	// future metering-disabled build path working. Audit ref:
	// ADMIN-QUOTA-7.
	api := NewAPIHandler(cfg, authHandler.AuthConfig(), orchestrator, symbolStore, settingsStore, scheduler, redis, engine, transport, quotaPolicyStore, usageStore)
	api.RegisterProtectedRoutes(mux, authMiddleware, csrfMiddleware)

	billing := NewBillingHandler(subStore, portalAudStore, billingClient, userStore)
	billing.RegisterRoutes(mux, authMiddleware, csrfMiddleware)

	// LLM metering: internal Reserve/Commit/Refund (shared-secret) +
	// user-facing GET /api/v1/billing/usage (auth + CSRF). The handler
	// guards the internal trio itself with a constant-time HMAC check
	// against the same X-Internal-Auth header the engine already uses
	// for its /internal/* surface.
	if meteringHandler != nil {
		meteringHandler.RegisterRoutes(mux, authMiddleware, csrfMiddleware)
	}

	// Cookie-consent endpoints. The handler owns its own auth-middleware
	// composition (OptionalAuth for the public POST/GET, RequireAuth +
	// CSRF for the authenticated /history and /attach endpoints) so the
	// mounting call only forwards the dependencies it cannot resolve
	// for itself.
	consentHandler.RegisterRoutes(mux, tokenService, csrfMiddleware)

	// Support & Contact Us endpoints. Public routes (contact form,
	// community-links) are reachable without authentication; the
	// authenticated ticketing CRUD inherits the standard
	// auth + CSRF middleware chain. The handler internally splits the
	// two surfaces so a single RegisterRoutes call is enough.
	supportHandler.RegisterRoutes(mux, authMiddleware, csrfMiddleware)

	// Trading System (PRACTICE.md Layer 2 — user personalization).
	// Public REST surface for the SPA + an internal endpoint the
	// Python engine calls when assembling the processor context. The
	// internal endpoint is guarded by the engine shared secret, not
	// the auth middleware, because the engine is the only legitimate
	// caller and it cannot hold a user JWT in background workers.
	if tradingSystemHandler != nil {
		tradingSystemHandler.RegisterRoutes(mux, authMiddleware, csrfMiddleware)
		tradingSystemHandler.RegisterInternalRoutes(mux)
	}

	// Trading Plan (PRACTICE.md “HOW I OPERATE” — 90-day workbook).
	// Same middleware pattern as Trading System: dashboard REST under
	// auth+csrf, engine callback under the shared-secret HMAC path.
	if tradingPlanHandler != nil {
		tradingPlanHandler.RegisterRoutes(mux, authMiddleware, csrfMiddleware)
		tradingPlanHandler.RegisterInternalRoutes(mux)
	}

	// Performance Review (PLAN.md — Weekly/Monthly AI performance analyst).
	// Public surface (latest/history/:id/generate) under auth+csrf;
	// engine callback/fail under the shared-secret HMAC path the
	// handler validates itself. Nil-tolerant so a future build that
	// disables this surface still starts cleanly.
	if perfReviewHandler != nil {
		perfReviewHandler.RegisterRoutes(mux, authMiddleware, csrfMiddleware)
		perfReviewHandler.RegisterInternalRoutes(mux)
	}

	// Admin-only billing read surface (read-only views over
	// billing_subscriptions, billing_subscription_events, billing_usage).
	// Every route is gated by auth -> RequireAdmin -> CSRF inside the
	// handler's own RegisterRoutes so the HTTP server only forwards
	// the middleware factories. A non-admin authenticated user gets a
	// clean 403 from RequireAdmin; the handler body never runs.
	if adminBillingHandler != nil {
		adminBillingHandler.RegisterRoutes(mux, authMiddleware, csrfMiddleware)
	}

	// Admin-only quota policy CRUD. Same chain as the billing admin
	// surface (auth -> RequireAdmin -> CSRF). Mounted on
	// /api/v1/admin/quota/policies[/{tier}]. Audit ref: ADMIN-QUOTA-6.
	if adminQuotaHandler != nil {
		adminQuotaHandler.RegisterRoutes(mux, authMiddleware, csrfMiddleware)
	}

	// User-facing billing read surface (Payment Methods card + Invoice
	// History feed). Every route is gated by auth -> CSRF and binds the
	// authenticated user_id server-side, so a forged caller cannot iterate
	// over another user's data. Nil-tolerant so future builds that skip
	// this surface still start up cleanly.
	if userBillingHandler != nil {
		userBillingHandler.RegisterRoutes(mux, authMiddleware, csrfMiddleware)
	}

	// Kill switch (CHECKLIST Section 8). Sole control plane for the
	// execution kill switch: client self-toggle (auth+CSRF) + admin
	// global/per-user override (auth -> RequireAdmin -> CSRF, composed
	// inside the handler). Delegates state + final authz to the
	// execution service via ports.ExecutionPort. Nil-tolerant so a
	// build without an execution engine still starts.
	if killSwitchHandler != nil {
		killSwitchHandler.RegisterRoutes(mux, authMiddleware, csrfMiddleware)
	}

	// CORS allowlist is validated at startup so a misconfig fails
	// the deploy loudly rather than silently producing 403s or, worse,
	// reflecting an unsafe origin under credentialed-CORS.
	allowedOrigins, err := buildCORSAllowlist(cfg.AllowedOrigins)
	if err != nil {
		return nil, fmt.Errorf("http_server: invalid CORS allowlist: %w", err)
	}

	s.server = &http.Server{
		Addr:    fmt.Sprintf(":%d", cfg.HTTPPort),
		Handler: corsMiddleware(allowedOrigins, authHandler.CSRFHeader())(mux),
		// ReadHeaderTimeout bounds the time to read request headers and
		// is the slow-loris guard on the read path. ReadTimeout bounds
		// the full request read (headers + body).
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       5 * time.Second,
		// WriteTimeout is intentionally 0 (no global write deadline).
		//
		// A single connection-wide write deadline cannot be scoped per
		// route, so any value low enough to be a useful slow-client
		// guard (e.g. 120s) also kills the gateway's legitimately
		// long-lived responses: POST /api/v1/cycle/run runs a full
		// TA+Macro+RAG+LLM cycle bounded by CycleTimeoutSeconds (up to
		// 900s), plus the notifications/long-poll surfaces. Per-request
		// duration is already bounded where it matters by the
		// orchestrator's context.WithTimeout(CycleTimeoutSeconds) and by
		// each phase's own context deadline, so request duration is
		// controlled without a blunt server-wide write deadline.
		WriteTimeout: 0,
		IdleTimeout:  60 * time.Second,
	}

	return s, nil
}

// Start begins serving HTTP. Blocks until the server stops.
func (s *HTTPServer) Start() error {
	s.log.Info().Str("addr", s.server.Addr).Msg("http_server_starting")
	err := s.server.ListenAndServe()
	if err == http.ErrServerClosed {
		return nil
	}
	return err
}

// Shutdown gracefully stops the HTTP server.
func (s *HTTPServer) Shutdown(ctx context.Context) error {
	s.log.Info().Msg("http_server_shutting_down")
	return s.server.Shutdown(ctx)
}

// buildCORSAllowlist normalises and validates the credentialed-CORS
// origin allowlist supplied via configuration. Every entry must be a
// full origin: scheme + host + optional port, no path, no wildcard.
//
// Refused (with a clear error) at startup:
//   - "*"        : credentialed CORS forbids the wildcard,
//   - "null"     : the literal "null" origin is used by sandboxed
//                  iframes and data: URLs; never legitimate here,
//   - empty / whitespace-only entries,
//   - any non-http/https scheme,
//   - entries containing a path, query, or fragment,
//   - entries that fail url.Parse.
func buildCORSAllowlist(raw []string) (map[string]bool, error) {
	allowed, rejected := auth.BuildCORSAllowlist(raw)
	if len(rejected) > 0 {
		// Fail the deploy: a malformed credentialed-CORS entry is an
		// operator error that must be fixed before the gateway serves
		// traffic, not silently dropped.
		return nil, fmt.Errorf("invalid CORS origin(s) %v: each entry must be a full http(s) origin (scheme://host[:port]) with no wildcard, no \"null\", and no path/query/fragment", rejected)
	}
	return allowed, nil
}

// corsMiddleware adds CORS headers for dashboard cross-origin requests.
// Allow-Headers is built dynamically from the configured CSRF header
// so renaming AUTH_CSRF_HEADER does not silently break the preflight.
func corsMiddleware(allowedOrigins map[string]bool, csrfHeaderName string) func(http.Handler) http.Handler {
	csrfHeaderName = strings.TrimSpace(csrfHeaderName)
	if csrfHeaderName == "" {
		csrfHeaderName = "X-CSRF-Token"
	}
	allowHeaders := strings.Join([]string{
		"Content-Type",
		"Authorization",
		"X-Trace-ID",
		csrfHeaderName,
	}, ", ")
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin := r.Header.Get("Origin")
			if origin != "" && allowedOrigins[origin] {
				w.Header().Set("Access-Control-Allow-Origin", origin)
				w.Header().Set("Access-Control-Allow-Credentials", "true")
				w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
				w.Header().Set("Access-Control-Allow-Headers", allowHeaders)
				w.Header().Set("Access-Control-Max-Age", "86400")
				w.Header().Add("Vary", "Origin")
			}

			if r.Method == http.MethodOptions {
				w.WriteHeader(http.StatusNoContent)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func (s *HTTPServer) handleHealth(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"status":"ok"}`))
}

// handleReadiness reports the pod ready ONLY when every dependency the
// gateway will hit on its first inbound request is reachable AND the
// gateway's OWN gRPC surface is bound and serving.
//
// The grpcServer dependency closes a real bug: the HTTP and gRPC
// servers start in parallel goroutines in main.go. Before this gate,
// the kubelet would mark the pod Ready as soon as the HTTP listener
// bound, but execution and management dial gateway:50052; until the
// gRPC goroutine reached net.Listen the dials returned ECONNREFUSED.
// Audit ref: G-C4.
func (s *HTTPServer) handleReadiness(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	redisOK := s.redis.HealthCheck(ctx)
	engineOK := s.engine.HealthCheck(ctx)
	grpcOK := s.grpcServer != nil && s.grpcServer.IsServing()

	w.Header().Set("Content-Type", "application/json")
	if redisOK && engineOK && grpcOK {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ready","redis":true,"engine":true,"grpc":true}`))
		return
	}
	w.WriteHeader(http.StatusServiceUnavailable)
	_, _ = fmt.Fprintf(w, `{"status":"not_ready","redis":%t,"engine":%t,"grpc":%t}`, redisOK, engineOK, grpcOK)
}
