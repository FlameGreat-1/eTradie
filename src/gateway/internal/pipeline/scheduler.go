package pipeline

import (
	"context"
	"math/rand"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/gateway/internal/config"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
	"github.com/flamegreat/etradie/src/gateway/internal/symbolstore"
)

// Scheduler manages the recurring gateway analysis cycle.
type Scheduler struct {
	orchestrator *Orchestrator
	symbolStore  *symbolstore.Store
	cfg          *config.Config
	log          zerolog.Logger
}

// NewScheduler creates a gateway cycle scheduler.
func NewScheduler(
	orchestrator *Orchestrator,
	symbolStore *symbolstore.Store,
	cfg *config.Config,
) *Scheduler {
	return &Scheduler{
		orchestrator: orchestrator,
		symbolStore:  symbolStore,
		cfg:          cfg,
		log:          observability.Logger("scheduler"),
	}
}

// Start begins the recurring cycle. Blocks until ctx is cancelled.
// Applies random jitter (0-10% of interval) to the first tick to
// prevent thundering herd when multiple gateway instances start.
func (s *Scheduler) Start(ctx context.Context) {
	if !s.cfg.Enabled {
		s.log.Info().Msg("gateway_disabled_skipping_scheduler")
		return
	}

	interval := time.Duration(s.cfg.CycleIntervalSeconds) * time.Second

	// Apply jitter to the first tick: random delay of 0-10% of the interval.
	// This prevents all gateway instances from firing their first cycle
	// at exactly the same time after a coordinated deployment/restart.
	maxJitter := interval / 10
	if maxJitter > 0 {
		jitter := time.Duration(rand.Int63n(int64(maxJitter)))
		s.log.Info().
			Int("interval_seconds", s.cfg.CycleIntervalSeconds).
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
			Int("interval_seconds", s.cfg.CycleIntervalSeconds).
			Int("timeout_seconds", s.cfg.CycleTimeoutSeconds).
			Msg("gateway_cycle_scheduler_started")
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			s.log.Info().Msg("gateway_cycle_scheduler_stopped")
			return
		case <-ticker.C:
			s.runCycle(ctx)
		}
	}
}

func (s *Scheduler) runCycle(ctx context.Context) {
	defer func() {
		if r := recover(); r != nil {
			observability.LogPanicRecovery(s.log, r, "scheduled_cycle")
		}
	}()

	symbols := s.symbolStore.GetActiveSymbols(ctx)

	s.log.Info().
		Strs("symbols", symbols).
		Msg("gateway_scheduled_cycle_starting")

	s.orchestrator.RunCycle(ctx, symbols, "")
}
