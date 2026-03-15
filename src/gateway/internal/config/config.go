package config

import (
	"fmt"
	"strings"

	"github.com/kelseyhightower/envconfig"
)

// Config holds all gateway configuration loaded from environment variables.
// Prefix: GATEWAY_. Validated at startup; the application fails fast on
// invalid values. Every field maps 1:1 to the Python GatewayConfig.
type Config struct {
	// Master switch.
	Enabled bool `envconfig:"ENABLED" default:"true"`

	// Symbols: gateway is the authority for active symbols.
	DefaultSymbols []string `envconfig:"DEFAULT_SYMBOLS" default:"EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,NZDUSD,USDCAD,XAUUSD"`

	// Cycle timing.
	CycleIntervalSeconds int `envconfig:"CYCLE_INTERVAL_SECONDS" default:"14400"`
	CycleTimeoutSeconds  int `envconfig:"CYCLE_TIMEOUT_SECONDS" default:"300"`

	// Parallelism.
	MaxConcurrentSymbols          int `envconfig:"MAX_CONCURRENT_SYMBOLS" default:"4"`
	TAMacroParallelTimeoutSeconds int `envconfig:"TA_MACRO_PARALLEL_TIMEOUT_SECONDS" default:"120"`

	// RAG.
	RAGTimeoutSeconds int `envconfig:"RAG_TIMEOUT_SECONDS" default:"30"`

	// Processor LLM.
	ProcessorTimeoutSeconds int `envconfig:"PROCESSOR_TIMEOUT_SECONDS" default:"60"`

	// Guard evaluation.
	GuardTimeoutSeconds int `envconfig:"GUARD_TIMEOUT_SECONDS" default:"10"`

	// Retry policy.
	MaxCycleRetries          int     `envconfig:"MAX_CYCLE_RETRIES" default:"1"`
	RetryBackoffBaseSeconds  float64 `envconfig:"RETRY_BACKOFF_BASE_SECONDS" default:"2.0"`

	// Observability.
	LogFullContextPayload bool   `envconfig:"LOG_FULL_CONTEXT_PAYLOAD" default:"false"`
	LogLevel              string `envconfig:"LOG_LEVEL" default:"INFO"`
	LogJSON               bool   `envconfig:"LOG_JSON" default:"true"`

	// gRPC endpoints for Python engine services.
	EngineGRPCAddress string `envconfig:"ENGINE_GRPC_ADDRESS" default:"localhost:50051"`

	// Redis.
	RedisURL            string `envconfig:"REDIS_URL" default:"redis://localhost:6379/0"`
	RedisMaxConnections int    `envconfig:"REDIS_MAX_CONNECTIONS" default:"20"`

	// OpenTelemetry.
	OTELEndpoint    string `envconfig:"OTEL_ENDPOINT" default:"localhost:4317"`
	OTELServiceName string `envconfig:"OTEL_SERVICE_NAME" default:"etradie-gateway"`

	// HTTP server (health, readiness, metrics).
	HTTPPort int `envconfig:"HTTP_PORT" default:"8080"`

	// gRPC server (gateway API).
	GRPCPort int `envconfig:"GRPC_PORT" default:"50052"`
}

// Load reads configuration from environment variables with the GATEWAY_ prefix
// and validates all constraints. Returns an error on any invalid value.
func Load() (*Config, error) {
	var cfg Config
	if err := envconfig.Process("GATEWAY", &cfg); err != nil {
		return nil, fmt.Errorf("config: load from env: %w", err)
	}
	if err := cfg.validate(); err != nil {
		return nil, fmt.Errorf("config: validation failed: %w", err)
	}
	return &cfg, nil
}

