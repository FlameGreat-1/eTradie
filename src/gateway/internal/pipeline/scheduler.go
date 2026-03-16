package pipeline

import (
	"context"
	"crypto/rand"
	"encoding/binary"
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
// The first cycle fires immediately after the jitter delay, then
// subsequent cycles fire on the configured interval.
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
		jitter := cryptoRandDuration(maxJitter)
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

	// Fire the first cycle immediately after jitter.
	// Without this, the gateway would sit idle for the entire interval
	// (default 4 hours) before performing any analysis - catastrophic
	// for a trading system that must react to market conditions on startup.
	s.runCycle(ctx)

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

// cryptoRandDuration returns a cryptographically random duration in [0, max).
// Uses crypto/rand for non-deterministic jitter in multi-instance deployments.
func cryptoRandDuration(max time.Duration) time.Duration {
	if max <= 0 {
		return 0
	}
	var buf [8]byte
	if _, err := rand.Read(buf[:]); err != nil {
		// crypto/rand.Read never returns an error on supported platforms,
		// but if it does, fall back to zero jitter (safe, just no spread).
		return 0
	}
	n := binary.LittleEndian.Uint64(buf[:])
	return time.Duration(n % uint64(max))
}
