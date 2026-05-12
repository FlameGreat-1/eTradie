package support

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/rs/zerolog"
)

// EmailSender is the minimal surface the support notifier needs from
// an SMTP sender. The mails.Sender in src/mails satisfies this.
// Decoupling behind an interface keeps the support package free of an
// import cycle and lets unit tests inject a deterministic fake.
type EmailSender interface {
	SendWithRetry(to, subject, htmlBody string)
}

// Event is the input to Notify. It is the union of every field the
// outbound channel renderers need.
type Event struct {
	// Kind selects the wording of the rendered message.
	Kind EventKind

	// Ticket is the canonical record; required for every event.
	Ticket *Ticket

	// LatestMessage is the just-appended message for reply events.
	// nil for EventNewTicket (the seed message lives on the ticket).
	LatestMessage *Message
}

// EventKind enumerates the notifier's supported wordings.
type EventKind string

const (
	// EventNewTicket fires the moment a brand-new ticket is
	// persisted (either from the dashboard or from the public
	// contact form).
	EventNewTicket EventKind = "new_ticket"

	// EventNewReply fires after a user appends a follow-up message.
	EventNewReply EventKind = "new_reply"

	// EventTicketClosed fires when the user closes their own ticket.
	EventTicketClosed EventKind = "ticket_closed"
)

// Notifier fans new events out to every configured channel.
type Notifier struct {
	cfg    *Config
	email  EmailSender
	http   *http.Client
	log    zerolog.Logger
}

// NewNotifier constructs a Notifier wired to the given email sender
// and an HTTP client with a bounded per-request timeout. Passing a
// nil EmailSender is permitted; only the email fan-out is then
// disabled and a warning is logged.
func NewNotifier(cfg *Config, email EmailSender, log zerolog.Logger) *Notifier {
	return &Notifier{
		cfg:   cfg,
		email: email,
		log:   log,
		http: &http.Client{
			Timeout: 15 * time.Second,
		},
	}
}

// Notify dispatches a single event to every configured channel
// concurrently. It always returns nil; channel failures are logged
// and never surfaced because the persisted ticket already represents
// the user's request — a downstream channel outage must not break
// the user-visible flow. Invoke this from a goroutine to keep HTTP
// response latency bounded.
func (n *Notifier) Notify(ctx context.Context, ev Event) {
	if ev.Ticket == nil {
		n.log.Error().Str("event", string(ev.Kind)).Msg("support_notify_missing_ticket")
		return
	}

	var wg sync.WaitGroup

	if n.cfg.EmailEnabled() && n.email != nil {
		wg.Add(1)
		go func() {
			defer wg.Done()
			n.sendEmail(ev)
		}()
	}
	if n.cfg.DiscordEnabled() {
		wg.Add(1)
		go func() {
			defer wg.Done()
			n.sendDiscord(ctx, ev)
		}()
	}
	if n.cfg.TelegramEnabled() {
		wg.Add(1)
		go func() {
			defer wg.Done()
			n.sendTelegram(ctx, ev)
		}()
	}
	if n.cfg.WhatsAppEnabled() {
		wg.Add(1)
		go func() {
			defer wg.Done()
			n.sendWhatsApp(ctx, ev)
		}()
	}

	wg.Wait()
}

// ----------------------------------------------------------------------
// Email
// ----------------------------------------------------------------------

func (n *Notifier) sendEmail(ev Event) {
	inbox := n.cfg.RouteInbox(ev.Ticket.Category)
	if inbox == "" {
		return
	}

	switch ev.Kind {
	case EventNewTicket:
		staffSubject := fmt.Sprintf("[%s] New %s ticket: %s",
			ev.Ticket.PublicRef, ev.Ticket.Category, ev.Ticket.Subject)
		staffBody := newTicketStaffHTML(ev.Ticket, n.cfg.PublicSiteURL)
		n.email.SendWithRetry(inbox, staffSubject, staffBody)

		userSubject := fmt.Sprintf("We received your request — %s", ev.Ticket.PublicRef)
		userBody := newTicketUserHTML(ev.Ticket, n.cfg.PublicSiteURL)
		n.email.SendWithRetry(ev.Ticket.Email, userSubject, userBody)

	case EventNewReply:
		if ev.LatestMessage == nil {
			return
		}
		staffSubject := fmt.Sprintf("[%s] New reply: %s",
			ev.Ticket.PublicRef, ev.Ticket.Subject)
		staffBody := newReplyStaffHTML(ev.Ticket, ev.LatestMessage, n.cfg.PublicSiteURL)
		n.email.SendWithRetry(inbox, staffSubject, staffBody)

	case EventTicketClosed:
		staffSubject := fmt.Sprintf("[%s] Closed by user: %s",
			ev.Ticket.PublicRef, ev.Ticket.Subject)
		staffBody := ticketClosedStaffHTML(ev.Ticket, n.cfg.PublicSiteURL)
		n.email.SendWithRetry(inbox, staffSubject, staffBody)
	}
}

