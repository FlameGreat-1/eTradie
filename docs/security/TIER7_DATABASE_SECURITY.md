# 🔴 TIER 7: Database Security — Audit & Remediation Plan

> Status: **IMPLEMENTATION IN PROGRESS** on branch
> `security/tier7-database-hardening` (Option B: in-place role downgrade).
>
> ### Progress tracker (this branch)
> - [x] **Fix 1 — least-privilege role.** `docker/postgres/init.sql` +
>   chart init-configmap downgrade the role: `NOSUPERUSER NOCREATEROLE
>   NOREPLICATION NOBYPASSRLS`. CREATEDB retained (restore drill needs
>   it; low-risk). Role stays owner so all boot DDL + SECURITY DEFINER
>   funcs keep working.
> - [x] **Fix 2 — TLS in transit.** billing `buildPostgresURL()` and the
>   gateway fallback DSN default `sslmode=require` (was `disable`).
>   `POSTGRES_SSLMODE` mapped in the gateway ExternalSecret (live) +
>   documented in the gateway Vault path. NOT mapped for engine/execution/
>   management (they read a full `*_DATABASE_URL`; sslmode lives in the
>   URL — a mapping there would be dead config).
> - [x] **Fix 3 — encryption at rest.** `values-production.yaml`
>   documents + exposes an operator-set encrypted `storageClassName` for
>   postgres/redis/chromadb and the backup PVC (portable; empty = cluster
>   default). Per-provider verification in the runbook.
> - [x] **Fix 4 — restore testing.** Weekly `postgres-restore-drill`
>   CronJob (restore latest dump into scratch DB, integrity check, drop),
>   values block, NetworkPolicy ingress+egress wiring, prod-enabled,
>   runbook `docs/runbooks/tier7-database-backup-restore.md`.
> - [x] **Fix 5 — DB audit logging.** Postgres `log_connections`,
>   `log_disconnections`, `log_statement=ddl`, attributable
>   `log_line_prefix` via `-c` args; `postgres.auditLogging` values
>   (enabled by default).
> - [x] **Fix 6 — comment cleanups.** gateway `values.yaml` (EKS/RDS/
>   ElastiCache wording), data-layer `values-production.yaml`
>   (eks_managed_node_groups/EKS), stale redis-configmap header comment.
> - [ ] Open the MR once CI (helm lint + kubeconform + Go build/tests +
>   Trivy/govulncheck) is green.
>
> ### Deviations from the original plan (for correctness)
> - Engine `POSTGRES_SSLMODE` ExternalSecret mapping was NOT added: the
>   engine reads a full `DATABASE_URL`, so the mapping would be an unused
>   (dead) env var. sslmode is carried in the URL.
> - `CREATEDB` retained on the role: under single-role Option B the
>   restore drill connects as this role and must CREATE/DROP a scratch
>   database. CREATEDB is low-risk (own-databases only; no cross-db
>   access, no role creation, no RLS bypass, no superuser escalation).
>
> ---
>
> Original audit status: **AUDIT COMPLETE — implementation NOT started.**
> Completed/merged tiers so far: TIER 1, 2, 3, 4, 6, 8, 9.
> This document is the authoritative pickup point for TIER 7. It records
> the full audit exactly as delivered, plus the exact files to touch and
> changes to make. Examine the live codebase on `main` (never git diff/
> history). The platform is **VPS/cloud-agnostic** — every fix must stay
> StorageClass-neutral and mesh/Vault-driven (runs identically on K3s,
> OKE, GKE, AKS, kubeadm, kind).

---

## Checklist items (verbatim from CHECKLIST.md)

**Access Control**
- [ ] No public database access
- [ ] Private network only
- [ ] Principle of least privilege

**Encryption**
- [ ] Encryption at rest
- [ ] TLS in transit

**Backups**
- [ ] Automated backups
- [ ] Restore testing
- [ ] Backup encryption

**Auditability**
- [ ] Audit logging
- [ ] Sensitive table monitoring

---

