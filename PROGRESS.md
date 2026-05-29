# Engineering progress — MT self-hosting hardening

## Current branch

`feature/mt-node-section-1-pre-section-7-hardening`, opened against `main`.
The prior MR (`!35`) merged sections 1-6 into `main`. This MR addresses every
pre-Section-7 audit gap and lands seven atomic hardening commits.

## Pre-Section-7 hardening (this MR)

| # | Commit                                                                                          | Audit gap closed                                            |
|---|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------|
| 1 | `fix(mt-node): drain zombie wine processes between supervised MT restarts`                       | Section 1 "Garbage process cleanup (zombie MT/Wine procs)". |
| 2 | `fix(mt-node): watchdog reuses a single REQ socket; resets on error`                             | Section 1 memory + Section 2 silent disconnect.             |
| 3 | `feat(mt-node): in-pod CPU watchdog with cgroup-aware throttle detection`                        | Section 1 "Indicator recalculation spikes do not freeze".   |
| 4 | `fix(mt-node): NetworkPolicy egress restricted to public IP space`                               | Section 9 tenant isolation + CIS 5.3.2 (IMDS exclusion).    |
| 5 | `refactor(hosted-provisioner): emit StatefulSet matching chart shape`                            | Dual-deployment-path divergence (chart + provisioner).      |
| 6 | `fix(execution): restore pending watchers BEFORE gRPC accepts traffic`                           | Section 3 step C commit-message lie (boot-order).           |
| 7 | `docs(mt-node): rewrite README, pin EA SHA, support offline mirror, correct Section 3 step C`    | Stale docs + supply chain + honest correction addendum.     |

Every commit is independently revertable and carries its own audit
reference. The PrometheusRule and metric names introduced in commit
3 are wired through `helm/mt-node/templates/configmap-watchdog.yaml`
and `helm/mt-node/values.yaml`. The StatefulSet refactor in commit 5
is zero-tenant-safe (operator confirmed zero existing hosted-mode
tenants).

The README rewrite in commit 7 documents the actual chart +
provisioner contract, lifecycle, watchdog semantics, operator
runbook, and CIS Kubernetes Benchmark v1.8 compliance posture.

## What was on the prior PROGRESS.md

The prior PROGRESS.md (before the merge) preserved a Section 7
Step A diff that the previous Section 7 commit attempt failed to
push. That diff remains relevant. Section 7 will resume by applying
it. The Step A design (in full) follows.

---

# Section 7 — Data consistency & state management (preserved design)

Section 7 of the CHECKLIST:

```
# DATA CONSISTENCY & STATE MANAGEMENT

### Trade state integrity
* [ ] Single source of truth for positions
* [ ] Broker vs system reconciliation loop
* [ ] No "ghost positions"

### Persistence layer
* [ ] All trades logged immutably
* [ ] Replay capability (audit + debugging)
* [ ] Recovery after full system restart
```

## Section 7 audit — honest state on `main` (post-merge of !35)

**Trade state integrity:**

1. ⚠️ **Single source of truth for positions** — partial. The **broker** is
   the SoT (correct), and the reconciler adopts/replaces engine state from
   the broker. BUT: there is **no canonical persisted "positions" table**
   in the engine DB. The reconciler logs `engine_only_position` as `ERROR`
   and **never deletes** it — meaning the engine memory accumulates ghost
   positions across restarts since memory is lost. On restart,
   `Manager.users` is empty so there are no `engine_only` to detect.
   There's no `positions_snapshot` table that the engine writes to.

2. ✅ **Broker vs system reconciliation loop** — exists (the reconciler
   in `src/execution/internal/state/reconciler.go`, runs every 60s by
   default).

3. ⚠️ **No "ghost positions"** — partially solved. The 60s reconciler will
   catch them within the window, but the engine memory between reconciles
   is the only source of "engine positions" — and on a restart, the engine
   has no idea what it "thought" was open.

**Persistence layer:**

