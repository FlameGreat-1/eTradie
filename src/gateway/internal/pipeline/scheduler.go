package pipeline

import (
	"context"
	"crypto/rand"
	"encoding/binary"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/settingsstore"
	"github.com/flamegreat-1/etradie/src/gateway/internal/symbolstore"
)

// userRunner holds the state for a single user's independent scheduler goroutine.
type userRunner struct {
	userID   string
	username string
	role     auth.Role
	cancel   context.CancelFunc
}

// Scheduler manages the recurring gateway analysis cycles for ALL active users.
// Each user gets their own independent goroutine with their own configured
// interval. Users run concurrently and independently: User A's slow cycle
// does not delay User B. Each user's interval is loaded from their Redis
// settings and can be updated at runtime without affecting other users.
type Scheduler struct {
	orchestrator  *Orchestrator
	symbolStore   *symbolstore.Store
	settingsStore *settingsstore.Store
	cfg           *config.Config
	transport     *alertredis.Transport
	tokenService  *auth.TokenService
	userStore     *auth.UserStore
	log           zerolog.Logger

	// Per-user goroutine management.
	mu      sync.Mutex
	runners map[string]*userRunner // keyed by user ID

	// How often to re-scan the user list for new/removed users.
	userScanInterval time.Duration
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
	return &Scheduler{
		orchestrator:     orchestrator,
		symbolStore:      symbolStore,
		settingsStore:    settingsStore,
		cfg:              cfg,
		transport:        transport,
		tokenService:     tokenService,
		userStore:        userStore,
		runners:          make(map[string]*userRunner),
		userScanInterval: 60 * time.Second,
		log:              observability.Logger("scheduler"),
	}
}

// CurrentIntervalForUser returns the cycle interval for a specific user.
// Reads from the user's persisted Redis settings. Falls back to the
// gateway config default if the user hasn't configured their own.
// Used by dashboard config endpoints to show the user their current interval.
func (s *Scheduler) CurrentIntervalForUser(ctx context.Context, userID string) int {
	if s.settingsStore != nil && userID != "" {
		persisted := s.settingsStore.GetCycleInterval(ctx, userID)
		if persisted >= 60 && persisted <= 86400 {
			return persisted
		}
	}
	return s.cfg.CycleIntervalSeconds
}

// DefaultIntervalSeconds returns the gateway config default interval.
// Used at startup for logging and as the fallback when no user-specific
// interval is configured.
func (s *Scheduler) DefaultIntervalSeconds() int {
	return s.cfg.CycleIntervalSeconds
}

// UpdateUserInterval persists the new interval for a specific user in Redis
// and logs the change. The user's goroutine periodically re-reads its
// interval from Redis, so the update takes effect within 5 minutes.
// For immediate effect, the goroutine also checks on every tick.
func (s *Scheduler) UpdateUserInterval(ctx context.Context, userID string, newInterval time.Duration) {
	newSeconds := int(newInterval.Seconds())

	// Persist to Redis so it survives restarts.
	if s.settingsStore != nil {
		if err := s.settingsStore.SetCycleInterval(ctx, userID, newSeconds); err != nil {
			s.log.Warn().
				Err(err).
				Str("user_id", userID).
				Int("interval_seconds", newSeconds).
				Msg("scheduler_persist_user_interval_failed")
		}
	}

	s.log.Info().
		Str("user_id", userID).
		Int("new_interval_seconds", newSeconds).
		Msg("scheduler_user_interval_updated")
}

// getUserInterval returns the cycle interval for a specific user as a Duration.
// Enforces a hardcoded 24-hour interval for Free tier users regardless of their Redis settings.
func (s *Scheduler) getUserInterval(ctx context.Context, user *auth.User) time.Duration {
	if user != nil && user.Role != "admin" && user.Tier == "free" {
		return 24 * time.Hour
	}
	return time.Duration(s.CurrentIntervalForUser(ctx, user.ID)) * time.Second
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

	serviceToken, err := s.tokenService.IssueServiceToken(user.ID, user.Username, user.Role, user.Tier, user.Status)
	if err != nil {
		s.log.Error().
			Err(err).
			Str("user_id", user.ID).
			Str("username", user.Username).
			Msg("scheduler_service_token_issuance_failed_for_user")
		return nil
	}

	// Inject BOTH the raw token (so downstream HTTP callers can
	// forward it as a Bearer for the engine's user-facing /api/*
	// surface) AND the parsed claims (so UserIDFromContext,
	// RoleFromContext, and ClaimsFromContext work for the gateway's
	// own /internal/* path — these readers look up the claimsKey,
	// NOT the rawTokenKey). Without the claims injection the gateway
	// never sets X-User-Id on /internal/processor/process and the
	// engine never fetches the user Trading System.
	claims := &auth.Claims{
		UserID:   user.ID,
		Username: user.Username,
		Role:     user.Role,
		Tier:     user.Tier,
		Status:   user.Status,
	}
	ctx = auth.InjectTokenIntoContext(ctx, serviceToken)
	ctx = auth.InjectClaimsIntoContext(ctx, claims)
	return ctx
}

