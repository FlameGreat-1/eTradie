package validator

import (
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/execution/internal/broker"
	"github.com/flamegreat/etradie/src/execution/internal/config"
	"github.com/flamegreat/etradie/src/execution/internal/models"
	"github.com/flamegreat/etradie/src/execution/internal/observability"
	"github.com/flamegreat/etradie/src/execution/internal/state"
)

type checkFunc func(
	req *models.TradeRequest,
	cfg *config.Config,
	sm *state.Manager,
	bp broker.Port,
) models.ValidationResult

// Validator runs the 10 pre-execution checks sequentially.
// Checks 1-3 are handled by the gateway. Module B owns 4-13.
type Validator struct {
	cfg    *config.Config
	state  *state.Manager
	broker broker.Port
	checks []checkFunc
	log    zerolog.Logger
}

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
		log: observability.Logger("validator"),
	}
}

// Validate runs all checks sequentially. Returns on first failure.
func (v *Validator) Validate(req *models.TradeRequest) models.ValidationResult {
	start := time.Now()

	for _, check := range v.checks {
		result := check(req, v.cfg, v.state, v.broker)
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
