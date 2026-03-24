package config

import (
	"strings"
	"testing"
)

// validConfig returns a Config that passes all validation rules.
// Tests mutate a single field to isolate each rule.
func validConfig() *Config {
	return &Config{
		Enabled:                       true,
		DefaultSymbols:                []string{"EURUSD", "GBPUSD"},
		CycleIntervalSeconds:          14400,
		CycleTimeoutSeconds:           300,
		MaxConcurrentSymbols:          4,
		TAMacroParallelTimeoutSeconds: 120,
		RAGTimeoutSeconds:             30,
		ProcessorTimeoutSeconds:       60,
		GuardTimeoutSeconds:           10,
		TACacheTTLSeconds:             300,
		MacroCacheTTLSeconds:          600,
		MaxCycleRetries:               1,
		RetryBackoffBaseSeconds:       2.0,
		LogLevel:                      "INFO",
		EngineHTTPURL:                 "http://localhost:8000",
		RedisURL:                      "redis://localhost:6379/0",
		RedisMaxConnections:           20,
		OTELEndpoint:                  "localhost:4317",
		OTELServiceName:               "etradie-gateway",
		ExecutionEnabled:              true,
		ExecutionAddr:                 "localhost:50053",
		ExecutionTimeoutMs:            5000,
		ManagementEnabled:             true,
		ManagementAddr:                "localhost:50054",
		ManagementTimeoutMs:           5000,
		HTTPPort:                      8080,
		GRPCPort:                      50052,
	}
}

// TestValidConfig_Passes confirms the baseline config is valid.
func TestValidConfig_Passes(t *testing.T) {
	cfg := validConfig()
	if err := cfg.validate(); err != nil {
		t.Fatalf("expected valid config to pass, got: %v", err)
	}
}

// --- Cycle Timing ---

func TestValidate_CycleIntervalSeconds_AtMinimum(t *testing.T) {
	cfg := validConfig()
	cfg.CycleIntervalSeconds = 60
	if err := cfg.validate(); err != nil {
		t.Fatalf("interval=60 should be valid, got: %v", err)
	}
}

func TestValidate_CycleIntervalSeconds_BelowMinimum(t *testing.T) {
	cfg := validConfig()
	cfg.CycleIntervalSeconds = 59
	err := cfg.validate()
	if err == nil {
		t.Fatal("interval=59 should fail validation")
	}
	if !strings.Contains(err.Error(), "CYCLE_INTERVAL_SECONDS") {
		t.Fatalf("error should mention CYCLE_INTERVAL_SECONDS, got: %v", err)
	}
}

func TestValidate_CycleIntervalSeconds_Zero(t *testing.T) {
	cfg := validConfig()
	cfg.CycleIntervalSeconds = 0
	err := cfg.validate()
	if err == nil {
		t.Fatal("interval=0 should fail validation")
	}
}

func TestValidate_CycleTimeoutSeconds_AtLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.CycleTimeoutSeconds = 300
	// Ensure sub-phase budget still fits.
	cfg.TAMacroParallelTimeoutSeconds = 120
	cfg.RAGTimeoutSeconds = 30
	cfg.ProcessorTimeoutSeconds = 60
	cfg.GuardTimeoutSeconds = 10
	// sub-phase = 120 + 30 + 60 + 10 = 220 < 300 ✓
	if err := cfg.validate(); err != nil {
		t.Fatalf("timeout=300 should be valid, got: %v", err)
	}
}

func TestValidate_CycleTimeoutSeconds_BelowLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.CycleTimeoutSeconds = 29
	err := cfg.validate()
	if err == nil {
		t.Fatal("timeout=29 should fail validation")
	}
	if !strings.Contains(err.Error(), "CYCLE_TIMEOUT_SECONDS") {
		t.Fatalf("error should mention CYCLE_TIMEOUT_SECONDS, got: %v", err)
	}
}

func TestValidate_CycleTimeoutSeconds_AtUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.CycleTimeoutSeconds = 600
	// sub-phase = 120 + 100 = 220 < 600 ✓
	if err := cfg.validate(); err != nil {
		t.Fatalf("timeout=600 should be valid, got: %v", err)
	}
}

func TestValidate_CycleTimeoutSeconds_AboveUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.CycleTimeoutSeconds = 601
	err := cfg.validate()
	if err == nil {
		t.Fatal("timeout=601 should fail validation")
	}
}

// --- Parallelism ---

func TestValidate_MaxConcurrentSymbols_AtLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.MaxConcurrentSymbols = 1
	if err := cfg.validate(); err != nil {
		t.Fatalf("concurrent=1 should be valid, got: %v", err)
	}
}

