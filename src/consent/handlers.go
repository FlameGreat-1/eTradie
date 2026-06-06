package consent

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
)

// IPResolver is the minimal surface the consent handler needs from a
// proxy-aware client-IP resolver. The auth package's ClientIPResolver
// satisfies this interface, so wiring just passes the existing one
// the gateway already constructed for rate limiting.
type IPResolver interface {
	Resolve(r *http.Request) string
}

// rateLimiter is the minimal surface the consent handler needs from a
// per-key rate limiter. *auth.RateLimiter satisfies this. Decoupling
// behind an interface keeps the consent package free of test-time
// concerns and lets unit tests inject a deterministic limiter.
type rateLimiter interface {
	Allow(key string) bool
}

// noopLimiter is used when NewHandler is called without limiters
// (in tests). It always allows; production wiring always supplies a
// real pair via NewHandlerWithLimiters.
type noopLimiter struct{}

func (noopLimiter) Allow(_ string) bool { return true }

// Handler serves the consent REST API.
type Handler struct {
	store      *Store
	resolver   IPResolver
	ipHashSalt []byte
	// ipLimiter caps total POST volume per resolved client IP. Cheap
	// volumetric defence; blocks naive DoS / DB-fill at the edge.
	ipLimiter rateLimiter
	// anonLimiter caps total POST volume per anonymous_id. Defeats a
	// single attacker rotating across many residential IPs (botnet)
	// who would individually slip under ipLimiter but collectively
	// inflate a target anonymous_id's history.
	anonLimiter rateLimiter
	log         zerolog.Logger
}

// NewHandler constructs the consent HTTP handler with no-op rate
// limiters. Intended for unit tests. The salt is used to derive
// ip_hash and the redacted anonymous_id_hash in audit logs; passing
// an empty slice is permitted (handlers still produce a non-empty
// hash) but a startup warning is logged so operators notice the
// misconfiguration.
//
// Production wiring MUST use NewHandlerWithLimiters so the public
// POST endpoint is protected against volumetric abuse and
// per-anonymous_id grinding.
func NewHandler(store *Store, resolver IPResolver, ipHashSalt []byte, log zerolog.Logger) *Handler {
	return NewHandlerWithLimiters(store, resolver, ipHashSalt, noopLimiter{}, noopLimiter{}, log)
}

// NewHandlerWithLimiters is the production constructor. It wires two
// independent rate limiters around POST /api/v1/consent:
//
//	ipLimiter   -- keyed on the resolved client IP; defends against
//	               volumetric attacks from a single origin.
//	anonLimiter -- keyed on the validated anonymous_id; defends
//	               against a botnet that rotates IPs but targets a
//	               single anonymous_id.
//
// nil limiters are treated as noop so the constructor never panics.
func NewHandlerWithLimiters(store *Store, resolver IPResolver, ipHashSalt []byte, ipLimiter, anonLimiter rateLimiter, log zerolog.Logger) *Handler {
	if len(ipHashSalt) == 0 {
		log.Warn().Msg("consent_ip_hash_salt_empty_audit_hashes_will_not_be_unique_across_deployments")
	}
	if ipLimiter == nil {
		ipLimiter = noopLimiter{}
	}
	if anonLimiter == nil {
		anonLimiter = noopLimiter{}
	}
	return &Handler{
		store:       store,
		resolver:    resolver,
		ipHashSalt:  ipHashSalt,
		ipLimiter:   ipLimiter,
		anonLimiter: anonLimiter,
		log:         log,
	}
}

