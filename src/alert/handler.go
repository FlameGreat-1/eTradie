package alert

import (
	"context"
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gorilla/websocket"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
)

const (
	writeWait      = 10 * time.Second
	pongWait       = 35 * time.Second
	pingPeriod     = 30 * time.Second
	maxMessageSize = 512
)

// newUpgrader returns a fresh gorilla/websocket Upgrader configured
// for the /ws/notifications endpoint. The upgrader's CheckOrigin
// consults the SAME authoritative allowlist the HTTP corsMiddleware
// uses (passed in by the caller from
// src/gateway/internal/server/http_server.go::buildCORSAllowlist),
// so there is a single source of truth for "which origin may talk
// to this gateway" across both classic HTTP routes and WebSocket
// upgrades.
//
//   • ReadBufferSize / WriteBufferSize tuned for our event payloads.
//   • CheckOrigin policy, in order:
//       1. Empty Origin -> admit. Non-browser clients (curl, grpc
//          tooling, src/gateway/e2etest/, Phase 14.5 hosted-MT
//          verification probes) routinely omit Origin; their auth
//          is enforced by RequireAuth above this layer.
//       2. localhost / 127.0.0.1 substring -> admit. Required for
//          the Vite dev server (env.gatewayWsUrl = ws://localhost:8080
//          in cotradee dev mode).
//       3. Otherwise -> exact-match against allowedOrigins (the map
//          built from helm/gateway/values-<env>.yaml::allowedOrigins).
//          Exact-match is deliberate: substring matching admits any
//          attacker-controlled suffix containing the allowed origin
//          as a prefix, which the previous Host-based code was
//          subtly vulnerable to.
//   • Subprotocols: we MUST advertise "Bearer" so the browser's
//     WebSocket('...', ['Bearer', '<jwt>']) handshake accepts our
//     101 response. Browsers in this deploy use the cookie channel
//     for auth (cookies are attached automatically to the WS
//     handshake by the browser; HttpOnly access_token cannot be
//     read into the subprotocol). Non-browser clients still use
//     the subprotocol channel verbatim. The auth middleware
//     (auth.RequireAuth) verifies whichever channel the client
//     used BEFORE we reach this upgrade call.
func newUpgrader(allowedOrigins map[string]bool) websocket.Upgrader {
	return websocket.Upgrader{
		ReadBufferSize:  1024,
		WriteBufferSize: 4096,
		Subprotocols:    []string{"Bearer"},
		CheckOrigin: func(r *http.Request) bool {
			origin := r.Header.Get("Origin")
			if origin == "" {
				return true
			}
			if strings.Contains(origin, "localhost") || strings.Contains(origin, "127.0.0.1") {
				return true
			}
			return allowedOrigins[origin]
		},
	}
}

// HistoryProvider is the interface for fetching persistent event history.
// Implemented by redis.Transport.
type HistoryProvider interface {
	Recent(ctx context.Context, n int64) []*Event
	RecentFiltered(ctx context.Context, n int64, minSeverity EventSeverity) []*Event
	RecentSince(ctx context.Context, lastEventID string, maxCount int64) []*Event
}

// WebSocketHandler returns an http.HandlerFunc that upgrades HTTP
// connections to WebSocket and streams events from the hub.
// Each connected dashboard client gets its own subscriber.
//
// allowedOrigins is the gateway's authoritative CORS allowlist (built
// by buildCORSAllowlist from helm/gateway/values-<env>.yaml). The WS
// upgrader's CheckOrigin admits exactly those origins (plus empty-
// Origin and localhost; see newUpgrader). This is the same map
// corsMiddleware consumes for HTTP routes - single source of truth.
//
// Supports optional severity filtering via query parameter:
//
//	ws://host/ws/notifications?severity=WARNING
//
// Only events at or above the given severity are delivered.
// Valid values: INFO, WARNING, ERROR, CRITICAL. Default: all events.
func WebSocketHandler(hub *Hub, allowedOrigins map[string]bool) http.HandlerFunc {
	log := newLogger("ws_handler")
	upgrader := newUpgrader(allowedOrigins)

	return func(w http.ResponseWriter, r *http.Request) {
		// Auth has already passed (we sit behind RequireAuth) so the
		// user ID is in the request context.
		userID := auth.UserIDFromContext(r.Context())

		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Error().Err(err).Str("remote", r.RemoteAddr).Msg("ws_upgrade_failed")
			return
		}

		minSeverity := parseSeverityParam(r.URL.Query().Get("severity"))

		sub := hub.SubscribeForUser(userID, minSeverity)

		log.Info().
			Str("remote", r.RemoteAddr).
			Str("subscriber_id", sub.id).
			Str("user_id", userID).
			Str("min_severity", string(minSeverity)).
			Msg("ws_client_connected")

		go readPump(conn, hub, sub, log)
		go writePump(conn, sub, log)
	}
}

