package store

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
)

const (
	settingsReadTimeout  = 3 * time.Second
	settingsWriteTimeout = 3 * time.Second
)

const upsertSettingSQL = `
INSERT INTO execution_settings (user_id, key, value, updated_at)
VALUES ($1, $2, $3, NOW())
ON CONFLICT (user_id, key)
DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
`

const selectAllSettingsSQL = `
SELECT key, value FROM execution_settings WHERE user_id = $1
`

const selectSettingSQL = `
SELECT value FROM execution_settings WHERE user_id = $1 AND key = $2
`

// Setting keys.
const (
	KeyExecutionMode       = "execution_mode"
	KeyMaxConcurrentTrades = "max_concurrent_trades"
	KeyDailyLossLimitPct   = "daily_loss_limit_pct"
	KeyWeeklyDrawdownPct   = "weekly_drawdown_pct"
)

// Settings holds all dashboard-configurable execution parameters.
type Settings struct {
	ExecutionMode       string  `json:"execution_mode"`
	MaxConcurrentTrades int     `json:"max_concurrent_trades"`
	DailyLossLimitPct   float64 `json:"daily_loss_limit_pct"`
	WeeklyDrawdownPct   float64 `json:"weekly_drawdown_pct"`
}

// SettingsStore handles PostgreSQL persistence for runtime-configurable
// execution settings. The dashboard reads and writes settings via the
// HTTP API; the execution pipeline reads them on every trade.
type SettingsStore struct {
	pool *pgxpool.Pool
	log  zerolog.Logger
}

// NewSettingsStore creates a settings store backed by the given pgx pool.
func NewSettingsStore(pool *pgxpool.Pool) *SettingsStore {
	return &SettingsStore{
		pool: pool,
		log:  observability.Logger("settings_store"),
	}
}

