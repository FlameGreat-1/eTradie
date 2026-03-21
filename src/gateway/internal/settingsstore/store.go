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
	settingsKey = "runtime_settings"
	// 90-day TTL as safety net. Dashboard settings are long-lived.
	settingsTTL = 90 * 24 * time.Hour
)

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

// Load reads the persisted runtime settings from Redis.
// Returns an empty Settings (all zero values) if nothing is persisted.
func (s *Store) Load(ctx context.Context) *Settings {
	raw, err := s.redis.Get(ctx, constants.GatewayCacheNamespace, settingsKey)
	if err != nil {
		s.log.Warn().Err(err).Msg("settings_store_read_failed")
		return &Settings{}
	}
	if raw == nil {
		s.log.Debug().Msg("settings_store_no_overrides_persisted")
		return &Settings{}
	}

	// Re-marshal from interface{} to JSON bytes, then unmarshal into Settings.
	rawJSON, err := json.Marshal(raw)
	if err != nil {
		s.log.Warn().Err(err).Msg("settings_store_remarshal_error")
		return &Settings{}
	}

	var settings Settings
	if err := json.Unmarshal(rawJSON, &settings); err != nil {
		s.log.Warn().Err(err).Msg("settings_store_unmarshal_error")
		return &Settings{}
	}

	s.log.Info().
		Int("cycle_interval_seconds", settings.CycleIntervalSeconds).
		Msg("settings_store_loaded_overrides")
	return &settings
}

// Save persists the runtime settings to Redis.
func (s *Store) Save(ctx context.Context, settings *Settings) error {
	err := s.redis.Set(ctx, constants.GatewayCacheNamespace, settingsKey, settings, settingsTTL)
	if err != nil {
		s.log.Error().Err(err).Msg("settings_store_write_failed")
		return err
	}

	s.log.Info().
		Int("cycle_interval_seconds", settings.CycleIntervalSeconds).
		Msg("settings_store_saved")
	return nil
}

// SetCycleInterval updates just the cycle interval in the persisted settings.
// Loads current settings, updates the field, and saves back.
func (s *Store) SetCycleInterval(ctx context.Context, intervalSeconds int) error {
	settings := s.Load(ctx)
	settings.CycleIntervalSeconds = intervalSeconds
	return s.Save(ctx, settings)
}

// GetCycleInterval returns the persisted cycle interval override.
// Returns 0 if no override is set (caller should use env var default).
func (s *Store) GetCycleInterval(ctx context.Context) int {
	settings := s.Load(ctx)
	return settings.CycleIntervalSeconds
}