4. ✅ **All trades logged immutably** — `execution_audit_logs` is INSERT-only,
   no UPDATE/DELETE in the codebase. There is no explicit "immutable"
   constraint at the DB level though — a future developer could add an
   UPDATE. Section 7 Step B closes this with a BEFORE UPDATE/DELETE trigger.

5. ❌ **Replay capability** — MISSING. The audit log has every trade event
   but there is **no replay tool** that walks the audit_log and rebuilds
   state, no `/internal/audit/replay` endpoint, no CLI subcommand.
   Audit + debugging requires raw SQL. Section 7 Step B closes this.

6. ⚠️ **Recovery after full system restart** — partial. Watcher restore
   exists (committed; boot-order fixed in this MR). Idempotency table
   persists. Reconciler catches divergence within 60s. But **engine
   in-memory state (positions, pending orders, P&L counters) is rebuilt
   only by polling the broker on first `Refresh()` per user** — which is
   lazy. P&L counters ARE persisted (good). Positions are not persisted
   at all — they live in memory until first `Refresh()` from the broker.

## Section 7 deliverables — three atomic commits

### Step A — positions_snapshot table + persistent ghost detection

- New `execution_positions_snapshot` table (per-user, immutable row per
  snapshot, sealed with `snapshot_ts + content_hash` for tamper detection).
- New `PositionSnapshotStore` (Go) with `WriteSnapshot(userID, positions)`
  and `LatestSnapshot(userID)`.
- Reconciler writes a snapshot at the END of every run (post-adopt/replace),
  so the DB always has the engine's last-known view.
- New rule in reconciler: when DB snapshot has positions the broker no
  longer reports AND those positions were `>= 5 min old` in the snapshot,
  classify as `ghost_position` (broker closed it cleanly between cycles;
  engine state is stale).
- New metric `etradie_execution_reconcile_drift_total{class=ghost_position}`
  + new PrometheusRule.

### Step B — DB-level immutability constraint + replay endpoint

- New DB trigger blocking UPDATE/DELETE on `execution_audit_logs`
  (PostgreSQL `BEFORE UPDATE/DELETE` trigger that raises an exception).
  Same for `execution_positions_snapshot`.
- New `/internal/audit/replay/{user_id}` gRPC endpoint on the execution
  service that walks the audit log between two timestamps and returns a
  chronologically-ordered event stream. Read-only; service-token-authenticated.
- New CLI subcommand `executionctl replay --user=<id> --since=<rfc3339>`
  for the operator runbook.

### Step C — engine-side position recovery on startup + chaos test + scorecard

- On execution service startup, **before** the reconciler starts, eagerly
  call `Refresh(userID)` for every active user so the engine's memory is
  hot before the first user request lands. This closes the "memory empty
  on restart" gap without changing the broker-as-SoT principle.
- Engine ConfigMap surfaces a new env
  `EXECUTION_PRELOAD_POSITIONS_ON_START` (default `true`).
- New chaos test `test_positions_snapshot_and_ghost.py` — writes a
  snapshot, simulates the broker losing one position, asserts the
  ghost-detection rule classifies it.
- MR description updated with Section 7 scorecard.

---

# Section 7 Step A — preserved diff (apply as the next commit)

The Step A commit attempt failed before push during the previous
session. The full diff is preserved below verbatim. To resume
Section 7, apply this diff as the first commit on a new branch off
`main` AFTER this hardening MR merges.

## Commit message

