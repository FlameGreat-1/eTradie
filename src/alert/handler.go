package alert

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gorilla/websocket"
	"github.com/rs/zerolog"
)

const (
	writeWait      = 10 * time.Second
	pongWait       = 35 * time.Second
	pingPeriod     = 30 * time.Second
	maxMessageSize = 512
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 4096,
	CheckOrigin: func(r *http.Request) bool {
		origin := r.Header.Get("Origin")
		if origin == "" {
			return true // Non-browser clients (gRPC tools, curl).
		}
		// Allow localhost for development.
		if strings.Contains(origin, "localhost") || strings.Contains(origin, "127.0.0.1") {
			return true
		}
		// In production, validate that the origin matches the request
		// host. The reverse proxy (nginx/Traefik) should set the Host
		// header to the actual domain. This prevents cross-site WS
		// hijacking while allowing same-origin dashboard connections.
		host := r.Host
		if host != "" && strings.Contains(origin, host) {
			return true
		}
		return false
	},
}

// WebSocketHandler returns an http.HandlerFunc that upgrades HTTP
// connections to WebSocket and streams events from the hub.
// Each connected dashboard client gets its own subscriber.
//
// Supports optional severity filtering via query parameter:
//
//	ws://host/ws/notifications?severity=WARNING
//
// Only events at or above the given severity are delivered.
// Valid values: INFO, WARNING, ERROR, CRITICAL. Default: all events.
func WebSocketHandler(hub *Hub) http.HandlerFunc {
	log := newLogger("ws_handler")

	return func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Error().Err(err).Str("remote", r.RemoteAddr).Msg("ws_upgrade_failed")
			return
		}

		// Parse optional severity filter from query string.
		minSeverity := parseSeverityParam(r.URL.Query().Get("severity"))

		sub := hub.SubscribeWithFilter(minSeverity)

		log.Info().
			Str("remote", r.RemoteAddr).
			Str("subscriber_id", sub.id).
			Str("min_severity", string(minSeverity)).
			Msg("ws_client_connected")

		// Read pump: handles client close frames and pong responses.
		go readPump(conn, hub, sub, log)

		// Write pump: streams events from subscriber channel to WebSocket.
		go writePump(conn, sub, log)
	}
}

// HistoryProvider is the interface for fetching event history.
// Implemented by redis.Transport.
type HistoryProvider interface {
	Recent(ctx context.Context, n int64) []*Event
	RecentFiltered(ctx context.Context, n int64, minSeverity EventSeverity) []*Event
	RecentSince(ctx context.Context, lastEventID string, maxCount int64) []*Event
}

// We need context for the HistoryProvider methods.
import "context"

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

		// Parse count parameter.
		count := int64(50)
		if countStr := r.URL.Query().Get("count"); countStr != "" {
			if parsed, err := strconv.ParseInt(countStr, 10, 64); err == nil && parsed > 0 {
				count = parsed
			}
		}
		if count > 500 {
			count = 500
		}

		// Parse severity filter.
		minSeverity := parseSeverityParam(r.URL.Query().Get("severity"))

		var events []*Event
		if minSeverity != "" {
			events = provider.RecentFiltered(r.Context(), count, minSeverity)
		} else {
			events = provider.Recent(r.Context(), count)
		}

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
				// Channel closed; subscriber was removed.
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
