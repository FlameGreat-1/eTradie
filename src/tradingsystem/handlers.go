package tradingsystem

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"net/http"
	"strings"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
)

const (
	internalAuthHeader   = "X-Internal-Auth"
	internalUserIDHeader = "X-User-Id"
)

// Handler serves the trading-system REST API.
//
// The public surface is mounted under the standard authMiddleware +
// csrfMiddleware chain owned by the gateway HTTP server, identical
// to billing, support, and consent. The internal surface uses a
// constant-time HMAC check against the engine's shared secret.
type Handler struct {
	store          *Store
	internalSecret string
	log            zerolog.Logger
}

// NewHandler builds a Handler. internalSecret is the same value the
// engine sends in X-Internal-Auth; pass an empty string only in
// tests. A deployed gateway with an empty secret refuses every
// internal call (safe by default).
func NewHandler(store *Store, internalSecret string, log zerolog.Logger) *Handler {
	return &Handler{
		store:          store,
		internalSecret: strings.TrimSpace(internalSecret),
		log:            log,
	}
}

// RegisterRoutes mounts the public REST surface. The middleware chain
// matches the rest of the dashboard API (auth -> csrf -> handler).
func (h *Handler) RegisterRoutes(
	mux *http.ServeMux,
	authMiddleware func(http.Handler) http.Handler,
	csrfMiddleware func(http.Handler) http.Handler,
) {
	wrap := func(handler http.HandlerFunc) http.Handler {
		return authMiddleware(csrfMiddleware(http.HandlerFunc(handler)))
	}

	mux.Handle("/api/v1/trading-system", wrap(h.handleProfile))
	mux.Handle("/api/v1/trading-system/status", wrap(h.handleStatus))
	mux.Handle("/api/v1/trading-system/skip", wrap(h.handleSkip))
	mux.Handle("/api/v1/trading-system/reset", wrap(h.handleReset))
	mux.Handle("/api/v1/trading-system/schema", wrap(h.handleSchema))
}

// RegisterInternalRoutes mounts the engine-callable surface.
func (h *Handler) RegisterInternalRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/internal/trading-system/get", h.handleInternalGet)
}

// ---------------------------------------------------------------------------
// GET / PUT /api/v1/trading-system
// ---------------------------------------------------------------------------

func (h *Handler) handleProfile(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		h.getProfile(w, r)
	case http.MethodPut:
		h.putProfile(w, r)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (h *Handler) getProfile(w http.ResponseWriter, r *http.Request) {
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	rec, err := h.store.Get(r.Context(), userID)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			writeJSON(w, http.StatusOK, map[string]interface{}{
				"status":      string(StatusNone),
				"version":     0,
				"profile":     nil,
				"has_profile": false,
			})
			return
		}
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_system_get_failed")
		writeError(w, http.StatusInternalServerError, "failed to load trading system")
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":      string(rec.Status),
		"version":     rec.Version,
		"profile":     rec.Profile,
		"has_profile": rec.Profile != nil,
		"created_at":  rec.CreatedAt,
		"updated_at":  rec.UpdatedAt,
	})
}

func (h *Handler) putProfile(w http.ResponseWriter, r *http.Request) {
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	// 64 KB is generous for the worst-case 14-section profile (~5 KB)
	// and small enough to defeat trivial memory-exhaustion attempts.
	r.Body = http.MaxBytesReader(w, r.Body, 64*1024)

	var p Profile
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&p); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	if err := Validate(&p); err != nil {
		var verr *ValidationError
		if errors.As(err, &verr) {
			writeJSON(w, http.StatusUnprocessableEntity, map[string]interface{}{
				"error":  verr.Message,
				"fields": verr.Fields,
			})
			return
		}
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	rec, err := h.store.Save(r.Context(), userID, &p)
	if err != nil {
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_system_save_failed")
		writeError(w, http.StatusInternalServerError, "failed to save trading system")
		return
	}

	h.log.Info().
		Str("user_id", userID).
		Int("version", rec.Version).
		Str("style", string(p.Style)).
		Str("automation", string(p.Automation.Mode)).
		Msg("trading_system_saved")

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":      string(rec.Status),
		"version":     rec.Version,
		"profile":     rec.Profile,
		"has_profile": true,
		"created_at":  rec.CreatedAt,
		"updated_at":  rec.UpdatedAt,
	})
}

// ---------------------------------------------------------------------------
// GET /api/v1/trading-system/status
// ---------------------------------------------------------------------------

func (h *Handler) handleStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	view, err := h.store.GetStatus(r.Context(), userID)
	if err != nil {
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_system_status_failed")
		writeError(w, http.StatusInternalServerError, "failed to load status")
		return
	}
	writeJSON(w, http.StatusOK, view)
}

// ---------------------------------------------------------------------------
// POST /api/v1/trading-system/skip
// ---------------------------------------------------------------------------

func (h *Handler) handleSkip(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	view, err := h.store.Skip(r.Context(), userID)
	if err != nil {
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_system_skip_failed")
		writeError(w, http.StatusInternalServerError, "failed to skip")
		return
	}
	h.log.Info().Str("user_id", userID).Str("status", string(view.Status)).Msg("trading_system_skipped")
	writeJSON(w, http.StatusOK, view)
}

// ---------------------------------------------------------------------------
// POST /api/v1/trading-system/reset
// ---------------------------------------------------------------------------

func (h *Handler) handleReset(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	if err := h.store.Reset(r.Context(), userID); err != nil {
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_system_reset_failed")
		writeError(w, http.StatusInternalServerError, "failed to reset")
		return
	}
	h.log.Info().Str("user_id", userID).Msg("trading_system_reset")
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":      string(StatusNone),
		"version":     0,
		"has_profile": false,
	})
}