```
feat(consistency): Section 7 step A - positions_snapshot table + ghost-position detection

Closes the two engine-side data-consistency gaps CHECKLIST Section 7
exposes:

  (1) The engine had no persisted view of 'what positions did the
      engine think were open just before the crash'. After restart,
      Manager.users was empty until the first Refresh(). The
      reconciler's engine_only_position branch never fired because
      the engine had no memory to compare against.

  (2) When the broker closed a position cleanly between two
      reconcile cycles (e.g. SL hit at minute 30s, next reconcile
      at minute 60s), the engine state still showed it open until
      a *user request* hit Refresh(). The reconciler could detect
      this but had no way to distinguish 'broker closed it' from
      'engine state is wrong' because there was no historical
      record.

1. src/execution/internal/store/schema.go
   - New table execution_positions_snapshot keyed by
     (user_id, snapshot_ts). Stores ONE row per reconcile cycle
     with the JSONB-encoded positions slice + a sha256 content_hash
     for tamper detection. INSERT-only by design (the immutability
     trigger added in Step B will enforce it at the DB level).
   - Indexes: (user_id, snapshot_ts DESC) for 'latest snapshot'
     queries, (snapshot_ts) for retention sweeps.

2. src/execution/internal/store/positions_snapshot.go (NEW)
   - PositionSnapshotStore.WriteSnapshot(ctx, userID, positions)
     - Marshals to JSONB, computes sha256 of canonicalised JSON,
       INSERTs the row. Fire-and-forget logging on error (same
       contract as audit.Write).
   - PositionSnapshotStore.LatestSnapshot(ctx, userID)
     - Returns the most recent snapshot + its parsed positions.
   - PositionSnapshotStore.SnapshotsBetween(ctx, userID, from, to)
     - For the replay endpoint added in Step B.
   - PositionSnapshotStore.PruneOlderThan(ctx, cutoff)
     - Retention sweep, called from a goroutine in main.go.

3. src/execution/internal/state/reconciler.go
   - After every successful runOnceForUser, write a snapshot of the
     current Manager.Positions(userID) to the new store. This is
     the engine's view AFTER the reconciler ran, i.e. the post-
     adopt/replace state.
   - New ghost-position rule: when LatestSnapshot returns positions
     that are NO LONGER in brokerByTicket AND the snapshot is
     >= GhostPositionMinAgeSecs old, emit
     etradie_execution_reconcile_drift_total{class="ghost_position"}
     and log at ERROR with the OrderID + Symbol + the snapshot age.
     The position is then ALSO removed from in-memory state via a
     new Manager.RemoveGhostPosition method, because the broker has
     authoritatively closed it.

4. src/execution/internal/state/manager.go
   - New RemoveGhostPosition(userID, brokerOrderID) helper. Returns
     true when a position was actually removed. Updates the
     OpenPositionCount gauge atomically.

5. src/execution/internal/observability/metrics.go
   - The reconcile drift counter already has variable labels. Step B
     adds the new PrometheusRule that pages on ghost_position rate.

6. src/execution/cmd/execution/main.go
   - Construct PositionSnapshotStore alongside AuditStore + WatcherStore.
     Pass it into NewReconciler via a new constructor parameter.
   - Launch a background retention sweeper (every 1h, deletes
     snapshots older than EXECUTION_POSITION_SNAPSHOT_RETENTION_HOURS,
     default 168 = 7 days).

7. helm/execution/templates/configmap.yaml + values.yaml
   - New env keys:
       EXECUTION_POSITION_SNAPSHOT_ENABLED          (default "true")
       EXECUTION_POSITION_SNAPSHOT_RETENTION_HOURS  (default "168")
       EXECUTION_GHOST_POSITION_MIN_AGE_SECS        (default "300")

All Section 7 changes are gated by EXECUTION_POSITION_SNAPSHOT_ENABLED
so the operator can disable the new snapshot writes without redeploy
while keeping the rest of the reconciler intact.

Audit refs:
- CHECKLIST Section 7 'Single source of truth for positions' (broker remains the SoT; engine snapshot is the rebuildable view)
- CHECKLIST Section 7 'No ghost positions'
- CHECKLIST Section 7 'Recovery after full system restart'
```

## File changes — schema.go

