package config

import (
	"fmt"
	"strings"

	"github.com/kelseyhightower/envconfig"

	"github.com/flamegreat/etradie/src/execution/internal/constants"
)

// Config holds all execution engine configuration. Loaded from
// environment variables with the EXECUTION_ prefix. Validated at
// startup; the application fails fast on invalid values.
type Config struct {
	// Servers.
	GRPCPort int `envconfig:"GRPC_PORT" default:"50053"`
	HTTPPort int `envconfig:"HTTP_PORT" default:"8080"`

	// Broker selection: "mock" for development, "mt5" for production.
	BrokerMode string `envconfig:"BROKER_MODE" default:"mock"`

	// MT5 broker bridge (Python FastAPI service that wraps MT5 API).
	// Points to the same engine service at src/engine/ which already
	// manages the MT5 connection for TA data.
	BrokerBridgeURL string `envconfig:"BROKER_BRIDGE_URL" default:"http://localhost:8000"`
	BrokerTimeoutMs int    `envconfig:"BROKER_TIMEOUT_MS" default:"5000"`

	// Mock broker starting balance (only used when BrokerMode=mock).
	MockBrokerBalance float64 `envconfig:"MOCK_BROKER_BALANCE" default:"10000.0"`

	// Module C address (for instant mode arming).
	ModuleCAddr string `envconfig:"MODULE_C_ADDR" default:"localhost:50055"`

	// Default execution mode. Dashboard can override via settings store.
	DefaultExecutionMode string `envconfig:"DEFAULT_EXECUTION_MODE" default:"LIMIT"`

	// Position sizing.
	MinLotSize float64 `envconfig:"MIN_LOT_SIZE" default:"0.01"`
	MaxLotSize float64 `envconfig:"MAX_LOT_SIZE" default:"10.0"`

	// Risk controls (defaults; dashboard can override via settings store).
	MaxConcurrentTrades int     `envconfig:"MAX_CONCURRENT_TRADES" default:"3"`
	DailyLossLimitPct   float64 `envconfig:"DAILY_LOSS_LIMIT_PCT" default:"3.0"`
	WeeklyDrawdownPct   float64 `envconfig:"WEEKLY_DRAWDOWN_PCT" default:"5.0"`

	// Spread thresholds.
	SpreadMultiplierNormal   float64 `envconfig:"SPREAD_MULTIPLIER_NORMAL" default:"2.0"`
	SpreadMultiplierScalping float64 `envconfig:"SPREAD_MULTIPLIER_SCALPING" default:"1.5"`

	// News lockout (minutes).
	NewsLockoutMinutes         int `envconfig:"NEWS_LOCKOUT_MINUTES" default:"30"`
	NewsLockoutMinutesScalping int `envconfig:"NEWS_LOCKOUT_MINUTES_SCALPING" default:"45"`

	// Session enablement (comma-separated).
	EnabledSessions []string `envconfig:"ENABLED_SESSIONS" default:"LONDON_OPEN,LONDON_NY_OVERLAP,NEW_YORK"`

	// Instant mode.
	OvershootToleranceMultiplier float64 `envconfig:"OVERSHOOT_TOLERANCE_MULTIPLIER" default:"1.5"`

	// Database (execution audit log, pnl tracker, settings).
	DatabaseURL         string `envconfig:"DATABASE_URL" required:"true"`
	DatabaseMaxConns    int    `envconfig:"DATABASE_MAX_CONNS" default:"10"`
	DatabaseMinConns    int    `envconfig:"DATABASE_MIN_CONNS" default:"2"`
	DatabaseMaxIdleMs   int    `envconfig:"DATABASE_MAX_IDLE_MS" default:"30000"`
	DatabaseConnMaxLife int    `envconfig:"DATABASE_CONN_MAX_LIFE_SECONDS" default:"3600"`

	// Observability.
	LogLevel        string `envconfig:"LOG_LEVEL" default:"INFO"`
	LogJSON         bool   `envconfig:"LOG_JSON" default:"true"`
	OTELEndpoint    string `envconfig:"OTEL_ENDPOINT" default:"localhost:4317"`
	OTELServiceName string `envconfig:"OTEL_SERVICE_NAME" default:"etradie-execution"`

	// HTTP API authentication.
	APIToken string `envconfig:"API_TOKEN" default:""`
}