// ---------------------------------------------------------------------------
// GET /api/v1/trading-system/schema
//
// Closed-enum catalogue so the SPA never hardcodes option lists that
// drift from the Go source of truth.
// ---------------------------------------------------------------------------

func (h *Handler) handleSchema(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	writeJSON(w, http.StatusOK, schemaCatalogue())
}

func schemaCatalogue() map[string]interface{} {
	return map[string]interface{}{
		"schema_version": CurrentSchemaVersion,
		"identity": map[string]interface{}{
			"experience":    []string{string(ExperienceBeginner), string(ExperienceIntermediate), string(ExperienceAdvanced)},
			"automation":    []string{string(AutomationManual), string(AutomationSemiAutomated), string(AutomationFullyAutomated)},
			"risk_appetite": []string{string(RiskAppetiteConservative), string(RiskAppetiteBalanced), string(RiskAppetiteAggressive)},
			"trader_type":   []string{string(TraderTypePrecision), string(TraderTypeFrequent)},
			"discipline":    []string{string(DisciplineRuleBased), string(DisciplineFlexibleDiscretion)},
		},
		"style":            []string{string(StyleScalping), string(StyleIntraday), string(StyleSwing), string(StylePositional)},
		"sessions":         []string{string(SessionAsian), string(SessionLondon), string(SessionNewYork), string(SessionLondonNYOverlap)},
		"risk_model":       []string{string(RiskModelFixed), string(RiskModelAdaptive)},
		"confirmation":     []string{string(ConfirmationAggressive), string(ConfirmationBalanced), string(ConfirmationStrict)},
		"frameworks":       []string{string(FrameworkSMC), string(FrameworkSnD), string(FrameworkWyckoff), string(FrameworkLiquidity)},
		"entry_mode":       []string{string(EntryLimitOnly), string(EntryMarketAllowed), string(EntryEitherAllowed)},
		"automation_modes": []string{string(AutoAlertOnly), string(AutoManualApproval), string(AutoSemiAutomatic), string(AutoFullyAutomatic)},
		"asset_class":      []string{string(AssetForex), string(AssetIndices), string(AssetGold), string(AssetCrypto), string(AssetVolatilityIndices)},
		"goal":             []string{string(GoalCapitalPreservation), string(GoalConsistency), string(GoalAggressiveGrowth), string(GoalLowStress), string(GoalHighProbabilityOnly), string(GoalFewerHighQuality)},
		"partial_tp":       []string{string(PartialTPDisabled), string(PartialTPAggressive), string(PartialTPBalanced), string(PartialTPLetRun)},
		"trailing_stop":    []string{string(TrailingDisabled), string(TrailingStructure), string(TrailingATR), string(TrailingFixed)},
		"break_even":       []string{string(BETriggerDisabled), string(BETriggerAtTP1), string(BETriggerAt1RR), string(BETriggerAtMidpoint)},
		"emphasis":         []string{"low", "medium", "high"},
		"limits": map[string]interface{}{
			"fixed_risk_percent":          map[string]float64{"min": 0.1, "max": 3.0},
			"max_daily_drawdown_percent":  map[string]float64{"min": 1.0, "max": 10.0},
			"max_weekly_drawdown_percent": map[string]float64{"min": 2.0, "max": 20.0},
			"max_simultaneous_trades":     map[string]int{"min": 1, "max": 10},
			"max_correlated_exposure":     map[string]int{"min": 1, "max": 5},
			"minimum_rr":                  map[string]float64{"min": 1.0, "max": 10.0},
			"max_losses_before_cooldown":  map[string]int{"min": 0, "max": 10},
			"confluence_weight":           map[string]int{"min": 0, "max": 3},
		},
	}
}

// ---------------------------------------------------------------------------
// Internal: POST /internal/trading-system/get
// ---------------------------------------------------------------------------

type internalGetRequest struct {
	UserID string `json:"user_id"`
}

func (h *Handler) handleInternalGet(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.verifyInternalSecret(r) {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	userID := strings.TrimSpace(r.Header.Get(internalUserIDHeader))
	if userID == "" {
		var body internalGetRequest
		if r.ContentLength > 0 {
			_ = json.NewDecoder(r.Body).Decode(&body)
		}
		userID = strings.TrimSpace(body.UserID)
	}
	if userID == "" {
		writeError(w, http.StatusBadRequest, "user_id is required")
		return
	}

	rec, err := h.store.Get(r.Context(), userID)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			writeJSON(w, http.StatusOK, map[string]interface{}{
				"user_id":     userID,
				"status":      string(StatusNone),
				"version":     0,
				"profile":     nil,
				"has_profile": false,
			})
			return
		}
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_system_internal_get_failed")
		writeError(w, http.StatusInternalServerError, "failed to load trading system")
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"user_id":     rec.UserID,
		"status":      string(rec.Status),
		"version":     rec.Version,
		"profile":     rec.Profile,
		"has_profile": rec.Profile != nil,
		"updated_at":  rec.UpdatedAt,
	})
}

// verifyInternalSecret performs a constant-time comparison of the
// X-Internal-Auth header against the configured shared secret. An
// unconfigured secret always returns false so a misconfigured
// gateway never exposes the internal surface.
func (h *Handler) verifyInternalSecret(r *http.Request) bool {
	if h.internalSecret == "" {
		return false
	}
	provided := strings.TrimSpace(r.Header.Get(internalAuthHeader))
	if provided == "" {
		return false
	}
	want := sha256.Sum256([]byte(h.internalSecret))
	got := sha256.Sum256([]byte(provided))
	wantHex := hex.EncodeToString(want[:])
	gotHex := hex.EncodeToString(got[:])
	return hmac.Equal([]byte(wantHex), []byte(gotHex))
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func writeJSON(w http.ResponseWriter, status int, body interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
