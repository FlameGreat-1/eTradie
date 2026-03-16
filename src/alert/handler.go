package alert

import (
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/gorilla/websocket"
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
func WebSocketHandler(hub *Hub) http.HandlerFunc {
	log := newLogger("ws_handler")

	return func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Error().Err(err).Str("remote", r.RemoteAddr).Msg("ws_upgrade_failed")
			return
		}

		sub := hub.Subscribe()

		log.Info().
			Str("remote", r.RemoteAddr).
			Str("subscriber_id", sub.id).
			Msg("ws_client_connected")

		// Read pump: handles client close frames and pong responses.
		go readPump(conn, hub, sub, log)

		// Write pump: streams events from subscriber channel to WebSocket.
		go writePump(conn, sub, log)
	}
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