func TestValidate_MaxConcurrentSymbols_AtUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.MaxConcurrentSymbols = 16
	if err := cfg.validate(); err != nil {
		t.Fatalf("concurrent=16 should be valid, got: %v", err)
	}
}

func TestValidate_MaxConcurrentSymbols_Zero(t *testing.T) {
	cfg := validConfig()
	cfg.MaxConcurrentSymbols = 0
	err := cfg.validate()
	if err == nil {
		t.Fatal("concurrent=0 should fail validation")
	}
	if !strings.Contains(err.Error(), "MAX_CONCURRENT_SYMBOLS") {
		t.Fatalf("error should mention MAX_CONCURRENT_SYMBOLS, got: %v", err)
	}
}

func TestValidate_MaxConcurrentSymbols_AboveUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.MaxConcurrentSymbols = 17
	err := cfg.validate()
	if err == nil {
		t.Fatal("concurrent=17 should fail validation")
	}
}

func TestValidate_TAMacroParallelTimeout_AtLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.TAMacroParallelTimeoutSeconds = 10
	// sub-phase = 10 + 100 = 110 < 300 ✓
	if err := cfg.validate(); err != nil {
		t.Fatalf("ta_macro=10 should be valid, got: %v", err)
	}
}

func TestValidate_TAMacroParallelTimeout_BelowLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.TAMacroParallelTimeoutSeconds = 9
	err := cfg.validate()
	if err == nil {
		t.Fatal("ta_macro=9 should fail validation")
	}
	if !strings.Contains(err.Error(), "TA_MACRO_PARALLEL_TIMEOUT_SECONDS") {
		t.Fatalf("error should mention TA_MACRO_PARALLEL_TIMEOUT_SECONDS, got: %v", err)
	}
}

func TestValidate_TAMacroParallelTimeout_AtUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.TAMacroParallelTimeoutSeconds = 200
	// sub-phase = 200 + 100 = 300 >= 300 → budget violation.
	// Need cycle timeout > 300.
	cfg.CycleTimeoutSeconds = 301
	if err := cfg.validate(); err != nil {
		t.Fatalf("ta_macro=200 with timeout=301 should be valid, got: %v", err)
	}
}

func TestValidate_TAMacroParallelTimeout_AboveUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.TAMacroParallelTimeoutSeconds = 301
	err := cfg.validate()
	if err == nil {
		t.Fatal("ta_macro=301 should fail validation")
	}
}

// --- RAG Timeout ---

func TestValidate_RAGTimeout_AtLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.RAGTimeoutSeconds = 5
	// sub-phase = 120 + 5 + 60 + 10 = 195 < 300 ✓
	if err := cfg.validate(); err != nil {
		t.Fatalf("rag=5 should be valid, got: %v", err)
	}
}

func TestValidate_RAGTimeout_BelowLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.RAGTimeoutSeconds = 4
	err := cfg.validate()
	if err == nil {
		t.Fatal("rag=4 should fail validation")
	}
	if !strings.Contains(err.Error(), "RAG_TIMEOUT_SECONDS") {
		t.Fatalf("error should mention RAG_TIMEOUT_SECONDS, got: %v", err)
	}
}

func TestValidate_RAGTimeout_AtUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.RAGTimeoutSeconds = 120
	// sub-phase = 120 + 120 + 60 + 10 = 310 >= 300 → budget violation.
	// Increase cycle timeout.
	cfg.CycleTimeoutSeconds = 311
	if err := cfg.validate(); err != nil {
		t.Fatalf("rag=120 with timeout=311 should be valid, got: %v", err)
	}
}

func TestValidate_RAGTimeout_AboveUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.RAGTimeoutSeconds = 121
	err := cfg.validate()
	if err == nil {
		t.Fatal("rag=121 should fail validation")
	}
}

// --- Processor Timeout ---

func TestValidate_ProcessorTimeout_AtLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.ProcessorTimeoutSeconds = 10
	// sub-phase = 120 + 30 + 10 + 10 = 170 < 300 ✓
	if err := cfg.validate(); err != nil {
		t.Fatalf("processor=10 should be valid, got: %v", err)
	}
}

func TestValidate_ProcessorTimeout_BelowLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.ProcessorTimeoutSeconds = 9
	err := cfg.validate()
	if err == nil {
		t.Fatal("processor=9 should fail validation")
	}
	if !strings.Contains(err.Error(), "PROCESSOR_TIMEOUT_SECONDS") {
		t.Fatalf("error should mention PROCESSOR_TIMEOUT_SECONDS, got: %v", err)
	}
}

