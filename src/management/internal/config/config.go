package config

import (
	"fmt"
	"net/url"
	"os"
	"strings"

	"github.com/kelseyhightower/envconfig"
)

// Config holds all management engine configuration. Loaded from
// environment variables with the MANAGEMENT_ prefix. Validated at
// startup; the application fails fast on invalid values.
type Config struct {
	// Servers.
	GRPCPort int `envconfig:"GRPC_PORT" default:"50054"`
	HTTPPort int `envconfig:"HTTP_PORT" default:"8083"`

	// Broker bridge (same Python FastAPI service used by Execution). The
	// management service has a single broker.Port implementation - the
	// mt5 bridge - which dispatches every call to the engine. The engine
	// resolves the per-user MT4 or MT5 connection from broker_connections
	// at request time, so the bridge itself is platform-agnostic.
	BrokerBridgeURL string `envconfig:"BROKER_BRIDGE_URL" default:"http://localhost:8000"`
	BrokerTimeoutMs int    `envconfig:"BROKER_TIMEOUT_MS" default:"5000"`

	// Shared secret for the engine's /internal/* surface.
	//
	// The Python engine's broker bridge endpoints
	// (src/engine/routers/broker_bridge.py) are protected by
	// engine.shared.internal_auth.verify_internal_auth, which compares
	// the X-Internal-Auth header against ENGINE_INTERNAL_SHARED_SECRET
	// in constant time. Must match the engine's value. Minimum length
	// 32 characters. Required unconditionally in production / staging
	// because the mt5 bridge is the only broker implementation;
	// optional in development where every bridge call returns 401
	// until configured.
	EngineInternalSecret string `envconfig:"ENGINE_INTERNAL_SHARED_SECRET"`

	// Application environment. Mirrors the engine's APP_ENV to flip
	// the production-grade validation on EngineInternalSecret.
	//
	// Note: envconfig.Process with prefix "MANAGEMENT" looks up the
	// env var MANAGEMENT_APP_ENV (prefix + tag). Production deployments
	// generally export only root APP_ENV, so validate() falls back to
	// os.Getenv("APP_ENV") when this field is empty.
	AppEnv string `envconfig:"APP_ENV" default:""`

	// Tick polling interval for live price monitoring (milliseconds).
	TickPollIntervalMs int `envconfig:"TICK_POLL_INTERVAL_MS" default:"1000"`

	// Candle polling interval for structural checks (seconds).
	// Used to check 4H/1D candle closes for invalidation logic.
	CandlePollIntervalSecs int `envconfig:"CANDLE_POLL_INTERVAL_SECS" default:"60"`

	// How often the reconciler supervisor re-evaluates the active-user
	// set, starting reconcilers for newly-active users and stopping
	// them for deactivated ones (seconds).
	ReconcileIntervalSecs int `envconfig:"RECONCILE_INTERVAL_SECS" default:"60"`

	// Database (trade journal, analytics, trade state).
	DatabaseURL         string `envconfig:"DATABASE_URL" required:"true"`
	DatabaseMaxConns    int    `envconfig:"DATABASE_MAX_CONNS" default:"10"`
	DatabaseMinConns    int    `envconfig:"DATABASE_MIN_CONNS" default:"2"`
	DatabaseMaxIdleMs   int    `envconfig:"DATABASE_MAX_IDLE_MS" default:"30000"`
	DatabaseConnMaxLife int    `envconfig:"DATABASE_CONN_MAX_LIFE_SECONDS" default:"3600"`

	// Redis (shared event notification hub).
	RedisURL string `envconfig:"REDIS_URL" default:"redis://localhost:6379/1"`

	// Observability.
	LogLevel string `envconfig:"LOG_LEVEL" default:"INFO"`
	LogJSON  bool   `envconfig:"LOG_JSON" default:"true"`
	// Empty = tracing disabled (opt-in no-op), matching the engine,
	// gateway, and execution. The Helm configmap injects the real
	// collector endpoint in the prod/staging overlays. A non-empty
	// default would make a bare run dial localhost:4317 (this pod).
	OTELEndpoint    string `envconfig:"OTEL_ENDPOINT" default:""`
	OTELServiceName string `envconfig:"OTEL_SERVICE_NAME" default:"etradie-management"`
}

// Load reads configuration from MANAGEMENT_ prefixed environment
// variables and validates all constraints.
func Load() (*Config, error) {
	var cfg Config
	if err := envconfig.Process("MANAGEMENT", &cfg); err != nil {
		return nil, fmt.Errorf("config: load from env: %w", err)
	}
	if err := cfg.validate(); err != nil {
		return nil, fmt.Errorf("config: validation: %w", err)
	}
	return &cfg, nil
}

