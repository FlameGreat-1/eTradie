package config

import (
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/kelseyhightower/envconfig"

	"github.com/flamegreat-1/etradie/src/execution/internal/constants"
)

// Config holds all execution engine configuration. Loaded from
// environment variables with the EXECUTION_ prefix. Validated at
// startup; the application fails fast on invalid values.
type Config struct {
	// Servers.
	GRPCPort int `envconfig:"GRPC_PORT" default:"50053"`
	HTTPPort int `envconfig:"HTTP_PORT" default:"8080"`

	// Broker selection: "mock" or "mt5".
	BrokerMode string `envconfig:"BROKER_MODE" default:"mock"`

	// MT5 broker bridge (Python FastAPI service that wraps MT5 API).
	BrokerBridgeURL string `envconfig:"BROKER_BRIDGE_URL" default:"http://localhost:8000"`
	BrokerTimeoutMs int    `envconfig:"BROKER_TIMEOUT_MS" default:"5000"`

	// Section 3: end-to-end latency kill-switch. When a placement
	// (validate + size + broker round-trip) takes longer than this,
	// the order is REJECTED even if the broker accepted it, and a
	// best-effort CancelOrder is fired so the slow placement does
	// not linger as a real exposure.
	MaxOrderLatencyMs int `envconfig:"MAX_ORDER_LATENCY_MS" default:"5000"`

	// Section 3: idempotency window. A second submission with the
	// same (user_id, idempotency_key) within this window short-
	// circuits without a broker call.
	OrderIdempotencyTTLSecs int `envconfig:"ORDER_IDEMPOTENCY_TTL_SECS" default:"86400"`

	// Section 3: broker reconciliation cadence. Every N seconds the
	// reconciler compares the broker's positions + pending orders
	// against the engine's view and surfaces drift.
	ReconcileIntervalSecs int `envconfig:"RECONCILE_INTERVAL_SECS" default:"60"`

	// Section 3: order intake backpressure. The BurstQueue gates the
	// ExecuteTrade pipeline: QueueMaxConcurrent bounds total in-flight
	// placements cluster-wide, QueuePerUserCap bounds one user's
	// in-flight placements so a noisy user cannot starve others, and
	// QueueDeadlineMs is the max time an order waits for a slot before
	// it is dropped (the broker price has moved; a stale order is
	// worse than a clear rejection).
	QueueMaxConcurrent int `envconfig:"QUEUE_MAX_CONCURRENT" default:"8"`
	QueuePerUserCap    int `envconfig:"QUEUE_PER_USER_CAP" default:"4"`
	QueueDeadlineMs    int `envconfig:"QUEUE_DEADLINE_MS" default:"2000"`

	// Section 7 (CHECKLIST): position snapshots.
	//
	// PositionSnapshotEnabled is the operator kill-switch. When false
	// the reconciler runs the legacy Section-3 path (no snapshot writes,
	// no ghost detection). The execution_positions_snapshot table is
	// still created by SchemaSQL() but remains empty.
	PositionSnapshotEnabled bool `envconfig:"POSITION_SNAPSHOT_ENABLED" default:"true"`

	// PositionSnapshotRetentionHours bounds the snapshot table. The
	// retention sweeper goroutine in main.go prunes rows older than
	// this value every 1h. Default 168 (7 days) matches the regulatory
	// minimum for retail trading audit. Range 1..720 (1h to 30d).
	PositionSnapshotRetentionHours int `envconfig:"POSITION_SNAPSHOT_RETENTION_HOURS" default:"168"`

	// GhostPositionMinAgeSecs is the minimum age the latest snapshot
	// must have before the reconciler classifies a 'broker no longer
	// reports' position as a ghost. Without this threshold, a position
	// closed in the SAME reconcile cycle as the broker reply would be
	// classified as a ghost even though the close is fresh. Default
	// 300s (5 min) comfortably exceeds the default 60s reconcile
	// cadence + broker REST latency. Range 60..3600 (1min..1h).
	GhostPositionMinAgeSecs int `envconfig:"GHOST_POSITION_MIN_AGE_SECS" default:"300"`

	// Section 7 Step C (CHECKLIST): eager position preload on startup.
	//
	// PreloadPositionsOnStart controls whether the execution service
	// eagerly calls state.Manager.Refresh() for every active user
	// BEFORE the gRPC listener opens. When true, the engine's in-memory
	// position state is hot before the first user request lands,
	// eliminating the 'memory empty on restart' gap that the reconciler
	// would otherwise close lazily within 60s.
	//
	// Set to false in dev/test environments where the broker bridge is
	// not available at startup (the Refresh() call would fail and log
	// errors for every user). Default true for production.
	PreloadPositionsOnStart bool `envconfig:"PRELOAD_POSITIONS_ON_START" default:"true"`

	// Shared secret for the engine's /internal/* surface.
	//
	// The Python engine's broker bridge endpoints
	// (src/engine/routers/broker_bridge.py) are protected by
	// engine.shared.internal_auth.verify_internal_auth, which compares
	// the X-Internal-Auth header against ENGINE_INTERNAL_SHARED_SECRET
	// in constant time. Without a matching secret the bridge cannot
	// fetch live broker state and the dashboard header reads empty.
	//
	// Must match the engine's ENGINE_INTERNAL_SHARED_SECRET. Minimum
	// length 32 characters (same policy as the engine and billing
	// services). Required in production/staging when BROKER_MODE=mt5;
	// optional in development (a warning is logged at startup).
	EngineInternalSecret string `envconfig:"ENGINE_INTERNAL_SHARED_SECRET"`

	// Application environment. Used to decide whether the engine
	// internal secret is mandatory (production/staging) or optional
	// (development / local). Mirrors the engine's APP_ENV variable so
	// a single deploy-time value flips both services in lockstep.
	//
	// Note: envconfig.Process with prefix "EXECUTION" looks up the
	// env var EXECUTION_APP_ENV (prefix + tag). Production deployments
	// generally export only root APP_ENV, so validate() falls back to
	// os.Getenv("APP_ENV") when this field is empty / left at default.
	AppEnv string `envconfig:"APP_ENV" default:""`

	// ----------------------------------------------------------------
	// Order-integrity request signing (CHECKLIST Tier 8: signed internal
	// execution requests + replay attack protection).
	//
	// The gateway signs every ExecuteTrade call (HMAC-SHA256 over a
	// canonical request string, carried in gRPC metadata) and execution
	// verifies it in a dedicated interceptor before any broker work.
	// ----------------------------------------------------------------

	// RequireSignedRequests controls enforcement of the ExecuteTrade
	// signature gate. An empty string (the default) is resolved in
	// validate(): ENFORCE in prod-like environments, warn-only
	// otherwise, so a phased rollout is possible without a flag day.
	// Set explicitly to "true"/"false" to override. The resolved
	// boolean is exposed via RequireSignedRequestsEnabled().
	RequireSignedRequests string `envconfig:"REQUIRE_SIGNED_REQUESTS" default:""`

	// RequestSignatureMaxSkewSecs is the freshness window (both clock
	// directions) AND the anti-replay nonce TTL. Default 30s. Range
	// 5..300. A request whose signed timestamp is outside now ± window
	// is rejected as stale.
	RequestSignatureMaxSkewSecs int `envconfig:"REQUEST_SIGNATURE_MAX_SKEW_SECS" default:"30"`

	// RequestSigningSecret is an OPTIONAL dedicated HMAC key for the
	// ExecuteTrade signature. When empty (the default) the verifier
	// falls back to EngineInternalSecret — the value the gateway and
	// execution already share from Vault — so no new secret is needed.
	RequestSigningSecret string `envconfig:"REQUEST_SIGNING_SECRET" default:""`

	// requireSignedRequests is the resolved boolean from
	// RequireSignedRequests (computed in validate()).
	requireSignedRequests bool

	// Mock broker starting balance (only used when BrokerMode=mock).
	MockBrokerBalance float64 `envconfig:"MOCK_BROKER_BALANCE" default:"10000.0"`

	// Gateway address (for instant mode confirmation callbacks).
	GatewayAddr string `envconfig:"GATEWAY_ADDR" default:"localhost:50052"`

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

	// Instant mode watcher.
	OvershootToleranceMultiplier   float64 `envconfig:"OVERSHOOT_TOLERANCE_MULTIPLIER" default:"1.5"`
	WatcherPollIntervalMs          int     `envconfig:"WATCHER_POLL_INTERVAL_MS" default:"500"`
	WatcherTimeoutMinutes          int     `envconfig:"WATCHER_TIMEOUT_MINUTES" default:"45"`
	WatcherConfirmPollIntervalSecs int     `envconfig:"WATCHER_CONFIRM_POLL_INTERVAL_SECS" default:"300"`

	// Database (execution audit log, pnl tracker, settings).
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
	OTELServiceName string `envconfig:"OTEL_SERVICE_NAME" default:"etradie-execution"`
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

	// Engine internal shared secret: required for MT5 mode in
	// production/staging because every /internal/broker/* call needs
	// it. In development we allow an empty value so a local docker-
	// compose run without secrets-management still boots; the bridge
	// will log a warning and every call will 401, which surfaces the
	// misconfiguration quickly at the dashboard layer.
	// Resolve the effective environment. Prefer the prefixed value
	// (EXECUTION_APP_ENV) when set explicitly; otherwise fall back to
	// the shared root APP_ENV. Default to "development" only when
	// neither is set, so a production deploy that exports only the
	// root variable still flips this service into prod mode and the
	// secret-required check below is enforced rather than warned.
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
	// prefixed override (EXECUTION_ENGINE_INTERNAL_SHARED_SECRET) is
	// empty. Production deploy templates have always exported one
	// root value shared with the engine and gateway; the prefixed
	// form is only useful when an operator deliberately wants per-
	// service secrets, which is unusual.
	if c.EngineInternalSecret == "" {
		c.EngineInternalSecret = strings.TrimSpace(os.Getenv("ENGINE_INTERNAL_SHARED_SECRET"))
	}
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

	// Order-integrity request signing (Tier 8 F-1/F-2). Resolve the
	// enforcement mode: an explicit true/false wins; an empty value
	// defaults to ENFORCE in prod-like envs and warn-only elsewhere.
	switch strings.ToLower(strings.TrimSpace(c.RequireSignedRequests)) {
	case "true", "1", "yes", "on":
		c.requireSignedRequests = true
	case "false", "0", "no", "off":
		c.requireSignedRequests = false
	case "":
		c.requireSignedRequests = isProdLike
	default:
		return fmt.Errorf("REQUIRE_SIGNED_REQUESTS must be true/false (or empty to auto-resolve), got %q", c.RequireSignedRequests)
	}
	if c.RequestSignatureMaxSkewSecs < 5 || c.RequestSignatureMaxSkewSecs > 300 {
		return fmt.Errorf("REQUEST_SIGNATURE_MAX_SKEW_SECS must be 5..300, got %d", c.RequestSignatureMaxSkewSecs)
	}
	c.RequestSigningSecret = strings.TrimSpace(c.RequestSigningSecret)
	// When enforcement is on, a usable HMAC key MUST exist now so the
	// deploy fails fast instead of rejecting every trade at runtime.
	if c.requireSignedRequests {
		if key := c.RequestSigningKey(); len(key) < 32 {
			return fmt.Errorf(
				"request signing is enforced but no usable key is available: set EXECUTION_REQUEST_SIGNING_SECRET "+
					"(>=32 chars) or ensure ENGINE_INTERNAL_SHARED_SECRET (>=32 chars) is configured",
			)
		}
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
	if c.WatcherPollIntervalMs < 100 || c.WatcherPollIntervalMs > 5000 {
		return fmt.Errorf("WATCHER_POLL_INTERVAL_MS must be 100..5000, got %d", c.WatcherPollIntervalMs)
	}
	// WatcherTimeoutMinutes is the fallback for unrecognized trading
	// styles. The style-specific map (constants.WatcherTimeoutMinutesByStyle)
	// takes precedence for known styles (up to 10080 min / 7 days for
	// positional). The fallback must support the same range so operators
	// can set a global override if needed.
	if c.WatcherTimeoutMinutes < 5 || c.WatcherTimeoutMinutes > 10080 {
		return fmt.Errorf("WATCHER_TIMEOUT_MINUTES must be 5..10080, got %d", c.WatcherTimeoutMinutes)
	}
	if c.WatcherConfirmPollIntervalSecs < 60 || c.WatcherConfirmPollIntervalSecs > 600 {
		return fmt.Errorf("WATCHER_CONFIRM_POLL_INTERVAL_SECS must be 60..600, got %d", c.WatcherConfirmPollIntervalSecs)
	}
	if c.GatewayAddr == "" {
		return fmt.Errorf("GATEWAY_ADDR must not be empty")
	}

	// Section 7 (CHECKLIST): position snapshot ranges.
	if c.PositionSnapshotRetentionHours < 1 || c.PositionSnapshotRetentionHours > 720 {
		return fmt.Errorf("POSITION_SNAPSHOT_RETENTION_HOURS must be 1..720, got %d", c.PositionSnapshotRetentionHours)
	}
	if c.GhostPositionMinAgeSecs < 60 || c.GhostPositionMinAgeSecs > 3600 {
		return fmt.Errorf("GHOST_POSITION_MIN_AGE_SECS must be 60..3600, got %d", c.GhostPositionMinAgeSecs)
	}
	if c.QueueMaxConcurrent < 1 || c.QueueMaxConcurrent > 256 {
		return fmt.Errorf("QUEUE_MAX_CONCURRENT must be 1..256, got %d", c.QueueMaxConcurrent)
	}
	if c.QueuePerUserCap < 1 || c.QueuePerUserCap > c.QueueMaxConcurrent {
		return fmt.Errorf("QUEUE_PER_USER_CAP must be 1..QUEUE_MAX_CONCURRENT (%d), got %d", c.QueueMaxConcurrent, c.QueuePerUserCap)
	}
	if c.QueueDeadlineMs < 100 || c.QueueDeadlineMs > 30000 {
		return fmt.Errorf("QUEUE_DEADLINE_MS must be 100..30000, got %d", c.QueueDeadlineMs)
	}
	// PreloadPositionsOnStart is a bool; no range check.

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
	// Production-mode Redis URL guard. Default redis://localhost:6379/1
	// silently masks a missing ExternalSecret in cluster. Audit ref:
	// SC-C4 / XS-1.
	if isProdLike {
		if strings.Contains(c.RedisURL, "localhost") || strings.Contains(c.RedisURL, "127.0.0.1") {
			return fmt.Errorf("EXECUTION_REDIS_URL points at localhost in %s; refusing the fallback that bypasses ExternalSecrets", env)
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

// RequireSignedRequestsEnabled reports the resolved enforcement mode
// for the ExecuteTrade signature gate (Tier 8 F-1/F-2). When false the
// verifier runs in warn-only mode: it observes/labels outcomes but does
// not reject.
func (c *Config) RequireSignedRequestsEnabled() bool {
	return c.requireSignedRequests
}

// RequestSignatureMaxSkew returns the freshness window / nonce TTL.
func (c *Config) RequestSignatureMaxSkew() time.Duration {
	return time.Duration(c.RequestSignatureMaxSkewSecs) * time.Second
}

// RequestSigningKey returns the HMAC key for ExecuteTrade signatures:
// the dedicated RequestSigningSecret when set, otherwise the shared
// EngineInternalSecret (already loaded from Vault and identical on the
// gateway side). Returns nil when neither is available.
func (c *Config) RequestSigningKey() []byte {
	if c.RequestSigningSecret != "" {
		return []byte(c.RequestSigningSecret)
	}
	if c.EngineInternalSecret != "" {
		return []byte(c.EngineInternalSecret)
	}
	return nil
}