func TestValidate_ProcessorTimeout_AtUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.ProcessorTimeoutSeconds = 180
	// sub-phase = 120 + 30 + 180 + 10 = 340 >= 300 → budget violation.
	cfg.CycleTimeoutSeconds = 341
	if err := cfg.validate(); err != nil {
		t.Fatalf("processor=180 with timeout=341 should be valid, got: %v", err)
	}
}

func TestValidate_ProcessorTimeout_AboveUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.ProcessorTimeoutSeconds = 181
	err := cfg.validate()
	if err == nil {
		t.Fatal("processor=181 should fail validation")
	}
}

// --- Guard Timeout ---

func TestValidate_GuardTimeout_AtLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.GuardTimeoutSeconds = 2
	// sub-phase = 120 + 30 + 60 + 2 = 212 < 300 ✓
	if err := cfg.validate(); err != nil {
		t.Fatalf("guard=2 should be valid, got: %v", err)
	}
}

func TestValidate_GuardTimeout_BelowLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.GuardTimeoutSeconds = 1
	err := cfg.validate()
	if err == nil {
		t.Fatal("guard=1 should fail validation")
	}
	if !strings.Contains(err.Error(), "GUARD_TIMEOUT_SECONDS") {
		t.Fatalf("error should mention GUARD_TIMEOUT_SECONDS, got: %v", err)
	}
}

func TestValidate_GuardTimeout_AtUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.GuardTimeoutSeconds = 30
	// sub-phase = 120 + 30 + 60 + 30 = 240 < 300 ✓
	if err := cfg.validate(); err != nil {
		t.Fatalf("guard=30 should be valid, got: %v", err)
	}
}

func TestValidate_GuardTimeout_AboveUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.GuardTimeoutSeconds = 31
	err := cfg.validate()
	if err == nil {
		t.Fatal("guard=31 should fail validation")
	}
}

// --- Cache TTL ---

func TestValidate_TACacheTTL_Zero_DisablesCaching(t *testing.T) {
	cfg := validConfig()
	cfg.TACacheTTLSeconds = 0
	if err := cfg.validate(); err != nil {
		t.Fatalf("ta_cache=0 should be valid (disables caching), got: %v", err)
	}
}

func TestValidate_TACacheTTL_Negative(t *testing.T) {
	cfg := validConfig()
	cfg.TACacheTTLSeconds = -1
	err := cfg.validate()
	if err == nil {
		t.Fatal("ta_cache=-1 should fail validation")
	}
	if !strings.Contains(err.Error(), "TA_CACHE_TTL_SECONDS") {
		t.Fatalf("error should mention TA_CACHE_TTL_SECONDS, got: %v", err)
	}
}

func TestValidate_TACacheTTL_AtUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.TACacheTTLSeconds = 3600
	if err := cfg.validate(); err != nil {
		t.Fatalf("ta_cache=3600 should be valid, got: %v", err)
	}
}

func TestValidate_TACacheTTL_AboveUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.TACacheTTLSeconds = 3601
	err := cfg.validate()
	if err == nil {
		t.Fatal("ta_cache=3601 should fail validation")
	}
}

func TestValidate_MacroCacheTTL_Zero_DisablesCaching(t *testing.T) {
	cfg := validConfig()
	cfg.MacroCacheTTLSeconds = 0
	if err := cfg.validate(); err != nil {
		t.Fatalf("macro_cache=0 should be valid (disables caching), got: %v", err)
	}
}

func TestValidate_MacroCacheTTL_Negative(t *testing.T) {
	cfg := validConfig()
	cfg.MacroCacheTTLSeconds = -1
	err := cfg.validate()
	if err == nil {
		t.Fatal("macro_cache=-1 should fail validation")
	}
	if !strings.Contains(err.Error(), "MACRO_CACHE_TTL_SECONDS") {
		t.Fatalf("error should mention MACRO_CACHE_TTL_SECONDS, got: %v", err)
	}
}

func TestValidate_MacroCacheTTL_AboveUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.MacroCacheTTLSeconds = 3601
	err := cfg.validate()
	if err == nil {
		t.Fatal("macro_cache=3601 should fail validation")
	}
}

// --- Retry Policy ---

func TestValidate_MaxCycleRetries_Zero_DisablesRetry(t *testing.T) {
	cfg := validConfig()
	cfg.MaxCycleRetries = 0
	if err := cfg.validate(); err != nil {
		t.Fatalf("retries=0 should be valid (disables retry), got: %v", err)
	}
}