// RecentEventsHandler returns an http.HandlerFunc that serves the
// event history REST endpoint.
//
//	GET /events/recent?count=50&severity=WARNING
//
// Returns the last `count` events (default 50, max 500) from Redis
// history, optionally filtered by minimum severity.
func RecentEventsHandler(provider HistoryProvider) http.HandlerFunc {
	log := newLogger("events_handler")

	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
			return
		}

		userID := auth.UserIDFromContext(r.Context())

		count := int64(50)
		if countStr := r.URL.Query().Get("count"); countStr != "" {
			if parsed, err := strconv.ParseInt(countStr, 10, 64); err == nil && parsed > 0 {
				count = parsed
			}
		}
		if count > 500 {
			count = 500
		}

		minSeverity := parseSeverityParam(r.URL.Query().Get("severity"))

		var events []*Event
		if minSeverity != "" {
			events = provider.RecentFiltered(r.Context(), count, minSeverity)
		} else {
			events = provider.Recent(r.Context(), count)
		}

		events = filterEventsByUser(events, userID)

		if events == nil {
			events = []*Event{}
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		if err := json.NewEncoder(w).Encode(map[string]interface{}{
			"events": events,
			"count":  len(events),
		}); err != nil {
			log.Error().Err(err).Msg("events_recent_encode_failed")
		}
	}
}

// EventsSinceHandler returns an http.HandlerFunc for catch-up after
// dashboard reconnection.
//
//	GET /events/since?last_event_id=20240101120000-abcd1234&count=100
//
// Returns events newer than the given event ID, up to `count` (default 100).
func EventsSinceHandler(provider HistoryProvider) http.HandlerFunc {
	log := newLogger("events_handler")

	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
			return
		}

		userID := auth.UserIDFromContext(r.Context())

		lastEventID := r.URL.Query().Get("last_event_id")

		count := int64(100)
		if countStr := r.URL.Query().Get("count"); countStr != "" {
			if parsed, err := strconv.ParseInt(countStr, 10, 64); err == nil && parsed > 0 {
				count = parsed
			}
		}
		if count > 500 {
			count = 500
		}

		events := provider.RecentSince(r.Context(), lastEventID, count)

		events = filterEventsByUser(events, userID)

		if events == nil {
			events = []*Event{}
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		if err := json.NewEncoder(w).Encode(map[string]interface{}{
			"events": events,
			"count":  len(events),
		}); err != nil {
			log.Error().Err(err).Msg("events_since_encode_failed")
		}
	}
}

// filterEventsByUser returns only events visible to the given user:
// system events (empty UserID) and events owned by the user.
// If userID is empty (unauthenticated), only system events are returned.
func filterEventsByUser(events []*Event, userID string) []*Event {
	if events == nil {
		return nil
	}
	filtered := make([]*Event, 0, len(events))
	for _, evt := range events {
		if evt.UserID == "" || evt.UserID == userID {
			filtered = append(filtered, evt)
		}
	}
	return filtered
}

// parseSeverityParam validates and normalizes a severity query parameter.
// Returns empty string if invalid (meaning no filter).
func parseSeverityParam(raw string) EventSeverity {
	if raw == "" {
		return ""
	}
	normalized := EventSeverity(strings.ToUpper(strings.TrimSpace(raw)))
	if _, ok := severityRankMap[normalized]; ok {
		return normalized
	}
	return ""
}

func readPump(conn *websocket.Conn, hub *Hub, sub *Subscriber, log zerolog.Logger) {
	defer func() {
		hub.Unsubscribe(sub)
		conn.Close()
		log.Info().Str("subscriber_id", sub.id).Msg("ws_read_pump_stopped")
	}()

	conn.SetReadLimit(maxMessageSize)
	_ = conn.SetReadDeadline(time.Now().Add(pongWait))
	conn.SetPongHandler(func(string) error {
		_ = conn.SetReadDeadline(time.Now().Add(pongWait))
		return nil
	})

	for {
		_, _, err := conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseNormalClosure) {
				log.Warn().Err(err).Str("subscriber_id", sub.id).Msg("ws_unexpected_close")
			}
			return
		}
	}
}

func writePump(conn *websocket.Conn, sub *Subscriber, log zerolog.Logger) {
	ticker := time.NewTicker(pingPeriod)
	defer func() {
		ticker.Stop()
		conn.Close()
		log.Info().Str("subscriber_id", sub.id).Msg("ws_write_pump_stopped")
	}()

	for {
		select {
		case evt, ok := <-sub.C:
			if !ok {
				_ = conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			_ = conn.SetWriteDeadline(time.Now().Add(writeWait))

			data, err := json.Marshal(evt)
			if err != nil {
				log.Error().Err(err).Str("event_type", evt.Type).Msg("ws_event_marshal_failed")
				continue
			}

			if err := conn.WriteMessage(websocket.TextMessage, data); err != nil {
				log.Warn().Err(err).Str("subscriber_id", sub.id).Msg("ws_write_failed")
				return
			}

		case <-ticker.C:
			_ = conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}
