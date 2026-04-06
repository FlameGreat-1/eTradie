package settingsstore

import (
	"context"
	"encoding/json"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
)

const (
	// 90-day TTL as safety net. Dashboard settings are long-lived.
	settingsTTL = 90 * 24 * time.Hour
)

// settingsKey returns the user-scoped Redis key for runtime settings.
// Each user has their own settings in multi-tenant mode.
func settingsKey(userID string) string {
	return "user:" + userID + ":runtime_settings"
}

// Settings holds all dashboard-configurable runtime overrides.
// Only fields with non-zero values are treated as overrides.
// Zero-value fields mean "use the env var default".
type Settings struct {
	CycleIntervalSeconds int `json:"cycle_interval_seconds,omitempty"`
}

// Store is a Redis-backed store for runtime-configurable gateway settings.
// These settings are changed by the dashboard and must survive restarts.
type Store struct {
	redis *infra.RedisClient
	log   zerolog.Logger
}

// NewStore creates a SettingsStore backed by Redis.
func NewStore(redis *infra.RedisClient) *Store {
	return &Store{
		redis: redis,
		log:   observability.Logger("settings_store"),
	}
}

// Load reads the persisted runtime settings from Redis for the given user.
// Returns an empty Settings (all zero values) if nothing is persisted.
// userID must be non-empty; callers must extract it from auth context.
func (s *Store) Load(ctx context.Context, userID string) *Settings {
	if userID == "" {
		s.log.Warn().Msg("settings_store_load_called_without_user_id")
		return &Settings{}
	}

	key := settingsKey(userID)
	raw, err := s.redis.Get(ctx, constants.GatewayCacheNamespace, key)
	if err != nil {
		s.log.Warn().Err(err).Str("user_id", userID).Msg("settings_store_read_failed")
		return &Settings{}
	}
	if raw == nil {
		s.log.Debug().Str("user_id", userID).Msg("settings_store_no_overrides_persisted")
		return &Settings{}
	}

	// Re-marshal from interface{} to JSON bytes, then unmarshal into Settings.
	rawJSON, err := json.Marshal(raw)
	if err != nil {
		s.log.Warn().Err(err).Str("user_id", userID).Msg("settings_store_remarshal_error")
		return &Settings{}
	}

	var settings Settings
	if err := json.Unmarshal(rawJSON, &settings); err != nil {
		s.log.Warn().Err(err).Str("user_id", userID).Msg("settings_store_unmarshal_error")
		return &Settings{}
	}

	s.log.Info().
		Int("cycle_interval_seconds", settings.CycleIntervalSeconds).
		Str("user_id", userID).
		Msg("settings_store_loaded_overrides")
	return &settings
}

// Save persists the runtime settings to Redis for the given user.
// userID must be non-empty; callers must extract it from auth context.
func (s *Store) Save(ctx context.Context, userID string, settings *Settings) error {
	if userID == "" {
		s.log.Warn().Msg("settings_store_save_called_without_user_id")
		return nil
	}

	key := settingsKey(userID)
	err := s.redis.Set(ctx, constants.GatewayCacheNamespace, key, settings, settingsTTL)
	if err != nil {
		s.log.Error().Err(err).Str("user_id", userID).Msg("settings_store_write_failed")
		return err
	}

	s.log.Info().
		Int("cycle_interval_seconds", settings.CycleIntervalSeconds).
		Str("user_id", userID).
		Msg("settings_store_saved")
	return nil
}

// SetCycleInterval updates just the cycle interval in the persisted settings.
// Loads current settings, updates the field, and saves back.
// userID must be non-empty; callers must extract it from auth context.
func (s *Store) SetCycleInterval(ctx context.Context, userID string, intervalSeconds int) error {
	settings := s.Load(ctx, userID)
	settings.CycleIntervalSeconds = intervalSeconds
	return s.Save(ctx, userID, settings)
}

// GetCycleInterval returns the persisted cycle interval override for the given user.
// Returns 0 if no override is set (caller should use env var default).
// userID must be non-empty; callers must extract it from auth context.
func (s *Store) GetCycleInterval(ctx context.Context, userID string) int {
	settings := s.Load(ctx, userID)
	return settings.CycleIntervalSeconds
}
