package pipeline

import (
	"context"
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
func (s *Scheduler) Start(ctx context.Context) {
	if !s.cfg.Enabled {
		s.log.Info().Msg("gateway_disabled_skipping_scheduler")
		return
	}

	interval := time.Duration(s.cfg.CycleIntervalSeconds) * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	s.log.Info().
		Int("interval_seconds", s.cfg.CycleIntervalSeconds).
		Int("timeout_seconds", s.cfg.CycleTimeoutSeconds).
		Msg("gateway_cycle_scheduler_started")

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
