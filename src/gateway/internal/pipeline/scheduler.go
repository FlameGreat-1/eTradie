package pipeline

import (
	"context"
	"crypto/rand"
	"encoding/binary"
	"sync/atomic"
	"time"

	"github.com/rs/zerolog"

	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/settingsstore"
	"github.com/flamegreat-1/etradie/src/gateway/internal/symbolstore"
)

// Scheduler manages the recurring gateway analysis cycles for ALL active users.
// Each user gets their own cycle with their own identity, symbols, and broker
// connection. The scheduler operates autonomously 24/7 regardless of whether
// any user is logged into the dashboard.
type Scheduler struct {
	orchestrator    *Orchestrator
	symbolStore     *symbolstore.Store
	settingsStore   *settingsstore.Store
	cfg             *config.Config
	transport       *alertredis.Transport
	tokenService    *auth.TokenService
	userStore       *auth.UserStore
	intervalSeconds atomic.Int64
	updateCh        chan time.Duration
	log             zerolog.Logger
}

// NewScheduler creates a gateway cycle scheduler.
// tokenService and userStore enable autonomous operation: the scheduler
// issues service tokens for each active user so downstream services
// (Python engine, Module B, Module C) can identify the correct broker
// connection and user context without requiring a dashboard login.
func NewScheduler(
	orchestrator *Orchestrator,
	symbolStore *symbolstore.Store,
	settingsStore *settingsstore.Store,
	cfg *config.Config,
	transport *alertredis.Transport,
	tokenService *auth.TokenService,
	userStore *auth.UserStore,
) *Scheduler {
	s := &Scheduler{
		orchestrator:  orchestrator,
		symbolStore:   symbolStore,
		settingsStore: settingsStore,
		cfg:           cfg,
		transport:     transport,
		tokenService:  tokenService,
		userStore:     userStore,
		updateCh:      make(chan time.Duration, 1),
		log:           observability.Logger("scheduler"),
	}

	// Set the initial interval from config.
	s.intervalSeconds.Store(int64(cfg.CycleIntervalSeconds))

	return s
}

// LoadPersistedInterval checks Redis for a dashboard-set interval override
// and applies it. Requires a userID since settings are user-scoped.
func (s *Scheduler) LoadPersistedInterval(ctx context.Context, userID string) {
	if s.settingsStore == nil || userID == "" {
		return
	}
	persisted := s.settingsStore.GetCycleInterval(ctx, userID)
	if persisted >= 60 && persisted <= 86400 {
		s.intervalSeconds.Store(int64(persisted))
		s.log.Info().
			Int("persisted_interval_seconds", persisted).
			Str("user_id", userID).
			Msg("scheduler_loaded_persisted_interval_from_redis")
	}
}

// CurrentIntervalSeconds returns the current cycle interval.
func (s *Scheduler) CurrentIntervalSeconds() int {
	return int(s.intervalSeconds.Load())
}

// UpdateInterval changes the cycle interval at runtime.
// The new interval takes effect immediately (ticker is reset).
// The caller is responsible for persisting the value in SettingsStore.
func (s *Scheduler) UpdateInterval(newInterval time.Duration) {
	newSeconds := int64(newInterval.Seconds())
	s.intervalSeconds.Store(newSeconds)

	// Non-blocking send: if the channel is full, the scheduler loop
	// will pick up the atomic value on the next tick anyway.
	select {
	case s.updateCh <- newInterval:
	default:
	}

	s.log.Info().
		Int64("new_interval_seconds", newSeconds).
		Msg("scheduler_interval_updated")
}

// issueUserServiceContext creates a context with a valid service token
// for the given user. The service token carries the user's identity so
// downstream services resolve the correct broker connection and account.
// Returns nil context if token issuance fails (caller should skip this user).
func (s *Scheduler) issueUserServiceContext(ctx context.Context, user *auth.User) context.Context {
	if s.tokenService == nil {
		s.log.Warn().
			Str("user_id", user.ID).
			Msg("scheduler_no_token_service_skipping_user")
		return nil
	}

	serviceToken, err := s.tokenService.IssueServiceToken(user.ID, user.Username, user.Role)
	if err != nil {
		s.log.Error().
			Err(err).
			Str("user_id", user.ID).
			Str("username", user.Username).
			Msg("scheduler_service_token_issuance_failed_for_user")
		return nil
	}

	return auth.InjectTokenIntoContext(ctx, serviceToken)
}

