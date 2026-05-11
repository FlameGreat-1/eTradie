// Package config loads and validates the billing microservice configuration
// from environment variables.
//
// Validation runs at startup so the service either boots fully-configured or
// refuses to boot at all. Half-configured webhook listeners are the exact
// failure mode this guards against — a missing PADDLE_WEBHOOK_SECRET would
// silently accept any signed payload and is treated as a fatal error.
package config

import (
	"errors"
	"fmt"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/kelseyhightower/envconfig"

	"github.com/flamegreat-1/etradie/src/billing/events"
	"github.com/flamegreat-1/etradie/src/billing/lemonsqueezy"
	"github.com/flamegreat-1/etradie/src/billing/paddle"
	"github.com/flamegreat-1/etradie/src/billing/service"
)

// Config is the fully-validated runtime configuration of the billing service.
type Config struct {
	// HTTP server.
	HTTPPort int `envconfig:"BILLING_HTTP_PORT" default:"8082"`

	// Logging.
	LogLevel string `envconfig:"BILLING_LOG_LEVEL" default:"INFO"`
	LogJSON  bool   `envconfig:"BILLING_LOG_JSON"  default:"true"`

	// Database. Falls back to POSTGRES_* env vars when empty so operators
	// don't have to repeat themselves between auth and billing.
	DatabaseURL string `envconfig:"BILLING_DATABASE_URL"`

	// Public origin where Paddle / Lemon Squeezy POST webhooks. MUST be
	// HTTPS in production. The value is logged on startup so operators can
	// verify it matches the URL registered in the provider dashboards;
	// mismatches between this and the dashboard config are the most common
	// cause of "webhooks not arriving" incidents and historically were
	// invisible because the service never loaded the value.
	PublicBaseURL string `envconfig:"BILLING_PUBLIC_BASE_URL" required:"true"`

	// Webhook hardening.
	WebhookReplayWindow time.Duration `envconfig:"BILLING_WEBHOOK_REPLAY_WINDOW_SECONDS" default:"300s"`
	WebhookMaxBodyBytes int64         `envconfig:"BILLING_WEBHOOK_MAX_BODY_BYTES"        default:"1048576"`

	// Period-end reconciler. Demotes paused/past_due/canceled/refunded
	// subscriptions whose current_period_end has elapsed, and prunes the
	// processed_webhook_events idempotency table. Both knobs are validated
	// to be positive so a misconfigured deployment cannot silently disable
	// the reconciler entirely.
	ReconcilerInterval       time.Duration `envconfig:"BILLING_RECONCILER_INTERVAL_SECONDS" default:"900s"`
	IdempotencyRetentionDays int           `envconfig:"BILLING_IDEMPOTENCY_RETENTION_DAYS" default:"30"`

	// Internal service-to-service auth between gateway and billing.
	InternalSharedSecret string `envconfig:"BILLING_INTERNAL_SHARED_SECRET" required:"true"`

	// Redis URL used by the cross-service alert transport. The billing
	// service publishes SUBSCRIPTION_UPGRADED / DOWNGRADED /
	// STATUS_CHANGED events on every applied tier or status change;
	// the gateway subscribes to the same Redis channel and fans the
	// events out to every connected SPA WebSocket. Without this, the
	// dashboard would lag the actual subscription state by up to
	// React Query's staleTime after a successful payment.
	//
	// Falls back to the shared REDIS_URL when BILLING_REDIS_URL is
	// empty so operators do not have to duplicate the value.
	RedisURL string `envconfig:"BILLING_REDIS_URL"`

	// Checkout return URLs.
	SuccessURL string `envconfig:"BILLING_CHECKOUT_SUCCESS_URL" required:"true"`
	CancelURL  string `envconfig:"BILLING_CHECKOUT_CANCEL_URL"  required:"true"`

	// Paddle.
	PaddleWebhookSecret   string `envconfig:"PADDLE_WEBHOOK_SECRET"    required:"true"`
	PaddleAPIKey          string `envconfig:"PADDLE_API_KEY"           required:"true"`
	PaddleAPIBaseURL      string `envconfig:"PADDLE_API_BASE_URL"      default:"https://api.paddle.com"`
	PaddlePriceProBYOK    string `envconfig:"PADDLE_PRICE_PRO_BYOK"    required:"true"`
	PaddlePriceProManaged string `envconfig:"PADDLE_PRICE_PRO_MANAGED" required:"true"`

	// Lemon Squeezy.
	LSWebhookSecret     string `envconfig:"LEMONSQUEEZY_WEBHOOK_SECRET"      required:"true"`
	LSAPIKey            string `envconfig:"LEMONSQUEEZY_API_KEY"             required:"true"`
	LSAPIBaseURL        string `envconfig:"LEMONSQUEEZY_API_BASE_URL"        default:"https://api.lemonsqueezy.com"`
	LSStoreID           string `envconfig:"LEMONSQUEEZY_STORE_ID"            required:"true"`
	LSVariantProBYOK    string `envconfig:"LEMONSQUEEZY_VARIANT_PRO_BYOK"    required:"true"`
	LSVariantProManaged string `envconfig:"LEMONSQUEEZY_VARIANT_PRO_MANAGED" required:"true"`
}

