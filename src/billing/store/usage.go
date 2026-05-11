package store

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

type UsageStore struct {
	db *pgxpool.Pool
}

func NewUsageStore(db *pgxpool.Pool) *UsageStore {
	return &UsageStore{db: db}
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
