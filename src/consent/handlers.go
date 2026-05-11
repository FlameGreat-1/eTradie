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

// Handler serves the consent REST API.
type Handler struct {
	store      *Store
	resolver   IPResolver
	ipHashSalt []byte
	log        zerolog.Logger
}

// NewHandler constructs the consent HTTP handler. The salt is used
// to derive ip_hash; passing an empty slice is permitted (handlers
// still produce a non-empty hash) but a startup warning is logged so
// operators notice the misconfiguration.
func NewHandler(store *Store, resolver IPResolver, ipHashSalt []byte, log zerolog.Logger) *Handler {
	if len(ipHashSalt) == 0 {
		log.Warn().Msg("consent_ip_hash_salt_empty_audit_hashes_will_not_be_unique_across_deployments")
	}
	return &Handler{
		store:      store,
		resolver:   resolver,
		ipHashSalt: ipHashSalt,
		log:        log,
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
// rate-limited at the platform edge to prevent volumetric abuse.
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
	var req postConsentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid JSON"})
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

	var userID *string
	if uid := auth.UserIDFromContext(r.Context()); uid != "" {
		userID = &uid
	}

	rec, err := h.store.Insert(r.Context(), InsertParams{
		UserID:        userID,
		AnonymousID:   req.AnonymousID,
		PolicyVersion: req.PolicyVersion,
		Categories:    req.Categories,
		IPHash:        h.hashIP(r),
		UserAgent:     r.UserAgent(),
	})
	if err != nil {
		h.log.Error().Err(err).Msg("consent_insert_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}

	h.log.Info().
		Str("anonymous_id", req.AnonymousID).
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
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid JSON"})
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
		Str("anonymous_id", req.AnonymousID).
		Int64("attached", n).
		Msg("consent_attached")

	writeJSON(w, http.StatusOK, attachResponse{Attached: n})
}

// ----------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------

// hashIP derives a salted SHA-256 hex digest of the resolved client
// IP. When the resolver is unset (defensive: tests / future
// configurations) the function returns the empty string rather than
// hashing whatever the request claims, because trusting raw
// RemoteAddr here would defeat the spoof-proof guarantees the auth
// package already provides.
func (h *Handler) hashIP(r *http.Request) string {
	if h.resolver == nil {
		return ""
	}
	ip := h.resolver.Resolve(r)
	if ip == "" {
		return ""
	}
	sum := sha256.New()
	sum.Write(h.ipHashSalt)
	sum.Write([]byte(ip))
	return hex.EncodeToString(sum.Sum(nil))
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}
