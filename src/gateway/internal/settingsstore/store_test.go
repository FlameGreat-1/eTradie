package settingsstore

import (
	"context"
	"testing"

	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
)

func testRedis(t *testing.T) *infra.RedisClient {
	t.Helper()
	rc, err := infra.NewRedisClient("redis://localhost:6379/0", 5)
	if err != nil {
		t.Fatalf("Redis connection failed: %v", err)
	}
	if !rc.HealthCheck(context.Background()) {
		rc.Close()
		t.Fatal("Redis health check failed")
	}
	t.Cleanup(func() {
		// Clean up test keys.
		rc.Delete(context.Background(), "gateway", settingsKey)
		rc.Close()
	})
	return rc
}

func TestLoad_EmptyRedis_ReturnsDefaults(t *testing.T) {
	rc := testRedis(t)
	// Ensure key doesn't exist.
	rc.Delete(context.Background(), "gateway", settingsKey)

	store := NewStore(rc)
	settings := store.Load(context.Background())

	if settings == nil {
		t.Fatal("Load should never return nil")
	}
	if settings.CycleIntervalSeconds != 0 {
		t.Fatalf("expected 0 (no override), got %d", settings.CycleIntervalSeconds)
	}
}

func TestSave_Load_RoundTrip(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc)
	ctx := context.Background()

	// Save.
	err := store.Save(ctx, &Settings{CycleIntervalSeconds: 7200})
	if err != nil {
		t.Fatalf("Save failed: %v", err)
	}

	// Load.
	settings := store.Load(ctx)
	if settings.CycleIntervalSeconds != 7200 {
		t.Fatalf("expected 7200, got %d", settings.CycleIntervalSeconds)
	}
}

func TestSetCycleInterval_GetCycleInterval(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc)
	ctx := context.Background()

	err := store.SetCycleInterval(ctx, 3600)
	if err != nil {
		t.Fatalf("SetCycleInterval failed: %v", err)
	}

	got := store.GetCycleInterval(ctx)
	if got != 3600 {
		t.Fatalf("expected 3600, got %d", got)
	}
}

func TestSetCycleInterval_OverwritesPrevious(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc)
	ctx := context.Background()

	store.SetCycleInterval(ctx, 3600)
	store.SetCycleInterval(ctx, 1800)

	got := store.GetCycleInterval(ctx)
	if got != 1800 {
		t.Fatalf("expected 1800 after overwrite, got %d", got)
	}
}

func TestGetCycleInterval_NoOverride_ReturnsZero(t *testing.T) {
	rc := testRedis(t)
	// Ensure clean state.
	rc.Delete(context.Background(), "gateway", settingsKey)

	store := NewStore(rc)
	got := store.GetCycleInterval(context.Background())
	if got != 0 {
		t.Fatalf("expected 0 when no override, got %d", got)
	}
}

func TestSave_OverwritesCompletely(t *testing.T) {
	rc := testRedis(t)
	store := NewStore(rc)
	ctx := context.Background()

	// Save with interval.
	store.Save(ctx, &Settings{CycleIntervalSeconds: 9000})

	// Overwrite with zero (clear override).
	store.Save(ctx, &Settings{CycleIntervalSeconds: 0})

	got := store.GetCycleInterval(ctx)
	if got != 0 {
		t.Fatalf("expected 0 after overwrite with zero, got %d", got)
	}
}