// Load reads, validates and returns Config. Returns a non-nil error on any
// missing required field; main.go is expected to log+exit in that case.
func Load() (*Config, error) {
	var cfg Config
	if err := envconfig.Process("", &cfg); err != nil {
		return nil, fmt.Errorf("billing config: %w", err)
	}
	if cfg.DatabaseURL == "" {
		cfg.DatabaseURL = buildPostgresURL()
		if cfg.DatabaseURL == "" {
			return nil, errors.New("billing config: BILLING_DATABASE_URL or POSTGRES_* env vars are required")
		}
	}
	if cfg.HTTPPort <= 0 || cfg.HTTPPort > 65535 {
		return nil, fmt.Errorf("billing config: invalid BILLING_HTTP_PORT=%d", cfg.HTTPPort)
	}
	if cfg.WebhookReplayWindow <= 0 {
		return nil, errors.New("billing config: BILLING_WEBHOOK_REPLAY_WINDOW_SECONDS must be positive")
	}
	if cfg.WebhookMaxBodyBytes <= 0 {
		return nil, errors.New("billing config: BILLING_WEBHOOK_MAX_BODY_BYTES must be positive")
	}
	if cfg.ReconcilerInterval <= 0 {
		return nil, errors.New("billing config: BILLING_RECONCILER_INTERVAL_SECONDS must be positive")
	}
	if cfg.IdempotencyRetentionDays <= 0 {
		return nil, errors.New("billing config: BILLING_IDEMPOTENCY_RETENTION_DAYS must be positive")
	}
	if len(cfg.InternalSharedSecret) < 32 {
		return nil, errors.New("billing config: BILLING_INTERNAL_SHARED_SECRET must be at least 32 characters")
	}
	if err := validatePublicURL(cfg.PublicBaseURL); err != nil {
		return nil, fmt.Errorf("billing config: BILLING_PUBLIC_BASE_URL: %w", err)
	}
	if cfg.RedisURL == "" {
		cfg.RedisURL = strings.TrimSpace(os.Getenv("REDIS_URL"))
	}
	if cfg.RedisURL == "" {
		return nil, errors.New("billing config: BILLING_REDIS_URL or REDIS_URL is required for cross-service alert publishing")
	}
	return &cfg, nil
}

// validatePublicURL ensures BILLING_PUBLIC_BASE_URL is a syntactically valid
// http(s) URL with a host component. The string is operator-facing only
// (logged at startup, used to construct external links) so we don't enforce
// trailing-slash policy or paths.
func validatePublicURL(raw string) error {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return errors.New("value is empty")
	}
	u, err := url.Parse(raw)
	if err != nil {
		return fmt.Errorf("parse: %w", err)
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return fmt.Errorf("scheme must be http or https, got %q", u.Scheme)
	}
	if u.Host == "" {
		return errors.New("host is empty")
	}
	return nil
}

// PriceTierMap returns the Paddle price_id → tier map.
func (c *Config) PriceTierMap() paddle.PriceTierMap {
	return paddle.PriceTierMap{
		c.PaddlePriceProBYOK:    events.TierProBYOK,
		c.PaddlePriceProManaged: events.TierProManaged,
	}
}

// VariantTierMap returns the Lemon Squeezy variant_id → tier map.
func (c *Config) VariantTierMap() lemonsqueezy.VariantTierMap {
	return lemonsqueezy.VariantTierMap{
		c.LSVariantProBYOK:    events.TierProBYOK,
		c.LSVariantProManaged: events.TierProManaged,
	}
}

// CheckoutConfig returns the slice of config the checkout service consumes.
func (c *Config) CheckoutConfig() service.CheckoutConfig {
	return service.CheckoutConfig{
		PaddleAPIBaseURL:      c.PaddleAPIBaseURL,
		PaddleAPIKey:          c.PaddleAPIKey,
		PaddlePriceProBYOK:    c.PaddlePriceProBYOK,
		PaddlePriceProManaged: c.PaddlePriceProManaged,
		LSAPIBaseURL:          c.LSAPIBaseURL,
		LSAPIKey:              c.LSAPIKey,
		LSStoreID:             c.LSStoreID,
		LSVariantProBYOK:      c.LSVariantProBYOK,
		LSVariantProManaged:   c.LSVariantProManaged,
		SuccessURL:            c.SuccessURL,
		CancelURL:             c.CancelURL,
		HTTPTimeout:           10 * time.Second,
	}
}

func buildPostgresURL() string {
	host := envOrDefault("POSTGRES_HOST", "")
	if host == "" {
		return ""
	}
	port := envOrDefault("POSTGRES_PORT", "5432")
	user := envOrDefault("POSTGRES_USER", "etradie")
	pass := envOrDefault("POSTGRES_PASSWORD", "")
	db := envOrDefault("POSTGRES_DB", "etradie")
	ssl := envOrDefault("POSTGRES_SSLMODE", "disable")
	return fmt.Sprintf("postgres[REDACTED]%s:%s/%s?sslmode=%s",
		user, pass, host, port, db, ssl)
}

func envOrDefault(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}
