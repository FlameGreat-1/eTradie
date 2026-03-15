package infra

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/gateway/internal/observability"
)

const (
	keyPrefix  = "etradie"
	maxRetries = 3
)

// RedisClient wraps go-redis with namespaced keys, JSON serialization,
// retry logic, and structured logging.
type RedisClient struct {
	client *redis.Client
	log    zerolog.Logger
}

// NewRedisClient creates a Redis client from the given URL.
func NewRedisClient(redisURL string, maxConns int) (*RedisClient, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("redis: parse URL: %w", err)
	}
	opts.PoolSize = maxConns
	opts.ReadTimeout = 5 * time.Second
	opts.WriteTimeout = 5 * time.Second
	opts.DialTimeout = 5 * time.Second

	client := redis.NewClient(opts)
	log := observability.Logger("redis")

	log.Info().
		Int("pool_size", maxConns).
		Msg("redis_client_initialized")

	return &RedisClient{client: client, log: log}, nil
}

func makeKey(namespace, key string) string {
	return fmt.Sprintf("%s:%s:%s", keyPrefix, namespace, key)
}

// Get retrieves a JSON value from Redis. Returns nil, nil on cache miss.
func (r *RedisClient) Get(ctx context.Context, namespace, key string) (interface{}, error) {
	fullKey := makeKey(namespace, key)

	var lastErr error
	for attempt := 0; attempt < maxRetries; attempt++ {
		raw, err := r.client.Get(ctx, fullKey).Bytes()
		if err == redis.Nil {
			return nil, nil
		}
		if err != nil {
			lastErr = err
			r.log.Warn().
				Str("key", fullKey).
				Int("attempt", attempt+1).
				Err(err).
				Msg("redis_get_retry")
			time.Sleep(backoff(attempt))
			continue
		}

		var value interface{}
		if err := json.Unmarshal(raw, &value); err != nil {
			return nil, fmt.Errorf("redis: unmarshal key %s: %w", fullKey, err)
		}
		return value, nil
	}
	return nil, fmt.Errorf("redis: get %s after %d retries: %w", fullKey, maxRetries, lastErr)
}

// Set stores a JSON-serializable value in Redis with the given TTL.
func (r *RedisClient) Set(ctx context.Context, namespace, key string, value interface{}, ttl time.Duration) error {
	fullKey := makeKey(namespace, key)

	raw, err := json.Marshal(value)
	if err != nil {
		return fmt.Errorf("redis: marshal key %s: %w", fullKey, err)
	}

	var lastErr error
	for attempt := 0; attempt < maxRetries; attempt++ {
		err := r.client.Set(ctx, fullKey, raw, ttl).Err()
		if err == nil {
			return nil
		}
		lastErr = err
		r.log.Warn().
			Str("key", fullKey).
			Int("attempt", attempt+1).
			Err(err).
			Msg("redis_set_retry")
		time.Sleep(backoff(attempt))
	}
	return fmt.Errorf("redis: set %s after %d retries: %w", fullKey, maxRetries, lastErr)
}

// Delete removes a key from Redis.
func (r *RedisClient) Delete(ctx context.Context, namespace, key string) error {
	fullKey := makeKey(namespace, key)

	var lastErr error
	for attempt := 0; attempt < maxRetries; attempt++ {
		err := r.client.Del(ctx, fullKey).Err()
		if err == nil {
			return nil
		}
		lastErr = err
		r.log.Warn().
			Str("key", fullKey).
			Int("attempt", attempt+1).
			Err(err).
			Msg("redis_delete_retry")
		time.Sleep(backoff(attempt))
	}
	return fmt.Errorf("redis: delete %s after %d retries: %w", fullKey, maxRetries, lastErr)
}

// HealthCheck pings Redis and returns true if healthy.
func (r *RedisClient) HealthCheck(ctx context.Context) bool {
	err := r.client.Ping(ctx).Err()
	if err != nil {
		r.log.Error().Err(err).Msg("redis_health_check_failed")
		return false
	}
	return true
}

// Close gracefully shuts down the Redis connection.
func (r *RedisClient) Close() error {
	err := r.client.Close()
	if err != nil {
		r.log.Error().Err(err).Msg("redis_close_failed")
		return err
	}
	r.log.Info().Msg("redis_client_closed")
	return nil
}

// backoff returns an exponential backoff duration with a simple jitter.
func backoff(attempt int) time.Duration {
	base := 100 * time.Millisecond
	delay := time.Duration(float64(base) * math.Pow(2, float64(attempt)))
	if delay > 5*time.Second {
		delay = 5 * time.Second
	}
	return delay
}
