package store

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"
)

// ---------------------------------------------------------------------------
// LLM metering errors and types
// ---------------------------------------------------------------------------

// ErrQuotaExceeded is returned by ReserveLLMTokens when the user has
// hit one of their per-tier caps. The Dimension field tells the caller
// which cap was breached so the SPA / engine can surface a meaningful
// 429 with a Retry-After hint.
//
// Dimension values are stable strings so dashboards and tests can match
// on them: "daily_input", "daily_output", "monthly_input",
// "monthly_output", "per_call_input", "model_not_allowed".
type QuotaExceededError struct {
	Dimension string
	Limit     int64
	Used      int64
	Requested int64
	ResetsAt  time.Time
}

func (e *QuotaExceededError) Error() string {
	return fmt.Sprintf(
		"llm quota exceeded: dimension=%s limit=%d used=%d requested=%d resets_at=%s",
		e.Dimension, e.Limit, e.Used, e.Requested, e.ResetsAt.UTC().Format(time.RFC3339),
	)
}

// IsQuotaExceeded is the canonical type-assertion helper.
func IsQuotaExceeded(err error) (*QuotaExceededError, bool) {
	var qe *QuotaExceededError
	if errors.As(err, &qe) {
		return qe, true
	}
	return nil, false
}

// LLMQuotaPolicy is the per-tier configuration the metering handler
// applies on every Reserve call. Built from auth.Config at the gateway
// boundary and handed to the store; the store does NOT read environment
// variables directly so unit tests can supply a deterministic policy.
//
// Zero values are NOT defaults: a zero DailyInputTokens means "cap of
// zero", which the handler interprets as "no LLM access" (e.g. free
// tier). This is deliberate so a misconfigured tier fails closed.
//
// AllowedModels is a case-insensitive set; an empty set means "any
// model the provider supports" (e.g. BYOK users supply their own key
// and pick their own model).
type LLMQuotaPolicy struct {
	DailyInputTokens       int64
	DailyOutputTokens      int64
	MonthlyInputTokens     int64
	MonthlyOutputTokens    int64
	MaxInputTokensPerCall  int64
	SoftCapPercent         int
	AllowedModels          map[string]bool
	// ReservationTTL is the wall-clock window inside which Commit /
	// Refund must arrive before the janitor reaps the reservation as a
	// Refund. 5 minutes is more than enough for the longest legitimate
	// LLM call (the processor's total_timeout_seconds default is 90s).
	ReservationTTL time.Duration
}

// HasLLMAccess reports whether this policy grants any LLM access at
// all. A tier with zero daily input AND zero daily output is treated as
// "managed access disabled" — relevant for the free tier today and any
// future restricted tier.
func (p *LLMQuotaPolicy) HasLLMAccess() bool {
	return p.DailyInputTokens > 0 && p.DailyOutputTokens > 0
}

// ModelAllowed returns true when model is in AllowedModels (case-insensitive)
// or when the allow-list is empty (no restriction).
func (p *LLMQuotaPolicy) ModelAllowed(model string) bool {
	if len(p.AllowedModels) == 0 {
		return true
	}
	return p.AllowedModels[strings.ToLower(strings.TrimSpace(model))]
}

// LLMUsageSnapshot is the read shape returned to the dashboard.
type LLMUsageSnapshot struct {
	InputTokensToday     int64     `json:"input_tokens_today"`
	OutputTokensToday    int64     `json:"output_tokens_today"`
	InputTokensMonth     int64     `json:"input_tokens_month"`
	OutputTokensMonth    int64     `json:"output_tokens_month"`
	BlockedToday         int       `json:"blocked_today"`
	BlockedMonth         int       `json:"blocked_month"`
	MonthlyWindowStart   time.Time `json:"monthly_window_start"`
	LastMeteredAt        *time.Time `json:"last_metered_at,omitempty"`
	DailyInputLimit      int64     `json:"daily_input_limit"`
	DailyOutputLimit     int64     `json:"daily_output_limit"`
	MonthlyInputLimit    int64     `json:"monthly_input_limit"`
	MonthlyOutputLimit   int64     `json:"monthly_output_limit"`
	SoftCapPercent       int       `json:"soft_cap_percent"`
	QuotaEnforced        bool      `json:"quota_enforced"`
}

