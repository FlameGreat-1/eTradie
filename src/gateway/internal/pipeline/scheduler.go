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

// Scheduler manages the recurring gateway analysis cycle.
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
// Called when a user authenticates and their persisted interval should
// override the default. In the current single-scheduler architecture,
// this applies the last-authenticated user's interval.
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

// issueServiceContext creates a context with a valid service token
// for autonomous background operations. The service token carries
// the admin user's identity so downstream services (Python engine,
// Module B, Module C) can identify the broker connection and user.
// Returns the base context if token issuance fails (graceful degradation).
func (s *Scheduler) issueServiceContext(ctx context.Context) context.Context {
	if s.tokenService == nil || s.userStore == nil {
		s.log.Warn().Msg("scheduler_no_token_service_running_without_auth")
		return ctx
	}

	// Look up the admin user to get their ID and username.
	// The admin is seeded at startup, so this should always succeed.
	users, err := s.userStore.ListUsers(ctx)
	if err != nil || len(users) == 0 {
		s.log.Error().Err(err).Msg("scheduler_failed_to_find_admin_user_for_service_token")
		return ctx
	}

	// Find the first active admin user.
	var adminUser *auth.User
	for _, u := range users {
		if u.IsAdmin() && u.Active {
			adminUser = u
			break
		}
	}
	if adminUser == nil {
		s.log.Error().Msg("scheduler_no_active_admin_user_found_for_service_token")
		return ctx
	}

	// Issue a long-lived service token for autonomous operation.
	serviceToken, err := s.tokenService.IssueServiceToken(adminUser.ID, adminUser.Username, adminUser.Role)
	if err != nil {
		s.log.Error().Err(err).Msg("scheduler_service_token_issuance_failed")
		return ctx
	}

	s.log.Info().
		Str("admin_user_id", adminUser.ID).
		Str("admin_username", adminUser.Username).
		Msg("scheduler_service_token_issued_for_autonomous_operation")

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

	// Issue a service token for autonomous 24/7 operation.
	// This ensures all downstream calls (Python engine, Module B, Module C)
	// carry valid authentication even when no user is logged in.
	serviceCtx := s.issueServiceContext(ctx)

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
	s.runCycle(serviceCtx)

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
			s.runCycle(serviceCtx)
		}
	}
}

func (s *Scheduler) runCycle(ctx context.Context) {
	defer func() {
		if r := recover(); r != nil {
			observability.LogPanicRecovery(s.log, r, "scheduled_cycle")
		}
	}()

	// Use the configured default symbols for scheduled cycles.
	// The context carries a service token for downstream auth.
	symbols := s.symbolStore.DefaultSymbols()

	s.log.Info().
		Strs("symbols", symbols).
		Str("source", "default_config").
		Msg("gateway_scheduled_cycle_starting")

	s.orchestrator.RunCycle(ctx, symbols, "")
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