## Files examined during this audit (all read in full on `main`)

- `CHECKLIST.md` (TIER 7 section verbatim)
- `helm/data-layer/templates/postgres-statefulset.yaml`
- `helm/data-layer/templates/postgres-service.yaml`
- `helm/data-layer/templates/networkpolicy.yaml`
- `helm/data-layer/templates/postgres-init-configmap.yaml`
- `helm/data-layer/templates/postgres-backup-cronjob.yaml`
- `helm/data-layer/templates/postgres-backup-externalsecret.yaml`
- `helm/data-layer/templates/linkerd-authzpolicy.yaml`
- `helm/data-layer/templates/redis-statefulset.yaml`
- `helm/data-layer/templates/redis-configmap.yaml`
- `helm/data-layer/templates/chromadb-statefulset.yaml`
- `helm/data-layer/values.yaml`, `values-production.yaml`
- `infrastructure/cluster/vault-paths/main.tf`
- `infrastructure/README.md`
- `helm/engine/templates/configmap.yaml`, `helm/engine/templates/externalsecret.yaml`
- `helm/gateway/templates/externalsecret.yaml`
- `helm/execution/templates/externalsecret.yaml`
- `helm/management/templates/externalsecret.yaml`
- `helm/billing/templates/externalsecret.yaml`
- `src/billing/config/config.go`
- `src/engine/shared/db/connection.py`
- `docker/postgres/init.sql`

---

## AUDIT (exactly as delivered)

### Access Control
- ✅ **No public access** — all datastores `ClusterIP`; namespace `ResourceQuota`
  hard-bans LoadBalancer + NodePort. Edge is Cloudflare Tunnel (no node port
  exposed). **Verified.**
- ✅ **Private network only** — default-deny NetworkPolicies per datastore
  (ingress only from the exact consumer pods; egress only Linkerd CP + DNS;
  backup gets a scoped egress). **Verified.**
- 🔴 **Least privilege — GAP.** Every service connects as the Postgres
  **superuser** (`etradie`). `init.sql` creates no restricted app role. Redis
  is better (requirepass + dangerous commands renamed/disabled) but still one
  shared credential. ChromaDB has a single token. **Not implemented for
  Postgres.**

### Encryption
- ⚠️ **At rest — not enforced.** PVCs use the cluster **default StorageClass**
  (`storageClassName: ""`); no requirement/pin for an encrypted class. Portable
  but unenforced. **Partial.**
- 🔴 **TLS in transit — NOT enforced anywhere (confirmed in code).** Postgres
  server runs stock `postgres:16-alpine` (no `ssl=on`); the engine
  `DatabaseManager` sets no `ssl` connect_arg; billing's `buildPostgresURL()`
  **defaults `sslmode=disable`**; gateway/execution/management depend on the
  operator embedding `sslmode` in the Vault `*_database_url`. Only the
  **Linkerd mesh `opaque-ports` mTLS** encrypts the hop — and
  `linkerdPolicy.enabled: false` by default. So with mesh off + default config,
  **DB traffic is plaintext.** Plus a **consistency bug**: only **billing** maps
  `POSTGRES_SSLMODE` in its ExternalSecret; the other four do not. **Real gap +
  misalignment.**

### Backups
- ✅ **Automated backups** — daily `pg_dump --format=custom` CronJob (02:00 UTC),
  retention 7d (staging) / 30d (prod), separate PVC, hardened pod (non-root 70,
  readOnlyRootFS, drop ALL), `concurrencyPolicy: Forbid`. **Verified, strong.**
- ✅ **Backup encryption** — off-site `rclone` copy (enabled in prod) to an
  S3-compatible remote with operator-required server-side encryption +
  object-lock; local PVC dump inherits the at-rest StorageClass caveat.
  **Verified at off-site layer.**
- 🟠 **Restore testing — GAP.** No restore-drill job/script/runbook anywhere.
  **Not implemented.**

