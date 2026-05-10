package main

import (
	"context"

	billingstore "github.com/flamegreat-1/etradie/src/billing/store"
)

// watcherUsageAdapter satisfies watcher.WatcherUsage by delegating to the
// shared billing UsageStore. Lives in main so the watcher package never
// imports billing/* and stays a pure execution concern.
type watcherUsageAdapter struct {
	store *billingstore.UsageStore
}

func (a *watcherUsageAdapter) IncrementWatchers(ctx context.Context, userID string) error {
	// Ensure the row exists (atomic upsert with daily reset semantics) before
	// incrementing the column — otherwise the increment is a no-op for users
	// whose row hasn't been touched today.
	if _, err := a.store.GetOrUpdateUsage(ctx, userID); err != nil {
		return err
	}
	return a.store.IncrementMetric(ctx, userID, "watcher_count", 1)
}

func (a *watcherUsageAdapter) DecrementWatchers(ctx context.Context, userID string) error {
	if _, err := a.store.GetOrUpdateUsage(ctx, userID); err != nil {
		return err
	}
	return a.store.IncrementMetric(ctx, userID, "watcher_count", -1)
}
