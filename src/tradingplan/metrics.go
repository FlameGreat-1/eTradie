package tradingplan

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// Prometheus instruments for the trading-plan module. Registered via
// promauto on the default registry to match tradingsystem and
// support. The package is imported exactly once per gateway process
// (from main.go), so there is no duplicate-registration risk.
//
// Label budgets stay well within the Prometheus operations guide's
// recommended 100-series-per-metric ceiling:
//
//   - outcome (generate):       4 values (queued, validation_error, throttled, error)
//   - outcome (edit/reset):     3 values (success, validation_error, error)
//   - outcome (callback):       3 values (success, validation_error, error)
//   - outcome (fetch):          3 values (hit, empty, error)
//   - outcome (internal):       4 values (success, validation_error, unauthorized, error)
//   - endpoint (rate_limited):  3 values (generate, edit, reset)
//   - source (balance):         2 values (broker, fallback)

const (
	outcomeSuccess         = "success"
	outcomeValidationError = "validation_error"
	outcomeError           = "error"
	outcomeQueued          = "queued"
	outcomeThrottled       = "throttled"
	outcomeHit             = "hit"
	outcomeEmpty           = "empty"
	outcomeUnauthorized    = "unauthorized"

	endpointGenerate = "generate"
	endpointEdit     = "edit"
	endpointReset    = "reset"

	// Journal auto-fill row actions.
	autofillUpdated  = "updated"
	autofillFilled   = "filled"
	autofillAppended = "appended"
	autofillRolled   = "rolled"
	autofillCapped   = "capped"

	// Journal auto-fill per-request outcomes.
	autofillApplied      = "applied"
	autofillNoop         = "noop"
	autofillReadError    = "read_error"
	autofillPersistError = "persist_error"
)

var (
	// TradingPlanGenerateTotal counts every POST /generate outcome.
	// 'queued' is the success path (the LLM call is fired and the
	// row is now status='generating'); 'throttled' means the per-
	// user rate limiter rejected the request; 'validation_error'
	// means the upstream trading-system was missing or invalid;
	// 'error' is reserved for true server-side failures.
	TradingPlanGenerateTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_plan_generate_total",
		Help: "Trading-plan generation attempts, partitioned by outcome.",
	}, []string{"outcome"})

	// TradingPlanGenerateDuration measures the wall-clock spent
	// inside the synchronous portion of the generate path (load
	// trading system, derive balance, dispatch engine call). The
	// LLM call itself happens asynchronously in the engine and is
	// measured by TradingPlanLLMCallDuration below.
	TradingPlanGenerateDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "trading_plan_generate_dispatch_duration_seconds",
		Help:    "Wall-clock spent dispatching a trading-plan generation request.",
		Buckets: []float64{0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0},
	})

	// TradingPlanLLMCallDuration measures the end-to-end time from
	// dispatch to the engine's callback completing. Useful for SLO
	// dashboards because the user is waiting on this in the UI.
	TradingPlanLLMCallDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "trading_plan_llm_call_duration_seconds",
		Help:    "Wall-clock between generation dispatch and engine callback.",
		Buckets: []float64{1, 2.5, 5, 10, 20, 30, 45, 60, 90, 120, 180, 300},
	})

	// TradingPlanEditTotal counts every PUT /api/v1/trading-plan
	// (in-app manual edit) outcome.
	TradingPlanEditTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_plan_edit_total",
		Help: "Trading-plan manual edit attempts, partitioned by outcome.",
	}, []string{"outcome"})

	// TradingPlanResetTotal counts every POST /reset outcome.
	TradingPlanResetTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_plan_reset_total",
		Help: "Trading-plan reset attempts, partitioned by outcome.",
	}, []string{"outcome"})

	// TradingPlanFetchTotal counts every GET /api/v1/trading-plan.
	TradingPlanFetchTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_plan_fetch_total",
		Help: "Trading-plan public fetch outcomes.",
	}, []string{"outcome"})

	// TradingPlanCallbackTotal counts every POST
	// /internal/trading-plan/callback. 'unauthorized' is the canary
	// for shared-secret drift between gateway and engine.
	TradingPlanCallbackTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_plan_callback_total",
		Help: "Trading-plan internal callback outcomes (engine -> gateway).",
	}, []string{"outcome"})

	// TradingPlanRateLimitedTotal counts every per-user rate-limit
	// rejection.
	TradingPlanRateLimitedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_plan_rate_limited_total",
		Help: "Trading-plan requests rejected by the per-user rate limiter.",
	}, []string{"endpoint"})

	// TradingPlanBalanceSourceTotal records which balance source
	// each generation used. A high fallback rate likely means the
	// broker integration is degraded; a high broker rate confirms
	// the happy-path is healthy.
	TradingPlanBalanceSourceTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_plan_balance_source_total",
		Help: "Generation count by balance source (broker vs. fallback).",
	}, []string{"source"})

	// TradingPlanJournalAutofillRows counts journal rows touched by the
	// manual-trade auto-fill, partitioned by action:
	//   updated  - an existing bound row's objective cells changed,
	//   filled   - a blank seed row was newly claimed + bound,
	//   appended - a new row was appended past the seeded blanks,
	//   rolled   - an auto row was reclaimed (reset to blank) because its
	//              trade fell out of the rolling journalWindowDays window
	//              (its objective facts remain in management_trades),
	//   capped   - a manual trade could not be placed because the journal
	//              is at journalMaxRows even AFTER roll-out (the extreme
	//              >200-annotated-rows-in-one-window canary; a non-zero
	//              rate means a user's window is saturated with annotated
	//              rows and the newest manual trades are not recorded).
	TradingPlanJournalAutofillRows = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_plan_journal_autofill_rows_total",
		Help: "Journal rows touched by the manual-trade auto-fill, by action.",
	}, []string{"action"})

	// TradingPlanJournalAutofillTotal counts each plan GET that ran the
	// auto-fill, partitioned by outcome:
	//   applied       - the merge changed the plan and it was persisted,
	//   noop          - nothing to apply (no facts / no change / no plan),
	//   read_error    - the management read failed (best-effort skip),
	//   persist_error - the transactional merge/persist failed.
	TradingPlanJournalAutofillTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_plan_journal_autofill_total",
		Help: "Manual-trade journal auto-fill runs, partitioned by outcome.",
	}, []string{"outcome"})
)
