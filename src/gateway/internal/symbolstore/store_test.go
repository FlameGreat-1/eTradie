package symbolstore

import (
	"context"
	"fmt"
	"os"
	"testing"

	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
)

const testUserID = "test-user-symbols-001"

func testRedisURL() string {
	if url := os.Getenv("REDIS_URL"); url != "" {
		return url
	}
	pw := os.Getenv("REDIS_PASSWORD")
	if pw != "" {
		return fmt.Sprintf("redis://:%s@localhost:6379/0", pw)
	}
	return "redis://localhost:6379/0"
}

func testRedis(t *testing.T) *infra.RedisClient {
	t.Helper()
	rc, err := infra.NewRedisClient(testRedisURL(), 5)
	if err != nil {
		t.Fatalf("Redis connection failed: %v", err)
	}
	if !rc.HealthCheck(context.Background()) {
		rc.Close()
		t.Fatal("Redis health check failed")
	}
	t.Cleanup(func() {
		rc.Delete(context.Background(), "gateway", activeSymbolsKey(testUserID))
		rc.Close()
	})
	return rc
}

// =============================================================================
// GetActiveSymbols
// =============================================================================

// SYMBOL SOURCE INVARIANT: a user with no persisted selection has an
// EMPTY active set. The store holds no operator-seeded default basket.
func TestGetActiveSymbols_ReturnsEmpty_WhenNoSelection(t *testing.T) {
	rc := testRedis(t)
	// Ensure clean state.
	rc.Delete(context.Background(), "gateway", activeSymbolsKey(testUserID))

	store := NewStore(rc)
	symbols := store.GetActiveSymbols(context.Background(), testUserID)

	if symbols == nil {
		t.Fatal("GetActiveSymbols must return a non-nil slice so JSON serialises to []")
	}
	if len(symbols) != 0 {
		t.Fatalf("expected empty selection, got %d: %v", len(symbols), symbols)
	}
}

func TestGetActiveSymbols_ReturnsEmpty_WhenUserIDBlank(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc)

	symbols := store.GetActiveSymbols(context.Background(), "")
	if symbols == nil || len(symbols) != 0 {
		t.Fatalf("expected empty non-nil slice for blank user id, got %v", symbols)
	}
}

// =============================================================================
// SetActiveSymbols + GetActiveSymbols
// =============================================================================

func TestSetActiveSymbols_RoundTrip(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc)
	ctx := context.Background()

	ok := store.SetActiveSymbols(ctx, testUserID, []string{"USDJPY", "USDCHF"})
	if !ok {
		t.Fatal("SetActiveSymbols should return true")
	}

	symbols := store.GetActiveSymbols(ctx, testUserID)
	if len(symbols) != 2 {
		t.Fatalf("expected 2 symbols, got %d: %v", len(symbols), symbols)
	}
	if symbols[0] != "USDJPY" || symbols[1] != "USDCHF" {
		t.Fatalf("expected [USDJPY USDCHF], got %v", symbols)
	}
}

func TestSetActiveSymbols_NormalizesToUppercase(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc)
	ctx := context.Background()

	store.SetActiveSymbols(ctx, testUserID, []string{"eurusd", "gbpusd"})

	symbols := store.GetActiveSymbols(ctx, testUserID)
	if symbols[0] != "EURUSD" || symbols[1] != "GBPUSD" {
		t.Fatalf("expected uppercase, got %v", symbols)
	}
}

func TestSetActiveSymbols_TrimsWhitespace(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc)
	ctx := context.Background()

	store.SetActiveSymbols(ctx, testUserID, []string{" EURUSD ", "\tGBPUSD\n"})

	symbols := store.GetActiveSymbols(ctx, testUserID)
	if symbols[0] != "EURUSD" || symbols[1] != "GBPUSD" {
		t.Fatalf("expected trimmed symbols, got %v", symbols)
	}
}

func TestSetActiveSymbols_EmptyList_ReturnsFalse(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc)

	ok := store.SetActiveSymbols(context.Background(), testUserID, []string{})
	if ok {
		t.Fatal("empty list should return false")
	}
}

func TestSetActiveSymbols_AllWhitespace_ReturnsFalse(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc)

	ok := store.SetActiveSymbols(context.Background(), testUserID, []string{" ", "\t", ""})
	if ok {
		t.Fatal("all-whitespace entries should return false")
	}
}

func TestSetActiveSymbols_OverwritesPrevious(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc)
	ctx := context.Background()

	store.SetActiveSymbols(ctx, testUserID, []string{"EURUSD", "GBPUSD"})
	store.SetActiveSymbols(ctx, testUserID, []string{"XAUUSD"})

	symbols := store.GetActiveSymbols(ctx, testUserID)
	if len(symbols) != 1 || symbols[0] != "XAUUSD" {
		t.Fatalf("expected [XAUUSD] after overwrite, got %v", symbols)
	}
}

// =============================================================================
// ClearSelection
// =============================================================================

func TestClearSelection_LeavesNextReadEmpty(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc)
	ctx := context.Background()

	// Set a custom selection.
	store.SetActiveSymbols(ctx, testUserID, []string{"USDJPY"})

	// Clear it.
	ok := store.ClearSelection(ctx, testUserID)
	if !ok {
		t.Fatal("ClearSelection should return true")
	}

	// The next read must be empty — there is no default to fall back to.
	symbols := store.GetActiveSymbols(ctx, testUserID)
	if symbols == nil || len(symbols) != 0 {
		t.Fatalf("expected empty selection after clear, got %v", symbols)
	}
}

func TestClearSelection_WhenAlreadyEmpty(t *testing.T) {
	rc := testRedis(t)
	rc.Delete(context.Background(), "gateway", activeSymbolsKey(testUserID))

	store := NewStore(rc)

	// Clearing when nothing is set should still succeed (idempotent).
	ok := store.ClearSelection(context.Background(), testUserID)
	if !ok {
		t.Fatal("ClearSelection on empty state should return true")
	}
}

func TestClearSelection_BlankUserID_ReturnsFalse(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc)

	ok := store.ClearSelection(context.Background(), "")
	if ok {
		t.Fatal("ClearSelection with blank user id should return false")
	}
}