```diff
--- src/execution/internal/store/schema.go
+++ src/execution/internal/store/schema.go
@@ -1,7 +1,34 @@
+-- Section 7 (CHECKLIST): position snapshots.
+--
+-- One INSERT-only row per reconcile cycle per user. Carries the
+-- JSONB-encoded list of engine-tracked positions AFTER the reconciler
+-- ran (post adopt/replace), plus a sha256 of the canonicalised JSON
+-- for tamper detection. The new ghost-position rule in reconciler.go
+-- compares 'positions that appear in the latest snapshot but not in
+-- the current broker reply' against a configurable min-age threshold.
+--
+-- Immutability: Step B adds a BEFORE UPDATE / BEFORE DELETE trigger
+-- on this table. The pruner uses a separate SECURITY DEFINER function
+-- to age out old rows; the app role cannot bypass the trigger.
+CREATE TABLE IF NOT EXISTS execution_positions_snapshot (
+    id              BIGSERIAL PRIMARY KEY,
+    user_id         VARCHAR(64) NOT NULL,
+    snapshot_ts     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
+    position_count  INTEGER NOT NULL DEFAULT 0,
+    positions       JSONB NOT NULL DEFAULT '[]'::jsonb,
+    content_hash    CHAR(64) NOT NULL,
+    reconcile_run_id TEXT NOT NULL DEFAULT ''
+);
+
+CREATE INDEX IF NOT EXISTS idx_exec_positions_snap_user_ts
+    ON execution_positions_snapshot (user_id, snapshot_ts DESC);
+CREATE INDEX IF NOT EXISTS idx_exec_positions_snap_ts
+    ON execution_positions_snapshot (snapshot_ts);
+
 -- Automatic schema migration for existing databases
 ALTER TABLE execution_pending_watchers ADD COLUMN IF NOT EXISTS broker_order_id TEXT NOT NULL DEFAULT '';
 ALTER TABLE execution_audit_logs ADD COLUMN IF NOT EXISTS volume_filled    DOUBLE PRECISION NOT NULL DEFAULT 0;
 ALTER TABLE execution_audit_logs ADD COLUMN IF NOT EXISTS volume_remaining DOUBLE PRECISION NOT NULL DEFAULT 0;
 ALTER TABLE execution_audit_logs ADD COLUMN IF NOT EXISTS fill_status      VARCHAR(20) NOT NULL DEFAULT '';
```

## File changes — src/execution/internal/store/positions_snapshot.go (NEW)

