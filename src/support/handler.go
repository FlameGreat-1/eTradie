package support

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
)

// IPResolver is the minimal surface the support handler needs from a
// proxy-aware client-IP resolver. Satisfied by *auth.ClientIPResolver.
type IPResolver interface {
	Resolve(r *http.Request) string
}

// rateLimiter is the minimal surface the support handler needs from
// auth.RateLimiter, matching the pattern in the consent package.
type rateLimiter interface {
	Allow(key string) bool
}

type noopLimiter struct{}

func (noopLimiter) Allow(_ string) bool { return true }

// UserLookup is the minimal surface the support handler needs from a
// user store: fetch the canonical user record by ID so the handler
// can populate ticket.email (the JWT Claims intentionally omit the
// email to keep tokens small). *auth.UserStore satisfies this. The
// abstraction also lets unit tests inject a deterministic fake.
type UserLookup interface {
	GetUserByID(ctx context.Context, id string) (*auth.User, error)
}

// Hard caps and policy constants. Centralised here so all branches of
// the handler reference the same values.
const (
	// maxRequestBodyBytes bounds the JSON body the handler will accept.
	// 64 KiB is far above any legitimate ticket payload (the body cap
	// in models.go is 8 KiB) and ensures a malicious client cannot
	// exhaust memory before validation runs.
	maxRequestBodyBytes = 64 * 1024

	// maxOpenTicketsPerEmail caps how many non-closed tickets a single
	// email may have at once via the public contact form. Anonymous
	// users cannot spam the inbox by opening a new ticket per
	// keystroke.
	maxOpenTicketsPerEmail = 5
)

// Handler serves the support REST API.
type Handler struct {
	store        *Store
	notifier     *Notifier
	cfg          *Config
	users        UserLookup
	resolver     IPResolver
	ipLimiter    rateLimiter
	emailLimiter rateLimiter
	log          zerolog.Logger
}

// NewHandler constructs a support HTTP handler. Passing nil for either
// limiter substitutes a no-op limiter so unit tests do not need to
// fabricate one; production wiring always supplies real limiters via
// NewHandlerWithLimiters.
func NewHandler(
	store *Store,
	notifier *Notifier,
	cfg *Config,
	users UserLookup,
	resolver IPResolver,
	log zerolog.Logger,
) *Handler {
	return NewHandlerWithLimiters(store, notifier, cfg, users, resolver, noopLimiter{}, noopLimiter{}, log)
}

// NewHandlerWithLimiters is the production constructor. It wires:
//
//	ipLimiter    -- keyed on the resolved client IP; defends against
//	                volumetric attacks from a single origin.
//	emailLimiter -- keyed on the validated email; defends against a
//	                rotating-IP attacker targeting a single mailbox.
func NewHandlerWithLimiters(
	store *Store,
	notifier *Notifier,
	cfg *Config,
	users UserLookup,
	resolver IPResolver,
	ipLimiter, emailLimiter rateLimiter,
	log zerolog.Logger,
) *Handler {
	if ipLimiter == nil {
		ipLimiter = noopLimiter{}
	}
	if emailLimiter == nil {
		emailLimiter = noopLimiter{}
	}
	return &Handler{
		store:        store,
		notifier:     notifier,
		cfg:          cfg,
		users:        users,
		resolver:     resolver,
		ipLimiter:    ipLimiter,
		emailLimiter: emailLimiter,
		log:          log,
	}
}

// RegisterRoutes mounts every support endpoint on the given mux.
//
// Public endpoints (no auth):
//
//	GET  /api/support/community-links
//	POST /api/support/contact
//
// Authenticated endpoints (auth + CSRF):
//
//	GET    /api/support/tickets
//	POST   /api/support/tickets
//	GET    /api/support/tickets/{id}
//	POST   /api/support/tickets/{id}/messages
//	POST   /api/support/tickets/{id}/close
//
// The shared /api/support/tickets/{...} prefix is dispatched by a
// single ServeMux entry; the inner mux logic peels the ticket id and
// the optional sub-action so we do not need a third-party router.
func (h *Handler) RegisterRoutes(
	mux *http.ServeMux,
	requireAuth func(http.Handler) http.Handler,
	requireCSRF func(http.Handler) http.Handler,
) {
	// Public.
	mux.HandleFunc("/api/support/community-links", h.handleCommunityLinks)
	mux.HandleFunc("/api/support/contact", h.handlePublicContact)

	// Authenticated.
	mux.Handle("/api/support/tickets", requireAuth(requireCSRF(http.HandlerFunc(h.handleTicketsCollection))))
	mux.Handle("/api/support/tickets/", requireAuth(requireCSRF(http.HandlerFunc(h.handleTicketsItem))))
}

