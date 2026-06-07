# Tier 7 (Database Security) — Backup, Restore & Encryption Runbook

> Companion to `docs/security/TIER7_DATABASE_SECURITY.md`. Operator
> procedures for the database controls that the Helm charts cannot fully
> automate: reading restore-drill results, performing a real restore,
> and verifying encryption at rest. Follow the relevant section in
> order.

---

## 1. Backup model (what exists)

- A daily `pg_dump --format=custom` CronJob (`postgres-backup`) writes
  `etradie-<timestamp>.dump` to a dedicated backups PVC at 02:00 UTC,
  retained 7 days (staging) / 30 days (production).
- When `postgres.backup.offsite.enabled=true` (production), an
  `rclone` sidecar copies every fresh dump to an S3-compatible remote
  BEFORE the retention prune runs.
- A weekly restore-drill CronJob (`postgres-restore-drill`, production)
  proves the latest local dump is restorable.

---

## 2. Reading restore-drill results

The drill runs Mondays 03:00 UTC (after the 02:00 backup). Inspect the
most recent run:

```sh
kubectl -n etradie-system get jobs -l app.kubernetes.io/name=postgres-restore-drill
kubectl -n etradie-system logs -l app.kubernetes.io/name=postgres-restore-drill --tail=50
```

- **PASS** — the log ends with `[restore-drill] PASS: <dump> is
  restorable`. The dump restored into a throwaway scratch database, the
  restored database had tables, `auth_users` was queryable, and the
  scratch database was dropped. No action needed.
- **FAIL** — any `[restore-drill] FATAL: ...` line. The Job is marked
  Failed. Treat as a backup-integrity incident: a dump that does not
  restore is not a backup. Investigate immediately (see section 3 to
  attempt a manual restore of an older dump and section 5 for likely
  causes).

The drill never touches the live database; it only creates and drops a
scratch database named `etradie_restore_drill`.

---

## 3. Manual restore (incident / DR)

Use this to restore into a FRESH database during a real recovery. Never
restore over the live database; restore into a new name and cut over
deliberately.

### 3a. From the local PVC dump

```sh
# Exec into a transient psql/pg_restore pod that mounts the backups PVC,
# or run from the postgres pod with the backups PVC mounted.
LATEST=$(ls -1t /backups/etradie-*.dump | head -n1)
psql -d "$POSTGRES_DB" -c 'CREATE DATABASE etradie_restored;'
pg_restore --no-owner --no-privileges --exit-on-error \
  --dbname=etradie_restored "$LATEST"
```

### 3b. From the off-cluster (rclone) copy

```sh
# Materialise rclone.conf from the postgres-backup-credentials secret,
# then pull the newest object from the remote bucket/prefix.
rclone --config /tmp/rclone/rclone.conf \
  copy "$RCLONE_REMOTE_NAME:$REMOTE_BUCKET/$REMOTE_PATH_PREFIX" /restore \
  --include 'etradie-*.dump'
LATEST=$(ls -1t /restore/etradie-*.dump | head -n1)
pg_restore --no-owner --no-privileges --exit-on-error \
  --dbname=etradie_restored "$LATEST"
```

After validating `etradie_restored`, cut over by pointing the services'
`*_DATABASE_URL` / `POSTGRES_DB` at the restored database (or rename),
then restart the consuming workloads.

---

## 4. Verifying encryption at rest (per provider)

Production `values-production.yaml` requires every datastore (and the
backup PVC) to bind an encrypted StorageClass. The class name is
provider-specific; verify the bound class is actually encrypted:

- **OCI OKE** — the default `oci-bv` Block Volume class is encrypted at
  rest by default (Oracle-managed keys, or your KMS key when the node
  pool sets `kms_key_id`). Confirm:
  ```sh
  kubectl get sc
  kubectl -n etradie-system get pvc -o custom-columns=NAME:.metadata.name,SC:.spec.storageClassName
  ```
  No extra action; optionally pin a CMK via the node pool `kms_key_id`.
- **Contabo / bare-metal K3s** — use a Longhorn StorageClass with
  encryption enabled (LUKS), or a LUKS-backed local class. Set
  `postgres.storage.storageClassName` (and redis/chromadb/backup) to
  that class in `values-production.yaml`.
- **Any other cloud** — set the datastore `storageClassName` to that
  provider's encrypted block class.

If `storageClassName` is left empty, the cluster default class is used;
confirm that default is encrypted before going to production.

---

## 5. Off-cluster backup encryption

The rclone remote MUST be configured by the operator (it cannot be
automated by the chart) with:

- server-side encryption (SSE) enabled on the bucket;
- object-lock / immutability matching `retentionDays` + a grace window;
- a lifecycle rule mirroring `retentionDays` so the remote does not grow
  unbounded (rclone does not enforce retention).

These are seeded in Vault under
`etradie/data-layer/postgres-backup/<env>` (keys `rclone_remote_name`,
`rclone_config`, `remote_bucket`, `remote_path_prefix`). Test the upload
path on staging before relying on it.

---

## 6. Common restore-drill failure causes

- **"no dump found in /backups"** — the backup CronJob has not run yet,
  or the backups PVC is not the one the backup job writes to. Confirm
  the backup Job succeeded first.
- **`pg_restore failed`** — the dump is truncated or corrupt. Check the
  backup Job logs for that day; the offsite copy may be intact even if
  the local one is not (section 3b).
- **"restored database has no tables" / "auth_users not queryable"** —
  the dump completed but is logically empty or partial. Treat as a
  backup-integrity incident.
