package watcher_test

import (
	"context"
	"testing"

	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/watcher"
)

// A safe dummy struct implementing broker.Port if needed, or we can use nil
// since Arm() doesn't immediately use the broker methods inside the lock.
// The same applies to GatewayPort, audit.Logger, and alertredis.Transport.

func TestManager_ShutdownPreventsNewArms(t *testing.T) {
	manager := watcher.NewManager(
		nil,
		nil,
		nil,
		nil,
		watcher.Config{PollIntervalMs: 10, TimeoutMinutes: 60},
		nil,
	)

	order1 := &models.Order{
		WatcherID: "W-1",
		Symbol:    "EURUSD",
	}

	order2 := &models.Order{
		WatcherID: "W-2",
		Symbol:    "GBPUSD",
	}

	// Arm normally
	manager.Arm(order1)

	if manager.ActiveCount() != 1 {
		t.Errorf("expected 1 active watcher, got %d", manager.ActiveCount())
	}

	// Initiate shutdown. This sets shuttingDown = true and stops existing watchers.
	manager.Shutdown()

	if manager.ActiveCount() != 0 {
		t.Errorf("expected 0 active watchers after shutdown, got %d", manager.ActiveCount())
	}

	// Try arming AFTER shutdown. Race condition protection should reject this.
	manager.Arm(order2)

	if manager.ActiveCount() != 0 {
		t.Errorf("expected manager to reject new arm requests after shutdown, but active count is %d", manager.ActiveCount())
	}
}

func TestManager_Disarm(t *testing.T) {
	manager := watcher.NewManager(
		nil,
		nil,
		nil,
		nil,
		watcher.Config{PollIntervalMs: 10, TimeoutMinutes: 60},
		nil,
	)

	order := &models.Order{
		WatcherID: "W-DISARM-TEST",
		Symbol:    "USDJPY",
	}

	manager.Arm(order)
	if manager.ActiveCount() != 1 {
		t.Fatalf("expected 1 active watcher, got %d", manager.ActiveCount())
	}

	manager.Disarm("W-DISARM-TEST")
	if manager.ActiveCount() != 0 {
		t.Errorf("expected 0 active watchers after disarm, got %d", manager.ActiveCount())
	}
}

func TestManager_ContextCancellation(t *testing.T) {
	// A manual context cancellation shouldn't deadlock.
	manager := watcher.NewManager(nil, nil, nil, nil, watcher.Config{PollIntervalMs: 10, TimeoutMinutes: 60}, nil)

	order := &models.Order{
		WatcherID: "W-CTX-TEST",
		Symbol:    "AUDUSD",
	}

	manager.Arm(order)

	// Calling shutdown internally cancels the manager's context.
	// Since we mock nothing, the watcher routine will exit very quickly
	// (usually when it tries to connect to nil interfaces) or block on its Context.
	// Shutdown waits for active count to hit 0, capping at 10 seconds.
	manager.Shutdown()

	if manager.ActiveCount() != 0 {
		t.Errorf("expected clean shutdown, active count is %d", manager.ActiveCount())
	}
}

type mockWatcherStore struct {
	deleted map[string]bool
}

func (m *mockWatcherStore) Insert(ctx context.Context, order *models.Order) error {
	return nil
}

func (m *mockWatcherStore) Delete(ctx context.Context, watcherID string) error {
	m.deleted[watcherID] = true
	return nil
}

func TestManager_ShutdownPreservesDatabase(t *testing.T) {
	store := &mockWatcherStore{
		deleted: make(map[string]bool),
	}
	manager := watcher.NewManager(
		nil,
		nil,
		nil,
		nil,
		watcher.Config{PollIntervalMs: 5, TimeoutMinutes: 1},
		store,
	)

	order := &models.Order{
		WatcherID: "W-SHUTDOWN-PRESERVE-TEST",
		Symbol:    "EURUSD",
	}

	manager.Arm(order)

	// Ensure the watcher is registered
	if manager.ActiveCount() != 1 {
		t.Fatalf("expected active count 1, got %d", manager.ActiveCount())
	}

	// Shutdown the manager. This cancels context and shuts down all watchers.
	manager.Shutdown()

	// Verify that the watcher exited but did NOT invoke Delete on the store
	if store.deleted["W-SHUTDOWN-PRESERVE-TEST"] {
		t.Errorf("expected database record NOT to be deleted on manager shutdown, but Delete was called")
	}
}

