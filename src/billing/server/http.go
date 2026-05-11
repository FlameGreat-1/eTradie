// Package server hosts the billing HTTP surface:
//   - public webhook endpoints for Paddle and Lemon Squeezy
//   - an internal checkout endpoint authenticated by a shared secret
//   - operational endpoints (health, readiness, metrics)
//
// Webhook handlers read the raw body once into memory under
// http.MaxBytesReader and pass the captured bytes unchanged to the verifier.
// Nothing in this package decodes JSON before the signature check completes.
//
// Listener creation is decoupled from serving: callers bind a net.Listener
// (failing fast on EADDRINUSE) and pass it to Start. main.go does this
// before kicking off background goroutines so a bind failure cannot leave
// the reconciler or any other worker running against a dead HTTP path.
package server

import (
	"context"
	"crypto/subtle"
	"encoding/json"
	"errors"
	"io"
	"net"
	"net/http"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"

	bevents "github.com/flamegreat-1/etradie/src/billing/events"
	"github.com/flamegreat-1/etradie/src/billing/lemonsqueezy"
	"github.com/flamegreat-1/etradie/src/billing/paddle"
	"github.com/flamegreat-1/etradie/src/billing/service"
)

// InternalAuthHeader is the request header that carries the gateway-side
// shared secret on /internal/checkout. The handler compares it to the
// configured value with constant-time compare.
const InternalAuthHeader = "X-Internal-Auth"

// Server wires the HTTP surface against the service layer.
type Server struct {
	http           *http.Server
	db             *pgxpool.Pool
	log            zerolog.Logger
	metrics        *Metrics
	internalSecret []byte

	paddleVerifier *paddle.Verifier
	paddlePrices   paddle.PriceTierMap

	lsVerifier *lemonsqueezy.Verifier
	lsVariants lemonsqueezy.VariantTierMap

	subSvc      *service.Service
	checkoutSvc *service.CheckoutService
}

// Options bundles the dependencies New requires. The listener is supplied
// to Start, not here, so port-bind failures are surfaced to the caller
// before any goroutines start.
type Options struct {
	DB             *pgxpool.Pool
	Log            zerolog.Logger
	Metrics        *Metrics
	InternalSecret string

	PaddleVerifier *paddle.Verifier
	PaddlePrices   paddle.PriceTierMap

	LSVerifier *lemonsqueezy.Verifier
	LSVariants lemonsqueezy.VariantTierMap

	SubscriptionService *service.Service
	CheckoutService     *service.CheckoutService
}

// New builds a Server. The HTTP server is not started yet; call Start with
// a pre-bound listener.
func New(opts Options) *Server {
	s := &Server{
		db:             opts.DB,
		log:            opts.Log,
		metrics:        opts.Metrics,
		internalSecret: []byte(opts.InternalSecret),
		paddleVerifier: opts.PaddleVerifier,
		paddlePrices:   opts.PaddlePrices,
		lsVerifier:     opts.LSVerifier,
		lsVariants:     opts.LSVariants,
		subSvc:         opts.SubscriptionService,
		checkoutSvc:    opts.CheckoutService,
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", s.handleHealth)
	mux.HandleFunc("/readiness", s.handleReadiness)
	mux.Handle("/metrics", promhttp.HandlerFor(opts.Metrics.Registry, promhttp.HandlerOpts{}))
	mux.HandleFunc("/webhooks/paddle", s.handlePaddleWebhook)
	mux.HandleFunc("/webhooks/lemonsqueezy", s.handleLSWebhook)
	mux.HandleFunc("/internal/checkout", s.handleInternalCheckout)
	mux.HandleFunc("/internal/portal", s.handleInternalPortal)

	s.http = &http.Server{
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      30 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
	return s
}

// Start serves HTTP on the supplied listener. Blocks until the listener
// stops accepting connections (via Shutdown or an unrecoverable Serve error).
func (s *Server) Start(lis net.Listener) error {
	s.log.Info().Str("addr", lis.Addr().String()).Msg("billing_http_starting")
	if err := s.http.Serve(lis); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}

// Shutdown gracefully drains the HTTP server.
func (s *Server) Shutdown(ctx context.Context) error { return s.http.Shutdown(ctx) }

// ---------------------------------------------------------------------------
// Operational endpoints
// ---------------------------------------------------------------------------

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleReadiness(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := s.db.Ping(ctx); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]any{"status": "not_ready", "db": false})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"status": "ready", "db": true})
}

// ---------------------------------------------------------------------------
// Webhook endpoints
// ---------------------------------------------------------------------------

