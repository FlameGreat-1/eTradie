package store

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5/pgxpool"
)

// schemaAdvisoryLockKey is a stable BIGINT key used by EnsureSchema's
// pg_advisory_lock call. The value is the xxh64 of the literal string
// "etradie-execution-schema" truncated to int64. Any non-zero stable
// value would work; we just need ALL processes in this codebase to
// agree on it, so the lock actually serializes them.
const schemaAdvisoryLockKey int64 = 0x6574726164696523 // "etradie#" as bytes

// EnsureSchema runs the execution-engine DDL serially across concurrent
// callers by taking a session-level Postgres advisory lock first.
//
// Background: SchemaSQL() contains CREATE OR REPLACE TRIGGER and
// CREATE OR REPLACE FUNCTION statements that take AccessExclusiveLock
// on execution_audit_logs and execution_positions_snapshot. When two
// processes (e.g. parallel Go test packages, or a rolling deploy with
// two replicas booting at the same time) hit these statements
// concurrently, Postgres reports SQLSTATE 40P01 ("deadlock detected")
// and aborts one of them. The DDL itself is idempotent — every
// statement uses CREATE OR REPLACE or CREATE ... IF NOT EXISTS — so
// the cure is to make sure only ONE process runs it at a time.
//
// pg_advisory_lock blocks the caller until the lock is free, then
// returns. A second concurrent caller waits behind the first; once it
// gets the lock it re-runs the same DDL (no-op) and proceeds. No
// deadlock, no missed setup.
//
// The lock is released when the underlying pgx connection is returned
// to the pool (session lock semantics). Callers do not need to
// explicitly unlock.
func EnsureSchema(ctx context.Context, pool *pgxpool.Pool) error {
	conn, err := pool.Acquire(ctx)
	if err != nil {
		return fmt.Errorf("acquire conn for schema setup: %w", err)
	}
	defer conn.Release()

	if _, err := conn.Exec(ctx, "SELECT pg_advisory_lock($1)", schemaAdvisoryLockKey); err != nil {
		return fmt.Errorf("take schema advisory lock: %w", err)
	}

	if _, err := conn.Exec(ctx, SchemaSQL()); err != nil {
		// Best-effort unlock so we don't hold the lock until conn close
		// if SchemaSQL fails for a non-deadlock reason (e.g. permission
		// error). Ignore the unlock error — SchemaSQL's error is the
		// one we want to surface.
		_, _ = conn.Exec(ctx, "SELECT pg_advisory_unlock($1)", schemaAdvisoryLockKey)
		return fmt.Errorf("apply schema: %w", err)
	}

	if _, err := conn.Exec(ctx, "SELECT pg_advisory_unlock($1)", schemaAdvisoryLockKey); err != nil {
		return fmt.Errorf("release schema advisory lock: %w", err)
	}
	return nil
}
