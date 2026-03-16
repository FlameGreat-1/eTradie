package alert

import (
	"crypto/rand"
	"encoding/hex"
	"os"
	"strings"
	"sync"
	"sync/atomic"

	"github.com/rs/zerolog"
)

const subscriberBufferSize = 128

// Subscriber receives events from the hub.
type Subscriber struct {
	C      chan *Event
	id     string
	closed atomic.Bool
}

// Hub is the central pub/sub dispatcher for all application notifications.
// Any module publishes events here; all connected dashboard clients
// receive them via WebSocket. Thread-safe.
type Hub struct {
	mu          sync.RWMutex
	subscribers map[*Subscriber]struct{}
	log         zerolog.Logger
}

// NewHub creates a notification hub.
func NewHub() *Hub {
	// Override the event ID generator with proper crypto/rand.
	cryptoRandRead = func(b []byte) (int, error) {
		return rand.Read(b)
	}
	hexEncode = func(b []byte) string {
		return hex.EncodeToString(b)
	}

	return &Hub{
		subscribers: make(map[*Subscriber]struct{}),
		log:         newLogger("alert_hub"),
	}
}

// Subscribe registers a new client. Returns a Subscriber whose C channel
// receives events. Caller must call Unsubscribe when done.
func (h *Hub) Subscribe() *Subscriber {
	sub := &Subscriber{
		C:  make(chan *Event, subscriberBufferSize),
		id: generateSubscriberID(),
	}

	h.mu.Lock()
	h.subscribers[sub] = struct{}{}
	count := len(h.subscribers)
	h.mu.Unlock()

	h.log.Info().
		Str("subscriber_id", sub.id).
		Int("total_subscribers", count).
		Msg("subscriber_added")

	return sub
}

// Unsubscribe removes a client and closes its channel.
func (h *Hub) Unsubscribe(sub *Subscriber) {
	if sub.closed.Swap(true) {
		return // Already closed.
	}

	h.mu.Lock()
	delete(h.subscribers, sub)
	count := len(h.subscribers)
	h.mu.Unlock()

	close(sub.C)

	h.log.Info().
		Str("subscriber_id", sub.id).
		Int("total_subscribers", count).
		Msg("subscriber_removed")
}

// Publish sends an event to all connected subscribers. Non-blocking:
// if a subscriber's buffer is full, the event is dropped for that
// subscriber (logged as warning). Publishing must never block the
// caller (execution pipeline, gateway, etc.).
func (h *Hub) Publish(evt *Event) {
	h.mu.RLock()
	defer h.mu.RUnlock()

	for sub := range h.subscribers {
		if sub.closed.Load() {
			continue
		}
		select {
		case sub.C <- evt:
		default:
			h.log.Warn().
				Str("subscriber_id", sub.id).
				Str("event_type", evt.Type).
				Str("event_id", evt.ID).
				Msg("event_dropped_subscriber_buffer_full")
		}
	}
}

// SubscriberCount returns the current number of connected subscribers.
func (h *Hub) SubscriberCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.subscribers)
}

// Close shuts down the hub and drains all subscribers.
func (h *Hub) Close() {
	h.mu.Lock()
	for sub := range h.subscribers {
		if !sub.closed.Swap(true) {
			close(sub.C)
		}
		delete(h.subscribers, sub)
	}
	h.mu.Unlock()

	h.log.Info().Msg("alert_hub_closed")
}

func generateSubscriberID() string {
	b := make([]byte, 6)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

// newLogger creates a zerolog logger for the alert package.
// Standalone to avoid importing execution's observability package.
func newLogger(component string) zerolog.Logger {
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnixMs
	return zerolog.New(os.Stdout).With().
		Timestamp().
		Str("service", "alert").
		Str("component", component).
		Logger()
}

// SetLogLevel configures the alert package log level.
func SetLogLevel(level string) {
	switch strings.ToUpper(level) {
	case "DEBUG":
		zerolog.SetGlobalLevel(zerolog.DebugLevel)
	case "WARN":
		zerolog.SetGlobalLevel(zerolog.WarnLevel)
	case "ERROR":
		zerolog.SetGlobalLevel(zerolog.ErrorLevel)
	default:
		zerolog.SetGlobalLevel(zerolog.InfoLevel)
	}
}