// RegisterRoutes mounts every consent endpoint on mux. The middleware
// chain matches the rest of the gateway: OptionalAuth where anonymous
// access is legitimate, RequireAuth + RequireCSRF for state-changing
// authenticated calls.
//
// Why no RequireCSRF on POST /api/v1/consent (the public write)?
// The endpoint is reachable by anonymous visitors who, by definition,
// have no session and therefore no CSRF cookie. A CSRF attack against
// this endpoint would at worst record a forged "reject all" entry
// against the victim's anonymous_id; that has no security or privacy
// consequence because there is nothing to read back. The endpoint is
// rate-limited per resolved client IP AND per anonymous_id (see
// NewHandlerWithLimiters) to prevent both volumetric abuse and
// per-target grinding.
//
// Why RequireCSRF on POST /api/v1/consent/attach? That endpoint runs
// after authentication and mutates server state in a way that links
// data to the user's identity; the standard CSRF defence applies.
func (h *Handler) RegisterRoutes(
	mux *http.ServeMux,
	tokenService *auth.TokenService,
	csrfMiddleware func(http.Handler) http.Handler,
) {
	optional := auth.OptionalAuth(tokenService)
	require := auth.RequireAuth(tokenService)

	mux.Handle("/api/v1/consent", optional(http.HandlerFunc(h.handleConsent)))
	mux.Handle("/api/v1/consent/history", require(csrfMiddleware(http.HandlerFunc(h.handleHistory))))
	mux.Handle("/api/v1/consent/attach", require(csrfMiddleware(http.HandlerFunc(h.handleAttach))))
}

// ----------------------------------------------------------------------
// POST / GET /api/v1/consent
// ----------------------------------------------------------------------

type postConsentRequest struct {
	AnonymousID   string     `json:"anonymous_id"`
	PolicyVersion string     `json:"policy_version"`
	Categories    Categories `json:"categories"`
}

type consentResponse struct {
	Record *Record `json:"record"`
}

func (h *Handler) handleConsent(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		h.handleGetLatest(w, r)
	case http.MethodPost:
		h.handlePostConsent(w, r)
	case http.MethodOptions:
		w.WriteHeader(http.StatusNoContent)
	default:
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
	}
}