// ----------------------------------------------------------------------
// GET /api/support/community-links (public)
// ----------------------------------------------------------------------

type communityLink struct {
	Platform string `json:"platform"`
	URL      string `json:"url"`
}

type communityResponse struct {
	Links []communityLink `json:"links"`
}

func (h *Handler) handleCommunityLinks(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusNoContent)
		return
	}
	if r.Method != http.MethodGet {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}

	links := make([]communityLink, 0, 4)
	if h.cfg.CommunityFacebookURL != "" {
		links = append(links, communityLink{Platform: "facebook", URL: h.cfg.CommunityFacebookURL})
	}
	if h.cfg.CommunityDiscordURL != "" {
		links = append(links, communityLink{Platform: "discord", URL: h.cfg.CommunityDiscordURL})
	}
	if h.cfg.CommunityTelegramURL != "" {
		links = append(links, communityLink{Platform: "telegram", URL: h.cfg.CommunityTelegramURL})
	}
	if h.cfg.CommunityWhatsAppURL != "" {
		links = append(links, communityLink{Platform: "whatsapp", URL: h.cfg.CommunityWhatsAppURL})
	}
	writeJSON(w, http.StatusOK, communityResponse{Links: links})
}

// ----------------------------------------------------------------------
// POST /api/support/contact (public)
// ----------------------------------------------------------------------

type publicContactRequest struct {
	Email    string `json:"email"`
	Name     string `json:"name"`
	Subject  string `json:"subject"`
	Message  string `json:"message"`
	Category string `json:"category"`
	Priority string `json:"priority"`
	// Website is a honeypot field. The legitimate SPA leaves it
	// empty; bots that auto-fill every text input populate it. When
	// non-empty the handler silently accepts the request (returns
	// 201 with a fabricated public_ref so the bot does not learn its
	// trap was tripped) but does NOT persist or notify. See
	// handlePublicContact for the dispatch logic.
	Website string `json:"website"`
}

type publicContactResponse struct {
	Ticket *Ticket `json:"ticket"`
}

