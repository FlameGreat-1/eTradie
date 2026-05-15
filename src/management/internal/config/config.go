package config

import (
	"fmt"
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

	// Broker selection: "mock" or "mt5".
	BrokerMode string `envconfig:"BROKER_MODE" default:"mock"`

	// MT5 broker bridge (same Python FastAPI service used by Execution).
	BrokerBridgeURL string `envconfig:"BROKER_BRIDGE_URL" default:"http://localhost:8000"`
	BrokerTimeoutMs int    `envconfig:"BROKER_TIMEOUT_MS" default:"5000"`

	// Shared secret for the engine's /internal/* surface.
	//
	// The Python engine's broker bridge endpoints
	// (src/engine/routers/broker_bridge.py) are protected by
	// engine.shared.internal_auth.verify_internal_auth, which compares
	// the X-Internal-Auth header against ENGINE_INTERNAL_SHARED_SECRET
	// in constant time. Must match the engine's value. Minimum length
	// 32 characters. Required in production/staging when
	// BROKER_MODE=mt5; optional (with a startup warning) in
	// development.
	EngineInternalSecret string `envconfig:"ENGINE_INTERNAL_SHARED_SECRET"`

	// Application environment. Mirrors the engine's APP_ENV to flip
	// the production-grade validation on EngineInternalSecret.
	AppEnv string `envconfig:"APP_ENV" default:"development"`

	// Mock broker starting balance (only used when BrokerMode=mock).
	MockBrokerBalance float64 `envconfig:"MOCK_BROKER_BALANCE" default:"10000.0"`

	// Tick polling interval for live price monitoring (milliseconds).
	TickPollIntervalMs int `envconfig:"TICK_POLL_INTERVAL_MS" default:"1000"`

	// Candle polling interval for structural checks (seconds).
	// Used to check 4H/1D candle closes for invalidation logic.
	CandlePollIntervalSecs int `envconfig:"CANDLE_POLL_INTERVAL_SECS" default:"60"`

	// Database (trade journal, analytics, trade state).
	DatabaseURL         string `envconfig:"DATABASE_URL" required:"true"`
	DatabaseMaxConns    int    `envconfig:"DATABASE_MAX_CONNS" default:"10"`
	DatabaseMinConns    int    `envconfig:"DATABASE_MIN_CONNS" default:"2"`
	DatabaseMaxIdleMs   int    `envconfig:"DATABASE_MAX_IDLE_MS" default:"30000"`
	DatabaseConnMaxLife int    `envconfig:"DATABASE_CONN_MAX_LIFE_SECONDS" default:"3600"`

	// Redis (shared event notification hub).
	RedisURL string `envconfig:"REDIS_URL" default:"redis://localhost:6379/1"`

	// Observability.
	LogLevel        string `envconfig:"LOG_LEVEL" default:"INFO"`
	LogJSON         bool   `envconfig:"LOG_JSON" default:"true"`
	OTELEndpoint    string `envconfig:"OTEL_ENDPOINT" default:"localhost:4317"`
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

	mode := strings.ToLower(c.BrokerMode)
	if mode != "mock" && mode != "mt5" {
		return fmt.Errorf("BROKER_MODE must be mock or mt5, got %q", c.BrokerMode)
	}
	c.BrokerMode = mode

	if mode == "mt5" && c.BrokerBridgeURL == "" {
		return fmt.Errorf("BROKER_BRIDGE_URL must not be empty when BROKER_MODE=mt5")
	}
	if c.BrokerTimeoutMs < 500 || c.BrokerTimeoutMs > 30000 {
		return fmt.Errorf("BROKER_TIMEOUT_MS must be 500..30000, got %d", c.BrokerTimeoutMs)
	}

	env := strings.ToLower(strings.TrimSpace(c.AppEnv))
	isProdLike := env == "production" || env == "prod" || env == "staging"
	c.EngineInternalSecret = strings.TrimSpace(c.EngineInternalSecret)
	if mode == "mt5" {
		if c.EngineInternalSecret == "" {
			if isProdLike {
				return fmt.Errorf(
					"ENGINE_INTERNAL_SHARED_SECRET must be set in %s when BROKER_MODE=mt5; "+
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
	}
	c.AppEnv = env

	if c.TickPollIntervalMs < 100 || c.TickPollIntervalMs > 10000 {
		return fmt.Errorf("TICK_POLL_INTERVAL_MS must be 100..10000, got %d", c.TickPollIntervalMs)
	}
	if c.CandlePollIntervalSecs < 10 || c.CandlePollIntervalSecs > 600 {
		return fmt.Errorf("CANDLE_POLL_INTERVAL_SECS must be 10..600, got %d", c.CandlePollIntervalSecs)
	}

	if c.DatabaseURL == "" {
		return fmt.Errorf("DATABASE_URL must not be empty")
	}
	if c.DatabaseMaxConns < 1 || c.DatabaseMaxConns > 100 {
		return fmt.Errorf("DATABASE_MAX_CONNS must be 1..100, got %d", c.DatabaseMaxConns)
	}

	if c.RedisURL == "" {
		return fmt.Errorf("REDIS_URL must not be empty")
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

// IsMT5Mode returns true when the broker is configured for MT5.
func (c *Config) IsMT5Mode() bool {
	return c.BrokerMode == "mt5"
}