// LLMReservation is the persisted reservation row.
type LLMReservation struct {
	ID                   string
	UserID               string
	Tier                 string
	Provider             string
	Model                string
	EstimatedInputTokens int64
	MaxOutputTokens      int64
	ActualInputTokens    *int64
	ActualOutputTokens   *int64
	Status               string
	TraceID              string
	CreatedAt            time.Time
	SettledAt            *time.Time
	ExpiresAt            time.Time
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

type UsageStore struct {
	db  *pgxpool.Pool
	log zerolog.Logger
}

func NewUsageStore(db *pgxpool.Pool) *UsageStore {
	return &UsageStore{
		db:  db,
		log: zerolog.New(os.Stdout).With().Timestamp().Str("component", "usage_store").Logger(),
	}
}

// generateReservationID returns a 32-hex-char id used as the primary
// key of billing_llm_reservations. Same shape and entropy as the auth
// package's GenerateID helper; declared here to avoid importing auth
// from the billing store (no cycle).
func generateReservationID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

type UsageMetrics struct {
	AnalysesToday     int        `json:"analyses_today"`
	LLMTokensUsed     int        `json:"llm_tokens_used"`
	TACyclesUsed      int        `json:"ta_cycles_used"`
	MacroCyclesUsed   int        `json:"macro_cycles_used"`
	ExecutionAttempts int        `json:"execution_attempts"`
	WatcherCount      int        `json:"watcher_count"`
	LastResetAt       time.Time  `json:"last_reset_at"`
	LastAnalysisAt    *time.Time `json:"last_analysis_at"`
}

func (s *UsageStore) GetOrUpdateUsage(ctx context.Context, userID string) (*UsageMetrics, error) {
	// Use an atomic query to get usage and handle daily resets in a single transaction.
	// This prevents race conditions and timezone reset vulnerabilities.
	query := `
		INSERT INTO billing_usage (user_id)
		VALUES ($1)
		ON CONFLICT (user_id) DO UPDATE SET
			analyses_today = CASE
				WHEN DATE(billing_usage.last_reset_at) < CURRENT_DATE THEN 0
				ELSE billing_usage.analyses_today
			END,
			last_reset_at = CASE
				WHEN DATE(billing_usage.last_reset_at) < CURRENT_DATE THEN NOW()
				ELSE billing_usage.last_reset_at
			END
		RETURNING analyses_today, llm_tokens_used, ta_cycles_used, macro_cycles_used, execution_attempts, watcher_count, last_reset_at, last_analysis_at
	`
	var m UsageMetrics
	err := s.db.QueryRow(ctx, query, userID).Scan(
		&m.AnalysesToday, &m.LLMTokensUsed, &m.TACyclesUsed, &m.MacroCyclesUsed, &m.ExecutionAttempts, &m.WatcherCount, &m.LastResetAt, &m.LastAnalysisAt,
	)
	if err != nil {
		return nil, err
	}

	return &m, nil
}

// IncrementMetric atomically adjusts a usage counter for the given user.
//
// The amount parameter can be negative (e.g., -1 when a watcher disarms).
// Every counter is clamped at zero with GREATEST(0, column + $1) so a
// stray decrement that arrives before its matching increment (panic
// recovery, retry races) cannot drive billing_usage below zero. This is
// defensive: in normal flow watcher_count is incremented by Arm BEFORE
// the corresponding Disarm runs, but the clamp guarantees the invariant
// without depending on call-site discipline.
func (s *UsageStore) IncrementMetric(ctx context.Context, userID string, column string, amount int) error {
	allowed := map[string]bool{
		"analyses_today":     true,
		"llm_tokens_used":    true,
		"ta_cycles_used":     true,
		"macro_cycles_used":  true,
		"execution_attempts": true,
		"watcher_count":      true,
	}
	if !allowed[column] {
		return fmt.Errorf("invalid metric column: %s", column)
	}

	query := fmt.Sprintf(`
		UPDATE billing_usage
		SET %s = GREATEST(0, %s + $1)
		WHERE user_id = $2
	`, column, column)

	_, err := s.db.Exec(ctx, query, amount, userID)
	return err
}

// ---------------------------------------------------------------------------
// LLM metering: Reserve / Commit / Refund
// ---------------------------------------------------------------------------

// ReserveLLMTokens performs the atomic check-and-debit that gates every
// LLM call for a managed-tier user.
//
// Inputs:
//   userID, tier              : caller-resolved identity / billing tier.
//   provider, model, traceID  : audit metadata stored on the reservation.
//   estimatedInput, maxOutput : the provisional debit. estimatedInput
//                               is the tokeniser-computed cost of the
//                               assembled prompt; maxOutput is the
//                               provider-honoured max_output_tokens.
//   policy                    : tier limits + reservation TTL.
//
// Returns the reservation ID on success. On quota breach returns a
// *QuotaExceededError with the breached dimension; on any other failure
// returns the underlying error wrapped with context.
//
// Concurrency: a SELECT FOR UPDATE on billing_usage inside a tx makes
// the read-modify-write race-free even under parallel reservations from
// the same user. The row is created lazily if it does not yet exist.
func (s *UsageStore) ReserveLLMTokens(
	ctx context.Context,
	userID, tier string,
	provider, model, traceID string,
	estimatedInput, maxOutput int64,
	policy LLMQuotaPolicy,
) (string, error) {
	if userID == "" {
		return "", fmt.Errorf("reserve_llm_tokens: user_id is required")
	}
	if estimatedInput < 0 || maxOutput < 0 {
		return "", fmt.Errorf("reserve_llm_tokens: token counts must be non-negative (input=%d output=%d)", estimatedInput, maxOutput)
	}

	// Pre-Reserve policy gates that do not require a DB round-trip.
	//
	// tier_not_eligible is a distinct dimension from the daily / monthly
	// cap dimensions because the operational meaning differs: the user
	// has not used anything; their tier just does not include managed
	// LLM access. The SPA renders a different CTA for this case
	// ("Add your own API key" / "Upgrade to Pro Managed") than for a
	// real cap breach ("Daily quota reached, resets at ...").
	if !policy.HasLLMAccess() {
		return "", &QuotaExceededError{
			Dimension: "tier_not_eligible",
			Limit:     0,
			Used:      0,
			Requested: estimatedInput,
			ResetsAt:  time.Now().UTC(),
		}
	}
	if !policy.ModelAllowed(model) {
		return "", &QuotaExceededError{
			Dimension: "model_not_allowed",
			Limit:     0,
			Used:      0,
			Requested: estimatedInput,
			ResetsAt:  time.Now().UTC(),
		}
	}
	if policy.MaxInputTokensPerCall > 0 && estimatedInput > policy.MaxInputTokensPerCall {
		return "", &QuotaExceededError{
			Dimension: "per_call_input",
			Limit:     policy.MaxInputTokensPerCall,
			Used:      0,
			Requested: estimatedInput,
			ResetsAt:  time.Now().UTC(),
		}
	}

	tx, err := s.db.BeginTx(ctx, pgx.TxOptions{IsoLevel: pgx.ReadCommitted})
	if err != nil {
		return "", fmt.Errorf("reserve_llm_tokens: begin tx: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	now := time.Now().UTC()

	// Upsert the usage row and lock it for update. If we just created
	// the row, both today/month start fresh at zero.
	var (
		inputToday, outputToday int64
		inputMonth, outputMonth int64
		monthlyWindowStart      time.Time
	)
	if err := tx.QueryRow(ctx, `
		INSERT INTO billing_usage (user_id, monthly_window_start, last_reset_at)
		VALUES ($1, $2, $2)
		ON CONFLICT (user_id) DO UPDATE SET
			llm_input_tokens_today  = CASE WHEN DATE(billing_usage.last_reset_at) < CURRENT_DATE
			                                THEN 0 ELSE billing_usage.llm_input_tokens_today END,
			llm_output_tokens_today = CASE WHEN DATE(billing_usage.last_reset_at) < CURRENT_DATE
			                                THEN 0 ELSE billing_usage.llm_output_tokens_today END,
			llm_quota_blocked_count_today = CASE WHEN DATE(billing_usage.last_reset_at) < CURRENT_DATE
			                                THEN 0 ELSE billing_usage.llm_quota_blocked_count_today END,
			last_reset_at           = CASE WHEN DATE(billing_usage.last_reset_at) < CURRENT_DATE
			                                THEN $2 ELSE billing_usage.last_reset_at END
		RETURNING llm_input_tokens_today, llm_output_tokens_today,
		          llm_input_tokens_month, llm_output_tokens_month,
		          monthly_window_start
	`, userID, now).Scan(
		&inputToday, &outputToday,
		&inputMonth, &outputMonth,
		&monthlyWindowStart,
	); err != nil {
		return "", fmt.Errorf("reserve_llm_tokens: upsert usage: %w", err)
	}

	// Quota predicates. Each branch records a blocked-count and returns
	// a typed error so the caller can map it to a 429 with a
	// dimension-specific Retry-After.
	checkCap := func(dimension string, used, requested, limit int64, resetsAt time.Time) error {
		if limit <= 0 {
			return nil
		}
		if used+requested > limit {
			return &QuotaExceededError{
				Dimension: dimension,
				Limit:     limit,
				Used:      used,
				Requested: requested,
				ResetsAt:  resetsAt,
			}
		}
		return nil
	}

	dailyResetAt := nextDailyReset(now)
	monthlyResetAt := nextMonthlyReset(monthlyWindowStart)

	if err := checkCap("daily_input", inputToday, estimatedInput, policy.DailyInputTokens, dailyResetAt); err != nil {
		return "", s.commitBlocked(ctx, tx, userID, err)
	}
	if err := checkCap("daily_output", outputToday, maxOutput, policy.DailyOutputTokens, dailyResetAt); err != nil {
		return "", s.commitBlocked(ctx, tx, userID, err)
	}
	if err := checkCap("monthly_input", inputMonth, estimatedInput, policy.MonthlyInputTokens, monthlyResetAt); err != nil {
		return "", s.commitBlocked(ctx, tx, userID, err)
	}
	if err := checkCap("monthly_output", outputMonth, maxOutput, policy.MonthlyOutputTokens, monthlyResetAt); err != nil {
		return "", s.commitBlocked(ctx, tx, userID, err)
	}

	// All checks passed. Provisionally debit both dimensions in one
	// UPDATE so a parallel reservation cannot land between them.
	if _, err := tx.Exec(ctx, `
		UPDATE billing_usage SET
			llm_input_tokens_today  = llm_input_tokens_today + $2,
			llm_output_tokens_today = llm_output_tokens_today + $3,
			llm_input_tokens_month  = llm_input_tokens_month + $2,
			llm_output_tokens_month = llm_output_tokens_month + $3
		WHERE user_id = $1
	`, userID, estimatedInput, maxOutput); err != nil {
		return "", fmt.Errorf("reserve_llm_tokens: debit: %w", err)
	}

	ttl := policy.ReservationTTL
	if ttl <= 0 {
		ttl = 5 * time.Minute
	}
	reservationID := generateReservationID()
	if _, err := tx.Exec(ctx, `
		INSERT INTO billing_llm_reservations
			(id, user_id, tier, provider, model,
			 estimated_input_tokens, max_output_tokens,
			 status, trace_id, created_at, expires_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, 'held', $8, $9, $10)
	`, reservationID, userID, tier, provider, model,
		estimatedInput, maxOutput,
		traceID, now, now.Add(ttl),
	); err != nil {
		return "", fmt.Errorf("reserve_llm_tokens: insert reservation: %w", err)
	}

	if err := tx.Commit(ctx); err != nil {
		return "", fmt.Errorf("reserve_llm_tokens: commit: %w", err)
	}
	return reservationID, nil
}

// commitBlocked increments the per-window blocked-count audit counters
// AND commits the tx so the audit counter is durable even though the
// reservation itself is rejected. Returns qerr unchanged for chaining.
//
// Replaces the older recordBlocked which committed inside the helper
// but left the outer defer-Rollback running against an already-committed
// tx (pgx returns an error in that state which was discarded). Now we
// explicitly Rollback on UPDATE failure and Commit on success, so the
// caller's outer defer-Rollback is a no-op safety net for panics only.
//
// Posture: the quota error is authoritative; a transient audit-counter
// failure must NOT mask the user-facing 429. So both error paths still
// return qerr to the caller; the failure is logged at the storage
// layer's pgx logging, not here, to keep this helper allocation-free.
//
// Audit ref: ADMIN-QUOTA-AUDIT-V2-2.
func (s *UsageStore) commitBlocked(ctx context.Context, tx pgx.Tx, userID string, qerr error) error {
	if _, err := tx.Exec(ctx, `
		UPDATE billing_usage SET
			llm_quota_blocked_count_today = llm_quota_blocked_count_today + 1,
			llm_quota_blocked_count_month = llm_quota_blocked_count_month + 1
		WHERE user_id = $1
	`, userID); err != nil {
		// Audit-counter UPDATE failed. The user-facing 429 still fires
		// (qerr is authoritative), but the operator MUST see this so a
		// silently-broken blocked counter does not hide a quota incident
		// from the dashboard. Audit ref: ADMIN-QUOTA-AUDIT-V3-A6.
		s.log.Error().
			Err(err).
			Str("user_id", userID).
			Msg("usage_store_commit_blocked_audit_update_failed")
		_ = tx.Rollback(ctx)
		return qerr
	}
	if err := tx.Commit(ctx); err != nil {
		s.log.Error().
			Err(err).
			Str("user_id", userID).
			Msg("usage_store_commit_blocked_tx_commit_failed")
		return qerr
	}
	return qerr
}

// CommitOutcome carries post-Commit signals the handler needs to act
// on:
//   * SoftCapJustCrossed: true on the first Commit whose corrected
//     usage crosses the soft-cap threshold in the current monthly
//     window.
//   * MonthlyWindowStart: the row's monthly_window_start at the
//     moment of the test-and-set, so the email's reset-date label
//     is computed from the SAME row the threshold check evaluated.
//     Eliminates the extra DB round-trip in fireSoftCapEmail and
//     closes the sub-millisecond race against a parallel
//     MonthlyReset (V4-C).
//
// UserID is returned so the handler can look up the email / username
// without a second DB round-trip against the reservations table.
//
// Audit ref: ADMIN-QUOTA-AUDIT-V3-A10, ADMIN-QUOTA-AUDIT-V4-C.
type CommitOutcome struct {
	UserID             string
	SoftCapJustCrossed bool
	MonthlyWindowStart time.Time
}

// CommitLLMTokens settles a held reservation with the real token counts
// returned by the LLM. The over-reservation on the output side
// (max_output_tokens - actual_output_tokens) is rolled back; the input
// side is corrected for the (rare) case where the tokeniser estimate
// diverged from the model's count.
//
// The soft-cap test-and-set runs INSIDE the same transaction so the
// counter adjustment and the threshold evaluation see a consistent
// snapshot. Firing the email from Reserve (pre-correction) would
// observe inflated usage and emit premature warnings.
// Audit ref: ADMIN-QUOTA-AUDIT-V3-A10.
//
// Idempotent: re-committing an already-committed reservation is a
// no-op so an at-least-once retry from the engine cannot double-charge.
//
// softCapPercent / monthlyInputLimit / monthlyOutputLimit are the
// resolved policy values for this user's tier. The caller (gateway
// metering handler) has them in hand from the same QuotaPolicyStore
// read that gated Reserve; passing them through avoids a second
// policy lookup inside the store.
func (s *UsageStore) CommitLLMTokens(
	ctx context.Context,
	reservationID string,
	actualInput, actualOutput int64,
	softCapPercent int,
	monthlyInputLimit, monthlyOutputLimit int64,
) (CommitOutcome, error) {
	if reservationID == "" {
		return CommitOutcome{}, fmt.Errorf("commit_llm_tokens: reservation_id is required")
	}
	if actualInput < 0 || actualOutput < 0 {
		return CommitOutcome{}, fmt.Errorf("commit_llm_tokens: token counts must be non-negative")
	}

	tx, err := s.db.BeginTx(ctx, pgx.TxOptions{IsoLevel: pgx.ReadCommitted})
	if err != nil {
		return CommitOutcome{}, fmt.Errorf("commit_llm_tokens: begin tx: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	now := time.Now().UTC()

	var (
		userID                    string
		estimatedInput, maxOutput int64
		monthlyWindowStart        time.Time
	)
	err = tx.QueryRow(ctx, `
		UPDATE billing_llm_reservations SET
			status               = 'committed',
			actual_input_tokens  = $2,
			actual_output_tokens = $3,
			settled_at           = $4
		WHERE id = $1 AND status = 'held'
		RETURNING user_id, estimated_input_tokens, max_output_tokens
	`, reservationID, actualInput, actualOutput, now,
	).Scan(&userID, &estimatedInput, &maxOutput)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			// Already settled or never existed. Idempotent: no-op.
			_ = tx.Commit(ctx)
			return CommitOutcome{}, nil
		}
		return CommitOutcome{}, fmt.Errorf("commit_llm_tokens: update reservation: %w", err)
	}

	// Adjust the counters: the input estimate is replaced with the
	// actual count (delta = actual - estimated, can be negative), and
	// the over-reservation on output is returned.
	inputDelta := actualInput - estimatedInput
	outputRefund := maxOutput - actualOutput
	if outputRefund < 0 {
		// Provider returned more than max_output (should be impossible)
		// — treat as zero refund rather than charge double.
		outputRefund = 0
	}

	if _, err := tx.Exec(ctx, `
		UPDATE billing_usage SET
			llm_input_tokens_today  = GREATEST(0, llm_input_tokens_today  + $2),
			llm_input_tokens_month  = GREATEST(0, llm_input_tokens_month  + $2),
			llm_output_tokens_today = GREATEST(0, llm_output_tokens_today - $3),
			llm_output_tokens_month = GREATEST(0, llm_output_tokens_month - $3),
			llm_tokens_used         = GREATEST(0, llm_tokens_used + $4),
			llm_last_metered_at     = $5
		WHERE user_id = $1
	`, userID, inputDelta, outputRefund, actualInput+actualOutput, now); err != nil {
		return CommitOutcome{}, fmt.Errorf("commit_llm_tokens: adjust counters: %w", err)
	}

	// Estimation-drift breach detection (Audit ref: ADMIN-QUOTA-AUDIT-V4-A).
	//
	// When inputDelta is positive (actualInput > estimatedInput), the
	// Commit ADDED tokens to the monthly counter. If the post-Commit
	// monthly counter now exceeds the cap, the engine's byte/4 estimate
	// drifted enough to let one call land over the cap. We do NOT roll
	// the LLM call back -- the user already got their response. But we
	// MUST record the breach so:
	//   * the audit-counter reflects the over-cap state,
	//   * the next pre-flight (used >= limit) blocks the next call,
	//   * operators can grep for the dedicated log line and tune the
	//     estimator if drift becomes common.
	//
	// Only fires when monthlyInputLimit > 0 (enforced tier). For BYOK
	// and free tiers monthlyInputLimit is 0 and this is a no-op.
	if inputDelta > 0 && monthlyInputLimit > 0 {
		var postCommitInputMonth int64
		if scanErr := tx.QueryRow(ctx, `
			SELECT llm_input_tokens_month
			FROM billing_usage WHERE user_id = $1
		`, userID).Scan(&postCommitInputMonth); scanErr == nil {
			if postCommitInputMonth > monthlyInputLimit {
				// V5-B: increment a dedicated counter, NOT the user-visible
				// blocked_count. The user did not see a 429; conflating the
				// two would make the operator dashboard's block metric
				// meaningless. Audit ref: ADMIN-QUOTA-AUDIT-V5-B.
				if _, err := tx.Exec(ctx, `
					UPDATE billing_usage SET
						llm_estimation_overshoot_count_today = llm_estimation_overshoot_count_today + 1,
						llm_estimation_overshoot_count_month = llm_estimation_overshoot_count_month + 1
					WHERE user_id = $1
				`, userID); err == nil {
					s.log.Warn().
						Str("user_id", userID).
						Int64("estimated_input", estimatedInput).
						Int64("actual_input", actualInput).
						Int64("monthly_input_limit", monthlyInputLimit).
						Int64("post_commit_input_month", postCommitInputMonth).
						Msg("commit_llm_tokens_estimation_drift_overshoot_recorded")
				}
			}
		}
	}

	// Soft-cap test-and-set inside the same tx so the threshold check
	// reads the just-adjusted counters. Returns true ONLY on the first
	// Commit whose corrected usage crosses the threshold in this
	// monthly window (soft_cap_notified_at IS NULL guard).
	softCapJustCrossed := false
	if softCapPercent > 0 && softCapPercent <= 100 &&
		(monthlyInputLimit > 0 || monthlyOutputLimit > 0) {
		ceilDiv := func(limit int64, pct int) int64 {
			if limit <= 0 {
				return 0
			}
			return (limit*int64(pct) + 99) / 100
		}
		inputThreshold := ceilDiv(monthlyInputLimit, softCapPercent)
		outputThreshold := ceilDiv(monthlyOutputLimit, softCapPercent)

		var (
			firedAt          *time.Time
			localWindowStart time.Time
		)
		scanErr := tx.QueryRow(ctx, `
			UPDATE billing_usage
			SET soft_cap_notified_at = NOW()
			WHERE user_id = $1
			  AND soft_cap_notified_at IS NULL
			  AND (
			       ($2 > 0 AND llm_input_tokens_month  >= $2)
			    OR ($3 > 0 AND llm_output_tokens_month >= $3)
			  )
			RETURNING soft_cap_notified_at, monthly_window_start
		`, userID, inputThreshold, outputThreshold).Scan(&firedAt, &localWindowStart)
		if scanErr == nil && firedAt != nil {
			softCapJustCrossed = true
			monthlyWindowStart = localWindowStart
		} else if scanErr != nil && !errors.Is(scanErr, pgx.ErrNoRows) {
			// Test-and-set itself failed (lock contention, schema drift).
			// Log + continue: the counter adjustment is correct; we
			// just miss the email this round. The next Commit retries.
			s.log.Error().
				Err(scanErr).
				Str("user_id", userID).
				Msg("commit_llm_tokens_soft_cap_check_failed")
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return CommitOutcome{}, fmt.Errorf("commit_llm_tokens: commit: %w", err)
	}
	return CommitOutcome{
		UserID:             userID,
		SoftCapJustCrossed: softCapJustCrossed,
		MonthlyWindowStart: monthlyWindowStart,
	}, nil
}

// RefundLLMTokens rolls back the full provisional debit on a held
// reservation. Called when the LLM call fails after retries are
// exhausted, or when the engine never returned a Commit before the
// reservation TTL elapsed (janitor path).
//
// Idempotent: a refund against an already-settled reservation is a
// no-op.
func (s *UsageStore) RefundLLMTokens(ctx context.Context, reservationID string) error {
	if reservationID == "" {
		return fmt.Errorf("refund_llm_tokens: reservation_id is required")
	}

	tx, err := s.db.BeginTx(ctx, pgx.TxOptions{IsoLevel: pgx.ReadCommitted})
	if err != nil {
		return fmt.Errorf("refund_llm_tokens: begin tx: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	now := time.Now().UTC()

	var (
		userID                    string
		estimatedInput, maxOutput int64
	)
	err = tx.QueryRow(ctx, `
		UPDATE billing_llm_reservations SET
			status     = 'refunded',
			settled_at = $2
		WHERE id = $1 AND status = 'held'
		RETURNING user_id, estimated_input_tokens, max_output_tokens
	`, reservationID, now).Scan(&userID, &estimatedInput, &maxOutput)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			_ = tx.Commit(ctx)
			return nil
		}
		return fmt.Errorf("refund_llm_tokens: update reservation: %w", err)
	}

	if _, err := tx.Exec(ctx, `
		UPDATE billing_usage SET
			llm_input_tokens_today  = GREATEST(0, llm_input_tokens_today  - $2),
			llm_input_tokens_month  = GREATEST(0, llm_input_tokens_month  - $2),
			llm_output_tokens_today = GREATEST(0, llm_output_tokens_today - $3),
			llm_output_tokens_month = GREATEST(0, llm_output_tokens_month - $3)
		WHERE user_id = $1
	`, userID, estimatedInput, maxOutput); err != nil {
		return fmt.Errorf("refund_llm_tokens: roll back counters: %w", err)
	}

	return tx.Commit(ctx)
}

// JanitorReapStaleReservations refunds reservations whose TTL has
// elapsed. Returns the number of rows refunded. Called by the billing
// reconciler.
func (s *UsageStore) JanitorReapStaleReservations(ctx context.Context) (int64, error) {
	rows, err := s.db.Query(ctx, `
		SELECT id FROM billing_llm_reservations
		WHERE status = 'held' AND expires_at <= NOW()
		ORDER BY expires_at ASC
		LIMIT 500
	`)
	if err != nil {
		return 0, fmt.Errorf("janitor_reap_stale: query: %w", err)
	}
	defer rows.Close()

	var ids []string
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return 0, fmt.Errorf("janitor_reap_stale: scan: %w", err)
		}
		ids = append(ids, id)
	}
	rows.Close()

	var refunded int64
	for _, id := range ids {
		if err := s.RefundLLMTokens(ctx, id); err != nil {
			return refunded, fmt.Errorf("janitor_reap_stale: refund %s: %w", id, err)
		}
		refunded++
	}
	return refunded, nil
}

// PreflightResult is the read-only outcome of a quota pre-flight check.
// Allowed=true means the deep Reserve path will accept a reservation of
// the supplied size at this instant (subject to a tiny race with another
// in-flight reservation from the same user; the deep path's SELECT FOR
// UPDATE is the authority on that race).
//
// When Allowed=false, the remaining fields describe the breached
// dimension so the gateway can return a 429 with the SAME body shape
// the deep path emits.
type PreflightResult struct {
	Allowed   bool
	Dimension string    // empty when Allowed=true
	Limit     int64
	Used      int64
	Requested int64
	ResetsAt  time.Time
}

// PreflightLLMQuota performs a cheap read-only check that the supplied
// (estimatedInput, maxOutput) reservation would succeed against the
// caller's current usage counters. Single SELECT, no transaction, no
// writes. Safe to call on every cycle trigger.
//
// Returns Allowed=true and the zero PreflightResult when the user has no
// row yet (treated as zero usage; the first Reserve will create the row).
// Returns Allowed=false with the breached dimension populated when any
// daily or monthly cap would be exceeded.
//
// The caller MUST have already established that policy.HasLLMAccess()
// before invoking this; a tier-not-eligible user should never reach the
// pre-flight check (the gateway handler enforces that gate separately,
// because the dimension name 'tier_not_eligible' is informational and
// requires no counter read).
func (s *UsageStore) PreflightLLMQuota(
	ctx context.Context,
	userID string,
	estimatedInput, maxOutput int64,
	policy LLMQuotaPolicy,
) (*PreflightResult, error) {
	if userID == "" {
		return nil, fmt.Errorf("preflight_llm_quota: user_id is required")
	}
	if estimatedInput < 0 || maxOutput < 0 {
		return nil, fmt.Errorf("preflight_llm_quota: token counts must be non-negative (input=%d output=%d)", estimatedInput, maxOutput)
	}

	// Per-call gate. Deep path applies this too; we short-circuit here
	// so a too-large prompt fails the pre-flight without burning a DB
	// round-trip.
	if policy.MaxInputTokensPerCall > 0 && estimatedInput > policy.MaxInputTokensPerCall {
		return &PreflightResult{
			Allowed:   false,
			Dimension: "per_call_input",
			Limit:     policy.MaxInputTokensPerCall,
			Used:      0,
			Requested: estimatedInput,
			ResetsAt:  time.Now().UTC(),
		}, nil
	}

	now := time.Now().UTC()

	// Single SELECT with the same daily-reset CASE expression Reserve uses.
	// Returns the four counters AS THEY WOULD BE READ AT THIS INSTANT,
	// without writing back the reset (the next Reserve will do that).
	var (
		inputToday, outputToday int64
		inputMonth, outputMonth int64
		monthlyWindowStart      time.Time
	)
	err := s.db.QueryRow(ctx, `
		SELECT
			CASE WHEN DATE(last_reset_at) < CURRENT_DATE
			     THEN 0 ELSE llm_input_tokens_today END,
			CASE WHEN DATE(last_reset_at) < CURRENT_DATE
			     THEN 0 ELSE llm_output_tokens_today END,
			llm_input_tokens_month,
			llm_output_tokens_month,
			monthly_window_start
		FROM billing_usage
		WHERE user_id = $1
	`, userID).Scan(
		&inputToday, &outputToday,
		&inputMonth, &outputMonth,
		&monthlyWindowStart,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			// No row yet -> user has zero usage. Pre-flight allowed; the
			// deep Reserve path will create the row in its tx.
			return &PreflightResult{Allowed: true}, nil
		}
		return nil, fmt.Errorf("preflight_llm_quota: query: %w", err)
	}

	dailyResetAt := nextDailyReset(now)
	monthlyResetAt := nextMonthlyReset(monthlyWindowStart)

	// Check each cap. First breach wins so the gateway can render a
	// dimension-specific message; ordering matches Reserve so the
	// pre-flight and the deep path agree on which dimension to surface
	// when multiple caps would breach simultaneously.
	//
	// Semantics differ slightly from the deep Reserve path's strict >
	// comparison: the pre-flight callers (handleRunCycle, scheduler
	// tick) pass requested=0 because the real prompt has not been
	// built yet. With strict > and requested=0 a user at exactly the
	// cap (used == limit) would not be blocked, leaking one more call
	// past the deep Reserve. We pre-emptively block that case here so
	// the resource-saving short-circuit fires the first time the user
	// reaches the cap, not one call later. When a future caller passes
	// a non-zero requested estimate the original semantics are
	// preserved (a call that would take the user PAST the limit is
	// blocked; a call that lands exactly at the limit is allowed).
	// Audit ref: ADMIN-QUOTA-AUDIT-3.
	check := func(dimension string, used, requested, limit int64, resetsAt time.Time) *PreflightResult {
		if limit <= 0 {
			return nil
		}
		blocked := used+requested > limit
		if requested == 0 {
			blocked = used >= limit
		}
		if blocked {
			return &PreflightResult{
				Allowed:   false,
				Dimension: dimension,
				Limit:     limit,
				Used:      used,
				Requested: requested,
				ResetsAt:  resetsAt,
			}
		}
		return nil
	}
	if r := check("daily_input", inputToday, estimatedInput, policy.DailyInputTokens, dailyResetAt); r != nil {
		return r, nil
	}
	if r := check("daily_output", outputToday, maxOutput, policy.DailyOutputTokens, dailyResetAt); r != nil {
		return r, nil
	}
	if r := check("monthly_input", inputMonth, estimatedInput, policy.MonthlyInputTokens, monthlyResetAt); r != nil {
		return r, nil
	}
	if r := check("monthly_output", outputMonth, maxOutput, policy.MonthlyOutputTokens, monthlyResetAt); r != nil {
		return r, nil
	}
	return &PreflightResult{Allowed: true}, nil
}

// GetLLMUsageSnapshot returns the SPA-facing usage shape for one user.
// The policy is supplied by the caller (gateway boundary) and merged
// in so the SPA can compute remaining/used percentages without doing
// math on potentially-stale environment knobs.
//
// Pure read: no INSERT, no UPDATE. A GET on /api/v1/billing/usage
// must not mutate billing_usage (architectural mix-up + audit
// confusion + read-replica safety + BYOK users have no row and don't
// need one). The Reserve path creates the row when it actually needs
// to write. Audit ref: ADMIN-QUOTA-AUDIT-V2-4.
//
// Daily-reset semantics: the returned llm_*_tokens_today values
// reflect the same CASE expression Reserve applies in its UPSERT,
// so a snapshot taken at 00:01 UTC the day after the user transacted
// still shows today's empty counters without writing the reset back.
//
// No row -> zero snapshot (BYOK / free / first-time visitor). The
// SPA UsagePanel renders nothing for those users anyway because
// quota_enforced=false.
func (s *UsageStore) GetLLMUsageSnapshot(
	ctx context.Context,
	userID string,
	policy LLMQuotaPolicy,
) (*LLMUsageSnapshot, error) {
	if userID == "" {
		return nil, fmt.Errorf("get_llm_usage_snapshot: user_id is required")
	}

	var snap LLMUsageSnapshot
	err := s.db.QueryRow(ctx, `
		SELECT
			CASE WHEN DATE(last_reset_at) < CURRENT_DATE
			     THEN 0 ELSE llm_input_tokens_today END,
			CASE WHEN DATE(last_reset_at) < CURRENT_DATE
			     THEN 0 ELSE llm_output_tokens_today END,
			llm_input_tokens_month,
			llm_output_tokens_month,
			CASE WHEN DATE(last_reset_at) < CURRENT_DATE
			     THEN 0 ELSE llm_quota_blocked_count_today END,
			llm_quota_blocked_count_month,
			monthly_window_start,
			llm_last_metered_at
		FROM billing_usage
		WHERE user_id = $1
	`, userID).Scan(
		&snap.InputTokensToday, &snap.OutputTokensToday,
		&snap.InputTokensMonth, &snap.OutputTokensMonth,
		&snap.BlockedToday, &snap.BlockedMonth,
		&snap.MonthlyWindowStart, &snap.LastMeteredAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			// No row yet: zero snapshot. Policy fields are still merged
			// in so the SPA can render "0 / limit" cards for a freshly
			// upgraded pro_managed user before their first cycle.
			snap.DailyInputLimit = policy.DailyInputTokens
			snap.DailyOutputLimit = policy.DailyOutputTokens
			snap.MonthlyInputLimit = policy.MonthlyInputTokens
			snap.MonthlyOutputLimit = policy.MonthlyOutputTokens
			snap.SoftCapPercent = policy.SoftCapPercent
			snap.QuotaEnforced = policy.HasLLMAccess()
			return &snap, nil
		}
		return nil, fmt.Errorf("get_llm_usage_snapshot: %w", err)
	}

	snap.DailyInputLimit = policy.DailyInputTokens
	snap.DailyOutputLimit = policy.DailyOutputTokens
	snap.MonthlyInputLimit = policy.MonthlyInputTokens
	snap.MonthlyOutputLimit = policy.MonthlyOutputTokens
	snap.SoftCapPercent = policy.SoftCapPercent
	snap.QuotaEnforced = policy.HasLLMAccess()
	return &snap, nil
}

