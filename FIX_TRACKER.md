# Audit Fix Tracker

Live progress of fixes against the 6 audit files. Updated on every commit.

## Decisions (locked)

- **Service naming:** rename gateway Service from `gateway-service` to `gateway`. Every other chart uses bare names (engine, postgres, redis, chromadb, execution, management). Envoy upstream already uses `gateway-headless` which keeps its name.
- **Namespace ownership:** data-layer chart owns `etradie-system` namespace + ResourceQuota + LimitRange (sync wave -2 = created first). All other charts (engine, gateway, billing, execution, management) default `namespace.create: false`. Edge-ingress and envoy own their own namespaces (`edge-ingress-system`, `envoy-system`) because they live in separate namespaces.
- **Vault path consolidation (chroma):** single canonical path `etradie/data-layer/chromadb/<env>` with key `auth_token`. Engine ExternalSecret reads from this path. Removes the duplicate `etradie/services/engine/<env>:rag_chroma_auth_token`.
- **Service-agnostic posture:** ALL fixes must work on Contabo K3s, OCI OKE, GKE, kubeadm, bare-metal K8s. No AWS/GCP/OCI hardcodes.

## Wave plan

| Wave | Status | Scope |
|------|--------|-------|
| 0 | DONE | This tracker |
| 1 | DONE | CI image tag/build matrix (CI-H1, CI-C1, CI-C2) |
| 2 | DONE | Service-name + DNS wiring (EX-C1, X-7, G-H4) |
| 3 | DONE | Namespace ownership consolidation (G-C1, X-2, B-M4) |
| 4 | DONE | Auth production safety (FV-H1, FV-H2, FV-H3). FV-H4 is documented behavior, no fix. |
| 5 | DONE | Engine production safety (SC-C2, SC-C4, XS-1, SC-H7, E-H5) |
| 6 | DONE | Vault path coherence (IV-C1, IV-C2, X-6, D-C3, IV-H4, IV-M2, IV-M3, IV-M4) |
| 7 | DONE | NetworkPolicy gaps (D-C2, EI-C3, EI-H1) |
| 8 | PARTIAL | Helm sweep: E-C1, E-C2, E-C3, E-M1, E-M2, E-M3, E-M5, X-3, X-4, X-5, X-10, G-H3, G-M2, EV-H2, EV-M3, EV-M4 done. STILL OPEN: G-C2/C4 (gRPC readiness), G-C3 (automount drive in remaining charts), X-8 (engine readiness endpoint -> Wave 14), MG-C1 (leader election -> Wave 14), MG-H1 (mgmt HTTP url verify) |
| 9 | DONE | Data-layer hardening: D-C4, D-H1, D-H2, D-H5, EI-C2 done. D-H3 (off-cluster backup copy) deferred - operator decision; D-M1/D-M2/D-M5/D-M7 are docs-only and already accurate in existing comments. |
| 10 | DONE | Deployments + infra: DA-C2, DA-C3, DA-H1, DA-H2, DA-H3, DA-H6, DC-H1, IC-C1, IC-H4, IO-H1, IV-H1, IV-H3, IV-H5, IB-C1, IB-H1, IB-H2 done. IO-H2 (k8s version), IC-C2 (zone ssl plan), IC-H2/H3, IV-M1, IB-M1/M2 (docs polish) covered in Wave 15. |
| 11 | DONE | Docker+root+CI: RD-C1, RD-H1, RD-H2, DC-C1, DC-C2, DC-C3, DI-H1, DI-H2, MK-C1, MK-C2, MK-H1, MK-H2, AL-C1, CI-H5 (tf job), CI-M6 (weekly cf workflow), SS-H1 done. Remaining MEDIUM/LOW docs polish in Wave 15. |
| 12 | DONE | TLS key + cert deleted from working tree, gitignored, README updated. OPERATOR ACTION: run `git filter-repo` to purge history (see deployments/edge-ingress/docker/certs/README.md). |
| 13 | DONE | mt-node deployment model documented + SIGTERM trap added. E-H5 closed in Wave 5. DMT-H1/H2 documented as operator decisions. DMT-M1 (image digest pin) in Wave 15 cleanup. |
| 14 | PENDING | Engine code fixes (V-14 readiness endpoint, SC-H11 deferred import, SC-H12 metering middleware verify, FV-M1 alembic schema imports) |
| 15 | PENDING | Cleanup pass (all remaining MEDIUM/LOW) |

## Findings closed (no fix needed)

- G-H2 — cookie validation IS in `src/auth/config.go` (V-12). False alarm.
- E-H2 — engine `/health` is non-blocking (V-13). No fix needed.
- B-H1 — billing `_SECONDS` env vars correctly parse as `time.Duration` (V-1). No fix needed.
- EX-H2 — execution `_MS` env vars correctly parse as int (V-2). No fix needed.
- AL-C1 — alembic env.py overrides URL at runtime (V-15). Downgraded to LOW; cleanup in Wave 11.
- DC-C2 — `--bootstrap` flag DOES exist in refresh-cloudflare-ips.sh. No fix needed.
- V-16 — migration chain 0001-0027 has no gaps. No fix needed.
- V-17 — engine internal router IS mounted. No fix needed.

## Operator actions (cannot be done by code)

- **DC-C1 / Wave 13:** run `make cf-bootstrap-aop-ca` to populate `aop-ca.sha256` and `origin-pull-ca.pem` with live Cloudflare AOP CA bytes; commit both. Cannot be automated — requires Cloudflare network access.
- **DA-C1 / Wave 12:** after I delete the leaked TLS key + add gitignore, you must run `git filter-repo --invert-paths --path deployments/edge-ingress/docker/certs/localhost.key` and force-push. The key is also already in git history; my tool cannot rewrite history.
- **Vault populate:** after Wave 6 changes paths, operator must repopulate Vault entries via `vault kv put`. Existing values keep working until repopulated because of `lifecycle.ignore_changes = [data_json]`.

## Branch

All fixes commit to branch `fix/all-audit-findings`. When the wave plan is complete and the user reviews, one MR rolls everything into `main`.