func TestValidate_MaxCycleRetries_AtUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.MaxCycleRetries = 3
	if err := cfg.validate(); err != nil {
		t.Fatalf("retries=3 should be valid, got: %v", err)
	}
}

func TestValidate_MaxCycleRetries_Negative(t *testing.T) {
	cfg := validConfig()
	cfg.MaxCycleRetries = -1
	err := cfg.validate()
	if err == nil {
		t.Fatal("retries=-1 should fail validation")
	}
	if !strings.Contains(err.Error(), "MAX_CYCLE_RETRIES") {
		t.Fatalf("error should mention MAX_CYCLE_RETRIES, got: %v", err)
	}
}

func TestValidate_MaxCycleRetries_AboveUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.MaxCycleRetries = 4
	err := cfg.validate()
	if err == nil {
		t.Fatal("retries=4 should fail validation")
	}
}

func TestValidate_RetryBackoff_AtLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.RetryBackoffBaseSeconds = 0.5
	if err := cfg.validate(); err != nil {
		t.Fatalf("backoff=0.5 should be valid, got: %v", err)
	}
}

func TestValidate_RetryBackoff_BelowLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.RetryBackoffBaseSeconds = 0.49
	err := cfg.validate()
	if err == nil {
		t.Fatal("backoff=0.49 should fail validation")
	}
	if !strings.Contains(err.Error(), "RETRY_BACKOFF_BASE_SECONDS") {
		t.Fatalf("error should mention RETRY_BACKOFF_BASE_SECONDS, got: %v", err)
	}
}

func TestValidate_RetryBackoff_AtUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.RetryBackoffBaseSeconds = 30.0
	if err := cfg.validate(); err != nil {
		t.Fatalf("backoff=30.0 should be valid, got: %v", err)
	}
}

func TestValidate_RetryBackoff_AboveUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.RetryBackoffBaseSeconds = 30.1
	err := cfg.validate()
	if err == nil {
		t.Fatal("backoff=30.1 should fail validation")
	}
}

// --- Timeout Budget ---

func TestValidate_TimeoutBudget_ExactlyEqual_Fails(t *testing.T) {
	// sub-phase sum == cycle timeout should fail (no overhead room).
	cfg := validConfig()
	cfg.CycleTimeoutSeconds = 220
	cfg.TAMacroParallelTimeoutSeconds = 120
	cfg.RAGTimeoutSeconds = 30
	cfg.ProcessorTimeoutSeconds = 60
	cfg.GuardTimeoutSeconds = 10
	// sub-phase = 120 + 30 + 60 + 10 = 220 == 220
	err := cfg.validate()
	if err == nil {
		t.Fatal("sub-phase sum == cycle timeout should fail (no overhead room)")
	}
	if !strings.Contains(err.Error(), "sub-phase timeouts") {
		t.Fatalf("error should mention sub-phase timeouts, got: %v", err)
	}
}

func TestValidate_TimeoutBudget_OneSecondMargin_Passes(t *testing.T) {
	cfg := validConfig()
	cfg.CycleTimeoutSeconds = 221
	cfg.TAMacroParallelTimeoutSeconds = 120
	cfg.RAGTimeoutSeconds = 30
	cfg.ProcessorTimeoutSeconds = 60
	cfg.GuardTimeoutSeconds = 10
	// sub-phase = 220 < 221 ✓
	if err := cfg.validate(); err != nil {
		t.Fatalf("sub-phase=220 < timeout=221 should pass, got: %v", err)
	}
}

func TestValidate_TimeoutBudget_Exceeds_Fails(t *testing.T) {
	cfg := validConfig()
	cfg.CycleTimeoutSeconds = 100
	cfg.TAMacroParallelTimeoutSeconds = 50
	cfg.RAGTimeoutSeconds = 20
	cfg.ProcessorTimeoutSeconds = 20
	cfg.GuardTimeoutSeconds = 15
	// sub-phase = 50 + 20 + 20 + 15 = 105 > 100
	err := cfg.validate()
	if err == nil {
		t.Fatal("sub-phase sum > cycle timeout should fail")
	}
}

// --- Log Level ---

func TestValidate_LogLevel_AllValidLevels(t *testing.T) {
	validLevels := []string{
		"DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL", "FATAL",
		"debug", "info", "warning", "warn", "error", "critical", "fatal",
		"Debug", "Info", "Error",
	}
	for _, level := range validLevels {
		cfg := validConfig()
		cfg.LogLevel = level
		if err := cfg.validate(); err != nil {
			t.Errorf("log_level=%q should be valid, got: %v", level, err)
		}
	}
}

