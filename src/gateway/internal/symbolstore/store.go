package symbolstore

import (
	"context"
	"strings"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
)

const (
	// 30-day TTL as safety net against orphaned keys.
	activeSymbolsTTL = 30 * 24 * time.Hour
)

// activeSymbolsKey returns the user-scoped Redis key for active symbols.
// Each user has their own symbol selection in multi-tenant mode.
func activeSymbolsKey(userID string) string {
	return "user:" + userID + ":active_symbols"
}

// Store is a Redis-backed store for the user's active symbol selection.
type Store struct {
	redis          *infra.RedisClient
	defaultSymbols []string
	log            zerolog.Logger
}

// NewStore creates a SymbolStore backed by Redis.
func NewStore(redis *infra.RedisClient, cfg *config.Config) *Store {
	return &Store{
		redis:          redis,
		defaultSymbols: cfg.DefaultSymbols,
		log:            observability.Logger("symbol_store"),
	}
}

// GetActiveSymbols returns the user's active symbols.
// Priority: 1) Redis persisted selection for this user, 2) config defaults.
// userID must be non-empty; callers must extract it from auth context.
func (s *Store) GetActiveSymbols(ctx context.Context, userID string) []string {
	if userID == "" {
		s.log.Warn().Msg("symbol_store_get_called_without_user_id_using_defaults")
		return s.copyDefaults()
	}

	key := activeSymbolsKey(userID)
	raw, err := s.redis.Get(ctx, constants.GatewayCacheNamespace, key)
	if err != nil {
		s.log.Warn().Err(err).Str("user_id", userID).Msg("symbol_store_read_failed_using_defaults")
		return s.copyDefaults()
	}

	if raw == nil {
		s.log.Debug().
			Strs("symbols", s.defaultSymbols).
			Str("source", "gateway_config").
			Str("user_id", userID).
			Msg("symbol_store_using_defaults")
		return s.copyDefaults()
	}

	// raw is interface{} from JSON unmarshal; expect []interface{}.
	slice, ok := raw.([]interface{})
	if !ok || len(slice) == 0 {
		return s.copyDefaults()
	}

	symbols := make([]string, 0, len(slice))
	for _, v := range slice {
		str, ok := v.(string)
		if ok && strings.TrimSpace(str) != "" {
			symbols = append(symbols, strings.ToUpper(strings.TrimSpace(str)))
		}
	}

	if len(symbols) == 0 {
		return s.copyDefaults()
	}

	s.log.Debug().
		Strs("symbols", symbols).
		Str("source", "redis").
		Str("user_id", userID).
		Msg("symbol_store_loaded_user_selection")
	return symbols
}

// SetActiveSymbols persists the user's symbol selection.
// userID must be non-empty; callers must extract it from auth context.
func (s *Store) SetActiveSymbols(ctx context.Context, userID string, symbols []string) bool {
	if userID == "" {
		s.log.Warn().Msg("symbol_store_set_called_without_user_id")
		return false
	}

	if len(symbols) == 0 {
		s.log.Warn().Str("user_id", userID).Msg("symbol_store_set_called_with_empty_list")
		return false
	}

	normalized := make([]string, 0, len(symbols))
	for _, sym := range symbols {
		trimmed := strings.TrimSpace(sym)
		if trimmed != "" {
			normalized = append(normalized, strings.ToUpper(trimmed))
		}
	}

	if len(normalized) == 0 {
		s.log.Warn().Str("user_id", userID).Msg("symbol_store_set_called_with_invalid_symbols")
		return false
	}

	key := activeSymbolsKey(userID)
	err := s.redis.Set(ctx, constants.GatewayCacheNamespace, key, normalized, activeSymbolsTTL)
	if err != nil {
		s.log.Error().
			Strs("symbols", normalized).
			Str("user_id", userID).
			Err(err).
			Msg("symbol_store_write_failed")
		return false
	}

	s.log.Info().
		Strs("symbols", normalized).
		Str("user_id", userID).
		Msg("symbol_store_updated")
	return true
}

// ResetToDefaults clears the user selection so the next read falls back to defaults.
// userID must be non-empty; callers must extract it from auth context.
func (s *Store) ResetToDefaults(ctx context.Context, userID string) bool {
	if userID == "" {
		s.log.Warn().Msg("symbol_store_reset_called_without_user_id")
		return false
	}

	key := activeSymbolsKey(userID)
	err := s.redis.Delete(ctx, constants.GatewayCacheNamespace, key)
	if err != nil {
		s.log.Error().Err(err).Str("user_id", userID).Msg("symbol_store_reset_failed")
		return false
	}

	s.log.Info().Str("user_id", userID).Msg("symbol_store_reset_to_defaults")
	return true
}

// DefaultSymbols returns a copy of the configured default symbols.
// Used by the scheduler when no user context is available.
func (s *Store) DefaultSymbols() []string {
	return s.copyDefaults()
}

func (s *Store) copyDefaults() []string {
	out := make([]string, len(s.defaultSymbols))
	copy(out, s.defaultSymbols)
	return out
}
