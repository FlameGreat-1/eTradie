package validator

import (
	"context"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/execution/internal/broker"
	"github.com/flamegreat-1/etradie/src/execution/internal/config"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
	"github.com/flamegreat-1/etradie/src/execution/internal/state"
)

// RuntimeParams holds dashboard-configurable values resolved from the
// settings store on every trade. These override the static config
// defaults so that dashboard changes take effect immediately.
type RuntimeParams struct {
	MaxConcurrentTrades int
	DailyLossLimitPct   float64
	WeeklyDrawdownPct   float64
}

// checkFunc is the signature for each pre-execution check.
// Accepts context for broker calls with timeouts.
type checkFunc func(
	ctx context.Context,
	req *models.TradeRequest,
	cfg *config.Config,
	params *RuntimeParams,
	sm *state.Manager,
	bp broker.Port,
	now time.Time,
) models.ValidationResult

// Validator runs the 10 pre-execution checks sequentially.
// Checks 1-3 are handled by the gateway. Module B owns 4-13.
type Validator struct {
	cfg    *config.Config
	state  *state.Manager
	broker broker.Port
	checks []checkFunc
	log    zerolog.Logger
	nowFn  func() time.Time // Injected for testability.
}

// NewValidator creates a pre-execution validator.
func NewValidator(cfg *config.Config, sm *state.Manager, bp broker.Port) *Validator {
	return &Validator{
		cfg:    cfg,
		state:  sm,
		broker: bp,
		checks: []checkFunc{
			check4NewsLockout,
			check5SessionFilter,
			check6SamePairPosition,
			check7CorrelatedExposure,
			check8MaxConcurrentTrades,
			check9DailyLossLimit,
			check10WeeklyDrawdown,
			check11Spread,
			check12MinRR,
			check13WeekendDayFilter,
		},
		log:   observability.Logger("validator"),
		nowFn: func() time.Time { return time.Now().UTC() },
	}
}

// Validate runs all checks sequentially with runtime parameters
// resolved from the settings store. Returns on first failure.
func (v *Validator) Validate(ctx context.Context, req *models.TradeRequest, params *RuntimeParams) models.ValidationResult {
	start := time.Now()
	now := v.nowFn()

	for _, check := range v.checks {
		result := check(ctx, req, v.cfg, params, v.state, v.broker, now)
		if !result.Passed {
			elapsed := time.Since(start).Seconds()
			observability.ValidationDuration.Observe(elapsed)
			observability.ValidationTotal.WithLabelValues(string(result.Outcome)).Inc()
			observability.ValidationRejections.WithLabelValues(checkLabel(result.FailedCheck)).Inc()

			v.log.Warn().
				Str("symbol", req.Symbol).
				Str("direction", string(req.Direction)).
				Int32("failed_check", int32(result.FailedCheck)).
				Str("outcome", string(result.Outcome)).
				Str("reason", result.Reason).
				Str("analysis_id", req.AnalysisID).
				Str("trace_id", req.TraceID).
				Float64("duration_ms", elapsed*1000).
				Msg("validation_failed")

			return result
		}
	}

	elapsed := time.Since(start).Seconds()
	observability.ValidationDuration.Observe(elapsed)
	observability.ValidationTotal.WithLabelValues("passed").Inc()

	v.log.Info().
		Str("symbol", req.Symbol).
		Str("direction", string(req.Direction)).
		Str("analysis_id", req.AnalysisID).
		Str("trace_id", req.TraceID).
		Float64("duration_ms", elapsed*1000).
		Msg("validation_passed")

	return pass()
}
