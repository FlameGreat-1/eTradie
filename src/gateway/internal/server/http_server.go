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
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/pipeline"
	"github.com/flamegreat-1/etradie/src/gateway/internal/settingsstore"
	"github.com/flamegreat-1/etradie/src/gateway/internal/symbolstore"
	"github.com/flamegreat-1/etradie/src/mails"
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
) *HTTPServer {
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

	// Waitlist endpoint (public, no auth required).
	waitlistHandler.RegisterRoutes(mux)

	// ---------------------------------------------------------------
	// Auth endpoints (public: login, register, refresh).
	// Protected auth endpoints are handled inside RegisterRoutes.
	// ---------------------------------------------------------------
	authHandler.RegisterRoutes(mux, tokenService)

	// ---------------------------------------------------------------
	// Protected endpoints (require valid JWT).
	// ---------------------------------------------------------------
	authMiddleware := auth.RequireAuth(tokenService)

	// WebSocket notifications (real-time event stream to dashboard).
	mux.Handle("/ws/notifications", authMiddleware(http.HandlerFunc(alert.WebSocketHandler(hub))))

	// Event history REST endpoints (Redis-backed persistence).
	mux.Handle("/events/recent", authMiddleware(http.HandlerFunc(alert.RecentEventsHandler(transport))))
	mux.Handle("/events/since", authMiddleware(http.HandlerFunc(alert.EventsSinceHandler(transport))))

	// Dashboard REST API (all protected).
	api := NewAPIHandler(cfg, orchestrator, symbolStore, settingsStore, scheduler, redis, engine, transport)
	api.RegisterProtectedRoutes(mux, authMiddleware)

	// Build the CORS origin allowlist from config.
	allowedOrigins := make(map[string]bool, len(cfg.AllowedOrigins))
	for _, o := range cfg.AllowedOrigins {
		allowedOrigins[strings.TrimSpace(o)] = true
	}

	s.server = &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.HTTPPort),
		Handler:      corsMiddleware(allowedOrigins)(mux),
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 120 * time.Second, // RunCycle can take up to cycle_timeout_seconds (default 300s)
		IdleTimeout:  60 * time.Second,
	}

	return s
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

// corsMiddleware adds CORS headers for dashboard cross-origin requests.
// Uses an explicit allowlist of origins to prevent bypass attacks.
func corsMiddleware(allowedOrigins map[string]bool) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin := r.Header.Get("Origin")
			if origin != "" && allowedOrigins[origin] {
				w.Header().Set("Access-Control-Allow-Origin", origin)
				w.Header().Set("Access-Control-Allow-Credentials", "true")
				w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
				w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Trace-ID")
				w.Header().Set("Access-Control-Max-Age", "86400")
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
