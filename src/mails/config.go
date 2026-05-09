package mails

import (
	"fmt"
	"strings"

	"github.com/kelseyhightower/envconfig"
)

// Config holds SMTP configuration loaded from environment variables
// with the SMTP_ prefix. Non-critical: the gateway starts even when
// SMTP is not configured; waitlist entries are still recorded in
// PostgreSQL and emails are skipped with a warning log.
type Config struct {
	// SMTP server hostname (e.g. smtp.gmail.com, smtp.hostinger.com).
	Host string `envconfig:"HOST" default:""`

	// SMTP server port. 587 for STARTTLS (recommended), 465 for implicit TLS.
	Port int `envconfig:"PORT" default:"587"`

	// SMTP authentication username (usually the full email address).
	User string `envconfig:"USER" default:""`

	// SMTP authentication password or app-specific password.
	Pass string `envconfig:"PASS" default:""`

	// Sender email address shown in the From header.
	FromEmail string `envconfig:"FROM_EMAIL" default:""`

	// Sender display name shown alongside the From email.
	FromName string `envconfig:"FROM_NAME" default:"Exoper"`
}

// LoadConfig reads SMTP_ prefixed environment variables into Config.
func LoadConfig() (*Config, error) {
	var cfg Config
	if err := envconfig.Process("SMTP", &cfg); err != nil {
		return nil, fmt.Errorf("mails config: %w", err)
	}
	cfg.Host = strings.TrimSpace(cfg.Host)
	cfg.User = strings.TrimSpace(cfg.User)
	cfg.Pass = strings.TrimSpace(cfg.Pass)
	cfg.FromEmail = strings.TrimSpace(cfg.FromEmail)
	cfg.FromName = strings.TrimSpace(cfg.FromName)
	return &cfg, nil
}

// IsConfigured returns true when the minimum SMTP fields are present
// to attempt email delivery. When false, the sender logs a warning
// and skips delivery — waitlist entries are still persisted.
func (c *Config) IsConfigured() bool {
	return c.Host != "" && c.User != "" && c.Pass != "" && c.FromEmail != ""
}