func (s *Server) handlePaddleWebhook(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	defer func() {
		s.metrics.WebhookDuration.WithLabelValues(paddle.Provider).Observe(time.Since(start).Seconds())
	}()

	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}

	body, err := readBody(r, s.paddleVerifier.MaxBodyBytes())
	if err != nil {
		s.metrics.WebhookReceived.WithLabelValues(paddle.Provider, "unknown", "body_error").Inc()
		writeJSON(w, http.StatusRequestEntityTooLarge, map[string]string{"error": "body too large"})
		return
	}

	if err := s.paddleVerifier.Verify(r, body); err != nil {
		s.metrics.WebhookReceived.WithLabelValues(paddle.Provider, "unknown", "signature").Inc()
		s.log.Warn().Err(err).Msg("paddle_webhook_signature_failed")
		// 401 makes the provider stop retrying — a signature failure is
		// permanent. Body is empty to avoid leaking comparison details.
		w.WriteHeader(http.StatusUnauthorized)
		return
	}

	ev, err := paddle.Parse(r, body, s.paddlePrices)
	if err != nil {
		eventLabel := r.Header.Get("Paddle-Notification-Type")
		if eventLabel == "" {
			eventLabel = "unknown"
		}
		s.metrics.WebhookReceived.WithLabelValues(paddle.Provider, eventLabel, "parse_error").Inc()
		// Log the full reason internally; return a sanitised message to the
		// provider so the notification dashboard never exposes the Go error
		// chain or wrapped values.
		s.log.Warn().
			Err(err).
			Str("provider", paddle.Provider).
			Str("event", eventLabel).
			Msg("paddle_webhook_parse_failed")
		// 422 is permanent caller error; provider stops retrying.
		writeJSON(w, http.StatusUnprocessableEntity, map[string]string{"error": "webhook payload could not be parsed"})
		return
	}

	s.applyAndRespond(w, r, ev)
}

func (s *Server) handleLSWebhook(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	defer func() {
		s.metrics.WebhookDuration.WithLabelValues(lemonsqueezy.Provider).Observe(time.Since(start).Seconds())
	}()

	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}

	body, err := readBody(r, s.lsVerifier.MaxBodyBytes())
	if err != nil {
		s.metrics.WebhookReceived.WithLabelValues(lemonsqueezy.Provider, "unknown", "body_error").Inc()
		writeJSON(w, http.StatusRequestEntityTooLarge, map[string]string{"error": "body too large"})
		return
	}

	if err := s.lsVerifier.Verify(r, body); err != nil {
		s.metrics.WebhookReceived.WithLabelValues(lemonsqueezy.Provider, "unknown", "signature").Inc()
		s.log.Warn().Err(err).Msg("lemonsqueezy_webhook_signature_failed")
		w.WriteHeader(http.StatusUnauthorized)
		return
	}

	ev, err := lemonsqueezy.Parse(r, body, s.lsVariants)
	if err != nil {
		eventLabel := r.Header.Get(lemonsqueezy.EventNameHeader)
		if eventLabel == "" {
			eventLabel = "unknown"
		}
		s.metrics.WebhookReceived.WithLabelValues(lemonsqueezy.Provider, eventLabel, "parse_error").Inc()
		s.log.Warn().
			Err(err).
			Str("provider", lemonsqueezy.Provider).
			Str("event", eventLabel).
			Msg("lemonsqueezy_webhook_parse_failed")
		writeJSON(w, http.StatusUnprocessableEntity, map[string]string{"error": "webhook payload could not be parsed"})
		return
	}

	s.applyAndRespond(w, r, ev)
}

// applyAndRespond dispatches to the service and translates Outcome to HTTP.
//
// Every non-error outcome (applied, duplicate, out_of_order) is logged at
// Info level with provider, event_id, event_name, and the resolved user_id.
// Operators correlating provider retry storms previously had only Prometheus
// counters to work with; the per-event log line closes that gap.
func (s *Server) applyAndRespond(w http.ResponseWriter, r *http.Request, ev *bevents.NormalizedEvent) {
	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	outcome, err := s.subSvc.HandleEvent(ctx, ev)
	if err != nil {
		if errors.Is(err, service.ErrCannotResolveUser) {
			s.metrics.WebhookReceived.WithLabelValues(ev.Provider, ev.EventName, "unresolvable").Inc()
			s.metrics.ApplyOutcome.WithLabelValues(ev.Provider, "unresolvable").Inc()
			s.log.Warn().
				Str("provider", ev.Provider).
				Str("event", ev.EventName).
				Str("event_id", ev.EventID).
				Msg("billing_webhook_unresolvable_user")
			writeJSON(w, http.StatusUnprocessableEntity, map[string]string{"error": "event refers to an unknown user"})
			return
		}
		s.metrics.WebhookReceived.WithLabelValues(ev.Provider, ev.EventName, "error").Inc()
		s.metrics.ApplyOutcome.WithLabelValues(ev.Provider, "error").Inc()
		s.log.Error().Err(err).
			Str("provider", ev.Provider).
			Str("event", ev.EventName).
			Str("event_id", ev.EventID).
			Msg("billing_apply_failed")
		// 5xx so the provider retries. Body deliberately generic.
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}

	switch {
	case outcome.AlreadyProcessed:
		s.metrics.WebhookReceived.WithLabelValues(ev.Provider, ev.EventName, "duplicate").Inc()
		s.metrics.ApplyOutcome.WithLabelValues(ev.Provider, "duplicate").Inc()
		s.log.Info().
			Str("provider", ev.Provider).
			Str("event", ev.EventName).
			Str("event_id", ev.EventID).
			Str("user_id", outcome.UserID).
			Msg("billing_webhook_duplicate")
	case outcome.OutOfOrder:
		s.metrics.WebhookReceived.WithLabelValues(ev.Provider, ev.EventName, "out_of_order").Inc()
		s.metrics.ApplyOutcome.WithLabelValues(ev.Provider, "out_of_order").Inc()
		s.log.Info().
			Str("provider", ev.Provider).
			Str("event", ev.EventName).
			Str("event_id", ev.EventID).
			Str("user_id", outcome.UserID).
			Msg("billing_webhook_out_of_order")
	default:
		s.metrics.WebhookReceived.WithLabelValues(ev.Provider, ev.EventName, "applied").Inc()
		s.metrics.ApplyOutcome.WithLabelValues(ev.Provider, "applied").Inc()
		s.log.Info().
			Str("provider", ev.Provider).
			Str("event", ev.EventName).
			Str("event_id", ev.EventID).
			Str("user_id", outcome.UserID).
			Bool("tier_changed", outcome.TierChanged).
			Bool("status_changed", outcome.StatusChanged).
			Msg("billing_webhook_applied")
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"status":            "ok",
		"already_processed": outcome.AlreadyProcessed,
		"out_of_order":      outcome.OutOfOrder,
		"applied":           outcome.Applied,
		"tier_changed":      outcome.TierChanged,
		"status_changed":    outcome.StatusChanged,
	})
}

