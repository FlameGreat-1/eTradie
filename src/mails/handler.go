package mails

import (
	"encoding/json"
	"errors"
	"net/http"
	"strings"

	"github.com/rs/zerolog"
)

// Handler serves the waitlist HTTP endpoint.
type Handler struct {
	store  *WaitlistStore
	sender *Sender
	log    zerolog.Logger
}

// NewHandler creates the waitlist HTTP handler.
func NewHandler(store *WaitlistStore, sender *Sender, log zerolog.Logger) *Handler {
	return &Handler{
		store:  store,
		sender: sender,
		log:    log,
	}
}

// RegisterRoutes mounts the public waitlist endpoint on the given mux.
// This endpoint is intentionally public (no auth required) so that
// unauthenticated landing page visitors can join the waitlist.
func (h *Handler) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/api/waitlist", h.handleWaitlist)
}

type waitlistRequest struct {
	Email string `json:"email"`
}

func (h *Handler) handleWaitlist(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusNoContent)
		return
	}
	if r.Method != http.MethodPost {
		writeResponse(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}

	// Bound + strict-decode the body. 4 KiB is far above the only
	// legitimate payload ({"email":"..."}) and DisallowUnknownFields
	// rejects padded/garbage submissions from bots. The pattern is
	// inlined rather than calling auth.DecodeJSONStrict because the
	// auth package already imports this (mails) package, so a reverse
	// import would create a cycle.
	r.Body = http.MaxBytesReader(w, r.Body, 4*1024)
	var req waitlistRequest
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&req); err != nil {
		var maxBytesErr *http.MaxBytesError
		if errors.As(err, &maxBytesErr) {
			writeResponse(w, http.StatusRequestEntityTooLarge, map[string]string{"error": "request body too large"})
			return
		}
		writeResponse(w, http.StatusBadRequest, map[string]string{"error": "invalid JSON"})
		return
	}

	req.Email = strings.ToLower(strings.TrimSpace(req.Email))
	if req.Email == "" || !strings.Contains(req.Email, "@") || !strings.Contains(req.Email, ".") {
		writeResponse(w, http.StatusBadRequest, map[string]string{"error": "a valid email address is required"})
		return
	}

	// Extract client IP from X-Forwarded-For or RemoteAddr.
	ip := r.Header.Get("X-Forwarded-For")
	if ip != "" {
		ip = strings.TrimSpace(strings.Split(ip, ",")[0])
	} else {
		ip = r.RemoteAddr
	}

	entry, err := h.store.CreateEntry(r.Context(), req.Email, ip)
	if err != nil {
		h.log.Error().Err(err).Str("email", req.Email).Msg("waitlist_store_failed")
		writeResponse(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}

	// entry == nil means the email already existed (idempotent).
	if entry == nil {
		h.log.Info().Str("email", req.Email).Msg("waitlist_duplicate_submission")
		writeResponse(w, http.StatusOK, map[string]string{
			"message": "you're already on the waitlist",
			"status":  "existing",
		})
		return
	}

	h.log.Info().Str("email", req.Email).Str("id", entry.ID).Msg("waitlist_entry_created")

	// Fire-and-forget email delivery in a background goroutine.
	// The sender handles retry with exponential backoff internally.
	// If SMTP is not configured or all retries fail, the sender logs
	// the error — the waitlist entry is already persisted.
	go func() {
		htmlBody := WaitlistWelcomeHTML(req.Email)
		h.sender.SendWithRetry(req.Email, "Welcome to the Exoper Waitlist", htmlBody)
	}()

	writeResponse(w, http.StatusCreated, map[string]string{
		"message": "welcome to the waitlist",
		"status":  "created",
	})
}

func writeResponse(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}