func (c *Config) validate() error {
	if c.GRPCPort < 1024 || c.GRPCPort > 65535 {
		return fmt.Errorf("GRPC_PORT must be 1024..65535, got %d", c.GRPCPort)
	}
	if c.HTTPPort < 1024 || c.HTTPPort > 65535 {
		return fmt.Errorf("HTTP_PORT must be 1024..65535, got %d", c.HTTPPort)
	}
	if c.GRPCPort == c.HTTPPort {
		return fmt.Errorf("GRPC_PORT and HTTP_PORT must differ (both are %d)", c.GRPCPort)
	}

	// The mt5 bridge is the sole broker.Port implementation, so the
	// bridge URL and timeout are always required.
	if strings.TrimSpace(c.BrokerBridgeURL) == "" {
		return fmt.Errorf("BROKER_BRIDGE_URL must not be empty")
	}
	if c.BrokerTimeoutMs < 500 || c.BrokerTimeoutMs > 30000 {
		return fmt.Errorf("BROKER_TIMEOUT_MS must be 500..30000, got %d", c.BrokerTimeoutMs)
	}

	// Resolve the effective environment with the same precedence used
	// in the execution config: prefixed override → root APP_ENV →
	// development. Prevents a prod deploy that exports only root
	// APP_ENV from silently treating this service as development and
	// reducing the secret-required check to a warning.
	env := strings.ToLower(strings.TrimSpace(c.AppEnv))
	if env == "" {
		env = strings.ToLower(strings.TrimSpace(os.Getenv("APP_ENV")))
	}
	if env == "" {
		env = "development"
	}
	isProdLike := env == "production" || env == "prod" || env == "staging"

	c.EngineInternalSecret = strings.TrimSpace(c.EngineInternalSecret)
	// Fall back to the root ENGINE_INTERNAL_SHARED_SECRET when the
	// prefixed override is empty; mirrors the execution config logic.
	if c.EngineInternalSecret == "" {
		c.EngineInternalSecret = strings.TrimSpace(os.Getenv("ENGINE_INTERNAL_SHARED_SECRET"))
	}
	if c.EngineInternalSecret == "" {
		if isProdLike {
			return fmt.Errorf(
				"ENGINE_INTERNAL_SHARED_SECRET must be set in %s; "+
					"the value must match the engine's ENGINE_INTERNAL_SHARED_SECRET",
				env,
			)
		}
	} else if len(c.EngineInternalSecret) < 32 {
		return fmt.Errorf(
			"ENGINE_INTERNAL_SHARED_SECRET must be at least 32 characters, got %d",
			len(c.EngineInternalSecret),
		)
	}
	c.AppEnv = env

	if c.TickPollIntervalMs < 100 || c.TickPollIntervalMs > 10000 {
		return fmt.Errorf("TICK_POLL_INTERVAL_MS must be 100..10000, got %d", c.TickPollIntervalMs)
	}
	if c.CandlePollIntervalSecs < 10 || c.CandlePollIntervalSecs > 600 {
		return fmt.Errorf("CANDLE_POLL_INTERVAL_SECS must be 10..600, got %d", c.CandlePollIntervalSecs)
	}
	if c.ReconcileIntervalSecs < 10 || c.ReconcileIntervalSecs > 600 {
		return fmt.Errorf("RECONCILE_INTERVAL_SECS must be 10..600, got %d", c.ReconcileIntervalSecs)
	}

	if c.DatabaseURL == "" {
		return fmt.Errorf("DATABASE_URL must not be empty")
	}
	// Fail closed on a non-TLS DB connection in production/staging. Only
	// require/verify-ca/verify-full encrypt unconditionally; disable/
	// allow/prefer (and an absent sslmode, which libpq treats as prefer)
	// can yield a plaintext connection.
	if isProdLike {
		u, err := url.Parse(strings.TrimSpace(c.DatabaseURL))
		if err != nil {
			return fmt.Errorf("DATABASE_URL is unparseable: %w", err)
		}
		switch strings.ToLower(strings.TrimSpace(u.Query().Get("sslmode"))) {
		case "require", "verify-ca", "verify-full":
		default:
			return fmt.Errorf("DATABASE_URL is not TLS-encrypted in %s; set sslmode to require, verify-ca, or verify-full", env)
		}
	}
	if c.DatabaseMaxConns < 1 || c.DatabaseMaxConns > 100 {
		return fmt.Errorf("DATABASE_MAX_CONNS must be 1..100, got %d", c.DatabaseMaxConns)
	}

	if c.RedisURL == "" {
		return fmt.Errorf("REDIS_URL must not be empty")
	}
	// Production-mode Redis URL guard. Audit ref: SC-C4 / XS-1.
	if isProdLike {
		if strings.Contains(c.RedisURL, "localhost") || strings.Contains(c.RedisURL, "127.0.0.1") {
			return fmt.Errorf("MANAGEMENT_REDIS_URL points at localhost in %s; refusing the fallback that bypasses ExternalSecrets", env)
		}
	}

	validLevels := map[string]bool{
		"DEBUG": true, "INFO": true, "WARN": true,
		"ERROR": true, "FATAL": true,
	}
	if !validLevels[strings.ToUpper(c.LogLevel)] {
		return fmt.Errorf("LOG_LEVEL must be DEBUG/INFO/WARN/ERROR/FATAL, got %q", c.LogLevel)
	}
	c.LogLevel = strings.ToUpper(c.LogLevel)

	return nil
}

// IsProdLike reports whether the service is running in production or
// staging, reading the AppEnv value normalized by validate().
func (c *Config) IsProdLike() bool {
	return c.AppEnv == "production" || c.AppEnv == "prod" || c.AppEnv == "staging"
}
