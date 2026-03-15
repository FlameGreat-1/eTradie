package observability

import (
	"os"
	"strings"

	"github.com/rs/zerolog"
)

var baseLogger zerolog.Logger

func init() {
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnixMs
	baseLogger = zerolog.New(os.Stdout).With().Timestamp().Str("service", "execution").Logger()
}

// SetLevel configures the global log level.
func SetLevel(level string) {
	switch strings.ToUpper(level) {
	case "DEBUG":
		zerolog.SetGlobalLevel(zerolog.DebugLevel)
	case "INFO":
		zerolog.SetGlobalLevel(zerolog.InfoLevel)
	case "WARN":
		zerolog.SetGlobalLevel(zerolog.WarnLevel)
	case "ERROR":
		zerolog.SetGlobalLevel(zerolog.ErrorLevel)
	case "FATAL":
		zerolog.SetGlobalLevel(zerolog.FatalLevel)
	default:
		zerolog.SetGlobalLevel(zerolog.InfoLevel)
	}
}

// Logger returns a child logger tagged with the given component name.
func Logger(component string) zerolog.Logger {
	return baseLogger.With().Str("component", component).Logger()
}