// LoadAll reads all settings from PostgreSQL and returns them merged
// with the provided defaults. DB values take precedence over defaults.
func (s *SettingsStore) LoadAll(ctx context.Context, userID string, defaults Settings) (*Settings, error) {
	readCtx, cancel := context.WithTimeout(ctx, settingsReadTimeout)
	defer cancel()

	result := defaults

	rows, err := s.pool.Query(readCtx, selectAllSettingsSQL, userID)
	if err != nil {
		return &result, fmt.Errorf("settings: load all: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var key, value string
		if err := rows.Scan(&key, &value); err != nil {
			s.log.Error().Err(err).Msg("settings_row_scan_failed")
			continue
		}
		applySetting(&result, key, value, s.log)
	}

	if err := rows.Err(); err != nil {
		return &result, fmt.Errorf("settings: iterate rows: %w", err)
	}

	s.log.Info().
		Str("execution_mode", result.ExecutionMode).
		Int("max_concurrent_trades", result.MaxConcurrentTrades).
		Float64("daily_loss_limit_pct", result.DailyLossLimitPct).
		Float64("weekly_drawdown_pct", result.WeeklyDrawdownPct).
		Msg("settings_loaded")

	return &result, nil
}

// Get reads a single setting value from PostgreSQL.
func (s *SettingsStore) Get(ctx context.Context, userID string, key string) (string, error) {
	readCtx, cancel := context.WithTimeout(ctx, settingsReadTimeout)
	defer cancel()

	var value string
	err := s.pool.QueryRow(readCtx, selectSettingSQL, userID, key).Scan(&value)
	if err != nil {
		return "", fmt.Errorf("settings: get %s: %w", key, err)
	}
	return value, nil
}

// Set writes a single setting to PostgreSQL (UPSERT).
func (s *SettingsStore) Set(ctx context.Context, userID string, key, value string) error {
	if err := validateSetting(key, value); err != nil {
		return err
	}

	writeCtx, cancel := context.WithTimeout(ctx, settingsWriteTimeout)
	defer cancel()

	_, err := s.pool.Exec(writeCtx, upsertSettingSQL, userID, key, value)
	if err != nil {
		s.log.Error().Err(err).Str("key", key).Str("value", value).Msg("setting_write_failed")
		return fmt.Errorf("settings: set %s: %w", key, err)
	}

	s.log.Info().Str("key", key).Str("value", value).Msg("setting_updated")
	return nil
}

// SaveAll writes all settings to PostgreSQL in a single transaction.
func (s *SettingsStore) SaveAll(ctx context.Context, userID string, settings *Settings) error {
	writeCtx, cancel := context.WithTimeout(ctx, settingsWriteTimeout)
	defer cancel()

	tx, err := s.pool.Begin(writeCtx)
	if err != nil {
		return fmt.Errorf("settings: begin tx: %w", err)
	}
	defer tx.Rollback(writeCtx)

	pairs := map[string]string{
		KeyExecutionMode:       strings.ToUpper(settings.ExecutionMode),
		KeyMaxConcurrentTrades: strconv.Itoa(settings.MaxConcurrentTrades),
		KeyDailyLossLimitPct:   strconv.FormatFloat(settings.DailyLossLimitPct, 'f', 2, 64),
		KeyWeeklyDrawdownPct:   strconv.FormatFloat(settings.WeeklyDrawdownPct, 'f', 2, 64),
	}

	for k, v := range pairs {
		if err := validateSetting(k, v); err != nil {
			return err
		}
		if _, err := tx.Exec(writeCtx, upsertSettingSQL, userID, k, v); err != nil {
			return fmt.Errorf("settings: save %s: %w", k, err)
		}
	}

	if err := tx.Commit(writeCtx); err != nil {
		return fmt.Errorf("settings: commit: %w", err)
	}

	s.log.Info().
		Str("execution_mode", settings.ExecutionMode).
		Int("max_concurrent_trades", settings.MaxConcurrentTrades).
		Msg("settings_saved")

	return nil
}

func validateSetting(key, value string) error {
	switch key {
	case KeyExecutionMode:
		v := strings.ToUpper(value)
		if v != "LIMIT" && v != "INSTANT" && v != "AUTO" {
			return fmt.Errorf("settings: %s must be LIMIT, INSTANT, or AUTO, got %q", key, value)
		}
	case KeyMaxConcurrentTrades:
		n, err := strconv.Atoi(value)
		if err != nil || n < 1 || n > 10 {
			return fmt.Errorf("settings: %s must be 1..10, got %q", key, value)
		}
	case KeyDailyLossLimitPct:
		f, err := strconv.ParseFloat(value, 64)
		if err != nil || f < 0.5 || f > 10.0 {
			return fmt.Errorf("settings: %s must be 0.5..10.0, got %q", key, value)
		}
	case KeyWeeklyDrawdownPct:
		f, err := strconv.ParseFloat(value, 64)
		if err != nil || f < 1.0 || f > 20.0 {
			return fmt.Errorf("settings: %s must be 1.0..20.0, got %q", key, value)
		}
	default:
		return fmt.Errorf("settings: unknown key %q", key)
	}
	return nil
}

func applySetting(s *Settings, key, value string, log zerolog.Logger) {
	switch key {
	case KeyExecutionMode:
		s.ExecutionMode = strings.ToUpper(value)
	case KeyMaxConcurrentTrades:
		if n, err := strconv.Atoi(value); err == nil {
			s.MaxConcurrentTrades = n
		} else {
			log.Warn().Str("key", key).Str("value", value).Msg("invalid_setting_value")
		}
	case KeyDailyLossLimitPct:
		if f, err := strconv.ParseFloat(value, 64); err == nil {
			s.DailyLossLimitPct = f
		} else {
			log.Warn().Str("key", key).Str("value", value).Msg("invalid_setting_value")
		}
	case KeyWeeklyDrawdownPct:
		if f, err := strconv.ParseFloat(value, 64); err == nil {
			s.WeeklyDrawdownPct = f
		} else {
			log.Warn().Str("key", key).Str("value", value).Msg("invalid_setting_value")
		}
	}
}
