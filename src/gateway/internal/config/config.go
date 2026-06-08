package config

import (
	"fmt"
	"net/url"
	"os"
	"strings"

	"github.com/kelseyhightower/envconfig"
)

// validateProxyUpstream enforces that a browser-facing reverse-proxy
// upstream URL (Option B — single public entry point) is a usable
// http(s) base URL. In production/staging it additionally refuses a
// localhost/127.0.0.1 host: such a value in cluster means the service
// DNS wiring is missing and every proxied dashboard request would fail
// closed against the gateway pod's own loopback. Dev/test are exempt so
// docker-compose and local runs keep working against localhost ports.
func validateProxyUpstream(name, raw string) error {
	v := strings.TrimSpace(raw)
	if v == "" {
		return fmt.Errorf("%s must not be empty", name)
	}
	u, err := url.Parse(v)
	if err != nil {
		return fmt.Errorf("%s is not a valid URL: %w", name, err)
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return fmt.Errorf("%s must be an http(s) URL, got scheme %q", name, u.Scheme)
	}
	if u.Host == "" {
		return fmt.Errorf("%s must include a host", name)
	}
	if isProdLikeEnv() {
		host := strings.ToLower(u.Hostname())
		if host == "localhost" || host == "127.0.0.1" || host == "::1" {
			return fmt.Errorf("%s points at localhost in production; set the in-cluster service DNS (e.g. http://execution.<ns>.svc.cluster.local:8081)", name)
		}
	}
	return nil
}

