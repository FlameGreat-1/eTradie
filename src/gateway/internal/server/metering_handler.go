package server

import (
	"context"
	"crypto/hmac"
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	billingstore "github.com/flamegreat-1/etradie/src/billing/store"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/mails"
)

// MeteringHandler exposes:
//
//   - the internal Reserve / Commit / Refund trio that the Python
//     engine calls before, after, and on-failure of every Pro-Managed
//     LLM call. Mounted on /internal/metering/* and authenticated
//     with the same shared secret used by the engine's other
//     /internal/* surfaces.
//
//   - the user-facing GET /api/v1/billing/usage that returns a
//     read-only snapshot for the SPA's usage panel. Mounted behind
//     the gateway's auth + CSRF middleware.
//
// The shared secret is constant-time-compared against the
// X-Internal-Auth header on every internal call. Failure paths are
// uniform (401 "unauthorized") so a probe cannot distinguish
// "no secret configured" from "wrong secret supplied".
type MeteringHandler struct {
	usage  *billingstore.UsageStore
	users  *auth.UserStore
	cfg    *auth.Config
	secret []byte
	log    zerolog.Logger

	// Optional out-of-band soft-cap warning email dispatcher. When nil
	// the soft-cap check is skipped entirely so the handler keeps its
	// zero-dependency posture for tests and minimal deployments. When
	// non-nil the handler fires a fire-and-forget email after a
	// successful Reserve if the user just crossed the soft-cap
	// threshold for the first time in their monthly window.
	mailer       *mails.Sender
	dashboardURL string
}

// NewMeteringHandler returns a ready-to-mount handler with email
// fan-out disabled. internalSecret is the gateway-side share of the
// engine internal secret (GATEWAY_ENGINE_INTERNAL_SHARED_SECRET). An
// empty secret disables every internal endpoint (they 401
// unconditionally) so an operator who forgets to configure the var
// fails closed.
func NewMeteringHandler(
	usage *billingstore.UsageStore,
	users *auth.UserStore,
	cfg *auth.Config,
	internalSecret string,
) *MeteringHandler {
	return &MeteringHandler{
		usage:  usage,
		users:  users,
		cfg:    cfg,
		secret: []byte(internalSecret),
		log:    observability.Logger("metering_handler"),
	}
}

// WithSoftCapMailer attaches an SMTP sender and the SPA dashboard URL
// so the handler can fire a one-shot warning email the first time a
// user's monthly usage crosses the configured soft-cap percentage in
// each billing window. Called from main.go after the mailer is already
// constructed; passing a nil sender leaves the soft-cap notification
// disabled (the SPA still renders its in-app banner regardless).
func (h *MeteringHandler) WithSoftCapMailer(mailer *mails.Sender, dashboardURL string) {
	h.mailer = mailer
	h.dashboardURL = strings.TrimRight(strings.TrimSpace(dashboardURL), "/")
}

// RegisterRoutes mounts every metering endpoint on mux.
//
//	internal trio: NO auth/CSRF middleware. The handler runs the
//	X-Internal-Auth check itself so the public route stays self-contained
//	and we cannot accidentally expose it through a future middleware
//	refactor.
//
//	user GET: standard auth + CSRF chain (RequireCSRF short-circuits GET
//	so the wrap is a no-op but keeps the registration pattern uniform).
func (h *MeteringHandler) RegisterRoutes(
	mux *http.ServeMux,
	authMiddleware func(http.Handler) http.Handler,
	csrfMiddleware func(http.Handler) http.Handler,
) {
	mux.HandleFunc("/internal/metering/reserve", h.handleReserve)
	mux.HandleFunc("/internal/metering/commit", h.handleCommit)
	mux.HandleFunc("/internal/metering/refund", h.handleRefund)

	mux.Handle("/api/v1/billing/usage", authMiddleware(csrfMiddleware(http.HandlerFunc(h.handleGetUsage))))
}

