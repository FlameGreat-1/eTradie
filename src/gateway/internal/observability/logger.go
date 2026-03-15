package observability

import (
	"io"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/rs/zerolog"
)

// sensitiveFields contains field names that must never appear in logs.
var sensitiveFields = map[string]struct{}{
	"password":      {},
	"secret":        {},
	"token":         {},
	"api_key":       {},
	"apikey":        {},
	"api-key":       {},
	"authorization": {},
	"auth":          {},
	"cookie":        {},
	"session":       {},
	"private_key":   {},
	"access_token":  {},
	"refresh_token": {},
	"client_secret": {},
	"ssn":           {},
	"credit_card":   {},
	"card_number":   {},
	"cvv":           {},
	"pin":           {},
}

var (
	rootLogger zerolog.Logger
	loggerOnce sync.Once
)

// InitLogger configures the global structured logger.
// Must be called once at startup. Subsequent calls are no-ops.
func InitLogger(level string, jsonOutput bool) {
	loggerOnce.Do(func() {
		zerolog.TimeFieldFormat = time.RFC3339Nano
		zerolog.TimestampFieldName = "timestamp"
		zerolog.LevelFieldName = "level"
		zerolog.MessageFieldName = "event"

		parsedLevel := parseLevel(level)
		zerolog.SetGlobalLevel(parsedLevel)

		var writer io.Writer
		if jsonOutput {
			writer = os.Stdout
		} else {
			writer = zerolog.ConsoleWriter{
				Out:        os.Stdout,
				TimeFormat: time.RFC3339,
			}
		}

		rootLogger = zerolog.New(writer).
			With().
			Timestamp().
			Str("service", "etradie-gateway").
			Logger()

		rootLogger.Info().
			Str("log_level", parsedLevel.String()).
			Bool("json_output", jsonOutput).
			Msg("logging_configured")
	})
}

func parseLevel(level string) zerolog.Level {
	switch strings.ToUpper(strings.TrimSpace(level)) {
	case "DEBUG":
		return zerolog.DebugLevel
	case "INFO":
		return zerolog.InfoLevel
	case "WARNING", "WARN":
		return zerolog.WarnLevel
	case "ERROR":
		return zerolog.ErrorLevel
	case "CRITICAL", "FATAL":
		return zerolog.FatalLevel
	default:
		return zerolog.InfoLevel
	}
}

// Logger returns a child logger scoped to the given component name.
func Logger(component string) zerolog.Logger {
	return rootLogger.With().Str("component", component).Logger()
}

// WithTraceID returns a child logger with the trace_id field bound.
func WithTraceID(logger zerolog.Logger, traceID string) zerolog.Logger {
	return logger.With().Str("trace_id", traceID).Logger()
}

// WithCycleID returns a child logger with the cycle_id field bound.
func WithCycleID(logger zerolog.Logger, cycleID string) zerolog.Logger {
	return logger.With().Str("cycle_id", cycleID).Logger()
}

// IsSensitiveField checks whether a field name should be redacted in logs.
func IsSensitiveField(name string) bool {
	_, found := sensitiveFields[strings.ToLower(name)]
	return found
}

// RedactedValue is the replacement string for sensitive fields.
const RedactedValue = "***REDACTED***"

// LogPanicRecovery logs a recovered panic with full context for post-mortem analysis.
func LogPanicRecovery(logger zerolog.Logger, recovered interface{}, operation string) {
	logger.Error().
		Str("operation", operation).
		Interface("panic_value", recovered).
		Msg("panic_recovered")
}