// Start begins the scheduler. Blocks until ctx is cancelled.
// Periodically scans the user list and ensures each active user has
// their own independent goroutine running on their own interval.
func (s *Scheduler) Start(ctx context.Context) {
	if !s.cfg.Enabled {
		s.log.Info().Msg("gateway_disabled_skipping_scheduler")
		return
	}

	if s.userStore == nil {
		s.log.Warn().Msg("scheduler_no_user_store_cannot_start_per_user_schedulers")
		return
	}

	s.log.Info().
		Float64("user_scan_interval_seconds", s.userScanInterval.Seconds()).
		Int("default_cycle_interval_seconds", s.cfg.CycleIntervalSeconds).
		Msg("scheduler_started_per_user_mode")

	// Initial scan and launch.
	s.reconcileUserRunners(ctx)

	scanTicker := time.NewTicker(s.userScanInterval)
	defer scanTicker.Stop()

	for {
		select {
		case <-ctx.Done():
			s.stopAllRunners()
			s.log.Info().Msg("scheduler_stopped")
			return
		case <-scanTicker.C:
			s.reconcileUserRunners(ctx)
		}
	}
}

// reconcileUserRunners ensures each active user has a running goroutine
// and stops goroutines for users that are no longer active.
func (s *Scheduler) reconcileUserRunners(ctx context.Context) {
	users, err := s.userStore.ListUsers(ctx)
	if err != nil {
		s.log.Error().Err(err).Msg("scheduler_failed_to_list_users")
		return
	}

	// Build set of active user IDs.
	activeIDs := make(map[string]*auth.User, len(users))
	for _, u := range users {
		if u.Active {
			activeIDs[u.ID] = u
		}
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	// Stop runners for users that are no longer active or have downgraded to Free.
	for uid, runner := range s.runners {
		user, stillActive := activeIDs[uid]
		downgraded := user != nil && user.Role != "admin" && user.Tier == "free"
		shouldStop := !stillActive || downgraded

		if shouldStop {
			s.log.Info().
				Str("user_id", uid).
				Str("username", runner.username).
				Bool("downgraded", downgraded).
				Msg("scheduler_stopping_runner_for_inactive_or_free_user")
			runner.cancel()
			delete(s.runners, uid)

			// Surface a non-silent dashboard message on tier downgrade so the
			// user knows their automated cycles have been disabled. Manual
			// analysis stays available; the message tells them how to use it.
			if downgraded && s.transport != nil {
				s.transport.Publish(ctx,
					alert.NewEvent(alert.SourceGateway, alert.TypeSubscriptionDowngraded, alert.SeverityWarning,
						"Automated analysis cycles have been disabled because your subscription is now on the Free tier. You can still trigger manual analyses from the dashboard.").
						WithUserID(uid).
						WithDetail("username", runner.username),
				)
			}
		}
	}

	// Start runners for new active users.
	for uid, user := range activeIDs {
		if _, exists := s.runners[uid]; !exists {
			// Free tier users do NOT get automated scheduling (except Admins).
			// They must trigger analysis manually from the dashboard.
			if user.Role != "admin" && user.Tier == "free" {
				continue
			}

			userCtx, cancel := context.WithCancel(ctx)
			runner := &userRunner{
				userID:   user.ID,
				username: user.Username,
				role:     user.Role,
				cancel:   cancel,
			}
			s.runners[uid] = runner

			s.log.Info().
				Str("user_id", user.ID).
				Str("username", user.Username).
				Msg("scheduler_starting_runner_for_user")

			go s.runUserLoop(userCtx, user)
		}
	}

	s.log.Debug().
		Int("active_runners", len(s.runners)).
		Int("active_users", len(activeIDs)).
		Msg("scheduler_reconciliation_complete")
}

// runUserLoop is the independent goroutine for a single user.
// It runs on the user's own configured interval, fetches their symbols,
// issues their service token, and executes their analysis cycle.
// Completely independent of all other users' goroutines.
func (s *Scheduler) runUserLoop(ctx context.Context, user *auth.User) {
	userLog := s.log.With().
		Str("user_id", user.ID).
		Str("username", user.Username).
		Logger()

	// Load this user's configured interval.
	interval := s.getUserInterval(ctx, user)

	userLog.Info().
		Float64("interval_seconds", interval.Seconds()).
		Msg("user_scheduler_loop_started")

	// Apply jitter to the first tick: random delay of 0-10% of the interval.
	// Prevents thundering herd when multiple user goroutines start simultaneously.
	maxJitter := interval / 10
	if maxJitter > 0 {
		jitter := cryptoRandDuration(maxJitter)
		select {
		case <-ctx.Done():
			userLog.Info().Msg("user_scheduler_stopped_during_jitter")
			return
		case <-time.After(jitter):
		}
	}

	// Fire the first cycle immediately after jitter.
	s.executeUserCycle(ctx, user, userLog)

	timer := time.NewTimer(interval)
	defer timer.Stop()

	// Re-check interval from Redis periodically to pick up dashboard changes.
	intervalCheckTicker := time.NewTicker(5 * time.Minute)
	defer intervalCheckTicker.Stop()

	for {
		select {
		case <-ctx.Done():
			userLog.Info().Msg("user_scheduler_loop_stopped")
			return

		case <-intervalCheckTicker.C:
			// Re-read the user's interval from Redis in case they changed it.
			newInterval := s.getUserInterval(ctx, user)
			if newInterval != interval {
				userLog.Info().
					Float64("old_interval_seconds", interval.Seconds()).
					Float64("new_interval_seconds", newInterval.Seconds()).
					Msg("user_scheduler_interval_changed")
				interval = newInterval
				// Next cycle will use the new interval when resetting.
			}

		case <-timer.C:
			s.executeUserCycle(ctx, user, userLog)
			timer.Reset(interval)
		}
	}
}

// executeUserCycle runs a single analysis cycle for one user.
func (s *Scheduler) executeUserCycle(ctx context.Context, user *auth.User, userLog zerolog.Logger) {
	defer func() {
		if r := recover(); r != nil {
			observability.LogPanicRecovery(userLog, r, "user_cycle_"+user.ID)
		}
	}()

	// Issue a service token for this user so downstream services
	// (Python engine, Module B, Module C) resolve their broker connection.
	userCtx := s.issueUserServiceContext(ctx, user)
	if userCtx == nil {
		userLog.Error().Msg("scheduler_skipping_cycle_no_service_context")
		return
	}

	// Load this user's symbol selection from Redis.
	symbols := s.symbolStore.GetActiveSymbols(userCtx, user.ID)

	// Enforce 1-symbol limit dynamically for Free tier users regardless of what is in Redis
	// This prevents downgrade bypasses and default config bypasses.
	if user.Role != "admin" && user.Tier == "free" && len(symbols) > 1 {
		s.log.Warn().
			Str("user_id", user.ID).
			Msg("scheduler_truncating_symbols_for_free_tier")
		symbols = symbols[:1]
	}

	userLog.Info().
		Strs("symbols", symbols).
		Msg("user_cycle_started")

	s.orchestrator.RunCycle(userCtx, symbols, "")

	userLog.Info().
		Strs("symbols", symbols).
		Msg("user_cycle_completed")
}

// stopAllRunners cancels all user goroutines.
func (s *Scheduler) stopAllRunners() {
	s.mu.Lock()
	defer s.mu.Unlock()

	for uid, runner := range s.runners {
		s.log.Info().
			Str("user_id", uid).
			Str("username", runner.username).
			Msg("scheduler_stopping_runner")
		runner.cancel()
	}
	s.runners = make(map[string]*userRunner)
}

// ActiveRunnerCount returns the number of currently running user goroutines.
// Used for observability and health checks.
func (s *Scheduler) ActiveRunnerCount() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.runners)
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