func (h *Handler) handlePublicContact(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusNoContent)
		return
	}
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}

	ip := h.resolveIP(r)
	if !h.ipLimiter.Allow(ip) {
		SupportRateLimitedTotal.WithLabelValues(rateScopeIP).Inc()
		h.write429(w)
		return
	}

	var req publicContactRequest
	if err := decodeJSON(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	// Honeypot check. The 'website' field is hidden from real users
	// (CSS display:none + aria-hidden + tabindex=-1 on the SPA side)
	// and any non-empty value is a strong signal of an automated bot.
	// We return a 201 with a fabricated reference so the bot's
	// success / failure detector cannot distinguish this from a real
	// submission, but we never persist or notify. Real users who
	// somehow trigger the field (e.g. an aggressive password manager)
	// see a successful confirmation and can re-submit from a follow-up
	// support email if they actually need a ticket opened.
	if strings.TrimSpace(req.Website) != "" {
		SupportRateLimitedTotal.WithLabelValues(rateScopeHoneypot).Inc()
		h.log.Warn().
			Str("ip", ip).
			Str("ua", TruncateUserAgent(r.UserAgent())).
			Msg("support_honeypot_triggered")
		writeJSON(w, http.StatusCreated, publicContactResponse{Ticket: &Ticket{
			ID:        generateID(),
			PublicRef: generatePublicRef(),
			Email:     strings.ToLower(strings.TrimSpace(req.Email)),
			Status:    StatusOpen,
			Channel:   ChannelContact,
			CreatedAt: time.Now().UTC(),
			UpdatedAt: time.Now().UTC(),
		}})
		return
	}

	email, err := ValidateEmail(req.Email)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "a valid email is required"})
		return
	}
	name, err := ValidateName(req.Name)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "name is too long"})
		return
	}
	subject, err := ValidateSubject(req.Subject)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "subject must be 3-200 characters"})
		return
	}
	body, err := ValidateBody(req.Message)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "message must be 5-8000 characters"})
		return
	}
	category, err := NormaliseCategory(req.Category)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid category"})
		return
	}
	priority, err := NormalisePriority(req.Priority)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid priority"})
		return
	}

	// Per-email rate limit AFTER validation. A single attacker rotating
	// IPs cannot fan out unlimited writes against one mailbox.
	if !h.emailLimiter.Allow(email) {
		SupportRateLimitedTotal.WithLabelValues(rateScopeEmail).Inc()
		h.write429(w)
		return
	}

	// Open-ticket ceiling per email.
	n, err := h.store.CountOpenByEmail(r.Context(), email)
	if err != nil {
		h.log.Error().Err(err).Msg("support_count_open_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}
	if n >= maxOpenTicketsPerEmail {
		SupportRateLimitedTotal.WithLabelValues(rateScopeOpenTicketCeiling).Inc()
		writeJSON(w, http.StatusTooManyRequests, map[string]string{
			"error": "too many open tickets for this email; please wait for a response before opening another",
		})
		return
	}

	ticket, err := h.store.CreateTicket(r.Context(), CreateParams{
		UserID:    nil,
		Email:     email,
		Name:      name,
		Subject:   subject,
		Body:      body,
		Category:  category,
		Priority:  priority,
		Channel:   ChannelContact,
		IPAddress: ip,
		UserAgent: r.UserAgent(),
	})
	if err != nil {
		h.log.Error().Err(err).Msg("support_create_ticket_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}

	SupportTicketsCreatedTotal.WithLabelValues(string(ticket.Channel), string(category)).Inc()
	h.log.Info().
		Str("public_ref", ticket.PublicRef).
		Str("email", email).
		Str("category", string(category)).
		Str("channel", string(ticket.Channel)).
		Msg("support_ticket_created")

	h.dispatchEvent(Event{Kind: EventNewTicket, Ticket: ticket})
	writeJSON(w, http.StatusCreated, publicContactResponse{Ticket: ticket})
}

// ----------------------------------------------------------------------
// /api/support/tickets (authenticated collection)
// ----------------------------------------------------------------------

func (h *Handler) handleTicketsCollection(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodOptions:
		w.WriteHeader(http.StatusNoContent)
	case http.MethodGet:
		h.handleListTickets(w, r)
	case http.MethodPost:
		h.handleCreateTicket(w, r)
	default:
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
	}
}

type listTicketsResponse struct {
	Tickets []Ticket `json:"tickets"`
	Limit   int      `json:"limit"`
	Offset  int      `json:"offset"`
}

func (h *Handler) handleListTickets(w http.ResponseWriter, r *http.Request) {
	uid := auth.UserIDFromContext(r.Context())
	if uid == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}

	limit := parseIntQuery(r, "limit", 25)
	offset := parseIntQuery(r, "offset", 0)

	tickets, err := h.store.ListByUser(r.Context(), uid, limit, offset)
	if err != nil {
		h.log.Error().Err(err).Msg("support_list_tickets_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}
	writeJSON(w, http.StatusOK, listTicketsResponse{
		Tickets: tickets,
		Limit:   limit,
		Offset:  offset,
	})
}

type createTicketRequest struct {
	Subject  string `json:"subject"`
	Message  string `json:"message"`
	Category string `json:"category"`
	Priority string `json:"priority"`
}

type ticketResponse struct {
	Ticket *Ticket `json:"ticket"`
}

func (h *Handler) handleCreateTicket(w http.ResponseWriter, r *http.Request) {
	uid := auth.UserIDFromContext(r.Context())
	if uid == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}
	if h.users == nil {
		h.log.Error().Msg("support_user_lookup_not_wired")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}
	user, err := h.users.GetUserByID(r.Context(), uid)
	if err != nil || user == nil {
		h.log.Warn().Err(err).Str("user_id", uid).Msg("support_user_lookup_failed")
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}

	var req createTicketRequest
	if err := decodeJSON(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	subject, err := ValidateSubject(req.Subject)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "subject must be 3-200 characters"})
		return
	}
	body, err := ValidateBody(req.Message)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "message must be 5-8000 characters"})
		return
	}
	category, err := NormaliseCategory(req.Category)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid category"})
		return
	}
	priority, err := NormalisePriority(req.Priority)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid priority"})
		return
	}

	email := strings.TrimSpace(strings.ToLower(user.Email))
	if email == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "account is missing an email"})
		return
	}

	ticket, err := h.store.CreateTicket(r.Context(), CreateParams{
		UserID:    &uid,
		Email:     email,
		Name:      strings.TrimSpace(user.Username),
		Subject:   subject,
		Body:      body,
		Category:  category,
		Priority:  priority,
		Channel:   ChannelWeb,
		IPAddress: h.resolveIP(r),
		UserAgent: r.UserAgent(),
	})
	if err != nil {
		h.log.Error().Err(err).Msg("support_create_ticket_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}

	SupportTicketsCreatedTotal.WithLabelValues(string(ticket.Channel), string(category)).Inc()
	h.log.Info().
		Str("public_ref", ticket.PublicRef).
		Str("user_id", uid).
		Str("category", string(category)).
		Msg("support_ticket_created")

	h.dispatchEvent(Event{Kind: EventNewTicket, Ticket: ticket})
	writeJSON(w, http.StatusCreated, ticketResponse{Ticket: ticket})
}

// ----------------------------------------------------------------------
// /api/support/tickets/{id}[/messages|/close] (authenticated item)
// ----------------------------------------------------------------------

func (h *Handler) handleTicketsItem(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusNoContent)
		return
	}

	rest := strings.TrimPrefix(r.URL.Path, "/api/support/tickets/")
	rest = strings.Trim(rest, "/")
	if rest == "" {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "not found"})
		return
	}
	parts := strings.SplitN(rest, "/", 2)
	ticketID := parts[0]
	sub := ""
	if len(parts) == 2 {
		sub = parts[1]
	}

	if !isValidIDFormat(ticketID) {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "ticket not found"})
		return
	}

	uid := auth.UserIDFromContext(r.Context())
	if uid == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}

	switch {
	case sub == "" && r.Method == http.MethodGet:
		h.handleGetTicket(w, r, ticketID, uid)
	case sub == "messages" && r.Method == http.MethodPost:
		h.handleAppendMessage(w, r, ticketID, uid)
	case sub == "close" && r.Method == http.MethodPost:
		h.handleCloseTicket(w, r, ticketID, uid)
	default:
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
	}
}