// Config holds all gateway configuration loaded from environment variables.
// Prefix: GATEWAY_. Validated at startup; the application fails fast on
// invalid values. Every field maps 1:1 to the Python GatewayConfig.
type Config struct {
	// Master switch.
	Enabled bool `envconfig:"ENABLED" default:"true"`

	// Symbols: gateway is the authority for active symbols.
	// Users are expected to add their own symbols via the dashboard matching their broker's format.
	DefaultSymbols []string `envconfig:"DEFAULT_SYMBOLS"`

	// Cycle timing.
	// CycleTimeoutSeconds upper bound raised to 900s so operators can
	// accommodate slow-tail LLM calls (Anthropic p99 for ~280KB user
	// messages with 26 RAG chunks is ~130-180s) without having to edit
	// this file. The default is unchanged; existing deployments keep
	// their current budget.
	CycleIntervalSeconds int `envconfig:"CYCLE_INTERVAL_SECONDS" default:"14400"`
	CycleTimeoutSeconds  int `envconfig:"CYCLE_TIMEOUT_SECONDS" default:"450"`

	// Parallelism.
	MaxConcurrentSymbols          int `envconfig:"MAX_CONCURRENT_SYMBOLS" default:"4"`
	TAMacroParallelTimeoutSeconds int `envconfig:"TA_MACRO_PARALLEL_TIMEOUT_SECONDS" default:"120"`

	// RAG.
	RAGTimeoutSeconds int `envconfig:"RAG_TIMEOUT_SECONDS" default:"30"`

	// Processor LLM.
	// Upper bound is 360s to match Python ProcessorConfig.total_timeout_seconds
	// so the gateway phase deadline and the engine's internal processor
	// timeout are coherent end-to-end.
	ProcessorTimeoutSeconds int `envconfig:"PROCESSOR_TIMEOUT_SECONDS" default:"180"`

	// Guard evaluation.
	GuardTimeoutSeconds int `envconfig:"GUARD_TIMEOUT_SECONDS" default:"10"`

	// Result caching TTLs. Set to 0 to disable caching for that collector.
	TACacheTTLSeconds    int `envconfig:"TA_CACHE_TTL_SECONDS" default:"300"`
	MacroCacheTTLSeconds int `envconfig:"MACRO_CACHE_TTL_SECONDS" default:"600"`

	// Retry policy.
	MaxCycleRetries         int     `envconfig:"MAX_CYCLE_RETRIES" default:"1"`
	RetryBackoffBaseSeconds float64 `envconfig:"RETRY_BACKOFF_BASE_SECONDS" default:"2.0"`

	// Observability.
	LogFullContextPayload bool   `envconfig:"LOG_FULL_CONTEXT_PAYLOAD" default:"false"`
	LogLevel              string `envconfig:"LOG_LEVEL" default:"INFO"`
	LogJSON               bool   `envconfig:"LOG_JSON" default:"true"`

	// HTTP endpoint for Python engine internal API.
	EngineHTTPURL string `envconfig:"ENGINE_HTTP_URL" default:"http://localhost:8000"`

	// Redis.
	RedisURL            string `envconfig:"REDIS_URL" default:"redis://localhost:6379/0"`
	RedisMaxConnections int    `envconfig:"REDIS_MAX_CONNECTIONS" default:"20"`

	// OpenTelemetry. An empty endpoint disables tracing cleanly
	// (no OTLP dial attempts, no export-deadline-exceeded noise in
	// the log). Operators opt in by setting GATEWAY_OTEL_ENDPOINT
	// to a real collector address, e.g. "otel-collector:4317".
	OTELEndpoint    string `envconfig:"OTEL_ENDPOINT" default:""`
	OTELServiceName string `envconfig:"OTEL_SERVICE_NAME" default:"etradie-gateway"`

	// Execution engine (Module B).
	ExecutionEnabled   bool   `envconfig:"EXECUTION_ENABLED" default:"true"`
	ExecutionAddr      string `envconfig:"EXECUTION_ADDR" default:"localhost:50053"`
	ExecutionTimeoutMs int    `envconfig:"EXECUTION_TIMEOUT_MS" default:"5000"`

	// Management engine (Module C).
	ManagementEnabled   bool   `envconfig:"MANAGEMENT_ENABLED" default:"true"`
	ManagementAddr      string `envconfig:"MANAGEMENT_ADDR" default:"localhost:50054"`
	ManagementTimeoutMs int    `envconfig:"MANAGEMENT_TIMEOUT_MS" default:"5000"`

	// Browser-facing reverse-proxy upstreams (Option B — single public
	// entry point). The gateway proxies the SPA's /api/execution/* and
	// /api/management/* prefixes to these internal HTTP servers so the
	// browser only ever talks to the gateway origin. These are the HTTP
	// surfaces (execution http_server.go :8081, management http :8083),
	// NOT the gRPC addresses above which the orchestrator/kill-switch use.
	// Engine's browser HTTP surface (/api/analysis|broker|llm|usage|
	// processor/*) is proxied to EngineHTTPURL, already configured above.
	ExecutionHTTPURL  string `envconfig:"EXECUTION_HTTP_URL" default:"http://localhost:8081"`
	ManagementHTTPURL string `envconfig:"MANAGEMENT_HTTP_URL" default:"http://localhost:8083"`

	// Billing microservice. The gateway calls /internal/checkout on this
	// service so provider API keys never leak into user-facing services.
	BillingServiceURL           string `envconfig:"BILLING_SERVICE_URL" default:"http://billing:8082"`
	BillingInternalSharedSecret string `envconfig:"BILLING_INTERNAL_SHARED_SECRET" required:"true"`
	BillingClientTimeoutMs      int    `envconfig:"BILLING_CLIENT_TIMEOUT_MS" default:"15000"`

	// Engine internal shared secret. The gateway sends this in the
	// X-Internal-Auth header on every call to the engine's /internal/*
	// endpoints so those routes can reject requests that did not
	// originate from the gateway. Must match ENGINE_INTERNAL_SHARED_SECRET
	// on the engine side. Min 32 chars; required in production.
	EngineInternalSharedSecret string `envconfig:"ENGINE_INTERNAL_SHARED_SECRET" required:"true"`

	// HTTP server (health, readiness, metrics).
	HTTPPort int `envconfig:"HTTP_PORT" default:"8080"`

	// gRPC server (gateway API).
	GRPCPort int `envconfig:"GRPC_PORT" default:"50052"`

	// CORS: explicit allowlist of origins permitted to make cross-origin
	// requests. In production, set to the dashboard URL(s). The default
	// allows common local development origins only.
	AllowedOrigins []string `envconfig:"ALLOWED_ORIGINS" default:"http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"`
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

// isProdLikeEnv returns true when APP_ENV / ENV / ENVIRONMENT indicate
// production or staging. Mirrors src/auth/config.go::isProdLikeEnv so
// the gateway and auth services agree on what 'prod-like' means.
func isProdLikeEnv() bool {
	for _, k := range []string{"APP_ENV", "ENV", "ENVIRONMENT"} {
		v := strings.ToLower(strings.TrimSpace(os.Getenv(k)))
		switch v {
		case "production", "prod", "staging":
			return true
		}
	}
	return false
}

// IsProdLike reports whether the gateway is running in production or
// staging, derived from APP_ENV / ENV / ENVIRONMENT.
func (c *Config) IsProdLike() bool {
	return isProdLikeEnv()
}

func (c *Config) validate() error {
	// Cycle timing bounds.
	if c.CycleIntervalSeconds < 60 {
		return fmt.Errorf("CYCLE_INTERVAL_SECONDS must be >= 60, got %d", c.CycleIntervalSeconds)
	}
	if c.CycleTimeoutSeconds < 30 || c.CycleTimeoutSeconds > 900 {
		return fmt.Errorf("CYCLE_TIMEOUT_SECONDS must be 30..900, got %d", c.CycleTimeoutSeconds)
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

	// Processor bounds. Upper bound aligned with Python
	// ProcessorConfig.total_timeout_seconds (max 600s).
	if c.ProcessorTimeoutSeconds < 10 || c.ProcessorTimeoutSeconds > 360 {
		return fmt.Errorf("PROCESSOR_TIMEOUT_SECONDS must be 10..360, got %d", c.ProcessorTimeoutSeconds)
	}

	// Guard bounds.
	if c.GuardTimeoutSeconds < 2 || c.GuardTimeoutSeconds > 30 {
		return fmt.Errorf("GUARD_TIMEOUT_SECONDS must be 2..30, got %d", c.GuardTimeoutSeconds)
	}

	// Cache TTL bounds.
	if c.TACacheTTLSeconds < 0 || c.TACacheTTLSeconds > 3600 {
		return fmt.Errorf("TA_CACHE_TTL_SECONDS must be 0..3600, got %d", c.TACacheTTLSeconds)
	}
	if c.MacroCacheTTLSeconds < 0 || c.MacroCacheTTLSeconds > 3600 {
		return fmt.Errorf("MACRO_CACHE_TTL_SECONDS must be 0..3600, got %d", c.MacroCacheTTLSeconds)
	}

	// Retry bounds.
	if c.MaxCycleRetries < 0 || c.MaxCycleRetries > 3 {
		return fmt.Errorf("MAX_CYCLE_RETRIES must be 0..3, got %d", c.MaxCycleRetries)
	}
	if c.RetryBackoffBaseSeconds < 0.5 || c.RetryBackoffBaseSeconds > 30.0 {
		return fmt.Errorf("RETRY_BACKOFF_BASE_SECONDS must be 0.5..30.0, got %f", c.RetryBackoffBaseSeconds)
	}

	// Timeout budget: sub-phase sum must be less than cycle timeout.
	// Since symbols are processed concurrently (bounded by MaxConcurrentSymbols),
	// the per-symbol phases (RAG + Processor + Guard) overlap. The worst-case
	// wall-clock time for the per-symbol phases is a single pass, not N * pass.
	// Therefore this single-pass check is the correct budget validation.
	perSymbolTimeout := c.RAGTimeoutSeconds + c.ProcessorTimeoutSeconds + c.GuardTimeoutSeconds
	subTotal := c.TAMacroParallelTimeoutSeconds + perSymbolTimeout
	if subTotal >= c.CycleTimeoutSeconds {
		return fmt.Errorf(
			"sum of sub-phase timeouts (TA_MACRO=%ds + per_symbol=%ds = %ds) must be less than "+
				"CYCLE_TIMEOUT_SECONDS (%ds) to allow overhead for context assembly and routing",
			c.TAMacroParallelTimeoutSeconds, perSymbolTimeout, subTotal, c.CycleTimeoutSeconds,
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

	// Browser-facing reverse-proxy upstream validation (Option B).
	// Both must be non-empty, parseable http(s) URLs. In production/
	// staging they must NOT point at localhost: a localhost upstream in
	// cluster silently masks a missing service-DNS wiring and would make
	// the gateway proxy fail closed on every dashboard request. Mirrors
	// the Redis prod guard below.
	if err := validateProxyUpstream("EXECUTION_HTTP_URL", c.ExecutionHTTPURL); err != nil {
		return err
	}
	if err := validateProxyUpstream("MANAGEMENT_HTTP_URL", c.ManagementHTTPURL); err != nil {
		return err
	}
	if err := validateProxyUpstream("ENGINE_HTTP_URL", c.EngineHTTPURL); err != nil {
		return err
	}

	// Billing client validation.
	if strings.TrimSpace(c.BillingServiceURL) == "" {
		return fmt.Errorf("BILLING_SERVICE_URL must not be empty")
	}
	if len(c.BillingInternalSharedSecret) < 32 {
		return fmt.Errorf("BILLING_INTERNAL_SHARED_SECRET must be at least 32 characters")
	}
	if c.BillingClientTimeoutMs < 1000 || c.BillingClientTimeoutMs > 60000 {
		return fmt.Errorf("BILLING_CLIENT_TIMEOUT_MS must be 1000..60000, got %d", c.BillingClientTimeoutMs)
	}

	// Production-mode Redis URL guard. The default redis://localhost:6379/0
	// silently masks a missing ExternalSecret in cluster (engine, gateway,
	// execution, management all share this risk). Refuse to boot in
	// production when REDIS_URL is empty OR points at localhost.
	// Audit ref: SC-C4 / XS-1.
	if isProdLikeEnv() {
		if strings.TrimSpace(c.RedisURL) == "" {
			return fmt.Errorf("GATEWAY_REDIS_URL must be set in production; refusing to boot with empty value")
		}
		if strings.Contains(c.RedisURL, "localhost") || strings.Contains(c.RedisURL, "127.0.0.1") {
			return fmt.Errorf("GATEWAY_REDIS_URL points at localhost in production; refusing the fallback that bypasses ExternalSecrets")
		}
	}

	return nil
}
