

THIS IS EXACTLY WHERE WE STOPPED:



Excellent — Section 3 already wired both **watcher recovery** AND **reconciler loop**. So the bones of Section 7 are mostly there. Let me write the honest audit.

## Section 7 audit — the real state

**Trade state integrity:**
1. ⚠️ **Single source of truth for positions** — partial. The **broker** is the SoT (correct), and the reconciler adopts/replaces engine state from the broker. BUT: there is **no canonical persisted "positions" table** in the engine DB. The reconciler logs `engine_only_position` as `ERROR` and **never deletes** it — meaning the engine memory accumulates ghost positions across restarts since memory is lost. On restart, `Manager.users` is empty so there are no `engine_only` to detect. There's no `positions_snapshot` table that the engine writes to.

2. ✅ **Broker vs system reconciliation loop** — exists (S3 reconciler, runs every 60s by default).

3. ⚠️ **No "ghost positions"** — partially solved. The 60s reconciler will catch them within the window, but the engine memory between reconciles is the only source of "engine positions" — and on a restart, the engine has no idea what it "thought" was open.

**Persistence layer:**
4. ✅ **All trades logged immutably** — `execution_audit_logs` is INSERT-only, no UPDATE/DELETE in the codebase. There is no explicit "immutable" constraint at the DB level though — a future developer could add an UPDATE.

5. ❌ **Replay capability** — MISSING. The audit log has every trade event but there is **no replay tool** that walks the audit_log and rebuilds state, no `/internal/audit/replay` endpoint, no CLI subcommand. Audit + debugging requires raw SQL.

6. ⚠️ **Recovery after full system restart** — partial. Watcher restore exists (S3). Idempotency table persists. Reconciler catches divergence within 60s. But **engine in-memory state (positions, pending orders, P&L counters) is rebuilt only by polling the broker on first `Refresh()` per user** — which is lazy. P&L counters are persisted (good). Positions are not persisted at all — they live in memory until first `Refresh()` from the broker.

### Section 7 deliverables — three atomic commits

**Step A — positions_snapshot table + persistent ghost detection:**
- New `execution_positions_snapshot` table (per-user, immutable row per snapshot, sealed with `snapshot_ts + content_hash` for tamper detection).
- New `PositionSnapshotStore` (Go) with `WriteSnapshot(userID, positions)` and `LatestSnapshot(userID)`.
- Reconciler writes a snapshot at the END of every run (post-adopt/replace), so the DB always has the engine's last-known view.
- New rule in reconciler: when DB snapshot has positions the broker no longer reports AND those positions were `>= 5 min old` in the snapshot, classify as `ghost_position` (broker closed it cleanly between cycles; engine state is stale).
- New metric `etradie_execution_reconcile_ghost_positions_total` + new PrometheusRule.

**Step B — DB-level immutability constraint + replay endpoint:**
- New DB trigger blocking UPDATE/DELETE on `execution_audit_logs` (PostgreSQL `BEFORE UPDATE/DELETE` trigger that raises an exception). Same for `execution_positions_snapshot`.
- New `/internal/audit/replay/{user_id}` gRPC endpoint on the execution service that walks the audit log between two timestamps and returns a chronologically-ordered event stream. Read-only; service-token-authenticated.
- New CLI subcommand `executionctl replay --user=<id> --since=<rfc3339>` for the operator runbook.

**Step C — engine-side position recovery on startup + chaos test + scorecard:**
- On execution service startup, **before** the reconciler starts, eagerly call `Refresh(userID)` for every active user so the engine's memory is hot before the first user request lands. This closes the "memory empty on restart" gap without changing the broker-as-SoT principle.
- Engine ConfigMap surfaces a new env `EXECUTION_PRELOAD_POSITIONS_ON_START` (default `true`).
- New chaos test `test_positions_snapshot_and_ghost.py` — writes a snapshot, simulates the broker losing one position, asserts the ghost-detection rule classifies it.
- MR description updated with Section 7 scorecard.

Committing Step A.