```go
package store

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sort"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
)

// PositionSnapshotStore persists per-user engine-position views into
// execution_positions_snapshot. Each snapshot is INSERT-only; the
// table's BEFORE UPDATE/DELETE trigger (added in Section 7 Step B)
// blocks mutation from the app role.
//
// Used by the reconciler (write) and by the replay endpoint (read).
//
// Audit ref: CHECKLIST Section 7.
type PositionSnapshotStore struct {
	pool *pgxpool.Pool
	log  zerolog.Logger
}

func NewPositionSnapshotStore(pool *pgxpool.Pool) *PositionSnapshotStore {
	return &PositionSnapshotStore{
		pool: pool,
		log:  observability.Logger("position_snapshot_store"),
	}
}

type SnapshotRow struct {
	ID             int64
	UserID         string
	SnapshotTS     time.Time
	PositionCount  int
	Positions      []models.Position
	ContentHash    string
	ReconcileRunID string
}

func (s *PositionSnapshotStore) WriteSnapshot(
	ctx context.Context,
	userID string,
	positions []models.Position,
	reconcileRunID string,
) error {
	if userID == "" {
		return fmt.Errorf("snapshot user_id must not be empty")
	}

	copy_ := make([]models.Position, len(positions))
	copy(copy_, positions)
	sort.Slice(copy_, func(i, j int) bool {
		return copy_[i].OrderID < copy_[j].OrderID
	})

	jsonBytes, err := json.Marshal(copy_)
	if err != nil {
		s.log.Warn().Err(err).Str("user_id", userID).Msg("snapshot_marshal_failed")
		return err
	}

	sum := sha256.Sum256(jsonBytes)
	hash := hex.EncodeToString(sum[:])

	writeCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	_, err = s.pool.Exec(writeCtx, `
		INSERT INTO execution_positions_snapshot
		  (user_id, snapshot_ts, position_count, positions, content_hash, reconcile_run_id)
		VALUES ($1, $2, $3, $4::jsonb, $5, $6)
	`,
		userID,
		time.Now().UTC(),
		len(copy_),
		jsonBytes,
		hash,
		reconcileRunID,
	)
	if err != nil {
		s.log.Warn().Err(err).Str("user_id", userID).Msg("snapshot_insert_failed")
		return err
	}
	return nil
}

func (s *PositionSnapshotStore) LatestSnapshot(
	ctx context.Context, userID string,
) (*SnapshotRow, error) {
	row := s.pool.QueryRow(ctx, `
		SELECT id, user_id, snapshot_ts, position_count, positions, content_hash, reconcile_run_id
		FROM execution_positions_snapshot
		WHERE user_id = $1
		ORDER BY snapshot_ts DESC
		LIMIT 1
	`, userID)

	var (
		r     SnapshotRow
		rawJS []byte
	)
	if err := row.Scan(&r.ID, &r.UserID, &r.SnapshotTS, &r.PositionCount, &rawJS, &r.ContentHash, &r.ReconcileRunID); err != nil {
		if err.Error() == "no rows in result set" {
			return nil, nil
		}
		return nil, fmt.Errorf("latest snapshot for %s: %w", userID, err)
	}
	if err := json.Unmarshal(rawJS, &r.Positions); err != nil {
		return nil, fmt.Errorf("unmarshal latest snapshot positions for %s: %w", userID, err)
	}
	return &r, nil
}

func (s *PositionSnapshotStore) SnapshotsBetween(
	ctx context.Context, userID string, from, to time.Time,
) ([]*SnapshotRow, error) {
	rows, err := s.pool.Query(ctx, `
		SELECT id, user_id, snapshot_ts, position_count, positions, content_hash, reconcile_run_id
		FROM execution_positions_snapshot
		WHERE user_id = $1 AND snapshot_ts BETWEEN $2 AND $3
		ORDER BY snapshot_ts ASC
	`, userID, from, to)
	if err != nil {
		return nil, fmt.Errorf("snapshots between for %s: %w", userID, err)
	}
	defer rows.Close()

	out := make([]*SnapshotRow, 0)
	for rows.Next() {
		var (
			r     SnapshotRow
			rawJS []byte
		)
		if err := rows.Scan(&r.ID, &r.UserID, &r.SnapshotTS, &r.PositionCount, &rawJS, &r.ContentHash, &r.ReconcileRunID); err != nil {
			return nil, fmt.Errorf("scan snapshot row: %w", err)
		}
		if err := json.Unmarshal(rawJS, &r.Positions); err != nil {
			return nil, fmt.Errorf("unmarshal snapshot positions: %w", err)
		}
		out = append(out, &r)
	}
	return out, rows.Err()
}

func (s *PositionSnapshotStore) PruneOlderThan(
	ctx context.Context, cutoff time.Time,
) (int64, error) {
	row := s.pool.QueryRow(ctx, `
		SELECT COUNT(*) FROM execution_positions_snapshot WHERE snapshot_ts < $1
	`, cutoff)
	var count int64
	if err := row.Scan(&count); err != nil {
		return 0, fmt.Errorf("count prune candidates: %w", err)
	}
	if count == 0 {
		return 0, nil
	}
	_, err := s.pool.Exec(ctx, `
		SELECT execution_snapshot_prune($1)
	`, cutoff)
	if err != nil {
		s.log.Warn().Err(err).Msg("snapshot_prune_failed_function_missing_until_step_b")
		return 0, err
	}
	return count, nil
}
```

## File changes — src/execution/internal/state/manager.go (additive)