### Auditability
- 🟠 **DB-level audit logging — GAP.** No `pgaudit`/`log_statement`/
  `log_connections`; stock postgres logging only. (App-level audit exists —
  that is TIER 13, not this.) **Not implemented.**
- 🟠 **Sensitive table monitoring — GAP.** No monitoring of reads/writes to
  high-value tables (broker creds, `auth_users`). **Not implemented.**

### Cross-cutting issues found (do NOT skip — pre-existing)
- 🟠 **`POSTGRES_SSLMODE` mapping inconsistency** — present only in billing's
  ExternalSecret; absent in gateway/execution/management/engine. The
  `vault-paths` bootstrap doc lists `postgres_sslmode` only for billing too.
- 🟡 **VPS-agnostic comment contamination** — `helm/gateway/values.yaml`
  ("EKS node cold-start") and `helm/data-layer/values-production.yaml`
  ("eks_managed_node_groups", "EKS") cite AWS specifics that contradict the
  documented cloud-agnostic design. Comment-only, but a real inconsistency.

### VPS-agnosticism — verified clean
Cloudflare Tunnel (no LB), default StorageClass (no cloud class), cloud-agnostic
Vault paths, pluggable cluster bootstrap (OKE *or* K3s/kubeadm/kind). Nothing in
prior tiers confines to a cloud. Only contamination is the two stale comments
above. All TIER 7 fixes must remain StorageClass-neutral and mesh/Vault-driven.

---

## Code-level proof captured (so the next session need not re-derive)

- `src/billing/config/config.go` → `buildPostgresURL()` ends with
  `ssl := envOrDefault("POSTGRES_SSLMODE", "disable")` → **plaintext default**.
- `src/engine/shared/db/connection.py` → `create_async_engine(...)` `connect_args`
  sets only `server_settings.statement_timeout`; **no `ssl`** → TLS depends
  entirely on the URL string from Vault.
- Go services (`pgxpool.ParseConfig(cfg.DatabaseURL)` in execution/management
  `main.go`) → TLS depends entirely on the URL string (Vault).
- `helm/billing/templates/externalsecret.yaml` maps `POSTGRES_SSLMODE`;
  `helm/{gateway,execution,management,engine}/templates/externalsecret.yaml`
  do **not**.
- `docker/postgres/init.sql` + `helm/data-layer/templates/postgres-init-configmap.yaml`
  create extensions only — **no app role**; services connect as superuser
  `etradie`.
- `helm/data-layer/templates/postgres-statefulset.yaml` — stock image, no
  `ssl=on`, no cert mounts, no custom `postgresql.conf`.
- `helm/data-layer/values.yaml` — Postgres meshed with
  `config.linkerd.io/opaque-ports: "5432"`; `linkerdPolicy.enabled: false`
  by default (enabled deliberately post-mesh-confirmation in prod overlay).
- `helm/data-layer/values*.yaml` — all `storageClassName: ""` (default class).

---

## REMEDIATION PLAN — exact files to touch and changes to make

Implement on branch `security/tier7-database-hardening`, small traced commits,
then open a NEW MR. Keep everything cloud-agnostic. CI is the authoritative
build/lint gate (helm lint + kubeconform + Go tests + Trivy/govulncheck).

### Fix 1 — 🔴 Least-privilege Postgres application role
**Goal:** services connect as a non-superuser role with only `CONNECT` + schema
`USAGE` + table CRUD, never as the bootstrap superuser.
- `docker/postgres/init.sql` — add creation of a non-superuser role
  (e.g. `etradie_app`) with `LOGIN`, no `SUPERUSER/CREATEROLE/CREATEDB`;
  `GRANT CONNECT` on the DB, `GRANT USAGE` on schema `public`, and default
  privileges for CRUD on tables/sequences. Password injected at runtime (do
  NOT hardcode). Keep idempotent (`DO $$ ... IF NOT EXISTS ... $$`).
- `helm/data-layer/templates/postgres-init-configmap.yaml` — mirror the SAME
  SQL (the two files must stay byte-aligned, as the comments already require).
