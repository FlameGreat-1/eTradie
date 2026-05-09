package mails

import (
	"crypto/tls"
	"fmt"
	"math"
	"net"
	"net/smtp"
	"strconv"
	"strings"
	"time"

	"github.com/rs/zerolog"
)

const (
	maxRetries     = 3
	baseBackoff    = 2 * time.Second
	maxBackoff     = 30 * time.Second
	dialTimeout    = 10 * time.Second
	backoffFactor  = 2.0
)

// Sender delivers HTML emails via SMTP with STARTTLS, automatic retry,
// and exponential backoff. Designed for fire-and-forget usage from a
// goroutine — the caller never blocks on delivery.
type Sender struct {
	cfg *Config
	log zerolog.Logger
}

// NewSender creates an email sender from the given SMTP configuration.
func NewSender(cfg *Config, log zerolog.Logger) *Sender {
	return &Sender{cfg: cfg, log: log}
}

// SendWithRetry delivers an HTML email with up to 3 automatic retries
// using exponential backoff (2s → 4s → 8s). This is the primary
// entry point — called from background goroutines so the HTTP
// response is never delayed by SMTP latency or transient failures.
func (s *Sender) SendWithRetry(to, subject, htmlBody string) {
	if !s.cfg.IsConfigured() {
		s.log.Warn().Str("to", to).Msg("email_skipped_smtp_not_configured")
		return
	}

	var lastErr error
	for attempt := 0; attempt <= maxRetries; attempt++ {
		if attempt > 0 {
			backoff := time.Duration(float64(baseBackoff) * math.Pow(backoffFactor, float64(attempt-1)))
			if backoff > maxBackoff {
				backoff = maxBackoff
			}
			s.log.Warn().
				Err(lastErr).
				Str("to", to).
				Int("attempt", attempt+1).
				Dur("backoff", backoff).
				Msg("email_retry_after_backoff")
			time.Sleep(backoff)
		}

		lastErr = s.send(to, subject, htmlBody)
		if lastErr == nil {
			s.log.Info().Str("to", to).Int("attempts", attempt+1).Msg("email_delivered")
			return
		}
	}

	s.log.Error().
		Err(lastErr).
		Str("to", to).
		Int("max_retries", maxRetries).
		Msg("email_delivery_failed_all_retries_exhausted")
}

// send performs a single SMTP delivery attempt.
func (s *Sender) send(to, subject, htmlBody string) error {
	addr := net.JoinHostPort(s.cfg.Host, strconv.Itoa(s.cfg.Port))

	// Build MIME headers.
	from := s.cfg.FromEmail
	if s.cfg.FromName != "" {
		from = fmt.Sprintf("%s <%s>", s.cfg.FromName, s.cfg.FromEmail)
	}

	headers := strings.Join([]string{
		"From: " + from,
		"To: " + to,
		"Subject: " + subject,
		"MIME-Version: 1.0",
		"Content-Type: text/html; charset=UTF-8",
		"Date: " + time.Now().UTC().Format(time.RFC1123Z),
	}, "\r\n")
	msg := []byte(headers + "\r\n\r\n" + htmlBody)

	// Connect with a bounded dial timeout.
	conn, err := net.DialTimeout("tcp", addr, dialTimeout)
	if err != nil {
		return fmt.Errorf("smtp dial: %w", err)
	}

	client, err := smtp.NewClient(conn, s.cfg.Host)
	if err != nil {
		conn.Close()
		return fmt.Errorf("smtp client: %w", err)
	}
	defer client.Close()

	// Upgrade to TLS (STARTTLS).
	tlsConfig := &tls.Config{
		ServerName: s.cfg.Host,
		MinVersion: tls.VersionTLS12,
	}
	if err := client.StartTLS(tlsConfig); err != nil {
		return fmt.Errorf("smtp starttls: %w", err)
	}

	// Authenticate.
	auth := smtp.PlainAuth("", s.cfg.User, s.cfg.Pass, s.cfg.Host)
	if err := client.Auth(auth); err != nil {
		return fmt.Errorf("smtp auth: %w", err)
	}

	// Set sender and recipient.
	if err := client.Mail(s.cfg.FromEmail); err != nil {
		return fmt.Errorf("smtp mail from: %w", err)
	}
	if err := client.Rcpt(to); err != nil {
		return fmt.Errorf("smtp rcpt to: %w", err)
	}

	// Write message body.
	w, err := client.Data()
	if err != nil {
		return fmt.Errorf("smtp data: %w", err)
	}
	if _, err := w.Write(msg); err != nil {
		return fmt.Errorf("smtp write: %w", err)
	}
	if err := w.Close(); err != nil {
		return fmt.Errorf("smtp close data: %w", err)
	}

	return client.Quit()
}
