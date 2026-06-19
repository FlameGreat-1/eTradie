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
//
// SYMBOL SOURCE INVARIANT: the active-symbol set is sourced EXCLUSIVELY
// from the user's own broker. A symbol only ever enters this store via
// SetActiveSymbols, which the API layer gates against the connected
// broker's catalogue (api_handlers.go::validateAgainstBrokerCatalog).
// There is NO operator-seeded default basket: a user who has not
// selected any symbol (e.g. before completing the broker-connect step
// of onboarding) has an empty active set, and every read path returns
// an empty list rather than a hardcoded fallback. This mirrors the SPA
// chart hook (useActiveSymbol), which likewise never falls back to
// gateway defaults, and keeps the whole platform honest about the fact
// that broker symbol names vary per broker (EURUSD vs EURUSDm vs
// EURUSD.x) and cannot be guessed by the gateway.
type Store struct {
	redis *infra.RedisClient
	log   zerolog.Logger
}

// NewStore creates a SymbolStore backed by Redis.
//
// The cfg argument is accepted but currently unused: the store no
// longer carries any operator-seeded default symbols. It is retained
// on the signature for one commit to keep this change isolated; a
// follow-up wiring commit drops it from both this signature and every
// call site.
func NewStore(redis *infra.RedisClient, _ *config.Config) *Store {
	return &Store{
		redis: redis,
		log:   observability.Logger("symbol_store"),
	}
}

// GetActiveSymbols returns the user's active symbols as selected from
// their connected broker's catalogue and persisted in Redis.
//
// When the user has made no selection (missing key, Redis read error,
// or an empty/whitespace-only persisted value) this returns an EMPTY
// slice — never a hardcoded default. An empty result is the correct,
// honest state for a user who has not yet connected a broker and
// resolved a symbol; callers (the scheduler, the run-cycle endpoint)
// treat it as "nothing to do" rather than analysing an arbitrary
// basket. The returned slice is always non-nil so JSON serialisation
// yields "symbols":[] rather than "symbols":null.
//
// userID must be non-empty; callers must extract it from auth context.
func (s *Store) GetActiveSymbols(ctx context.Context, userID string) []string {
	empty := []string{}

	if userID == "" {
		s.log.Warn().Msg("symbol_store_get_called_without_user_id")
		return empty
	}

	key := activeSymbolsKey(userID)
	raw, err := s.redis.Get(ctx, constants.GatewayCacheNamespace, key)
	if err != nil {
		s.log.Warn().Err(err).Str("user_id", userID).Msg("symbol_store_read_failed")
		return empty
	}

	if raw == nil {
		s.log.Debug().
			Str("user_id", userID).
			Msg("symbol_store_no_selection")
		return empty
	}

	// raw is interface{} from JSON unmarshal; expect []interface{}.
	slice, ok := raw.([]interface{})
	if !ok || len(slice) == 0 {
		return empty
	}

	symbols := make([]string, 0, len(slice))
	for _, v := range slice {
		str, ok := v.(string)
		if ok && strings.TrimSpace(str) != "" {
			symbols = append(symbols, strings.TrimSpace(str))
		}
	}

	if len(symbols) == 0 {
		return empty
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

	normalized := make([]string, 0, len(symbols))
	for _, sym := range symbols {
		trimmed := strings.TrimSpace(sym)
		if trimmed != "" {
			normalized = append(normalized, strings.ToUpper(trimmed))
		}
	}

	// Reject a selection that contains no usable symbol (empty input or
	// only blank/whitespace entries) without writing to Redis, so the
	// caller can surface a validation error instead of persisting an
	// empty set.
	if len(normalized) == 0 {
		s.log.Warn().Str("user_id", userID).Msg("symbol_store_set_rejected_empty_selection")
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

// ClearSelection removes the user's persisted symbol selection. After
// this call the next GetActiveSymbols returns an empty list until the
// user selects a symbol from their broker catalogue again.
//
// This replaces the former ResetToDefaults: there are no operator
// defaults to reset to, so "reset" now means "forget my customisation".
// userID must be non-empty; callers must extract it from auth context.
func (s *Store) ClearSelection(ctx context.Context, userID string) bool {
	if userID == "" {
		s.log.Warn().Msg("symbol_store_clear_called_without_user_id")
		return false
	}

	key := activeSymbolsKey(userID)
	err := s.redis.Delete(ctx, constants.GatewayCacheNamespace, key)
	if err != nil {
		s.log.Error().Err(err).Str("user_id", userID).Msg("symbol_store_clear_failed")
		return false
	}

	s.log.Info().Str("user_id", userID).Msg("symbol_store_selection_cleared")
	return true
}