```go
// RemoveGhostPosition deletes a position the broker no longer
// reports. Returns true when an entry was actually removed.
//
// Called by the reconciler's ghost-position branch when the engine's
// view contains a position that:
//   (a) is NOT in the current broker positions list, AND
//   (b) was present in the last persisted positions snapshot >= the
//       configured ghost-position min-age threshold ago.
// Together, those two facts say 'the broker closed this cleanly
// between cycles'. The engine adopts the close.
//
// Audit ref: CHECKLIST Section 7 'No ghost positions'.
func (m *Manager) RemoveGhostPosition(userID, brokerOrderID string) bool {
	if userID == "" || brokerOrderID == "" {
		return false
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	us := m.getUserRead(userID)
	if us == nil {
		return false
	}
	for i := range us.positions {
		if us.positions[i].OrderID == brokerOrderID {
			us.positions = append(us.positions[:i], us.positions[i+1:]...)
			observability.OpenPositionCount.Set(float64(len(us.positions)))
			return true
		}
	}
	return false
}
```

## File changes — src/execution/internal/state/reconciler.go (extended)

Three edits:

### a) Reconciler struct gains snapshot fields

```go
type Reconciler struct {
	broker      broker.Port
	state       *Manager
	identity    IdentityProvider
	interval    time.Duration
	log         zerolog.Logger
	snapshots   *store.PositionSnapshotStore  // NEW
	ghostMinAge time.Duration                  // NEW
	snapEnabled bool                           // NEW

	mu      sync.Mutex
	stopped bool
}
```

### b) NewReconciler signature gains three params

```go
func NewReconciler(
	bp broker.Port,
	st *Manager,
	identity IdentityProvider,
	interval time.Duration,
	snapshots *store.PositionSnapshotStore,
	ghostMinAge time.Duration,
	snapEnabled bool,
) *Reconciler {
	if interval <= 0 {
		interval = 60 * time.Second
	}
	if ghostMinAge <= 0 {
		ghostMinAge = 5 * time.Minute
	}
	return &Reconciler{
		broker:      bp,
		state:       st,
		identity:    identity,
		interval:    interval,
		log:         observability.Logger("reconciler"),
		snapshots:   snapshots,
		ghostMinAge: ghostMinAge,
		snapEnabled: snapEnabled,
	}
}
```

### c) detectGhostPositions + snapshot write inside runOnceForUser

```go
func (r *Reconciler) runOnceForUser(parent context.Context, userID string) {
	// ... existing body unchanged up to:
	r.reconcilePositions(userID, brokerPositions)
	r.reconcilePending(userID, brokerPending)

	// Section 7 (CHECKLIST): ghost-position detection + snapshot write.
	if r.snapEnabled && r.snapshots != nil {
		r.detectGhostPositions(ctx, userID, brokerPositions)
		if err := r.snapshots.WriteSnapshot(ctx, userID, r.state.Positions(userID), ""); err != nil {
			r.log.Warn().Err(err).Str("user_id", userID).Msg("reconcile_snapshot_write_failed")
		}
	}

	reconcileTotal.WithLabelValues("ok").Inc()
}

func (r *Reconciler) detectGhostPositions(
	ctx context.Context, userID string, brokerPositions []models.Position,
) {
	latest, err := r.snapshots.LatestSnapshot(ctx, userID)
	if err != nil || latest == nil {
		return
	}
	if time.Since(latest.SnapshotTS) < r.ghostMinAge {
		return
	}
	brokerSet := make(map[string]struct{}, len(brokerPositions))
	for _, bp := range brokerPositions {
		brokerSet[bp.OrderID] = struct{}{}
	}
	for _, sp := range latest.Positions {
		if sp.OrderID == "" {
			continue
		}
		if _, present := brokerSet[sp.OrderID]; present {
			continue
		}
		removed := r.state.RemoveGhostPosition(userID, sp.OrderID)
		if !removed {
			continue
		}
		reconcileDrift.WithLabelValues("ghost_position").Inc()
		r.log.Error().
			Str("user_id", userID).
			Str("broker_order_id", sp.OrderID).
			Str("symbol", sp.Symbol).
			Str("direction", sp.Direction).
			Float64("lot_size", sp.LotSize).
			Dur("snapshot_age", time.Since(latest.SnapshotTS)).
			Msg("reconcile_ghost_position_detected_removing")
	}
}
```

Add to imports:

```go
"github.com/flamegreat-1/etradie/src/execution/internal/store"
```