// MonthlyReset zeroes the monthly counters and bumps the window start.
// Called by the billing reconciler on every subscription period-end
// renewal so a paying customer's quota lifecycle matches their billing
// cycle exactly.
//
// soft_cap_notified_at is cleared in the same UPDATE so the new monthly
// window gets one fresh notification opportunity. Without this clear, a
// user who crossed the soft cap last month would never get warned again.
//
// Race-safety (Audit ref: ADMIN-QUOTA-AUDIT-V5-A):
//
//	The UPDATE is wrapped in a tx with an explicit row lock so an
//	in-flight Reserve cannot land its debit AFTER the read snapshot
//	but BEFORE the reset, losing the debit. The WHERE
//	monthly_window_start < $2 predicate makes the reset idempotent
//	and prevents an out-of-order older reset from clobbering a newer
//	window that has already been advanced by a more recent renewal
//	event.
func (s *UsageStore) MonthlyReset(ctx context.Context, userID string, windowStart time.Time) error {
	if userID == "" {
		return fmt.Errorf("monthly_reset: user_id is required")
	}

	tx, err := s.db.BeginTx(ctx, pgx.TxOptions{IsoLevel: pgx.ReadCommitted})
	if err != nil {
		return fmt.Errorf("monthly_reset: begin tx: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	// Take an explicit row lock so any concurrent Reserve's SELECT FOR
	// UPDATE (implicit via INSERT ... ON CONFLICT DO UPDATE) waits for
	// us. If the row does not exist yet (BYOK / free user who never
	// transacted), the SELECT returns no rows and the UPDATE is a
	// no-op -- correct behaviour because there is no counter to reset.
	var existingWindowStart time.Time
	err = tx.QueryRow(ctx, `
		SELECT monthly_window_start FROM billing_usage
		WHERE user_id = $1
		FOR UPDATE
	`, userID).Scan(&existingWindowStart)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			_ = tx.Commit(ctx)
			return nil
		}
		return fmt.Errorf("monthly_reset: lock row: %w", err)
	}

	// Idempotency / out-of-order guard. If the stored window_start is
	// already at or after the proposed new windowStart, this reset
	// would either be a duplicate (same renewal applied twice) or an
	// out-of-order older event landing after a newer one. Either way,
	// no-op.
	newWindow := windowStart.UTC()
	if !newWindow.After(existingWindowStart.UTC()) {
		_ = tx.Commit(ctx)
		return nil
	}

	if _, err := tx.Exec(ctx, `
		UPDATE billing_usage SET
			llm_input_tokens_month        = 0,
			llm_output_tokens_month       = 0,
			llm_quota_blocked_count_month = 0,
			monthly_window_start          = $2,
			soft_cap_notified_at          = NULL
		WHERE user_id = $1
	`, userID, newWindow); err != nil {
		return fmt.Errorf("monthly_reset: %w", err)
	}

	if err := tx.Commit(ctx); err != nil {
		return fmt.Errorf("monthly_reset: commit: %w", err)
	}
	return nil
}

