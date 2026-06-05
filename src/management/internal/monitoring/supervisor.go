package monitoring

import (
	"context"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
)

// UserLister yields the currently-active users. Implemented by
// auth.UserStore.
type UserLister interface {
	ListActiveUsers(ctx context.Context) ([]*auth.User, error)
}

// ServiceTokenIssuer mints a service token for a user. Implemented by
// auth.TokenService.
type ServiceTokenIssuer interface {
	IssueServiceToken(userID, username string, role auth.Role, tier, status string, tokenEpoch int) (string, error)
}

// reconcilerHandle tracks one running per-user reconciler.
type reconcilerHandle struct {
	cancel context.CancelFunc
	done   chan struct{}
}

// ReconcilerSupervisor keeps exactly one StateReconciler running per
// active user. It reconciles the active-user set against the running
// set on a fixed interval, so users who connect a broker after boot
// get account-level reconciliation without a restart, and users who
// are deactivated have their reconciler stopped.
type ReconcilerSupervisor struct {
	mgr       *Manager
	bp        broker.Port
	repo      *journal.Repository
	transport AlertTransport
	users     UserLister
	tokens    ServiceTokenIssuer

	watchInterval time.Duration
	syncInterval  time.Duration
	log           zerolog.Logger

	mu      sync.Mutex
	running map[string]*reconcilerHandle // keyed by userID
	wg      sync.WaitGroup
}

// NewReconcilerSupervisor builds a supervisor. watchInterval is the
// per-reconciler position-poll cadence; syncInterval is how often the
// supervisor re-evaluates the active-user set (<=0 falls back to 60s).
func NewReconcilerSupervisor(
	mgr *Manager,
	bp broker.Port,
	repo *journal.Repository,
	transport AlertTransport,
	users UserLister,
	tokens ServiceTokenIssuer,
	watchInterval, syncInterval time.Duration,
) *ReconcilerSupervisor {
	if syncInterval <= 0 {
		syncInterval = 60 * time.Second
	}
	return &ReconcilerSupervisor{
		mgr:           mgr,
		bp:            bp,
		repo:          repo,
		transport:     transport,
		users:         users,
		tokens:        tokens,
		watchInterval: watchInterval,
		syncInterval:  syncInterval,
		log:           observability.Logger("reconciler_supervisor"),
		running:       make(map[string]*reconcilerHandle),
	}
}

// Run drives the supervisor until ctx is cancelled. It evaluates the
// active-user set immediately, then every syncInterval.
func (s *ReconcilerSupervisor) Run(ctx context.Context) {
	ticker := time.NewTicker(s.syncInterval)
	defer ticker.Stop()

	s.reconcileUsers(ctx)
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			s.reconcileUsers(ctx)
		}
	}
}

// reconcileUsers starts reconcilers for newly-active users and stops
// reconcilers for users that are no longer active.
func (s *ReconcilerSupervisor) reconcileUsers(ctx context.Context) {
	users, err := s.users.ListActiveUsers(ctx)
	if err != nil {
		s.log.Warn().Err(err).Msg("active_user_list_failed")
		return
	}

	active := make(map[string]*auth.User, len(users))
	for _, u := range users {
		active[u.ID] = u
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	// Stop reconcilers for users that are no longer active.
	for uid, h := range s.running {
		if _, ok := active[uid]; !ok {
			h.cancel()
			delete(s.running, uid)
			s.log.Info().Str("user_id", uid).Msg("reconciler_stopped_user_inactive")
		}
	}

	// Start reconcilers for newly-active users.
	firstIdentitySet := s.mgr.TickCache().HasServiceIdentity()
	for uid, u := range active {
		if _, ok := s.running[uid]; ok {
			continue
		}
		svcToken, tokenErr := s.tokens.IssueServiceToken(u.ID, u.Username, u.Role, u.Tier, u.Status, u.TokenEpoch)
		if tokenErr != nil {
			s.log.Warn().Err(tokenErr).Str("user_id", uid).Msg("reconciler_token_issue_failed")
			continue
		}

		// Seed the tick cache with the first available identity so a
		// zero-trade cold start can authenticate price polls.
		if !firstIdentitySet {
			s.mgr.TickCache().SetServiceIdentity(&auth.Claims{
				UserID:   u.ID,
				Username: u.Username,
				Role:     u.Role,
				Tier:     u.Tier,
				Status:   u.Status,
			}, svcToken)
			firstIdentitySet = true
		}

		rctx, cancel := context.WithCancel(ctx)
		handle := &reconcilerHandle{cancel: cancel, done: make(chan struct{})}
		s.running[uid] = handle

		reconciler := NewStateReconciler(
			s.mgr, s.bp, s.repo, s.transport, u, svcToken, s.watchInterval,
		)

		s.wg.Add(1)
		go func(r *StateReconciler, h *reconcilerHandle) {
			defer s.wg.Done()
			defer close(h.done)
			_ = r.RunStartupSync(rctx)
			r.RunStreamListener(rctx)
		}(reconciler, handle)

		s.log.Info().Str("user_id", uid).Str("username", u.Username).Msg("reconciler_started")
	}
}

// Shutdown cancels all running reconcilers and waits for them to exit.
func (s *ReconcilerSupervisor) Shutdown() {
	s.mu.Lock()
	for uid, h := range s.running {
		h.cancel()
		delete(s.running, uid)
	}
	s.mu.Unlock()
	s.wg.Wait()
}