// ----------------------------------------------------------------------
// Discord (incoming webhook)
// ----------------------------------------------------------------------

type discordEmbed struct {
	Title       string                `json:"title"`
	Description string                `json:"description,omitempty"`
	Color       int                   `json:"color"`
	URL         string                `json:"url,omitempty"`
	Fields      []discordEmbedField   `json:"fields,omitempty"`
	Timestamp   string                `json:"timestamp,omitempty"`
	Footer      *discordEmbedFooter   `json:"footer,omitempty"`
}

type discordEmbedField struct {
	Name   string `json:"name"`
	Value  string `json:"value"`
	Inline bool   `json:"inline,omitempty"`
}

type discordEmbedFooter struct {
	Text string `json:"text"`
}

type discordPayload struct {
	Username string         `json:"username,omitempty"`
	Embeds   []discordEmbed `json:"embeds"`
}

func (n *Notifier) sendDiscord(ctx context.Context, ev Event) {
	color := discordColorForEvent(ev.Kind, ev.Ticket.Priority)
	title, desc := discordTitleAndBody(ev)

	fields := []discordEmbedField{
		{Name: "Reference", Value: ev.Ticket.PublicRef, Inline: true},
		{Name: "Status", Value: string(ev.Ticket.Status), Inline: true},
		{Name: "Priority", Value: string(ev.Ticket.Priority), Inline: true},
		{Name: "Category", Value: string(ev.Ticket.Category), Inline: true},
		{Name: "From", Value: discordEscape(ev.Ticket.Email), Inline: true},
		{Name: "Channel", Value: string(ev.Ticket.Channel), Inline: true},
	}

	payload := discordPayload{
		Username: "Exoper Support",
		Embeds: []discordEmbed{{
			Title:       title,
			Description: desc,
			Color:       color,
			Fields:      fields,
			Timestamp:   time.Now().UTC().Format(time.RFC3339),
			Footer:      &discordEmbedFooter{Text: "Exoper Support • " + ev.Ticket.PublicRef},
		}},
	}

	body, err := json.Marshal(payload)
	if err != nil {
		n.log.Error().Err(err).Msg("support_discord_marshal_failed")
		return
	}

	n.postWithRetry(ctx, "discord", n.cfg.DiscordWebhookURL, "application/json", body, nil)
}

func discordColorForEvent(k EventKind, p TicketPriority) int {
	if k == EventTicketClosed {
		return 0x6B7280 // slate-500
	}
	switch p {
	case PriorityUrgent:
		return 0xDC2626 // red-600
	case PriorityHigh:
		return 0xEA580C // orange-600
	case PriorityLow:
		return 0x059669 // emerald-600
	}
	return 0x2563EB // blue-600
}

func discordTitleAndBody(ev Event) (string, string) {
	switch ev.Kind {
	case EventNewTicket:
		body := ""
		if len(ev.Ticket.Messages) > 0 {
			body = ev.Ticket.Messages[0].Body
		}
		return "🆕 New ticket: " + discordEscape(ev.Ticket.Subject),
			discordTruncate(body, 1800)
	case EventNewReply:
		body := ""
		if ev.LatestMessage != nil {
			body = ev.LatestMessage.Body
		}
		return "💬 New reply on: " + discordEscape(ev.Ticket.Subject),
			discordTruncate(body, 1800)
	case EventTicketClosed:
		return "✅ Ticket closed: " + discordEscape(ev.Ticket.Subject), ""
	}
	return discordEscape(ev.Ticket.Subject), ""
}

