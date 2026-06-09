package server

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
)

// RedisAttemptLimiter is the production, cluster-wide implementation of
// auth.AttemptLimiter. All state lives in Redis so the rate limit and
// per-account lockout are shared across every gateway replica, closing
// the per-pod-limit bypass of the old in-memory limiter.
//
// Fail posture: on a Redis error every method fails OPEN (allows the
// request / reports not-locked) and logs at WARN. On a money platform a
// transient Redis outage must NOT lock the entire user base out of
// logging in; rate limiting and lockout are defence-in-depth throttles
// layered on top of the real authentication gate (password + session),
// so a brief over-permit during an outage is preferable to a
// platform-wide login failure. The loud log makes the degraded state
// visible to operators.
type RedisAttemptLimiter struct {
	rdb    *redis.Client
	log    zerolog.Logger
	window time.Duration
	limits map[string]int
}

const (
	// authLimitKeyPrefix namespaces every key this limiter writes.
	authLimitKeyPrefix = "etradie:authlimit"
)

// NewRedisAttemptLimiter builds the production limiter from a raw
// go-redis client (gateway RedisClient.RawClient()).
func NewRedisAttemptLimiter(rdb *redis.Client) *RedisAttemptLimiter {
	return &RedisAttemptLimiter{
		rdb:    rdb,
		log:    observability.Logger("auth_attempt_limiter"),
		window: time.Minute,
		limits: map[string]int{
			auth.ScopeLogin:    10,
			auth.ScopeRegister: 5,
			auth.ScopeRefresh:  20,
		},
	}
}

// rateScript atomically increments the window counter, sets the window
// TTL on first hit, and returns the post-increment count. Keeping the
// INCR + PEXPIRE in one script prevents a key that never expires when a
// process dies between the two commands.
var rateScript = redis.NewScript(`
local c = redis.call('INCR', KEYS[1])
if c == 1 then
  redis.call('PEXPIRE', KEYS[1], ARGV[1])
end
return c
`)

// failScript atomically increments the failure counter (refreshing its
// sliding window), and returns the post-increment count so the caller
// can compute the lock duration. The counter window is refreshed on
// every failure so consecutive failures accumulate.
var failScript = redis.NewScript(`
local c = redis.call('INCR', KEYS[1])
redis.call('PEXPIRE', KEYS[1], ARGV[1])
return c
`)

func (l *RedisAttemptLimiter) rateKey(scope, key string) string {
	return fmt.Sprintf("%s:rate:%s:%s", authLimitKeyPrefix, scope, key)
}
func (l *RedisAttemptLimiter) failKey(accountKey string) string {
	return fmt.Sprintf("%s:fail:%s", authLimitKeyPrefix, accountKey)
}
func (l *RedisAttemptLimiter) lockKey(accountKey string) string {
	return fmt.Sprintf("%s:lock:%s", authLimitKeyPrefix, accountKey)
}

// AllowRequest implements the cluster-wide sliding-window rate limit.
func (l *RedisAttemptLimiter) AllowRequest(ctx context.Context, scope, key string) (bool, time.Duration) {
	limit, ok := l.limits[scope]
	if !ok {
		limit = 10
	}
	rk := l.rateKey(scope, key)
	count, err := rateScript.Run(ctx, l.rdb, []string{rk}, l.window.Milliseconds()).Int()
	if err != nil {
		// Fail OPEN (see type doc): allow, but log loudly.
		l.log.Warn().Err(err).Str("scope", scope).Msg("auth_rate_limit_redis_error_failing_open")
		return true, 0
	}
	if count > limit {
		// Over the limit: report the worst-case remaining window so the
		// client backs off for the full window. Emit the gateway
		// rate-limit counter under route="auth" so the
		// AuthCredentialStuffingSuspected PrometheusRule
		// (etradie_gateway_rate_limited_total{route="auth"}) has a
		// series to fire on. tier="-" because the auth limiter runs
		// pre-authentication and has no subscription tier in scope.
		observability.GatewayRateLimitedTotal.WithLabelValues("auth", "-").Inc()
		return false, l.window
	}
	return true, 0
}

// IsLocked reports whether the account is currently locked.
func (l *RedisAttemptLimiter) IsLocked(ctx context.Context, accountKey string) (bool, time.Duration) {
	ttl, err := l.rdb.PTTL(ctx, l.lockKey(accountKey)).Result()
	if err != nil {
		l.log.Warn().Err(err).Msg("auth_lockout_pttl_redis_error_failing_open")
		return false, 0
	}
	// PTTL returns -2 (no key) or -1 (no expiry) as negative durations.
	if ttl > 0 {
		return true, ttl
	}
	return false, 0
}

// RegisterFailure records a failed login and applies the lockout policy.
func (l *RedisAttemptLimiter) RegisterFailure(ctx context.Context, accountKey string) (bool, time.Duration) {
	count, err := failScript.Run(
		ctx, l.rdb, []string{l.failKey(accountKey)},
		auth.LockoutCounterWindowMillis(),
	).Int()
	if err != nil {
		l.log.Warn().Err(err).Msg("auth_register_failure_redis_error_failing_open")
		return false, 0
	}
	lockDur := auth.LockoutDurationForFailures(count)
	if lockDur <= 0 {
		return false, 0
	}
	// Set (or extend) the lock key with the computed backoff TTL.
	if err := l.rdb.Set(ctx, l.lockKey(accountKey), "1", lockDur).Err(); err != nil {
		l.log.Warn().Err(err).Msg("auth_set_lock_redis_error")
		// The counter is set; even if the lock write failed the next
		// failure will retry. Report locked so the current response
		// still backs the caller off.
		return true, lockDur
	}
	return true, lockDur
}

// ResetFailures clears the counter and any active lock on success.
func (l *RedisAttemptLimiter) ResetFailures(ctx context.Context, accountKey string) {
	if err := l.rdb.Del(ctx, l.failKey(accountKey), l.lockKey(accountKey)).Err(); err != nil {
		l.log.Warn().Err(err).Msg("auth_reset_failures_redis_error")
	}
}