// ---------------------------------------------------------------------------
// Internal: shared-secret guard
// ---------------------------------------------------------------------------

func (h *MeteringHandler) verifyInternal(r *http.Request) bool {
	if len(h.secret) == 0 {
		return false
	}
	provided := strings.TrimSpace(r.Header.Get("X-Internal-Auth"))
	if provided == "" {
		return false
	}
	return hmac.Equal([]byte(provided), h.secret)
}

func (h *MeteringHandler) rejectInternal(w http.ResponseWriter) {
	writeJSONError(w, http.StatusUnauthorized, "unauthorized")
}

// ---------------------------------------------------------------------------
// POST /internal/metering/reserve
// ---------------------------------------------------------------------------

type reserveRequest struct {
	Provider             string `json:"provider"`
	Model                string `json:"model"`
	EstimatedInputTokens int64  `json:"estimated_input_tokens"`
	MaxOutputTokens      int64  `json:"max_output_tokens"`
	TraceID              string `json:"trace_id"`
}

type reserveResponse struct {
	ReservationID string `json:"reservation_id"`
	ExpiresInSecs int    `json:"expires_in_seconds"`
}

func (h *MeteringHandler) handleReserve(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.verifyInternal(r) {
		h.rejectInternal(w)
		return
	}

	userID := strings.TrimSpace(r.Header.Get("X-User-Id"))
	if userID == "" {
		writeJSONError(w, http.StatusBadRequest, "X-User-Id header required")
		return
	}

	var req reserveRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSONError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	req.Provider = strings.ToLower(strings.TrimSpace(req.Provider))
	req.Model = strings.TrimSpace(req.Model)
	if req.EstimatedInputTokens < 0 || req.MaxOutputTokens <= 0 {
		writeJSONError(w, http.StatusBadRequest, "estimated_input_tokens must be >= 0 and max_output_tokens must be > 0")
		return
	}

	lookupCtx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()
	user, err := h.users.GetUserByID(lookupCtx, userID)
	if err != nil || user == nil {
		writeJSONError(w, http.StatusNotFound, "user not found")
		return
	}

	policy := h.policyForUser(user)

	reservationID, err := h.usage.ReserveLLMTokens(
		r.Context(),
		user.ID, tierFor(user),
		req.Provider, req.Model, req.TraceID,
		req.EstimatedInputTokens, req.MaxOutputTokens,
		policy,
	)
	if err != nil {
		var qerr *billingstore.QuotaExceededError
		if errors.As(err, &qerr) {
			retryAfter := int(time.Until(qerr.ResetsAt).Seconds())
			if retryAfter < 1 {
				retryAfter = 1
			}
			w.Header().Set("Retry-After", strconv.Itoa(retryAfter))
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusTooManyRequests)
			_ = json.NewEncoder(w).Encode(map[string]any{
				"error":     "llm quota exceeded",
				"dimension": qerr.Dimension,
				"limit":     qerr.Limit,
				"used":      qerr.Used,
				"requested": qerr.Requested,
				"resets_at": qerr.ResetsAt.UTC().Format(time.RFC3339),
			})
			h.log.Info().
				Str("user_id", user.ID).
				Str("tier", tierFor(user)).
				Str("dimension", qerr.Dimension).
				Int64("limit", qerr.Limit).
				Int64("used", qerr.Used).
				Int64("requested", qerr.Requested).
				Msg("llm_quota_blocked")
			return
		}
		h.log.Error().Err(err).Str("user_id", user.ID).Msg("metering_reserve_failed")
		writeJSONError(w, http.StatusInternalServerError, "metering reserve failed")
		return
	}

	writeJSON(w, http.StatusOK, &reserveResponse{
		ReservationID: reservationID,
		ExpiresInSecs: int(policy.ReservationTTL.Seconds()),
	})

	// Soft-cap notification (out-of-band warning email).
	//
	// After a successful Reserve, check whether the user's post-debit
	// monthly usage has just crossed the configured soft-cap threshold
	// for the first time in this window. The store's test-and-set is
	// atomic so two parallel reserves cannot both fire the email; the
	// goroutine wraps the SMTP path (which already retries with
	// exponential backoff) so the metering hot path is never blocked
	// by mail delivery.
	h.maybeFireSoftCapEmail(user, policy)
}