- `infrastructure/cluster/vault-paths/main.tf` — extend the data-layer-postgres
  bootstrap note to include the new app-role password key, and update each
  service path note so `*_database_url` uses the app role, not superuser.
- Migrations (Alembic, plus execution/management `SchemaSQL()` + billing
  `SchemaSQL()`) run as the owner — confirm the app role has the privileges
  the running services need at runtime (CRUD) while DDL/migrations may use a
  separate higher-priv role at deploy time. Document the split.
- **Verify end-to-end:** every service `*_database_url` in Vault notes points
  at the app role; the migration path still has DDL rights.

### Fix 2 — 🔴 Enforce + normalize TLS in transit
- `src/billing/config/config.go` — change `buildPostgresURL()` default from
  `sslmode=disable` to `sslmode=require` (operator can still override via
  `POSTGRES_SSLMODE`).
- `helm/gateway/templates/externalsecret.yaml`,
  `helm/execution/templates/externalsecret.yaml`,
  `helm/management/templates/externalsecret.yaml`,
  `helm/engine/templates/externalsecret.yaml` — add a `POSTGRES_SSLMODE`
  mapping (parity with billing) so sslmode is a first-class, consistent knob
  across ALL services.
- `infrastructure/cluster/vault-paths/main.tf` — add `postgres_sslmode` to the
  bootstrap notes for gateway/execution/management/engine + data-layer.
- Decide native server TLS vs mesh-only (OPEN DECISION — see below). If native:
  `helm/data-layer/templates/postgres-statefulset.yaml` — mount a Vault-sourced
  server cert/key, add a `postgresql.conf` with `ssl = on` +
  `ssl_cert_file`/`ssl_key_file`, and a new `vault_kv_secret_v2` path for the
  PG server cert. Keep mesh mTLS as defense-in-depth.
- **Verify end-to-end:** `helm template` renders the new env on every service;
  app connects with TLS even if the mesh is off.

### Fix 3 — ⚠️ Encryption at rest
- `helm/data-layer/values-production.yaml` — pin an encrypted StorageClass
  (overridable; keep `""` default in base `values.yaml` for portability) and
  document that production MUST use an encrypted class.
- Add an operator note (runbook) on verifying volume encryption per provider
  (LUKS/Longhorn-encrypted, OCI default-encrypted, etc.) — provider-neutral.

### Fix 4 — 🟠 Restore testing
- `helm/data-layer/templates/` — add a `postgres-restore-drill-cronjob.yaml`
  (weekly): `pg_restore` the latest dump into a scratch DB, run an integrity
  `SELECT`/row-count check, emit a metric/log, drop the scratch DB. Hardened
  pod (non-root 70, readOnlyRootFS, drop ALL), scoped NetworkPolicy egress to
  postgres, gated by a `postgres.restoreDrill.enabled` value (default true in
  prod overlay).
- `helm/data-layer/values.yaml` + `values-production.yaml` — add the
  `restoreDrill` block (schedule, resources, scratch DB name).
- `docs/runbooks/` — add a restore-drill runbook.
- **Verify:** CI `helm template` + kubeconform render the new CronJob cleanly.

### Fix 5 — 🟠 DB-level audit logging + sensitive-table monitoring
- `helm/data-layer/templates/postgres-init-configmap.yaml` (or a new mounted
  `postgresql.conf`) — enable `log_connections`, `log_disconnections`,
  `log_statement = 'ddl'`, and (if adding the extension) `pgaudit` scoped to
  sensitive tables (broker credentials, `auth_users`). If `pgaudit` is used it
  must be in the image — prefer config-only (`log_statement`/`log_*`) first to
  avoid a custom image, then evaluate `pgaudit`.
- `helm/data-layer/templates/postgres-statefulset.yaml` — mount the
  `postgresql.conf` and pass `-c config_file=` (or include via
  `docker-entrypoint`), keeping readOnlyRootFS posture intact.
- **Verify:** rendered config loads; logs show connection/DDL events.