// Start begins the recurring cycle. Blocks until ctx is cancelled.
// Applies random jitter (0-10% of interval) to the first tick to
// prevent thundering herd when multiple gateway instances start.
// The first cycle fires immediately after the jitter delay, then
// subsequent cycles fire on the configured interval.
func (s *Scheduler) Start(ctx context.Context) {
	if !s.cfg.Enabled {
		s.log.Info().Msg("gateway_disabled_skipping_scheduler")
		return
	}

	interval := time.Duration(s.intervalSeconds.Load()) * time.Second

	// Apply jitter to the first tick: random delay of 0-10% of the interval.
	maxJitter := interval / 10
	if maxJitter > 0 {
		jitter := cryptoRandDuration(maxJitter)
		s.log.Info().
			Int64("interval_seconds", s.intervalSeconds.Load()).
			Int("timeout_seconds", s.cfg.CycleTimeoutSeconds).
			Float64("initial_jitter_seconds", jitter.Seconds()).
			Msg("gateway_cycle_scheduler_started")

		select {
		case <-ctx.Done():
			s.log.Info().Msg("gateway_cycle_scheduler_stopped_during_jitter")
			return
		case <-time.After(jitter):
			// Jitter elapsed, proceed to first cycle.
		}
	} else {
		s.log.Info().
			Int64("interval_seconds", s.intervalSeconds.Load()).
			Int("timeout_seconds", s.cfg.CycleTimeoutSeconds).
			Msg("gateway_cycle_scheduler_started")
	}

	// Fire the first cycle immediately after jitter.
	s.runAllUserCycles(ctx)

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			s.log.Info().Msg("gateway_cycle_scheduler_stopped")
			return

		case newInterval := <-s.updateCh:
			// Dashboard changed the interval. Reset the ticker immediately.
			ticker.Reset(newInterval)
			s.log.Info().
				Float64("new_interval_seconds", newInterval.Seconds()).
				Msg("scheduler_ticker_reset")

		case <-ticker.C:
			s.runAllUserCycles(ctx)
		}
	}
}

// runAllUserCycles iterates over all active users and runs an analysis
// cycle for each one with their own identity, symbols, and broker context.
// This is the core of autonomous 24/7 multi-tenant operation.
func (s *Scheduler) runAllUserCycles(ctx context.Context) {
	defer func() {
		if r := recover(); r != nil {
			observability.LogPanicRecovery(s.log, r, "scheduled_all_user_cycles")
		}
	}()

	if s.userStore == nil {
		// No user store available; fall back to unauthenticated cycle
		// with default symbols (backward compatibility).
		s.log.Warn().Msg("scheduler_no_user_store_running_unauthenticated_cycle")
		symbols := s.symbolStore.DefaultSymbols()
		s.orchestrator.RunCycle(ctx, symbols, "")
		return
	}

	// List all active users from the database.
	users, err := s.userStore.ListUsers(ctx)
	if err != nil {
		s.log.Error().Err(err).Msg("scheduler_failed_to_list_users")
		return
	}

	// Filter to active users only.
	var activeUsers []*auth.User
	for _, u := range users {
		if u.Active {
			activeUsers = append(activeUsers, u)
		}
	}

	if len(activeUsers) == 0 {
		s.log.Warn().Msg("scheduler_no_active_users_found_skipping_cycle")
		return
	}

	s.log.Info().
		Int("active_users", len(activeUsers)).
		Msg("scheduler_starting_cycles_for_all_users")

	// Run a cycle for each active user sequentially.
	// Sequential execution prevents resource contention when multiple
	// users' cycles hit the Python engine and broker APIs simultaneously.
	for _, user := range activeUsers {
		if ctx.Err() != nil {
			s.log.Info().Msg("scheduler_context_cancelled_stopping_user_cycles")
			return
		}

		s.runUserCycle(ctx, user)
	}

	s.log.Info().
		Int("users_processed", len(activeUsers)).
		Msg("scheduler_completed_all_user_cycles")
}

// runUserCycle runs a single analysis cycle for one user with their
// own identity, symbols, and broker connection context.
func (s *Scheduler) runUserCycle(ctx context.Context, user *auth.User) {
	defer func() {
		if r := recover(); r != nil {
			observability.LogPanicRecovery(s.log, r, "scheduled_user_cycle_"+user.ID)
		}
	}()

	userLog := s.log.With().
		Str("user_id", user.ID).
		Str("username", user.Username).
		Str("role", string(user.Role)).
		Logger()

	// Issue a service token for this user so downstream services
	// (Python engine, Module B, Module C) resolve their broker connection.
	userCtx := s.issueUserServiceContext(ctx, user)
	if userCtx == nil {
		userLog.Error().Msg("scheduler_skipping_user_no_service_context")
		return
	}

	// Load this user's symbol selection from Redis.
	// Falls back to config defaults if the user hasn't customized.
	symbols := s.symbolStore.GetActiveSymbols(userCtx, user.ID)

	userLog.Info().
		Strs("symbols", symbols).
		Msg("scheduler_starting_user_cycle")

	s.orchestrator.RunCycle(userCtx, symbols, "")

	userLog.Info().
		Strs("symbols", symbols).
		Msg("scheduler_completed_user_cycle")
}

// cryptoRandDuration returns a cryptographically random duration in [0, max).
// Uses crypto/rand for non-deterministic jitter in multi-instance deployments.
func cryptoRandDuration(max time.Duration) time.Duration {
	if max <= 0 {
		return 0
	}

	var buf [8]byte
	if _, err := rand.Read(buf[:]); err != nil {
		// crypto/rand.Read should never fail on supported platforms.
		// If it does, fall back to zero jitter (safe behavior).
		return 0
	}

	n := binary.LittleEndian.Uint64(buf[:])
	return time.Duration(n % uint64(max))
}