// maybeFireSoftCapEmail is the post-Reserve hook that fans out the
// one-shot soft-cap warning. Safe to call unconditionally: it returns
// immediately when the mailer is unwired, when the tier has no soft
// cap configured, when the user has no email address, or when the user
// has not yet crossed the threshold. The atomic test-and-set inside
// MarkSoftCapNotifiedIfCrossed guarantees at-most-one email per
// monthly window.
func (h *MeteringHandler) maybeFireSoftCapEmail(
	user *auth.User,
	policy billingstore.LLMQuotaPolicy,
) {
	if h.mailer == nil {
		return
	}
	if policy.SoftCapPercent <= 0 || policy.SoftCapPercent > 100 {
		return
	}
	if strings.TrimSpace(user.Email) == "" {
		return
	}

	// Use a detached context with a short timeout: the store call is a
	// single UPDATE so it should never need more than a second, and we
	// must not block the handler's response on it.
	checkCtx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	justCrossed, err := h.usage.MarkSoftCapNotifiedIfCrossed(
		checkCtx,
		user.ID,
		policy.SoftCapPercent,
		policy.MonthlyInputTokens,
		policy.MonthlyOutputTokens,
	)
	if err != nil {
		h.log.Error().
			Err(err).
			Str("user_id", user.ID).
			Msg("metering_soft_cap_check_failed")
		return
	}
	if !justCrossed {
		return
	}

	// Fetch the snapshot so we can render the reset date accurately.
	// On any error we fall back to a generic phrase rather than skipping
	// the email entirely.
	snapCtx, snapCancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer snapCancel()
	snap, snapErr := h.usage.GetLLMUsageSnapshot(snapCtx, user.ID, policy)
	resetLabel := ""
	if snapErr == nil && snap != nil && !snap.MonthlyWindowStart.IsZero() {
		resetLabel = snap.MonthlyWindowStart.AddDate(0, 1, 0).Format("2 January 2006")
	}

	subject := mails.SoftCapWarningSubject
	body := mails.SoftCapWarningHTML(
		user.Username,
		policy.SoftCapPercent,
		resetLabel,
		policy.MonthlyInputTokens,
		policy.MonthlyOutputTokens,
		h.dashboardURL,
	)

	h.log.Info().
		Str("user_id", user.ID).
		Int("soft_cap_percent", policy.SoftCapPercent).
		Str("reset_label", resetLabel).
		Msg("metering_soft_cap_email_dispatched")

	// Fire-and-forget: SendWithRetry has its own bounded retry/backoff,
	// so the worst case is one failed delivery logged at error level
	// inside the sender.
	go h.mailer.SendWithRetry(user.Email, subject, body)
}

// ---------------------------------------------------------------------------
// POST /internal/metering/commit
// ---------------------------------------------------------------------------

type commitRequest struct {
	ReservationID      string `json:"reservation_id"`
	ActualInputTokens  int64  `json:"actual_input_tokens"`
	ActualOutputTokens int64  `json:"actual_output_tokens"`
}

