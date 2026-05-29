package executor_test

import (
	"context"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/execution/internal/executor"
)

func TestBurstQueueFIFOAndGlobalCap(t *testing.T) {
	q := executor.NewBurstQueue(executor.QueueConfig{
		MaxConcurrent:   2,
		PerUserCap:      10,
		DefaultDeadline: 500 * time.Millisecond,
	})

	// Hold two slots so the third Enter must wait for one to be
	// released.
	r1, err := q.Enter(context.Background(), "u1")
	require.NoError(t, err)
	defer r1()
	r2, err := q.Enter(context.Background(), "u1")
	require.NoError(t, err)

	var wg sync.WaitGroup
	wg.Add(1)
	var entered atomic.Bool
	go func() {
		defer wg.Done()
		rel, err := q.Enter(context.Background(), "u1")
		if err == nil {
			entered.Store(true)
			rel()
		}
	}()

	time.Sleep(50 * time.Millisecond)
	require.False(t, entered.Load(), "third enter must wait for a slot to free")
	r2()
	wg.Wait()
	require.True(t, entered.Load(), "third enter must complete once a slot frees")
}

func TestBurstQueueDeadlineDrops(t *testing.T) {
	q := executor.NewBurstQueue(executor.QueueConfig{
		MaxConcurrent:   1,
		PerUserCap:      10,
		DefaultDeadline: 50 * time.Millisecond,
	})

	// Saturate the only slot.
	rel, err := q.Enter(context.Background(), "u1")
	require.NoError(t, err)
	t.Cleanup(rel)

	start := time.Now()
	_, err = q.Enter(context.Background(), "u1")
	require.Error(t, err)
	require.Contains(t, err.Error(), "deadline")
	require.GreaterOrEqual(t, time.Since(start), 50*time.Millisecond)
}

func TestBurstQueuePerUserOverflow(t *testing.T) {
	q := executor.NewBurstQueue(executor.QueueConfig{
		MaxConcurrent:   16,
		PerUserCap:      2,
		DefaultDeadline: 500 * time.Millisecond,
	})

	// Fill the per-user quota for u1.
	r1, err := q.Enter(context.Background(), "u1")
	require.NoError(t, err)
	defer r1()
	r2, err := q.Enter(context.Background(), "u1")
	require.NoError(t, err)
	defer r2()

	// Third enter for u1 must reject without waiting (fast-path).
	start := time.Now()
	_, err = q.Enter(context.Background(), "u1")
	require.Error(t, err)
	require.Contains(t, err.Error(), "per-user overflow")
	require.Less(t, time.Since(start), 50*time.Millisecond)

	// Another user is unaffected by u1's overflow.
	r3, err := q.Enter(context.Background(), "u2")
	require.NoError(t, err)
	defer r3()
}