func (h *Handler) handleGetTicket(w http.ResponseWriter, r *http.Request, ticketID, uid string) {
	t, err := h.store.GetWithMessages(r.Context(), ticketID, uid)
	if err != nil {
		if errors.Is(err, ErrTicketNotFound) {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "ticket not found"})
			return
		}
		h.log.Error().Err(err).Msg("support_get_ticket_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		return
	}
	writeJSON(w, http.StatusOK, ticketResponse{Ticket: t})
}

type appendMessageRequest struct {
	Message string `json:"message"`
}

type appendMessageResponse struct {
	Message *Message `json:"message"`
	Ticket  *Ticket  `json:"ticket"`
}

func (h *Handler) handleAppendMessage(w http.ResponseWriter, r *http.Request, ticketID, uid string) {
	var req appendMessageRequest
	if err := decodeJSON(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	body, err := ValidateBody(req.Message)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "message must be 5-8000 characters"})
		return
	}

	msg, ticket, err := h.store.AppendMessage(r.Context(), ticketID, uid, AuthorKindUser, body)
	if err != nil {
		switch {
		case errors.Is(err, ErrTicketNotFound):
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "ticket not found"})
		case errors.Is(err, ErrTicketClosed):
			writeJSON(w, http.StatusConflict, map[string]string{"error": "ticket is closed"})
		default:
			h.log.Error().Err(err).Msg("support_append_message_failed")
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		}
		return
	}

	h.log.Info().
		Str("public_ref", ticket.PublicRef).
		Str("user_id", uid).
		Msg("support_message_appended")

	h.dispatchEvent(Event{Kind: EventNewReply, Ticket: ticket, LatestMessage: msg})
	writeJSON(w, http.StatusCreated, appendMessageResponse{Message: msg, Ticket: ticket})
}