func (h *MeteringHandler) handleCommit(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.verifyInternal(r) {
		h.rejectInternal(w)
		return
	}

	var req commitRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSONError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	req.ReservationID = strings.TrimSpace(req.ReservationID)
	if req.ReservationID == "" {
		writeJSONError(w, http.StatusBadRequest, "reservation_id is required")
		return
	}
	if req.ActualInputTokens < 0 || req.ActualOutputTokens < 0 {
		writeJSONError(w, http.StatusBadRequest, "actual_* token counts must be non-negative")
		return
	}

	if err := h.usage.CommitLLMTokens(r.Context(), req.ReservationID, req.ActualInputTokens, req.ActualOutputTokens); err != nil {
		h.log.Error().Err(err).Str("reservation_id", req.ReservationID).Msg("metering_commit_failed")
		writeJSONError(w, http.StatusInternalServerError, "metering commit failed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "committed"})
}

// ---------------------------------------------------------------------------
// POST /internal/metering/refund
// ---------------------------------------------------------------------------

type refundRequest struct {
	ReservationID string `json:"reservation_id"`
}

func (h *MeteringHandler) handleRefund(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.verifyInternal(r) {
		h.rejectInternal(w)
		return
	}

	var req refundRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSONError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	req.ReservationID = strings.TrimSpace(req.ReservationID)
	if req.ReservationID == "" {
		writeJSONError(w, http.StatusBadRequest, "reservation_id is required")
		return
	}

	if err := h.usage.RefundLLMTokens(r.Context(), req.ReservationID); err != nil {
		h.log.Error().Err(err).Str("reservation_id", req.ReservationID).Msg("metering_refund_failed")
		writeJSONError(w, http.StatusInternalServerError, "metering refund failed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "refunded"})
}

// ---------------------------------------------------------------------------
// GET /api/v1/billing/usage
// ---------------------------------------------------------------------------

func (h *MeteringHandler) handleGetUsage(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	claims := auth.ClaimsFromContext(r.Context())
	if claims == nil {
		writeJSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	lookupCtx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()
	user, err := h.users.GetUserByID(lookupCtx, claims.UserID)
	if err != nil || user == nil {
		writeJSONError(w, http.StatusNotFound, "user not found")
		return
	}

	policy := h.policyForUser(user)
	snap, err := h.usage.GetLLMUsageSnapshot(r.Context(), user.ID, policy)
	if err != nil {
		h.log.Error().Err(err).Str("user_id", user.ID).Msg("metering_usage_snapshot_failed")
		writeJSONError(w, http.StatusInternalServerError, "usage snapshot failed")
		return
	}
	writeJSON(w, http.StatusOK, snap)
}

// ---------------------------------------------------------------------------
// Tier resolution + policy conversion
// ---------------------------------------------------------------------------

// tierFor returns the canonical tier string the metering layer applies
// to this user. Admins are treated as "admin" so the auth config can
// map them to the managed-tier policy independent of whatever tier
// string lives on their billing subscription row (admins typically
// retain tier="free" because they do not pay).
//
// Centralised in one helper so every call site — the Reserve insert,
// the quota-blocked log line, the policy lookup — sees the same
// canonicalised string and cannot drift.
func tierFor(user *auth.User) string {
	if user.IsAdmin() {
		return "admin"
	}
	return user.Tier
}

// policyForUser resolves the user's LLM quota policy from the auth
// config. Snapshot copy of the auth-package shape into the billing-store
// shape so neither package needs to import the other.
func (h *MeteringHandler) policyForUser(user *auth.User) billingstore.LLMQuotaPolicy {
	authPol := h.cfg.LLMQuotaPolicyForTier(tierFor(user))

	allowed := make(map[string]bool, len(authPol.AllowedModels))
	for _, m := range authPol.AllowedModels {
		allowed[m] = true
	}
	return billingstore.LLMQuotaPolicy{
		DailyInputTokens:      authPol.DailyInputTokens,
		DailyOutputTokens:     authPol.DailyOutputTokens,
		MonthlyInputTokens:    authPol.MonthlyInputTokens,
		MonthlyOutputTokens:   authPol.MonthlyOutputTokens,
		MaxInputTokensPerCall: authPol.MaxInputTokensPerCall,
		SoftCapPercent:        authPol.SoftCapPercent,
		AllowedModels:         allowed,
		ReservationTTL:        authPol.ReservationTTL,
	}
}