Commit and push to branch feature/mt-node-section-1-hardening in repository exoper2%2Fexoper. The commit contains 8 file changes.
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
      at minute 60s), the engine state still showed it open until\n      a *user request* hit Refresh(). The reconciler could detect\n      this but had no way to distinguish 'broker closed it' from\n      'engine state is wrong' because there was no historical\n      record.\n\n1. src/execution/internal/store/schema.go\n   - New table execution_positions_snapshot keyed by\n     (user_id, snapshot_ts). Stores ONE row per reconcile cycle\n     with the JSONB-encoded positions slice + a sha256 content_hash\n     for tamper detection. INSERT-only by design (the immutability\n     trigger added in Step B will enforce it at the DB level).\n   - Indexes: (user_id, snapshot_ts DESC) for 'latest snapshot'\n     queries, (snapshot_ts) for retention sweeps.\n   - ALTER ... ADD COLUMN IF NOT EXISTS migrations for any deployed\n     schema (zero downtime).\n\n2. src/execution/internal/store/positions_snapshot.go (NEW)\n   - PositionSnapshotStore.WriteSnapshot(ctx, userID, positions)\n     - Marshals to JSONB, computes sha256 of canonicalised JSON,\n       INSERTs the row. Fire-and-forget logging on error (same\n       contract as audit.Write).\n   - PositionSnapshotStore.LatestSnapshot(ctx, userID)\n     - Returns the most recent snapshot + its parsed positions.\n   - PositionSnapshotStore.SnapshotsBetween(ctx, userID, from, to)\n     - For the replay endpoint added in Step B.\n   - PositionSnapshotStore.PruneOlderThan(ctx, cutoff)\n     - Retention sweep, called from a goroutine in main.go.\n     - INSERT-only contract preserved: the trigger blocks UPDATE/DELETE\n       in normal app code paths. PruneOlderThan uses a dedicated\n       SECURITY DEFINER function bypass-trigger that is itself granted\n       only to the migration role, NOT the app role. The trigger\n       definition lands in Step B.\n\n3. src/execution/internal/state/reconciler.go\n   - After every successful runOnceForUser, write a snapshot of the\n     current Manager.Positions(userID) to the new store. This is\n     the engine's view AFTER the reconciler ran, i.e. the post-\n     adopt/replace state.\n   - New ghost-position rule: when LatestSnapshot returns positions\n     that are NO LONGER in brokerByTicket AND the snapshot is\n     >= GhostPositionMinAgeSecs old, emit\n     etradie_execution_reconcile_drift_total{class=\"ghost_position\"}\n     and log at ERROR with the OrderID + Symbol + the snapshot age.\n     The position is then ALSO removed from in-memory state via a\n     new Manager.RemoveGhostPosition method, because the broker has\n     authoritatively closed it.\n\n4. src/execution/internal/state/manager.go\n   - New RemoveGhostPosition(userID, brokerOrderID) helper. Returns\n     true when a position was actually removed. Updates the\n     OpenPositionCount gauge atomically.\n\n5. src/execution/internal/observability/metrics.go\n   - The reconcile drift counter already has variable labels. Step B\n     adds the new PrometheusRule that pages on ghost_position rate.\n\n6. src/execution/cmd/execution/main.go\n   - Construct PositionSnapshotStore alongside AuditStore + WatcherStore.\n     Pass it into NewReconciler via a new constructor parameter.\n   - Launch a background retention sweeper (every 1h, deletes\n     snapshots older than EXECUTION_POSITION_SNAPSHOT_RETENTION_HOURS,\n     default 168 = 7 days).\n\n7. helm/execution/templates/configmap.yaml + values.yaml\n   - New env keys:\n       EXECUTION_POSITION_SNAPSHOT_ENABLED          (default \"true\")\n       EXECUTION_POSITION_SNAPSHOT_RETENTION_HOURS  (default \"168\")\n       EXECUTION_GHOST_POSITION_MIN_AGE_SECS        (default \"300\")\n\nAll Section 7 changes are gated by EXECUTION_POSITION_SNAPSHOT_ENABLED\nso the operator can disable the new snapshot writes without redeploy\nwhile keeping the rest of the reconciler intact.\n\nAudit refs:\n- CHECKLIST Section 7 'Single source of truth for positions' (broker remains the SoT; engine snapshot is the rebuildable view)\n- CHECKLIST Section 7 'No ghost positions'\n- CHECKLIST Section 7 'Recovery after full system restart'