// Load reads configuration from EXECUTION_ prefixed environment
// variables and validates all constraints.
func Load() (*Config, error) {
	var cfg Config
	if err := envconfig.Process("EXECUTION", &cfg); err != nil {
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

	execMode := strings.ToUpper(c.DefaultExecutionMode)
	if execMode != string(constants.ModeLimit) && execMode != string(constants.ModeInstant) {
		return fmt.Errorf("DEFAULT_EXECUTION_MODE must be LIMIT or INSTANT, got %q", c.DefaultExecutionMode)
	}
	c.DefaultExecutionMode = execMode

	if c.MinLotSize < 0.01 || c.MinLotSize > 1.0 {
		return fmt.Errorf("MIN_LOT_SIZE must be 0.01..1.0, got %f", c.MinLotSize)
	}
	if c.MaxLotSize < c.MinLotSize || c.MaxLotSize > 100.0 {
		return fmt.Errorf("MAX_LOT_SIZE must be >= MIN_LOT_SIZE and <= 100.0, got %f", c.MaxLotSize)
	}

	if c.MaxConcurrentTrades < 1 || c.MaxConcurrentTrades > 10 {
		return fmt.Errorf("MAX_CONCURRENT_TRADES must be 1..10, got %d", c.MaxConcurrentTrades)
	}
	if c.DailyLossLimitPct < 0.5 || c.DailyLossLimitPct > 10.0 {
		return fmt.Errorf("DAILY_LOSS_LIMIT_PCT must be 0.5..10.0, got %f", c.DailyLossLimitPct)
	}
	if c.WeeklyDrawdownPct < 1.0 || c.WeeklyDrawdownPct > 20.0 {
		return fmt.Errorf("WEEKLY_DRAWDOWN_PCT must be 1.0..20.0, got %f", c.WeeklyDrawdownPct)
	}

	if c.SpreadMultiplierNormal < 1.0 || c.SpreadMultiplierNormal > 5.0 {
		return fmt.Errorf("SPREAD_MULTIPLIER_NORMAL must be 1.0..5.0, got %f", c.SpreadMultiplierNormal)
	}
	if c.SpreadMultiplierScalping < 1.0 || c.SpreadMultiplierScalping > 5.0 {
		return fmt.Errorf("SPREAD_MULTIPLIER_SCALPING must be 1.0..5.0, got %f", c.SpreadMultiplierScalping)
	}

	if c.NewsLockoutMinutes < 10 || c.NewsLockoutMinutes > 120 {
		return fmt.Errorf("NEWS_LOCKOUT_MINUTES must be 10..120, got %d", c.NewsLockoutMinutes)
	}
	if c.NewsLockoutMinutesScalping < 10 || c.NewsLockoutMinutesScalping > 120 {
		return fmt.Errorf("NEWS_LOCKOUT_MINUTES_SCALPING must be 10..120, got %d", c.NewsLockoutMinutesScalping)
	}

	if len(c.EnabledSessions) == 0 {
		return fmt.Errorf("ENABLED_SESSIONS must contain at least one session")
	}
	validSessions := map[string]bool{
		"LONDON_OPEN": true, "LONDON_NY_OVERLAP": true,
		"NEW_YORK": true, "ASIAN": true,
	}
	for i, s := range c.EnabledSessions {
		norm := strings.ToUpper(strings.TrimSpace(s))
		if !validSessions[norm] {
			return fmt.Errorf("ENABLED_SESSIONS[%d] %q is not a valid session", i, s)
		}
		c.EnabledSessions[i] = norm
	}

	if c.OvershootToleranceMultiplier < 1.0 || c.OvershootToleranceMultiplier > 3.0 {
		return fmt.Errorf("OVERSHOOT_TOLERANCE_MULTIPLIER must be 1.0..3.0, got %f", c.OvershootToleranceMultiplier)
	}

	if c.DatabaseURL == "" {
		return fmt.Errorf("DATABASE_URL must not be empty")
	}
	if c.DatabaseMaxConns < 1 || c.DatabaseMaxConns > 100 {
		return fmt.Errorf("DATABASE_MAX_CONNS must be 1..100, got %d", c.DatabaseMaxConns)
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

// ExecutionMode returns the parsed default execution mode.
func (c *Config) ExecutionMode() constants.ExecutionMode {
	return constants.ExecutionMode(c.DefaultExecutionMode)
}

// IsSessionEnabled checks if a session name is in the enabled list.
func (c *Config) IsSessionEnabled(session string) bool {
	norm := strings.ToUpper(strings.TrimSpace(session))
	for _, s := range c.EnabledSessions {
		if s == norm {
			return true
		}
	}
	return false
}

// IsMT5Mode returns true when the broker is configured for MT5.
func (c *Config) IsMT5Mode() bool {
	return c.BrokerMode == "mt5"
}