func TestValidate_LogLevel_Invalid(t *testing.T) {
	invalidLevels := []string{"TRACE", "VERBOSE", "NONE", "", "info "}
	for _, level := range invalidLevels {
		cfg := validConfig()
		cfg.LogLevel = level
		err := cfg.validate()
		if err == nil {
			t.Errorf("log_level=%q should fail validation", level)
		}
	}
}

// --- Port Bounds ---

func TestValidate_HTTPPort_AtLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.HTTPPort = 1024
	if err := cfg.validate(); err != nil {
		t.Fatalf("http_port=1024 should be valid, got: %v", err)
	}
}

func TestValidate_HTTPPort_BelowLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.HTTPPort = 1023
	err := cfg.validate()
	if err == nil {
		t.Fatal("http_port=1023 should fail validation (privileged port)")
	}
	if !strings.Contains(err.Error(), "HTTP_PORT") {
		t.Fatalf("error should mention HTTP_PORT, got: %v", err)
	}
}

func TestValidate_HTTPPort_AtUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.HTTPPort = 65535
	if err := cfg.validate(); err != nil {
		t.Fatalf("http_port=65535 should be valid, got: %v", err)
	}
}

func TestValidate_HTTPPort_AboveUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.HTTPPort = 65536
	err := cfg.validate()
	if err == nil {
		t.Fatal("http_port=65536 should fail validation")
	}
}

func TestValidate_GRPCPort_BelowLowerBound(t *testing.T) {
	cfg := validConfig()
	cfg.GRPCPort = 80
	err := cfg.validate()
	if err == nil {
		t.Fatal("grpc_port=80 should fail validation (privileged port)")
	}
	if !strings.Contains(err.Error(), "GRPC_PORT") {
		t.Fatalf("error should mention GRPC_PORT, got: %v", err)
	}
}

func TestValidate_GRPCPort_AboveUpperBound(t *testing.T) {
	cfg := validConfig()
	cfg.GRPCPort = 65536
	err := cfg.validate()
	if err == nil {
		t.Fatal("grpc_port=65536 should fail validation")
	}
}

func TestValidate_Ports_SameValue_Fails(t *testing.T) {
	cfg := validConfig()
	cfg.HTTPPort = 8080
	cfg.GRPCPort = 8080
	err := cfg.validate()
	if err == nil {
		t.Fatal("HTTP and gRPC on same port should fail validation")
	}
	if !strings.Contains(err.Error(), "must be different") {
		t.Fatalf("error should mention ports must be different, got: %v", err)
	}
}

func TestValidate_Ports_DifferentValues_Passes(t *testing.T) {
	cfg := validConfig()
	cfg.HTTPPort = 8080
	cfg.GRPCPort = 50052
	if err := cfg.validate(); err != nil {
		t.Fatalf("different ports should be valid, got: %v", err)
	}
}

// --- Default Symbols ---

func TestValidate_DefaultSymbols_Empty_Fails(t *testing.T) {
	cfg := validConfig()
	cfg.DefaultSymbols = []string{}
	err := cfg.validate()
	if err == nil {
		t.Fatal("empty default symbols should fail validation")
	}
	if !strings.Contains(err.Error(), "DEFAULT_SYMBOLS") {
		t.Fatalf("error should mention DEFAULT_SYMBOLS, got: %v", err)
	}
}

func TestValidate_DefaultSymbols_Nil_Fails(t *testing.T) {
	cfg := validConfig()
	cfg.DefaultSymbols = nil
	err := cfg.validate()
	if err == nil {
		t.Fatal("nil default symbols should fail validation")
	}
}

func TestValidate_DefaultSymbols_SingleSymbol_Passes(t *testing.T) {
	cfg := validConfig()
	cfg.DefaultSymbols = []string{"XAUUSD"}
	if err := cfg.validate(); err != nil {
		t.Fatalf("single symbol should be valid, got: %v", err)
	}
}

func TestValidate_DefaultSymbols_AllEightPairs(t *testing.T) {
	cfg := validConfig()
	cfg.DefaultSymbols = []string{
		"EURUSD", "GBPUSD", "USDJPY", "USDCHF",
		"AUDUSD", "NZDUSD", "USDCAD", "XAUUSD",
	}
	if err := cfg.validate(); err != nil {
		t.Fatalf("all 8 default pairs should be valid, got: %v", err)
	}
}