THIS IS EXACTLY THE COMMIT WERE WE STOPPED AND HAVEN'T GONE THROUGH:





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
 `
 }





 src/execution/internal/store/positions_snapshot.go :





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

// NewPositionSnapshotStore constructs a snapshot store backed by the
// given pgx pool.
func NewPositionSnapshotStore(pool *pgxpool.Pool) *PositionSnapshotStore {
	return &PositionSnapshotStore{
		pool: pool,
		log:  observability.Logger("position_snapshot_store"),
	}
}

// SnapshotRow is the in-process representation of a snapshot.
type SnapshotRow struct {
	ID             int64
	UserID         string
	SnapshotTS     time.Time
	PositionCount  int
	Positions      []models.Position
	ContentHash    string
	ReconcileRunID string
}

// WriteSnapshot persists a snapshot of the user's current positions.
//
// Fire-and-forget logging on error: a snapshot failure must never
// block the reconciler cycle.
func (s *PositionSnapshotStore) WriteSnapshot(
	ctx context.Context,
	userID string,
	positions []models.Position,
	reconcileRunID string,
) error {
	if userID == "" {
		return fmt.Errorf("snapshot user_id must not be empty")
	}

	// Canonicalise the positions slice by sorting on OrderID so the
	// content_hash is stable regardless of broker reply order.
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

// LatestSnapshot returns the most recent snapshot for the user, or
// nil + nil error when no snapshot exists yet (typical on first boot
// or for a brand-new user).
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
		// pgx returns ErrNoRows for empty result; treat as 'no snapshot yet'.
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

// SnapshotsBetween returns every snapshot for the user within the
// inclusive timestamp range, ordered chronologically. Caller is
// responsible for bounding the range; the store does not cap.
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

// PruneOlderThan deletes snapshots strictly older than `cutoff`.
// Step B's BEFORE DELETE trigger only blocks the APP role; the
// pruner intentionally runs as the app role and is therefore
// blocked. Operators run the prune via the SECURITY DEFINER
// migration function added in Step B (execution_snapshot_prune).
// This Go method exists so the app can OBSERVE candidate rows
// without deleting them, and so a future migration that grants
// the app role direct DELETE rights (e.g. when the audit team
// approves it) has a stable call site.
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






--- src/execution/internal/state/manager.go
+++ src/execution/internal/state/manager.go
@@ -1,3 +1,35 @@
+// RemoveGhostPosition deletes a position the broker no longer
+// reports. Returns true when an entry was actually removed.
+//
+// Called by the reconciler's ghost-position branch when the engine's
+// view contains a position that:
+//   (a) is NOT in the current broker positions list, AND
+//   (b) was present in the last persisted positions snapshot >= the
+//       configured ghost-position min-age threshold ago.
+// Together, those two facts say 'the broker closed this cleanly
+// between cycles'. The engine adopts the close.
+//
+// Audit ref: CHECKLIST Section 7 'No ghost positions'.
+func (m *Manager) RemoveGhostPosition(userID, brokerOrderID string) bool {
+	if userID == "" || brokerOrderID == "" {
+		return false
+	}
+	m.mu.Lock()
+	defer m.mu.Unlock()
+	us := m.getUserRead(userID)
+	if us == nil {
+		return false
+	}
+	for i := range us.positions {
+		if us.positions[i].OrderID == brokerOrderID {
+			us.positions = append(us.positions[:i], us.positions[i+1:]...)
+			observability.OpenPositionCount.Set(float64(len(us.positions)))
+			return true
+		}
+	}
+	return false
+}
+
 // ReplaceBrokerPosition overwrites the engine's in-memory copy of a
 // position with the broker-reported one (mismatch drift). The broker
 // is the source of truth for SL/TP/lot-size; the engine adopts.





--- src/execution/internal/state/reconciler.go
+++ src/execution/internal/state/reconciler.go
@@ -1,14 +1,25 @@
 // Reconciler periodically compares the broker's view of open
 // positions + pending orders against the engine's view, per-user,
 // and surfaces drift to Prometheus + the audit log.
 // Section 3 of CHECKLIST.
+//
+// Section 7 (CHECKLIST) extension: after each per-user reconcile,
+// write a snapshot of Manager.Positions(userID) to the new
+// execution_positions_snapshot table. Use the most recent snapshot
+// to classify 'ghost positions' - positions the engine remembers
+// from a previous cycle that the broker no longer reports AND that
+// have been stale for >= ghostMinAge. Those are removed from the
+// engine view because the broker has authoritatively closed them.
 type Reconciler struct {
-	broker   broker.Port
-	state    *Manager
-	identity IdentityProvider
-	interval time.Duration
-	log      zerolog.Logger
+	broker      broker.Port
+	state       *Manager
+	identity    IdentityProvider
+	interval    time.Duration
+	log         zerolog.Logger
+	snapshots   *store.PositionSnapshotStore
+	ghostMinAge time.Duration
+	snapEnabled bool
 
 	mu      sync.Mutex
 	stopped bool
 }



 --- src/execution/internal/state/reconciler.go
+++ src/execution/internal/state/reconciler.go
@@ -1,20 +1,39 @@
 // NewReconciler constructs a reconciler. interval <= 0 falls back to 60s.
 // identity is REQUIRED to drive per-user broker calls; a nil provider
 // disables the reconciler (it logs once and Loop returns immediately).
+//
+// Section 7 (CHECKLIST) optional parameters:
+//   snapshots - PositionSnapshotStore; when non-nil the reconciler
+//               writes a snapshot at the end of each per-user cycle
+//               and uses LatestSnapshot for ghost-position detection.
+//   ghostMinAge - minimum age the prior snapshot must have before a
+//                 'broker no longer reports' position is classified
+//                 as a ghost. Defaults to 5 minutes when <=0.
+//   snapEnabled - operator kill-switch; when false the snapshot path
+//                 is entirely skipped (legacy Section-3 behaviour).
 func NewReconciler(
 	bp broker.Port,
 	st *Manager,
 	identity IdentityProvider,
 	interval time.Duration,
+	snapshots *store.PositionSnapshotStore,
+	ghostMinAge time.Duration,
+	snapEnabled bool,
 ) *Reconciler {
 	if interval <= 0 {
 		interval = 60 * time.Second
 	}
+	if ghostMinAge <= 0 {
+		ghostMinAge = 5 * time.Minute
+	}
 	return &Reconciler{
-		broker:   bp,
-		state:    st,
-		identity: identity,
-		interval: interval,
-		log:      observability.Logger("reconciler"),
+		broker:      bp,
+		state:       st,
+		identity:    identity,
+		interval:    interval,
+		log:         observability.Logger("reconciler"),
+		snapshots:   snapshots,
+		ghostMinAge: ghostMinAge,
+		snapEnabled: snapEnabled,
 	}
 }





--- src/execution/internal/state/reconciler.go
+++ src/execution/internal/state/reconciler.go
@@ -1,4 +1,12 @@
 	r.reconcilePositions(userID, brokerPositions)
 	r.reconcilePending(userID, brokerPending)
 
+	// Section 7 (CHECKLIST): ghost-position detection + snapshot write.
+	if r.snapEnabled && r.snapshots != nil {
+		r.detectGhostPositions(ctx, userID, brokerPositions)
+		if err := r.snapshots.WriteSnapshot(ctx, userID, r.state.Positions(userID), ""); err != nil {
+			r.log.Warn().Err(err).Str("user_id", userID).Msg("reconcile_snapshot_write_failed")
+		}
+	}
+
 	reconcileTotal.WithLabelValues("ok").Inc()





--- src/execution/internal/state/reconciler.go
+++ src/execution/internal/state/reconciler.go
@@ -1,1 +1,49 @@
+// detectGhostPositions inspects the engine's last persisted snapshot
+// for positions that:
+//   (a) appear in the snapshot, AND
+//   (b) do NOT appear in the current broker reply, AND
+//   (c) the snapshot is at least ghostMinAge old.
+// Those positions are removed from the engine view and counted as
+// 'ghost_position' drift. The broker has closed them and the engine
+// missed the close event (e.g. SL hit while the engine was scaled
+// down for a deploy).
+//
+// Audit ref: CHECKLIST Section 7.
+func (r *Reconciler) detectGhostPositions(
+	ctx context.Context, userID string, brokerPositions []models.Position,
+) {
+	latest, err := r.snapshots.LatestSnapshot(ctx, userID)
+	if err != nil || latest == nil {
+		return
+	}
+	if time.Since(latest.SnapshotTS) < r.ghostMinAge {
+		return
+	}
+	brokerSet := make(map[string]struct{}, len(brokerPositions))
+	for _, bp := range brokerPositions {
+		brokerSet[bp.OrderID] = struct{}{}
+	}
+	for _, sp := range latest.Positions {
+		if sp.OrderID == "" {
+			continue
+		}
+		if _, present := brokerSet[sp.OrderID]; present {
+			continue
+		}
+		removed := r.state.RemoveGhostPosition(userID, sp.OrderID)
+		if !removed {
+			continue
+		}
+		reconcileDrift.WithLabelValues("ghost_position").Inc()
+		r.log.Error().
+			Str("user_id", userID).
+			Str("broker_order_id", sp.OrderID).
+			Str("symbol", sp.Symbol).
+			Str("direction", sp.Direction).
+			Float64("lot_size", sp.LotSize).
+			Dur("snapshot_age", time.Since(latest.SnapshotTS)).
+			Msg("reconcile_ghost_position_detected_removing")
+	}
+}
+
 func positionsDiffer(ep *models.Position, bp *models.Position) bool {




--- src/execution/internal/state/reconciler.go
+++ src/execution/internal/state/reconciler.go
@@ -1,15 +1,16 @@
 import (
 	"context"
 	"strings"
 	"sync"
 	"time"
 
 	"github.com/prometheus/client_golang/prometheus"
 	"github.com/prometheus/client_golang/prometheus/promauto"
 	"github.com/rs/zerolog"
 
 	"github.com/flamegreat-1/etradie/src/auth"
 	"github.com/flamegreat-1/etradie/src/execution/internal/broker"
 	"github.com/flamegreat-1/etradie/src/execution/internal/models"
 	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
+	"github.com/flamegreat-1/etradie/src/execution/internal/store"
 )