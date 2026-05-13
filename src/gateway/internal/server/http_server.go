package server

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
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
	"github.com/flamegreat-1/etradie/src/support"
)

// HTTPServer serves health, readiness, metrics, WebSocket notifications,
// event history, and the dashboard REST API.
type HTTPServer struct {
	server *http.Server
	redis  *infra.RedisClient
	engine *infra.EngineHTTPClient
	log    zerolog.Logger
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
) (*HTTPServer, error) {
	s := &HTTPServer{
		redis:  redis,
		engine: engine,
		log:    observability.Logger("http_server"),
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

	api := NewAPIHandler(cfg, orchestrator, symbolStore, settingsStore, scheduler, redis, engine, transport)
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

	// CORS allowlist is validated at startup so a misconfig fails
	// the deploy loudly rather than silently producing 403s or, worse,
	// reflecting an unsafe origin under credentialed-CORS.
	allowedOrigins, err := buildCORSAllowlist(cfg.AllowedOrigins)
	if err != nil {
		return nil, fmt.Errorf("http_server: invalid CORS allowlist: %w", err)
	}

	s.server = &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.HTTPPort),
		Handler:      corsMiddleware(allowedOrigins, authHandler.CSRFHeader())(mux),
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 120 * time.Second,
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
	out := make(map[string]bool, len(raw))
	for _, entry := range raw {
		s := strings.TrimSpace(entry)
		if s == "" {
			continue
		}
		if s == "*" {
			return nil, fmt.Errorf("wildcard origin %q is incompatible with credentialed CORS", s)
		}
		if strings.EqualFold(s, "null") {
			return nil, fmt.Errorf("literal null origin is not a valid CORS entry")
		}
		u, err := url.Parse(s)
		if err != nil {
			return nil, fmt.Errorf("invalid origin %q: %w", s, err)
		}
		if u.Scheme != "http" && u.Scheme != "https" {
			return nil, fmt.Errorf("origin %q must use http or https scheme", s)
		}
		if u.Host == "" {
			return nil, fmt.Errorf("origin %q is missing host", s)
		}
		if u.Path != "" || u.RawQuery != "" || u.Fragment != "" {
			return nil, fmt.Errorf("origin %q must not contain a path, query, or fragment", s)
		}
		normalised := u.Scheme + "://" + u.Host
		out[normalised] = true
	}
	return out, nil
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

func (s *HTTPServer) handleReadiness(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	redisOK := s.redis.HealthCheck(ctx)
	engineOK := s.engine.HealthCheck(ctx)

	w.Header().Set("Content-Type", "application/json")
	if redisOK && engineOK {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ready","redis":true,"engine":true}`))
	} else {
		w.WriteHeader(http.StatusServiceUnavailable)
		_, _ = fmt.Fprintf(w, `{"status":"not_ready","redis":%t,"engine":%t}`, redisOK, engineOK)
	}
}
