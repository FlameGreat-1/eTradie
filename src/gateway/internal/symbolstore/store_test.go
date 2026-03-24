package symbolstore

import (
	"context"
	"testing"

	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
)

func testRedis(t *testing.T) *infra.RedisClient {
	t.Helper()
	rc, err := infra.NewRedisClient("redis://localhost:6379/0", 5)
	if err != nil {
		t.Skipf("Redis unavailable, skipping: %v", err)
	}
	if !rc.HealthCheck(context.Background()) {
		rc.Close()
		t.Skip("Redis health check failed, skipping")
	}
	t.Cleanup(func() {
		rc.Delete(context.Background(), "gateway", activeSymbolsKey)
		rc.Close()
	})
	return rc
}

func testConfig() *config.Config {
	return &config.Config{
		DefaultSymbols: []string{"EURUSD", "GBPUSD", "XAUUSD"},
	}
}

// =============================================================================
// GetActiveSymbols
// =============================================================================

func TestGetActiveSymbols_ReturnsDefaults_WhenEmpty(t *testing.T) {
	rc := testRedis(t)
	// Ensure clean state.
	rc.Delete(context.Background(), "gateway", activeSymbolsKey)

	store := NewStore(rc, testConfig())
	symbols := store.GetActiveSymbols(context.Background())

	if len(symbols) != 3 {
		t.Fatalf("expected 3 default symbols, got %d: %v", len(symbols), symbols)
	}
	if symbols[0] != "EURUSD" || symbols[1] != "GBPUSD" || symbols[2] != "XAUUSD" {
		t.Fatalf("expected [EURUSD GBPUSD XAUUSD], got %v", symbols)
	}
}

func TestGetActiveSymbols_DefaultsAreCopy(t *testing.T) {
	rc := testRedis(t)
	rc.Delete(context.Background(), "gateway", activeSymbolsKey)

	store := NewStore(rc, testConfig())

	symbols1 := store.GetActiveSymbols(context.Background())
	symbols1[0] = "MUTATED"

	symbols2 := store.GetActiveSymbols(context.Background())
	if symbols2[0] == "MUTATED" {
		t.Fatal("GetActiveSymbols should return a copy, not a shared reference")
	}
}

// =============================================================================
// SetActiveSymbols + GetActiveSymbols
// =============================================================================

func TestSetActiveSymbols_RoundTrip(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc, testConfig())
	ctx := context.Background()

	ok := store.SetActiveSymbols(ctx, []string{"USDJPY", "USDCHF"})
	if !ok {
		t.Fatal("SetActiveSymbols should return true")
	}

	symbols := store.GetActiveSymbols(ctx)
	if len(symbols) != 2 {
		t.Fatalf("expected 2 symbols, got %d: %v", len(symbols), symbols)
	}
	if symbols[0] != "USDJPY" || symbols[1] != "USDCHF" {
		t.Fatalf("expected [USDJPY USDCHF], got %v", symbols)
	}
}

func TestSetActiveSymbols_NormalizesToUppercase(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc, testConfig())
	ctx := context.Background()

	store.SetActiveSymbols(ctx, []string{"eurusd", "gbpusd"})

	symbols := store.GetActiveSymbols(ctx)
	if symbols[0] != "EURUSD" || symbols[1] != "GBPUSD" {
		t.Fatalf("expected uppercase, got %v", symbols)
	}
}

func TestSetActiveSymbols_TrimsWhitespace(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc, testConfig())
	ctx := context.Background()

	store.SetActiveSymbols(ctx, []string{" EURUSD ", "\tGBPUSD\n"})

	symbols := store.GetActiveSymbols(ctx)
	if symbols[0] != "EURUSD" || symbols[1] != "GBPUSD" {
		t.Fatalf("expected trimmed symbols, got %v", symbols)
	}
}

func TestSetActiveSymbols_EmptyList_ReturnsFalse(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc, testConfig())

	ok := store.SetActiveSymbols(context.Background(), []string{})
	if ok {
		t.Fatal("empty list should return false")
	}
}

func TestSetActiveSymbols_AllWhitespace_ReturnsFalse(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc, testConfig())

	ok := store.SetActiveSymbols(context.Background(), []string{" ", "\t", ""})
	if ok {
		t.Fatal("all-whitespace entries should return false")
	}
}

func TestSetActiveSymbols_OverwritesPrevious(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc, testConfig())
	ctx := context.Background()

	store.SetActiveSymbols(ctx, []string{"EURUSD", "GBPUSD"})
	store.SetActiveSymbols(ctx, []string{"XAUUSD"})

	symbols := store.GetActiveSymbols(ctx)
	if len(symbols) != 1 || symbols[0] != "XAUUSD" {
		t.Fatalf("expected [XAUUSD] after overwrite, got %v", symbols)
	}
}

// =============================================================================
// ResetToDefaults
// =============================================================================

func TestResetToDefaults_ClearsSelection(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc, testConfig())
	ctx := context.Background()

	// Set custom symbols.
	store.SetActiveSymbols(ctx, []string{"USDJPY"})

	// Reset.
	ok := store.ResetToDefaults(ctx)
	if !ok {
		t.Fatal("ResetToDefaults should return true")
	}

	// Should fall back to defaults.
	symbols := store.GetActiveSymbols(ctx)
	if len(symbols) != 3 {
		t.Fatalf("expected 3 defaults after reset, got %d: %v", len(symbols), symbols)
	}
	if symbols[0] != "EURUSD" {
		t.Fatalf("expected defaults after reset, got %v", symbols)
	}
}

func TestResetToDefaults_WhenAlreadyEmpty(t *testing.T) {
	rc := testRedis(t)
	rc.Delete(context.Background(), "gateway", activeSymbolsKey)

	store := NewStore(rc, testConfig())

	// Reset when nothing is set should still succeed.
	ok := store.ResetToDefaults(context.Background())
	if !ok {
		t.Fatal("ResetToDefaults on empty state should return true")
	}
}
