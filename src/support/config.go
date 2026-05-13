package support

import (
	"fmt"
	"strings"
	"time"

	"github.com/kelseyhightower/envconfig"
)

// Config holds Support module configuration loaded from environment
// variables under the SUPPORT_ prefix.
//
// Operating modes:
//   - When the inbox email is unset the notifier logs a warning and
//     suppresses email fan-out. Ticket creation still succeeds.
//   - When every external-channel token is unset the notifier still
//     functions and persists tickets; only fan-out is skipped.
//   - Community link fields are pure passthrough: configured links
//     are exposed via GET /api/support/community-links so the SPA
//     can render the public Facebook / Discord / Telegram / WhatsApp
//     entry points uniformly.
type Config struct {
	InboxEmail            string `envconfig:"INBOX_EMAIL" default:""`
	BillingInboxEmail     string `envconfig:"BILLING_INBOX_EMAIL" default:""`
	SecurityInboxEmail    string `envconfig:"SECURITY_INBOX_EMAIL" default:""`
	DiscordWebhookURL     string `envconfig:"DISCORD_WEBHOOK_URL" default:""`
	TelegramBotToken      string `envconfig:"TELEGRAM_BOT_TOKEN" default:""`
	TelegramChatID        string `envconfig:"TELEGRAM_CHAT_ID" default:""`
	WhatsAppToken         string `envconfig:"WHATSAPP_TOKEN" default:""`
	WhatsAppPhoneNumberID string `envconfig:"WHATSAPP_PHONE_NUMBER_ID" default:""`
	WhatsAppRecipient     string `envconfig:"WHATSAPP_RECIPIENT" default:""`
	CommunityFacebookURL  string `envconfig:"COMMUNITY_FACEBOOK_URL" default:""`
	CommunityDiscordURL   string `envconfig:"COMMUNITY_DISCORD_URL" default:""`
	CommunityTelegramURL  string `envconfig:"COMMUNITY_TELEGRAM_URL" default:""`
	CommunityWhatsAppURL  string `envconfig:"COMMUNITY_WHATSAPP_URL" default:""`
	PublicSiteURL         string `envconfig:"PUBLIC_SITE_URL" default:"https://exoper.com"`
	// AutoCloseAfterRaw is the human-readable duration string for the
	// inactivity window after which a 'resolved' ticket is automatically
	// transitioned to 'closed' by the background janitor. Parsed into
	// AutoCloseAfter in LoadConfig. Set to "0" to disable auto-close.
	AutoCloseAfterRaw string `envconfig:"AUTO_CLOSE_AFTER" default:"72h"`

	// AutoCloseAfter is the parsed duration. Not populated by envconfig;
	// set by LoadConfig after parsing AutoCloseAfterRaw.
	AutoCloseAfter time.Duration `envconfig:"-"`
}

// LoadConfig reads SUPPORT_-prefixed env vars and trims whitespace.
func LoadConfig() (*Config, error) {
	var cfg Config
	if err := envconfig.Process("SUPPORT", &cfg); err != nil {
		return nil, fmt.Errorf("support config: %w", err)
	}
	cfg.InboxEmail = strings.TrimSpace(cfg.InboxEmail)
	cfg.BillingInboxEmail = strings.TrimSpace(cfg.BillingInboxEmail)
	cfg.SecurityInboxEmail = strings.TrimSpace(cfg.SecurityInboxEmail)
	cfg.DiscordWebhookURL = strings.TrimSpace(cfg.DiscordWebhookURL)
	cfg.TelegramBotToken = strings.TrimSpace(cfg.TelegramBotToken)
	cfg.TelegramChatID = strings.TrimSpace(cfg.TelegramChatID)
	cfg.WhatsAppToken = strings.TrimSpace(cfg.WhatsAppToken)
	cfg.WhatsAppPhoneNumberID = strings.TrimSpace(cfg.WhatsAppPhoneNumberID)
	cfg.WhatsAppRecipient = strings.TrimSpace(cfg.WhatsAppRecipient)
	cfg.CommunityFacebookURL = strings.TrimSpace(cfg.CommunityFacebookURL)
	cfg.CommunityDiscordURL = strings.TrimSpace(cfg.CommunityDiscordURL)
	cfg.CommunityTelegramURL = strings.TrimSpace(cfg.CommunityTelegramURL)
	cfg.CommunityWhatsAppURL = strings.TrimSpace(cfg.CommunityWhatsAppURL)
	cfg.PublicSiteURL = strings.TrimRight(strings.TrimSpace(cfg.PublicSiteURL), "/")
	if cfg.PublicSiteURL == "" {
		cfg.PublicSiteURL = "https://exoper.com"
	}

	// Parse the auto-close duration. "0" or empty disables auto-close.
	raw := strings.TrimSpace(cfg.AutoCloseAfterRaw)
	if raw == "" || raw == "0" {
		cfg.AutoCloseAfter = 0
	} else {
		d, err := time.ParseDuration(raw)
		if err != nil {
			return nil, fmt.Errorf("support config: invalid AUTO_CLOSE_AFTER %q: %w", raw, err)
		}
		if d < 0 {
			return nil, fmt.Errorf("support config: AUTO_CLOSE_AFTER must be non-negative, got %v", d)
		}
		cfg.AutoCloseAfter = d
	}

	return &cfg, nil
}

// EmailEnabled reports whether the email fan-out path can run.
func (c *Config) EmailEnabled() bool { return c.InboxEmail != "" }

// DiscordEnabled reports whether the Discord fan-out can run.
func (c *Config) DiscordEnabled() bool { return c.DiscordWebhookURL != "" }

// TelegramEnabled reports whether the Telegram fan-out can run.
func (c *Config) TelegramEnabled() bool {
	return c.TelegramBotToken != "" && c.TelegramChatID != ""
}

// WhatsAppEnabled reports whether the WhatsApp Cloud API fan-out can run.
func (c *Config) WhatsAppEnabled() bool {
	return c.WhatsAppToken != "" &&
		c.WhatsAppPhoneNumberID != "" &&
		c.WhatsAppRecipient != ""
}

// HasCommunityLinks reports whether at least one community URL is set.
func (c *Config) HasCommunityLinks() bool {
	return c.CommunityFacebookURL != "" ||
		c.CommunityDiscordURL != "" ||
		c.CommunityTelegramURL != "" ||
		c.CommunityWhatsAppURL != ""
}

// RouteInbox picks the email inbox most appropriate for a ticket's
// category, falling back to the generic InboxEmail when a specialised
// inbox is not configured.
func (c *Config) RouteInbox(category TicketCategory) string {
	switch category {
	case CategoryBilling, CategoryComplaint:
		if c.BillingInboxEmail != "" {
			return c.BillingInboxEmail
		}
	case CategorySecurity:
		if c.SecurityInboxEmail != "" {
			return c.SecurityInboxEmail
		}
	}
	return c.InboxEmail
}

// AutoCloseEnabled reports whether the background janitor should
// transition resolved tickets to closed after inactivity.
func (c *Config) AutoCloseEnabled() bool {
	return c.AutoCloseAfter > 0
}
