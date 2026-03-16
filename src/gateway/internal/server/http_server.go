package server

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/alert"
	alertredis "github.com/flamegreat/etradie/src/alert/redis"
	"github.com/flamegreat/etradie/src/gateway/internal/config"
	"github.com/flamegreat/etradie/src/gateway/internal/infra"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
)

// HTTPServer serves health, readiness, metrics, WebSocket notifications,
// and event history endpoints.
type HTTPServer struct {
	server *http.Server
	redis  *infra.RedisClient
	engine *infra.EngineHTTPClient
	log    zerolog.Logger
}

// NewHTTPServer creates the HTTP server with all endpoints mounted.
func NewHTTPServer(
	cfg *config.Config,
	redis *infra.RedisClient,
	engine *infra.EngineHTTPClient,
	hub *alert.Hub,
	transport *alertredis.Transport,
) *HTTPServer {
	s := &HTTPServer{
		redis:  redis,
		engine: engine,
		log:    observability.Logger("http_server"),
	}

	mux := http.NewServeMux()

	// Ops endpoints.
	mux.HandleFunc("/health", s.handleHealth)
	mux.HandleFunc("/readiness", s.handleReadiness)
	mux.Handle("/metrics", promhttp.Handler())

	// WebSocket notifications (real-time event stream to dashboard).
	mux.HandleFunc("/ws/notifications", alert.WebSocketHandler(hub))

	// Event history REST endpoints (Redis-backed persistence).
	mux.HandleFunc("/events/recent", alert.RecentEventsHandler(transport))
	mux.HandleFunc("/events/since", alert.EventsSinceHandler(transport))

	s.server = &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.HTTPPort),
		Handler:      mux,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
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