func (c *Config) validate() error {
	// Cycle timing bounds.
	if c.CycleIntervalSeconds < 60 {
		return fmt.Errorf("CYCLE_INTERVAL_SECONDS must be >= 60, got %d", c.CycleIntervalSeconds)
	}
	if c.CycleTimeoutSeconds < 30 || c.CycleTimeoutSeconds > 600 {
		return fmt.Errorf("CYCLE_TIMEOUT_SECONDS must be 30..600, got %d", c.CycleTimeoutSeconds)
	}

	// Parallelism bounds.
	if c.MaxConcurrentSymbols < 1 || c.MaxConcurrentSymbols > 16 {
		return fmt.Errorf("MAX_CONCURRENT_SYMBOLS must be 1..16, got %d", c.MaxConcurrentSymbols)
	}
	if c.TAMacroParallelTimeoutSeconds < 10 || c.TAMacroParallelTimeoutSeconds > 300 {
		return fmt.Errorf("TA_MACRO_PARALLEL_TIMEOUT_SECONDS must be 10..300, got %d", c.TAMacroParallelTimeoutSeconds)
	}

	// RAG bounds.
	if c.RAGTimeoutSeconds < 5 || c.RAGTimeoutSeconds > 120 {
		return fmt.Errorf("RAG_TIMEOUT_SECONDS must be 5..120, got %d", c.RAGTimeoutSeconds)
	}

	// Processor bounds.
	if c.ProcessorTimeoutSeconds < 10 || c.ProcessorTimeoutSeconds > 180 {
		return fmt.Errorf("PROCESSOR_TIMEOUT_SECONDS must be 10..180, got %d", c.ProcessorTimeoutSeconds)
	}

	// Guard bounds.
	if c.GuardTimeoutSeconds < 2 || c.GuardTimeoutSeconds > 30 {
		return fmt.Errorf("GUARD_TIMEOUT_SECONDS must be 2..30, got %d", c.GuardTimeoutSeconds)
	}

	// Retry bounds.
	if c.MaxCycleRetries < 0 || c.MaxCycleRetries > 3 {
		return fmt.Errorf("MAX_CYCLE_RETRIES must be 0..3, got %d", c.MaxCycleRetries)
	}
	if c.RetryBackoffBaseSeconds < 0.5 || c.RetryBackoffBaseSeconds > 30.0 {
		return fmt.Errorf("RETRY_BACKOFF_BASE_SECONDS must be 0.5..30.0, got %f", c.RetryBackoffBaseSeconds)
	}

	// Timeout budget: sub-phase sum must be less than cycle timeout.
	subTotal := c.TAMacroParallelTimeoutSeconds +
		c.RAGTimeoutSeconds +
		c.ProcessorTimeoutSeconds +
		c.GuardTimeoutSeconds
	if subTotal >= c.CycleTimeoutSeconds {
		return fmt.Errorf(
			"sum of sub-phase timeouts (%ds) must be less than CYCLE_TIMEOUT_SECONDS (%ds) "+
				"to allow overhead for context assembly and routing",
			subTotal, c.CycleTimeoutSeconds,
		)
	}

	// Log level validation.
	validLevels := map[string]bool{
		"DEBUG": true, "INFO": true, "WARNING": true, "WARN": true,
		"ERROR": true, "CRITICAL": true, "FATAL": true,
	}
	if !validLevels[strings.ToUpper(c.LogLevel)] {
		return fmt.Errorf("LOG_LEVEL must be one of DEBUG/INFO/WARNING/ERROR/CRITICAL, got %q", c.LogLevel)
	}

	// Port bounds.
	if c.HTTPPort < 1024 || c.HTTPPort > 65535 {
		return fmt.Errorf("HTTP_PORT must be 1024..65535, got %d", c.HTTPPort)
	}
	if c.GRPCPort < 1024 || c.GRPCPort > 65535 {
		return fmt.Errorf("GRPC_PORT must be 1024..65535, got %d", c.GRPCPort)
	}
	if c.HTTPPort == c.GRPCPort {
		return fmt.Errorf("HTTP_PORT and GRPC_PORT must be different, both are %d", c.HTTPPort)
	}

	// Default symbols must not be empty.
	if len(c.DefaultSymbols) == 0 {
		return fmt.Errorf("DEFAULT_SYMBOLS must contain at least one symbol")
	}

	return nil
}