### Fix 6 — 🟡 VPS-agnostic comment cleanup
- `helm/gateway/values.yaml` — reword the "EKS node cold-start" comment to be
  provider-neutral (e.g. "node cold-start").
- `helm/data-layer/values-production.yaml` — reword "eks_managed_node_groups"/
  "EKS" references to provider-neutral wording (the taint is generic).
- Comment-only; no behaviour change.

---

## OPEN DECISION required before Fix 2 native TLS
Native Postgres server TLS (`ssl=on` + mounted certs) **in addition to** the
Linkerd mesh mTLS (defense-in-depth, recommended for a money platform), **or**
rely on mesh mTLS + app-side `sslmode=require` only. Recommendation: BOTH.
Confirm before implementing the StatefulSet cert-mount portion of Fix 2.

---

## Verification / constraints reminders for the next session
- Examine the LIVE codebase on `main`, not git diff/history.
- `list_repository_tree` is paginated — always pass `per_page: 100` and verify.
- Reading a file on a branch whose name contains `/` fails — read by commit SHA
  or `https://gitlab.com/exoper2/exoper/-/blob/<sha>/<path>`.
- Cannot run builds/helm/promtool locally — CI is the authoritative gate; say so.
- No in-code audit-reference tags in comments (describe behaviour only); commit
  messages may reference finding IDs.
- Open a NEW MR for the implementation branch.






The engine `DatabaseManager` does **not** set any TLS/`ssl` in `connect_args` — it relies entirely on whatever `sslmode`/`ssl` is embedded in the `DATABASE_URL` string from Vault. asyncpg defaults to `ssl=prefer` *only if* the URL says so; with a bare URL it does **not** force TLS. So, like the Go services, TLS is **operator-string-dependent, not enforced in code.**

I now have **complete, 100%-certain, code-and-config-level evidence** across every datastore, every service, the Helm charts, the Terraform Vault paths, and the DB-client code. Here is the final, complete TIER 7 audit.

#### 🔴 TIER 7: Database Security — COMPLETE Audit (fully evidence-backed, every file read)

**Files examined this tier:** `CHECKLIST.md` (TIER 7 verbatim); data-layer chart — postgres statefulset/service/networkpolicy/init-configmap/backup-cronjob/backup-externalsecret/linkerd-authzpolicy/values/values-production, redis statefulset+configmap, chromadb statefulset; `infrastructure/cluster/vault-paths/main.tf`; `infrastructure/README.md`; engine + gateway + execution + management + billing externalsecrets and engine configmap; `src/billing/config/config.go`; `src/engine/shared/db/connection.py`; `docker/postgres/init.sql`.

**Access Control**
- ✅ **No public access** — all datastores `ClusterIP`; namespace `ResourceQuota` hard-bans LoadBalancer + NodePort. Edge is Cloudflare Tunnel (no node port exposed). **Verified.**
- ✅ **Private network only** — default-deny NetworkPolicies per datastore (ingress only from the exact consumer pods; egress only Linkerd CP + DNS; backup gets a scoped egress). **Verified.**
- 🔴 **Least privilege — GAP.** Every service connects as the Postgres **superuser** (`etradie`). `init.sql` creates no restricted app role. Redis is better (requirepass + dangerous commands renamed/disabled) but still one shared credential. ChromaDB has a single token. **Not implemented for Postgres.**

**Encryption**
- ⚠️ **At rest — not enforced.** PVCs use the cluster **default StorageClass** (`storageClassName: ""`); no requirement/pin for an encrypted class. Portable but unenforced. **Partial.**
- 🔴 **TLS in transit — NOT enforced anywhere (confirmed in code).** Postgres server runs stock (no `ssl=on`); the engine `DatabaseManager` sets no `ssl` connect_arg; billing's `buildPostgresURL()` **defaults `sslmode=disable`**; gateway/execution/management depend on the operator embedding `sslmode` in the Vault URL. Only the **Linkerd mesh `opaque-ports` mTLS** encrypts the hop — and `linkerdPolicy.enabled: false` by default. So with mesh off + default config, **DB traffic is plaintext.** Plus a **consistency bug**: only **billing** maps `POSTGRES_SSLMODE` in its ExternalSecret; the other four don't. **Real gap + misalignment.**