// discordEscape escapes Discord markdown control chars in user-controlled
// strings so a malicious subject cannot break out of an embed field.
func discordEscape(s string) string {
	replacer := strings.NewReplacer(
		"`", "\\`",
		"*", "\\*",
		"_", "\\_",
		"~", "\\~",
		"|", "\\|",
	)
	return replacer.Replace(s)
}

func discordTruncate(s string, max int) string {
	s = strings.TrimSpace(s)
	if len(s) <= max {
		return s
	}
	return s[:max] + "\u2026"
}

// ----------------------------------------------------------------------
// Telegram (Bot API sendMessage)
// ----------------------------------------------------------------------

type telegramPayload struct {
	ChatID                string `json:"chat_id"`
	Text                  string `json:"text"`
	ParseMode             string `json:"parse_mode"`
	DisableWebPagePreview bool   `json:"disable_web_page_preview"`
}

func (n *Notifier) sendTelegram(ctx context.Context, ev Event) {
	text := telegramBody(ev)
	payload := telegramPayload{
		ChatID:                n.cfg.TelegramChatID,
		Text:                  text,
		ParseMode:             "HTML",
		DisableWebPagePreview: true,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		n.log.Error().Err(err).Msg("support_telegram_marshal_failed")
		return
	}
	url := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", n.cfg.TelegramBotToken)
	n.postWithRetry(ctx, "telegram", url, "application/json", body, nil)
}

func telegramBody(ev Event) string {
	var header, snippet string
	switch ev.Kind {
	case EventNewTicket:
		header = "🆕 <b>New support ticket</b>"
		if len(ev.Ticket.Messages) > 0 {
			snippet = ev.Ticket.Messages[0].Body
		}
	case EventNewReply:
		header = "💬 <b>New reply</b>"
		if ev.LatestMessage != nil {
			snippet = ev.LatestMessage.Body
		}
	case EventTicketClosed:
		header = "✅ <b>Ticket closed by user</b>"
	}

	var b strings.Builder
	b.WriteString(header)
	b.WriteString("\n\n")
	b.WriteString("<b>Ref:</b> ")
	b.WriteString(htmlEscape(ev.Ticket.PublicRef))
	b.WriteString("\n<b>Subject:</b> ")
	b.WriteString(htmlEscape(ev.Ticket.Subject))
	b.WriteString("\n<b>From:</b> ")
	b.WriteString(htmlEscape(ev.Ticket.Email))
	b.WriteString("\n<b>Category:</b> ")
	b.WriteString(htmlEscape(string(ev.Ticket.Category)))
	b.WriteString("\n<b>Priority:</b> ")
	b.WriteString(htmlEscape(string(ev.Ticket.Priority)))
	b.WriteString("\n<b>Status:</b> ")
	b.WriteString(htmlEscape(string(ev.Ticket.Status)))
	if snippet != "" {
		b.WriteString("\n\n")
		b.WriteString(htmlEscape(truncate(snippet, 1500)))
	}
	return b.String()
}

// ----------------------------------------------------------------------
// WhatsApp (Meta Cloud API)
// ----------------------------------------------------------------------

type whatsappPayload struct {
	MessagingProduct string            `json:"messaging_product"`
	To               string            `json:"to"`
	Type             string            `json:"type"`
	Text             whatsappTextBlock `json:"text"`
}

type whatsappTextBlock struct {
	PreviewURL bool   `json:"preview_url"`
	Body       string `json:"body"`
}

func (n *Notifier) sendWhatsApp(ctx context.Context, ev Event) {
	text := whatsappBody(ev)
	payload := whatsappPayload{
		MessagingProduct: "whatsapp",
		To:               n.cfg.WhatsAppRecipient,
		Type:             "text",
		Text: whatsappTextBlock{
			PreviewURL: false,
			Body:       text,
		},
	}
	body, err := json.Marshal(payload)
	if err != nil {
		n.log.Error().Err(err).Msg("support_whatsapp_marshal_failed")
		return
	}
	url := fmt.Sprintf("https://graph.facebook.com/v18.0/%s/messages", n.cfg.WhatsAppPhoneNumberID)
	headers := map[string]string{
		"Authorization": "Bearer " + n.cfg.WhatsAppToken,
	}
	n.postWithRetry(ctx, "whatsapp", url, "application/json", body, headers)
}