## File changes — cmd/execution/main.go (additive)

- Construct `store.NewPositionSnapshotStore(pool)` alongside the
  other stores.
- Pass it to `state.NewReconciler` along with `ghostMinAge` (from
  `EXECUTION_GHOST_POSITION_MIN_AGE_SECS`) and `snapEnabled` (from
  `EXECUTION_POSITION_SNAPSHOT_ENABLED`).
- Launch a background retention goroutine that calls
  `PruneOlderThan(now - retention)` every 1h.

## helm/execution/values.yaml + configmap.yaml

New keys under `config.execution`:

```yaml
positionSnapshotEnabled: "true"
positionSnapshotRetentionHours: "168"
ghostPositionMinAgeSecs: "300"
```

Surface via ConfigMap as:

```yaml
EXECUTION_POSITION_SNAPSHOT_ENABLED:          "{{ .Values.config.execution.positionSnapshotEnabled | default \"true\" }}"
EXECUTION_POSITION_SNAPSHOT_RETENTION_HOURS:  "{{ .Values.config.execution.positionSnapshotRetentionHours | default \"168\" }}"
EXECUTION_GHOST_POSITION_MIN_AGE_SECS:        "{{ .Values.config.execution.ghostPositionMinAgeSecs | default \"300\" }}"
```

## src/execution/internal/config/config.go

New fields:

```go
PositionSnapshotEnabled         bool `envconfig:"POSITION_SNAPSHOT_ENABLED" default:"true"`
PositionSnapshotRetentionHours  int  `envconfig:"POSITION_SNAPSHOT_RETENTION_HOURS" default:"168"`
GhostPositionMinAgeSecs         int  `envconfig:"GHOST_POSITION_MIN_AGE_SECS" default:"300"`
```

Validate each in `validate()` with sensible ranges.

---

# After Step A lands — Steps B + C

## Step B — DB-level audit immutability + replay endpoint + CLI

Key deliverables:

1. New SQL function + BEFORE UPDATE/BEFORE DELETE trigger on both
   `execution_audit_logs` AND `execution_positions_snapshot`. The
   pruner uses a `SECURITY DEFINER` function (`execution_snapshot_prune`)
   granted only to the migration role to age out old rows.
2. New gRPC method `ReplayAuditLog(user_id, since, until)` on the
   execution service. Returns a chronologically-ordered stream of
   audit + snapshot events. Service-token-authenticated.
3. New CLI subcommand for `executionctl replay --user=<id>
   --since=<rfc3339>` that wraps the gRPC call.
4. New PrometheusRule alarm:
   `ExecutionReconcileGhostPositions` — ghost-position rate
   > 0 over 5m. Fires on any cross-restart ghost detection.

## Step C — eager Refresh on startup + chaos test + scorecard

Key deliverables:

1. Boot path in `cmd/execution/main.go`: before the reconciler
   starts (and AFTER the watcher restoration committed in Commit 6
   of this MR), iterate `userStore.ListActiveUsers(ctx)` and call
   `state.Manager.Refresh(ctx, userID)` for every user. Engine
   memory is hot before the first user request lands. Gated by a
   new env `EXECUTION_PRELOAD_POSITIONS_ON_START` (default `true`).
2. New chaos test `tests/chaos/test_positions_snapshot_and_ghost.py`:
   writes a snapshot, simulates the broker losing one position,
   asserts the ghost-detection rule classifies it.
3. Update MR description with Section 7 scorecard table
   (12 items across the two sub-sections, all green).

---

# Onward — Sections 8 / 9 / 10

Not yet planned in detail. Section 8 (Failure recovery), Section 9
(Security & isolation), Section 10 (Testing & simulation) remain
ahead. Section 9's tenant-isolation items are partially closed by
Commit 4 of this MR (NetworkPolicy egress hardening). Section 10
load + chaos test scaffolding already exists in `tests/chaos/`;
the load-test budgets (10 → 50 → 100 MT terminals) need a dedicated
harness.