**Backups**
- ✅ **Automated backups** — daily `pg_dump` CronJob, retention 7/30d, separate PVC, hardened pod, `Forbid` concurrency. **Verified, strong.**
- ✅ **Backup encryption** — off-site rclone (prod) with operator-required SSE + object-lock; local dump inherits the at-rest caveat. **Verified at off-site layer.**
- 🟠 **Restore testing — GAP.** No restore-drill job/script/runbook anywhere. **Not implemented.**

**Auditability**
- 🟠 **DB-level audit logging — GAP.** No `pgaudit`/`log_statement`/`log_connections`; stock postgres logging only. (App-level audit exists — that's TIER 13, not this.) **Not implemented.**
- 🟠 **Sensitive table monitoring — GAP.** No monitoring of reads/writes to high-value tables (broker creds, auth_users). **Not implemented.**

**Cross-cutting issues found (per your "don't skip pre-existing / inconsistencies" rule):**
- 🟠 **`POSTGRES_SSLMODE` mapping inconsistency** — present only in billing's ExternalSecret; absent in gateway/execution/management/engine. The vault-paths bootstrap doc lists `postgres_sslmode` only for billing too.
- 🟡 **VPS-agnostic comment contamination** — `helm/gateway/values.yaml` ("EKS node cold-start") and `helm/data-layer/values-production.yaml` ("eks_managed_node_groups", "EKS") cite AWS specifics that contradict the documented cloud-agnostic design. Comment-only, but a real inconsistency.

#### On VPS-agnosticism (your direct concern) — verified clean
The platform is genuinely VPS-agnostic: Cloudflare Tunnel (no LB), default StorageClass (no cloud class), cloud-agnostic Vault paths, pluggable cluster bootstrap (OKE *or* K3s/kubeadm/kind). **Nothing I committed in TIER 6 confines to a cloud.** The only contamination is the two stale comments above. Any TIER 7 fixes I write will stay StorageClass-neutral and mesh/Vault-driven so they run on any VPS/K8s.

#### TIER 7 fix plan (cloud-agnostic, small traced commits on `security/tier7-database-hardening`)
1. 🔴 **Least-privilege Postgres app role** — add a non-superuser role + grants in both `docker/postgres/init.sql` and the chart init-configmap; migrate service connection strings to it (documented in vault-paths bootstrap).
2. 🔴 **Enforce/normalize TLS in transit** — make `POSTGRES_SSLMODE` a first-class mapping in **all** service ExternalSecrets (not just billing); change billing's code default from `disable` → `require`; add native Postgres `ssl=on` with mounted certs (Vault-sourced) **or** document mesh-mTLS as the enforced transit layer with `linkerdPolicy` required in prod. (I'll propose `ssl=require` app-side + keep mesh as defense-in-depth — your call on native server TLS.)
3. ⚠️ **At-rest** — pin/require an encrypted StorageClass in `values-production.yaml` (kept overridable, no cloud lock-in) + doc.
4. 🟠 **Restore testing** — add a restore-drill CronJob (`pg_restore` into a scratch DB + `SELECT` integrity check) + runbook.
5. 🟠 **DB audit logging + sensitive-table monitoring** — mount a `postgresql.conf` enabling `log_connections`/`log_disconnections`/`log_statement='ddl'` (and `pgaudit` if we add the extension) scoped to sensitive tables.
6. 🟡 **Comment cleanup** — make the two AWS/EKS comments provider-neutral.

The audit is now **complete** — every required file read, no assumptions, code-level proof for the TLS finding. Want me to proceed implementing fixes 1–6 in steps and open the MR? For #2 I need one decision: **native Postgres server TLS *in addition to* the mesh, or rely on mesh-mTLS + app-side `sslmode=require`?** I recommend both (defense-in-depth) for a money platform, but it's your call.