// ---------------------------------------------------------------------------
// Internal checkout endpoint
// ---------------------------------------------------------------------------

func (s *Server) handleInternalCheckout(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}
	provided := []byte(r.Header.Get(InternalAuthHeader))
	if len(provided) == 0 || subtle.ConstantTimeCompare(provided, s.internalSecret) != 1 {
		w.WriteHeader(http.StatusUnauthorized)
		return
	}

	var req service.CheckoutRequest
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, 16*1024))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid json: " + err.Error()})
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 15*time.Second)
	defer cancel()

	resp, err := s.checkoutSvc.CreateCheckout(ctx, req)
	if err != nil {
		switch {
		case errors.Is(err, service.ErrInvalidProvider),
			errors.Is(err, service.ErrInvalidTier),
			errors.Is(err, service.ErrUnconfiguredProduct):
			s.metrics.CheckoutCreated.WithLabelValues(req.Provider, string(req.Tier), "invalid").Inc()
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		case errors.Is(err, service.ErrProviderAPI):
			s.metrics.CheckoutCreated.WithLabelValues(req.Provider, string(req.Tier), "provider_error").Inc()
			s.log.Error().Err(err).Msg("billing_checkout_provider_failed")
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": "provider error"})
			return
		}
		s.metrics.CheckoutCreated.WithLabelValues(req.Provider, string(req.Tier), "error").Inc()
		s.log.Error().Err(err).Msg("billing_checkout_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}
	s.metrics.CheckoutCreated.WithLabelValues(req.Provider, string(req.Tier), "ok").Inc()
	writeJSON(w, http.StatusOK, resp)
}

// ---------------------------------------------------------------------------
// Internal portal endpoint
//
// The gateway calls this after looking up the authenticated user's
// (provider, provider_customer_id) from billing_subscriptions. The
// shared-secret check below mirrors handleInternalCheckout so the
// security posture is consistent across every /internal/* route.
// ---------------------------------------------------------------------------

func (s *Server) handleInternalPortal(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}
	provided := []byte(r.Header.Get(InternalAuthHeader))
	if len(provided) == 0 || subtle.ConstantTimeCompare(provided, s.internalSecret) != 1 {
		w.WriteHeader(http.StatusUnauthorized)
		return
	}

	var req service.PortalRequest
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, 16*1024))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid json: " + err.Error()})
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 15*time.Second)
	defer cancel()

	resp, err := s.checkoutSvc.CreatePortalSession(ctx, req)
	if err != nil {
		switch {
		case errors.Is(err, service.ErrInvalidProvider):
			s.log.Warn().Err(err).Str("provider", req.Provider).Msg("billing_portal_invalid_provider")
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		case errors.Is(err, service.ErrPortalNotSupported):
			s.log.Info().Err(err).Str("provider", req.Provider).Str("user_id", req.UserID).Msg("billing_portal_not_supported")
			writeJSON(w, http.StatusNotImplemented, map[string]string{"error": err.Error()})
			return
		case errors.Is(err, service.ErrProviderAPI):
			s.log.Error().Err(err).Str("provider", req.Provider).Msg("billing_portal_provider_failed")
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": "provider error"})
			return
		}
		s.log.Error().Err(err).Str("provider", req.Provider).Msg("billing_portal_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}
	writeJSON(w, http.StatusOK, resp)
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

// readBody captures the raw body under a hard byte limit. The verifier MUST
// be given the bytes that arrived on the wire — not a re-encoded JSON value.
func readBody(r *http.Request, max int64) ([]byte, error) {
	defer r.Body.Close()
	return io.ReadAll(http.MaxBytesReader(nil, r.Body, max))
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