// PeekReservationOwner returns (user_id, tier) for a 'held' reservation
// without locking the row or modifying any state. Used by the gateway's
// handleCommit to resolve the per-tier soft-cap policy BEFORE calling
// CommitLLMTokens, so the in-tx test-and-set inside CommitLLMTokens
// can run atomically with the counter adjustment.
//
// Returns ("", "", nil) when the reservation is missing OR is no longer
// in 'held' status (already committed / refunded / reaped). The caller
// proceeds to CommitLLMTokens with softCapPercent=0 which short-circuits
// the test-and-set; the Commit itself remains idempotent.
//
// Audit ref: ADMIN-QUOTA-AUDIT-V3-A10.
func (s *UsageStore) PeekReservationOwner(
	ctx context.Context,
	reservationID string,
) (userID, tier string, err error) {
	if reservationID == "" {
		return "", "", fmt.Errorf("peek_reservation_owner: reservation_id is required")
	}
	err = s.db.QueryRow(ctx, `
		SELECT user_id, tier
		FROM billing_llm_reservations
		WHERE id = $1 AND status = 'held'
	`, reservationID).Scan(&userID, &tier)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return "", "", nil
		}
		return "", "", fmt.Errorf("peek_reservation_owner: %w", err)
	}
	return userID, tier, nil
}

// ---------------------------------------------------------------------------
// Time helpers (no time-zone surprises: we standardise on UTC).
// ---------------------------------------------------------------------------

// nextDailyReset returns the next 00:00 UTC after now.
func nextDailyReset(now time.Time) time.Time {
	u := now.UTC()
	return time.Date(u.Year(), u.Month(), u.Day(), 0, 0, 0, 0, time.UTC).Add(24 * time.Hour)
}

// nextMonthlyReset returns the next monthly anniversary of windowStart
// after now. If windowStart is the zero time (no row yet), defaults to
// the first of next month.
func nextMonthlyReset(windowStart time.Time) time.Time {
	now := time.Now().UTC()
	if windowStart.IsZero() {
		return time.Date(now.Year(), now.Month()+1, 1, 0, 0, 0, 0, time.UTC)
	}
	candidate := windowStart.UTC()
	for !candidate.After(now) {
		candidate = candidate.AddDate(0, 1, 0)
	}
	return candidate
}
