package symbolstore

import (
	"context"
	"strings"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/gateway/internal/config"
	"github.com/flamegreat/etradie/src/gateway/internal/constants"
	"github.com/flamegreat/etradie/src/gateway/internal/infra"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
)

const (
	activeSymbolsKey = "active_symbols"
	// 30-day TTL as safety net against orphaned keys.
	activeSymbolsTTL = 30 * 24 * time.Hour
)

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
// Priority: 1) Redis persisted selection, 2) config defaults.
func (s *Store) GetActiveSymbols(ctx context.Context) []string {
	raw, err := s.redis.Get(ctx, constants.GatewayCacheNamespace, activeSymbolsKey)
	if err != nil {
		s.log.Warn().Err(err).Msg("symbol_store_read_failed_using_defaults")
		return s.copyDefaults()
	}

	if raw == nil {
		s.log.Debug().
			Strs("symbols", s.defaultSymbols).
			Str("source", "gateway_config").
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
		Msg("symbol_store_loaded_user_selection")
	return symbols
}

// SetActiveSymbols persists the user's symbol selection.
func (s *Store) SetActiveSymbols(ctx context.Context, symbols []string) bool {
	if len(symbols) == 0 {
		s.log.Warn().Msg("symbol_store_set_called_with_empty_list")
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
		s.log.Warn().Msg("symbol_store_set_called_with_invalid_symbols")
		return false
	}

	err := s.redis.Set(ctx, constants.GatewayCacheNamespace, activeSymbolsKey, normalized, activeSymbolsTTL)
	if err != nil {
		s.log.Error().
			Strs("symbols", normalized).
			Err(err).
			Msg("symbol_store_write_failed")
		return false
	}

	s.log.Info().
		Strs("symbols", normalized).
		Msg("symbol_store_updated")
	return true
}

// ResetToDefaults clears the user selection so the next read falls back to defaults.
func (s *Store) ResetToDefaults(ctx context.Context) bool {
	err := s.redis.Delete(ctx, constants.GatewayCacheNamespace, activeSymbolsKey)
	if err != nil {
		s.log.Error().Err(err).Msg("symbol_store_reset_failed")
		return false
	}

	s.log.Info().Msg("symbol_store_reset_to_defaults")
	return true
}

func (s *Store) copyDefaults() []string {
	out := make([]string, len(s.defaultSymbols))
	copy(out, s.defaultSymbols)
	return out
}
