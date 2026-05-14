package tradingsystem

import (
	"context"
	"encoding/json"

	"github.com/rs/zerolog"
)

// invalidationChannel is the Redis pub/sub channel the engine subscribes
// to. The engine's invalidation listener (Workstream B, Python side)
// listens on this channel and calls UserOSCache.invalidate() when it
// receives a message for a user_id it has cached.
//
// The channel name is intentionally simple and stable. Changing it
// requires a coordinated deploy of both gateway and engine.
const invalidationChannel = "etradie:user_os:invalidate"

// invalidationMessage is the JSON payload published on every profile
// mutation (save, skip, reset). The engine listener uses user_id to
// target the correct cache entry.
type invalidationMessage struct {
	UserID string `json:"user_id"`
	Event  string `json:"event"` // "save" | "skip" | "reset"
}

// RedisPublisher is the minimal interface the invalidation publisher
// needs from the gateway's Redis client. Defined here so the
// tradingsystem package does not import the infra package (which would
// create a circular dependency).
type RedisPublisher interface {
	Publish(ctx context.Context, channel string, payload []byte)
}

// InvalidationPublisher publishes user OS cache invalidation events to
// Redis pub/sub after every profile mutation. The engine's async
// listener receives these events and busts its in-process version
// cache + the Redis negative-cache sentinel for the affected user.
//
// When redis is nil (no Redis configured, e.g. local dev without
// Redis), Publish is a no-op. The engine's cache will still expire
// naturally via TTL.
type InvalidationPublisher struct {
	redis RedisPublisher
	log   zerolog.Logger
}

// NewInvalidationPublisher creates a publisher. Pass nil for redis to
// disable publishing (safe default for environments without Redis).
func NewInvalidationPublisher(redis RedisPublisher, log zerolog.Logger) *InvalidationPublisher {
	return &InvalidationPublisher{redis: redis, log: log}
}

// Publish sends an invalidation event for the given user. Best-effort:
// a Redis error is logged but never returned so the HTTP handler that
// triggered the mutation can still respond 200 to the client.
func (p *InvalidationPublisher) Publish(ctx context.Context, userID, event string) {
	if p.redis == nil || userID == "" {
		return
	}
	msg := invalidationMessage{UserID: userID, Event: event}
	payload, err := json.Marshal(msg)
	if err != nil {
		// json.Marshal on a plain struct with string fields never fails;
		// this branch is purely defensive.
		p.log.Error().
			Str("user_id", userID).
			Str("event", event).
			Err(err).
			Msg("user_os_invalidation_marshal_failed")
		return
	}
	p.redis.Publish(ctx, invalidationChannel, payload)
	p.log.Debug().
		Str("user_id", userID).
		Str("event", event).
		Str("channel", invalidationChannel).
		Msg("user_os_invalidation_published")
}
