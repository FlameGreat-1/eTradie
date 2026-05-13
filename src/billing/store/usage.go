package store

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
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
	db *pgxpool.Pool
}

func NewUsageStore(db *pgxpool.Pool) *UsageStore {
	return &UsageStore{db: db}
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
	if !policy.HasLLMAccess() {
		return "", &QuotaExceededError{
			Dimension: "daily_input",
			Limit:     0,
			Used:      0,
			Requested: estimatedInput,
			ResetsAt:  nextDailyReset(time.Now().UTC()),
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
		return "", s.recordBlocked(ctx, tx, userID, err)
	}
	if err := checkCap("daily_output", outputToday, maxOutput, policy.DailyOutputTokens, dailyResetAt); err != nil {
		return "", s.recordBlocked(ctx, tx, userID, err)
	}
	if err := checkCap("monthly_input", inputMonth, estimatedInput, policy.MonthlyInputTokens, monthlyResetAt); err != nil {
		return "", s.recordBlocked(ctx, tx, userID, err)
	}
	if err := checkCap("monthly_output", outputMonth, maxOutput, policy.MonthlyOutputTokens, monthlyResetAt); err != nil {
		return "", s.recordBlocked(ctx, tx, userID, err)
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

// recordBlocked increments the per-window blocked-count audit counters
// and commits the tx so the blocked counter is durable even though the
// reservation itself is rejected. Returns qerr unchanged for chaining.
func (s *UsageStore) recordBlocked(ctx context.Context, tx pgx.Tx, userID string, qerr error) error {
	_, _ = tx.Exec(ctx, `
		UPDATE billing_usage SET
			llm_quota_blocked_count_today = llm_quota_blocked_count_today + 1,
			llm_quota_blocked_count_month = llm_quota_blocked_count_month + 1
		WHERE user_id = $1
	`, userID)
	_ = tx.Commit(ctx)
	return qerr
}

// CommitLLMTokens settles a held reservation with the real token counts
// returned by the LLM. The over-reservation on the output side
// (max_output_tokens - actual_output_tokens) is rolled back; the input
// side is corrected for the (rare) case where the tokeniser estimate
// diverged from the model's count.
//
// Idempotent: re-committing an already-committed reservation is a
// no-op so an at-least-once retry from the engine cannot double-charge.
func (s *UsageStore) CommitLLMTokens(
	ctx context.Context,
	reservationID string,
	actualInput, actualOutput int64,
) error {
	if reservationID == "" {
		return fmt.Errorf("commit_llm_tokens: reservation_id is required")
	}
	if actualInput < 0 || actualOutput < 0 {
		return fmt.Errorf("commit_llm_tokens: token counts must be non-negative")
	}

	tx, err := s.db.BeginTx(ctx, pgx.TxOptions{IsoLevel: pgx.ReadCommitted})
	if err != nil {
		return fmt.Errorf("commit_llm_tokens: begin tx: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	now := time.Now().UTC()

	var (
		userID                    string
		estimatedInput, maxOutput int64
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
			return nil
		}
		return fmt.Errorf("commit_llm_tokens: update reservation: %w", err)
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
		return fmt.Errorf("commit_llm_tokens: adjust counters: %w", err)
	}

	return tx.Commit(ctx)
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

// GetLLMUsageSnapshot returns the SPA-facing usage shape for one user.
// The policy is supplied by the caller (gateway boundary) and merged in
// so the SPA can compute remaining/used percentages without doing math
// on potentially-stale environment knobs.
func (s *UsageStore) GetLLMUsageSnapshot(
	ctx context.Context,
	userID string,
	policy LLMQuotaPolicy,
) (*LLMUsageSnapshot, error) {
	if userID == "" {
		return nil, fmt.Errorf("get_llm_usage_snapshot: user_id is required")
	}
	now := time.Now().UTC()

	// Same conditional daily-reset trick as the reservation path so a
	// snapshot taken at 00:01 reflects today's empty counters even if
	// the user has not transacted since yesterday.
	var snap LLMUsageSnapshot
	err := s.db.QueryRow(ctx, `
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
		          llm_quota_blocked_count_today, llm_quota_blocked_count_month,
		          monthly_window_start, llm_last_metered_at
	`, userID, now).Scan(
		&snap.InputTokensToday, &snap.OutputTokensToday,
		&snap.InputTokensMonth, &snap.OutputTokensMonth,
		&snap.BlockedToday, &snap.BlockedMonth,
		&snap.MonthlyWindowStart, &snap.LastMeteredAt,
	)
	if err != nil {
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
func (s *UsageStore) MonthlyReset(ctx context.Context, userID string, windowStart time.Time) error {
	if userID == "" {
		return fmt.Errorf("monthly_reset: user_id is required")
	}
	_, err := s.db.Exec(ctx, `
		UPDATE billing_usage SET
			llm_input_tokens_month        = 0,
			llm_output_tokens_month       = 0,
			llm_quota_blocked_count_month = 0,
			monthly_window_start          = $2,
			soft_cap_notified_at          = NULL
		WHERE user_id = $1
	`, userID, windowStart.UTC())
	if err != nil {
		return fmt.Errorf("monthly_reset: %w", err)
	}
	return nil
}

// MarkSoftCapNotifiedIfCrossed performs a one-shot test-and-set inside
// a single atomic UPDATE: returns (true, nil) the first time the user's
// current-window monthly usage crosses softCapPercent of either the
// input or output cap; returns (false, nil) on every subsequent call
// until MonthlyReset clears soft_cap_notified_at.
//
// The handler calls this immediately after a successful Reserve and
// fires the warning email when the return is true. The test-and-set
// happens entirely in SQL so two parallel reserve calls from the same
// user cannot both observe "just crossed" and double-fire the email
// (PostgreSQL serialises the UPDATE on the row's MVCC version).
//
// Inputs:
//
//	softCapPercent       : 0..100. Values <= 0 disable the check
//	                       (returns false, nil) so a tier without a
//	                       configured soft cap never triggers a notice.
//	monthlyInputLimit    : tier policy cap on input tokens this window.
//	                       Values <= 0 disable the input-side trigger.
//	monthlyOutputLimit   : same, for output tokens.
//
// The threshold is computed as ceil(limit * pct / 100) so a soft cap of
// 80% on a 20,000,000 input cap fires at exactly 16,000,000 tokens, not
// at 15,999,999.
func (s *UsageStore) MarkSoftCapNotifiedIfCrossed(
	ctx context.Context,
	userID string,
	softCapPercent int,
	monthlyInputLimit, monthlyOutputLimit int64,
) (bool, error) {
	if userID == "" {
		return false, fmt.Errorf("mark_soft_cap_notified: user_id is required")
	}
	if softCapPercent <= 0 || softCapPercent > 100 {
		return false, nil
	}
	if monthlyInputLimit <= 0 && monthlyOutputLimit <= 0 {
		return false, nil
	}

	// ceilDiv computes ⌈a * pct / 100⌉ without floating-point error.
	ceilDiv := func(limit int64, pct int) int64 {
		if limit <= 0 {
			return 0
		}
		num := limit * int64(pct)
		return (num + 99) / 100
	}
	inputThreshold := ceilDiv(monthlyInputLimit, softCapPercent)
	outputThreshold := ceilDiv(monthlyOutputLimit, softCapPercent)

	var firedAt *time.Time
	err := s.db.QueryRow(ctx, `
		UPDATE billing_usage
		SET soft_cap_notified_at = NOW()
		WHERE user_id = $1
		  AND soft_cap_notified_at IS NULL
		  AND (
		       ($2 > 0 AND llm_input_tokens_month  >= $2)
		    OR ($3 > 0 AND llm_output_tokens_month >= $3)
		  )
		RETURNING soft_cap_notified_at
	`, userID, inputThreshold, outputThreshold).Scan(&firedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return false, nil
		}
		return false, fmt.Errorf("mark_soft_cap_notified: %w", err)
	}
	return firedAt != nil, nil
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