func whatsappBody(ev Event) string {
	var header, snippet string
	switch ev.Kind {
	case EventNewTicket:
		header = "🆕 New Exoper support ticket"
		if len(ev.Ticket.Messages) > 0 {
			snippet = ev.Ticket.Messages[0].Body
		}
	case EventNewReply:
		header = "💬 New reply on Exoper ticket"
		if ev.LatestMessage != nil {
			snippet = ev.LatestMessage.Body
		}
	case EventTicketClosed:
		header = "✅ Exoper ticket closed by user"
	}

	var b strings.Builder
	b.WriteString(header)
	b.WriteString("\n\nRef: ")
	b.WriteString(ev.Ticket.PublicRef)
	b.WriteString("\nSubject: ")
	b.WriteString(ev.Ticket.Subject)
	b.WriteString("\nFrom: ")
	b.WriteString(ev.Ticket.Email)
	b.WriteString("\nCategory: ")
	b.WriteString(string(ev.Ticket.Category))
	b.WriteString(" • Priority: ")
	b.WriteString(string(ev.Ticket.Priority))
	if snippet != "" {
		b.WriteString("\n\n")
		b.WriteString(truncate(snippet, 1200))
	}
	return b.String()
}

// ----------------------------------------------------------------------
// Shared HTTP path with retry and bounded backoff
// ----------------------------------------------------------------------

const (
	notifierMaxRetries    = 3
	notifierBaseBackoff   = 2 * time.Second
	notifierMaxBackoff    = 30 * time.Second
	notifierBackoffFactor = 2.0
	notifierMaxBodyBytes  = 1 << 14 // 16 KiB read-back cap
)

func (n *Notifier) postWithRetry(
	ctx context.Context,
	channel, url, contentType string,
	body []byte,
	extraHeaders map[string]string,
) {
	var lastErr error
	for attempt := 0; attempt <= notifierMaxRetries; attempt++ {
		if attempt > 0 {
			back := time.Duration(float64(notifierBaseBackoff) * math.Pow(notifierBackoffFactor, float64(attempt-1)))
			if back > notifierMaxBackoff {
				back = notifierMaxBackoff
			}
			select {
			case <-time.After(back):
			case <-ctx.Done():
				return
			}
		}

		req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
		if err != nil {
			lastErr = err
			continue
		}
		req.Header.Set("Content-Type", contentType)
		req.Header.Set("User-Agent", "exoper-support-notifier/1.0")
		for k, v := range extraHeaders {
			req.Header.Set(k, v)
		}

		resp, err := n.http.Do(req)
		if err != nil {
			lastErr = err
			continue
		}
		// Always drain to allow connection reuse.
		responseBody, _ := io.ReadAll(io.LimitReader(resp.Body, notifierMaxBodyBytes))
		_ = resp.Body.Close()

		if resp.StatusCode >= 200 && resp.StatusCode < 300 {
			n.log.Info().
				Str("channel", channel).
				Int("status", resp.StatusCode).
				Int("attempts", attempt+1).
				Msg("support_notify_delivered")
			return
		}
		lastErr = fmt.Errorf("http %d: %s", resp.StatusCode, truncate(string(responseBody), 200))

		// 4xx (other than 429 rate-limit) means the request itself is
		// wrong; no amount of retrying fixes that.
		if resp.StatusCode >= 400 && resp.StatusCode < 500 && resp.StatusCode != http.StatusTooManyRequests {
			break
		}
	}
	n.log.Error().
		Str("channel", channel).
		Err(lastErr).
		Msg("support_notify_failed_all_retries_exhausted")
}

// ----------------------------------------------------------------------
// Misc helpers
// ----------------------------------------------------------------------

func truncate(s string, max int) string {
	s = strings.TrimSpace(s)
	if len(s) <= max {
		return s
	}
	return s[:max] + "\u2026"
}

// htmlEscape replaces the five XML/HTML reserved characters with
// their entity references. Used by the Telegram HTML parse_mode body
// builder and by every email template.
func htmlEscape(s string) string {
	replacer := strings.NewReplacer(
		"&", "&amp;",
		"<", "&lt;",
		">", "&gt;",
		`"`, "&quot;",
		"'", "&#39;",
	)
	return replacer.Replace(s)
}

// ErrNotifierDisabled is returned by helpers that explicitly want to
// signal a no-op rather than silently skipping. Unused externally but
// exported for potential future tests.
var ErrNotifierDisabled = errors.New("support: notifier disabled")