func (h *Handler) handleCloseTicket(w http.ResponseWriter, r *http.Request, ticketID, uid string) {
	t, err := h.store.CloseTicket(r.Context(), ticketID, uid)
	if err != nil {
		switch {
		case errors.Is(err, ErrTicketNotFound):
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "ticket not found"})
		case errors.Is(err, ErrTicketClosed):
			writeJSON(w, http.StatusConflict, map[string]string{"error": "ticket already closed"})
		default:
			h.log.Error().Err(err).Msg("support_close_ticket_failed")
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
		}
		return
	}

	h.log.Info().
		Str("public_ref", t.PublicRef).
		Str("user_id", uid).
		Msg("support_ticket_closed")

	h.dispatchEvent(Event{Kind: EventTicketClosed, Ticket: t})
	writeJSON(w, http.StatusOK, ticketResponse{Ticket: t})
}

// ----------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------

// dispatchEvent fans the event out to every configured channel in a
// detached goroutine with a fresh background context bounded by a
// generous timeout. We deliberately do not use r.Context() because
// the request context is cancelled the moment the HTTP response is
// written, which would race with the notifier.
//
// The detached goroutine is registered on the notifier's WaitGroup
// via Track / TrackDone so Notifier.Shutdown can drain it during a
// graceful shutdown. Notify itself also registers each per-channel
// goroutine on the same WaitGroup, giving us end-to-end tracking from
// the moment a ticket is persisted until every channel has been
// delivered to (or the shutdown context has expired).
func (h *Handler) dispatchEvent(ev Event) {
	if h.notifier == nil {
		return
	}
	h.notifier.Track()
	go func() {
		defer h.notifier.TrackDone()
		ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
		defer cancel()
		h.notifier.Notify(ctx, ev)
	}()
}

func (h *Handler) resolveIP(r *http.Request) string {
	if h.resolver == nil {
		return ""
	}
	return h.resolver.Resolve(r)
}

func (h *Handler) write429(w http.ResponseWriter) {
	w.Header().Set("Retry-After", "60")
	writeJSON(w, http.StatusTooManyRequests, map[string]string{
		"error": "rate limit exceeded, try again later",
	})
}

// decodeJSON reads a bounded body and JSON-decodes it into the given
// destination. The MaxBytesReader caps the body BEFORE the decoder
// allocates anything, so a 10 MB request never reaches the CPU /
// memory cost of JSON parsing.
func decodeJSON(r *http.Request, dst any) error {
	r.Body = http.MaxBytesReader(nil, r.Body, maxRequestBodyBytes)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(dst); err != nil {
		if errors.Is(err, io.EOF) {
			return errors.New("empty request body")
		}
		return errors.New("invalid JSON: " + err.Error())
	}
	return nil
}

func parseIntQuery(r *http.Request, key string, defaultVal int) int {
	raw := strings.TrimSpace(r.URL.Query().Get(key))
	if raw == "" {
		return defaultVal
	}
	n, err := strconv.Atoi(raw)
	if err != nil {
		return defaultVal
	}
	return n
}

// isValidIDFormat returns true when s looks like one of our generated
// 16-byte (32 hex chars) primary keys. Avoids spending DB cycles on
// payloads that cannot possibly match a real row.
func isValidIDFormat(s string) bool {
	if len(s) != 32 {
		return false
	}
	for _, r := range s {
		if !((r >= '0' && r <= '9') || (r >= 'a' && r <= 'f')) {
			return false
		}
	}
	return true
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}