func (h *Handler) handlePostConsent(w http.ResponseWriter, r *http.Request) {
	// 1. Per-IP rate limit BEFORE decoding the body so an attacker
	//    cannot pay JSON-decode CPU for every probe. Identity is the
	//    resolved client IP, spoof-proof via the trust-aware
	//    ClientIPResolver shared with the auth rate limiter.
	ip := h.resolveIP(r)
	if !h.ipLimiter.Allow(ip) {
		h.write429(w)
		return
	}

	var req postConsentRequest
	if err := auth.DecodeJSONStrict(w, r, &req, 0); err != nil {
		status, msg := auth.DecodeJSONError(err)
		writeJSON(w, status, map[string]string{"error": msg})
		return
	}

	req.AnonymousID = strings.TrimSpace(req.AnonymousID)
	req.PolicyVersion = strings.TrimSpace(req.PolicyVersion)
	if err := ValidateAnonymousID(req.AnonymousID); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "anonymous_id is required"})
		return
	}
	if err := ValidatePolicyVersion(req.PolicyVersion); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "policy_version is required"})
		return
	}

	// 2. Per-anonymous_id rate limit AFTER validation but BEFORE the
	//    DB insert. A single attacker rotating across many residential
	//    IPs cannot fan out unlimited writes against one target.
	if !h.anonLimiter.Allow(req.AnonymousID) {
		h.write429(w)
		return
	}

	var userID *string
	if uid := auth.UserIDFromContext(r.Context()); uid != "" {
		userID = &uid
	}

	rec, err := h.store.Insert(r.Context(), InsertParams{
		UserID:        userID,
		AnonymousID:   req.AnonymousID,
		PolicyVersion: req.PolicyVersion,
		Categories:    req.Categories,
		IPHash:        h.hashWithSalt(ip),
		UserAgent:     r.UserAgent(),
	})
	if err != nil {
		h.log.Error().Err(err).Msg("consent_insert_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}

	h.log.Info().
		Str("anonymous_id_hash", h.hashAnonymousID(req.AnonymousID)).
		Bool("has_user", userID != nil).
		Str("policy_version", req.PolicyVersion).
		Bool("functional", req.Categories.Functional).
		Bool("analytics", req.Categories.Analytics).
		Msg("consent_recorded")

	writeJSON(w, http.StatusCreated, consentResponse{Record: rec})
}

func (h *Handler) handleGetLatest(w http.ResponseWriter, r *http.Request) {
	if uid := auth.UserIDFromContext(r.Context()); uid != "" {
		rec, err := h.store.LatestForUserID(r.Context(), uid)
		if err != nil {
			h.log.Error().Err(err).Msg("consent_latest_user_failed")
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
			return
		}
		writeJSON(w, http.StatusOK, consentResponse{Record: rec})
		return
	}

	anonID := strings.TrimSpace(r.URL.Query().Get("anonymous_id"))
	if err := ValidateAnonymousID(anonID); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "anonymous_id is required"})
		return
	}

	rec, err := h.store.LatestForAnonymousID(r.Context(), anonID)
	if err != nil {
		h.log.Error().Err(err).Msg("consent_latest_anonymous_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}
	writeJSON(w, http.StatusOK, consentResponse{Record: rec})
}

// ----------------------------------------------------------------------
// GET /api/v1/consent/history
// ----------------------------------------------------------------------

func (h *Handler) handleHistory(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}

	uid := auth.UserIDFromContext(r.Context())
	if uid == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}

	limit := 25
	if raw := strings.TrimSpace(r.URL.Query().Get("limit")); raw != "" {
		if n, err := strconv.Atoi(raw); err == nil {
			limit = n
		}
	}

	records, err := h.store.HistoryForUserID(r.Context(), uid, limit)
	if err != nil {
		h.log.Error().Err(err).Msg("consent_history_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"records": records})
}

// ----------------------------------------------------------------------
// POST /api/v1/consent/attach
// ----------------------------------------------------------------------

type attachRequest struct {
	AnonymousID string `json:"anonymous_id"`
}

type attachResponse struct {
	Attached int64 `json:"attached"`
}

func (h *Handler) handleAttach(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}

	uid := auth.UserIDFromContext(r.Context())
	if uid == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}

	var req attachRequest
	if err := auth.DecodeJSONStrict(w, r, &req, 0); err != nil {
		status, msg := auth.DecodeJSONError(err)
		writeJSON(w, status, map[string]string{"error": msg})
		return
	}
	req.AnonymousID = strings.TrimSpace(req.AnonymousID)
	if err := ValidateAnonymousID(req.AnonymousID); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "anonymous_id is required"})
		return
	}

	n, err := h.store.AttachAnonymousToUser(r.Context(), req.AnonymousID, uid)
	if err != nil {
		h.log.Error().Err(err).Msg("consent_attach_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}

	h.log.Info().
		Str("user_id", uid).
		Str("anonymous_id_hash", h.hashAnonymousID(req.AnonymousID)).
		Int64("attached", n).
		Msg("consent_attached")

	writeJSON(w, http.StatusOK, attachResponse{Attached: n})
}

// ----------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------

// write429 emits a 429 Too Many Requests with the standard
// Retry-After header. Shared between the per-IP and per-anonymous_id
// limit branches.
func (h *Handler) write429(w http.ResponseWriter) {
	w.Header().Set("Retry-After", "60")
	writeJSON(w, http.StatusTooManyRequests, map[string]string{"error": "rate limit exceeded, try again later"})
}

// resolveIP returns the resolved client IP, or an empty string if the
// resolver is unset. Used both as the rate-limit identity and as the
// input to the ip_hash column.
func (h *Handler) resolveIP(r *http.Request) string {
	if h.resolver == nil {
		return ""
	}
	return h.resolver.Resolve(r)
}

// hashWithSalt derives a salted SHA-256 hex digest of the given
// value. Used for both ip_hash storage and anonymous_id_hash logging
// so an attacker who reads the audit log cannot trivially correlate
// a leaked anonymous_id back to a recorded decision.
func (h *Handler) hashWithSalt(value string) string {
	if value == "" {
		return ""
	}
	sum := sha256.New()
	sum.Write(h.ipHashSalt)
	sum.Write([]byte(value))
	return hex.EncodeToString(sum.Sum(nil))
}

// hashAnonymousID returns a short hex prefix of the salted hash of an
// anonymous_id, suitable for log emission. The prefix is long enough
// to correlate rows across log lines but short enough to avoid bloat.
func (h *Handler) hashAnonymousID(id string) string {
	full := h.hashWithSalt(id)
	if len(full) > 16 {
		return full[:16]
	}
	return full
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}
