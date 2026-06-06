# Tier 9 (Microservice Security / Linkerd mTLS) — Operator Rollout Runbook

> Companion to `docs/security/TIER9_MICROSERVICE_SECURITY.md` (design
> history) and `ISSUES.md` (current status). Step-by-step operator
> procedure to bring the mesh up SAFELY. Follow it in order; do NOT
> skip the staging verification before enabling per-service
> authorization in production. Validate chart renders first with
> `make mesh-verify`.

---

## 0. One-time: generate the mesh CA and populate Vault

The platform runs NO cert-manager; the Linkerd identity material lives
in Vault at `etradie/platform/linkerd/<env>` (created by
`infrastructure/cluster/vault-paths`). Generate with smallstep `step`:

```bash
# Root CA (trust anchor) — PUBLIC cert, long-lived.
step certificate create root.linkerd.cluster.local ca.crt ca.key \
  --profile root-ca --no-password --insecure

# Intermediate issuer — signed by the root, 1-year validity.
step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
  --profile intermediate-ca --not-after 8760h --no-password --insecure \
  --ca ca.crt --ca-key ca.key
```

Populate Vault (the linkerd-identity ExternalSecret reads these keys):

```bash
vault kv put etradie/platform/linkerd/production \
  trust_anchor_pem=@ca.crt \
  issuer_tls_crt=@issuer.crt \
  issuer_tls_key=@issuer.key
```

The control-plane Application carries an `identityTrustAnchorsPEM`
helm parameter set to a non-PEM sentinel
(`REPLACE_AT_PROMOTE_WITH_VAULT_TRUST_ANCHOR_PEM`) so a forgotten
override fails loud at sync instead of silently starting identity with
no anchor. Override it at promote with the PUBLIC anchor from Vault:

```bash
vault kv get -field=trust_anchor_pem \
  etradie/platform/linkerd/production > ca.crt
argocd app set linkerd-control-plane-production \
  --helm-set-file identityTrustAnchorsPEM=ca.crt
```

The issuer cert/key are delivered separately as the
`linkerd-identity-issuer` kubernetes.io/tls Secret by ESO; no cert
bytes live in git.

> Cluster requirement: the mesh enables Linkerd native sidecar
> (`config.linkerd.io/proxy-enable-native-sidecar`), which needs K8s
> >= 1.29 (SidecarContainers GA). The provisioned OKE cluster is v1.32.
> On an older cluster the proxy would start after init containers and
> meshed init hops (engine migrate, wait-for-deps, the mt-node Vault
> Agent) would be refused.

> Rotation: re-issue the intermediate from the same root and update
> `issuer_tls_crt`/`issuer_tls_key`; ESO refreshes within
> refreshInterval. The trust anchor only changes on a full CA rotation
> (rare; requires a coordinated cluster-wide proxy restart).

---

## 1. Install the control plane (waves -6 -> -4, before workloads)

ArgoCD reconciles, in order: `linkerd-identity-production` (-6, ESO
materialises the issuer Secret), `linkerd-crds-production` (-5),
`linkerd-control-plane-production` (-4). Verify:

```bash
linkerd check            # all checks green BEFORE injecting workloads
kubectl -n linkerd get pods   # identity, destination, proxy-injector Ready
```

---

## 2. Roll the workloads into the mesh

The production overlays already carry `linkerd.io/inject: enabled`. A
normal ArgoCD sync of each service rolls its pods with the proxy. Roll
ONE service at a time (data-layer first, then engine, then gateway/
execution/management, then envoy/edge-ingress) and confirm each is
meshed before the next:

```bash
linkerd viz stat deploy -n etradie-system
linkerd viz stat statefulset -n etradie-system
```

---

## 3. VERIFY 100% mTLS on every edge (GATE before step 4)

```bash
linkerd viz edges deployment -n etradie-system
linkerd viz edges statefulset -n etradie-system
linkerd viz edges -n envoy-system
linkerd viz edges -n edge-ingress-system
```

Every internal edge MUST show `SECURED` (√). Expected edges:
- gateway <-> execution, gateway <-> management (gRPC)
- gateway/execution/management -> engine (HTTP)
- engine -> postgres / redis / chromadb / mt-node
- edge-ingress -> envoy -> gateway

If ANY edge is not secured, STOP and fix it before step 4. Do NOT
enable per-service authorization while an edge is plaintext.

---

## 4. Enable per-service authorization (G9-2)

`linkerdPolicy.enabled` is `false` in every production overlay so the
mesh rolls (and is verified, steps 2-3) WITHOUT per-service
deny-by-default. Enabling authz is a deliberate step: set
`linkerdPolicy.enabled: true` in the affected service's
`values-production.yaml` and re-sync that one Application. Do this one
service at a time, only after step 3 shows SECURED on that service's
edges. Until enabled, the control-plane `defaultAllowPolicy:
all-unauthenticated` still encrypts every meshed<->meshed hop.

After enabling, verify the authz did not deny legitimate traffic:

```bash
# No authz denials on the money path:
linkerd viz stat deploy/etradie-execution -n etradie-system -o wide
# Backups still run (un-meshed pod admitted via NetworkAuthentication):
kubectl -n etradie-system get cronjob postgres-backup
kubectl -n etradie-system get jobs -l app.kubernetes.io/name=postgres-backup
# Prometheus still scraping (NetworkAuthentication on metrics ports):
# check the targets page / `up` metric for every etradie-system pod.
```

## Per-service authorization matrix (as-built)

| Server (port)            | Allowed callers (mTLS identity)                          | Un-meshed allowance |
|--------------------------|----------------------------------------------------------|---------------------|
| execution gRPC :50053    | etradie-gateway                                          | — |
| execution HTTP :8080      | etradie-gateway                                          | Prometheus (/metrics) |
| management gRPC :50054    | etradie-gateway                                          | — |
| management HTTP :8083     | etradie-gateway                                          | Prometheus (/metrics) |
| gateway gRPC :50052       | etradie-execution, etradie-management                    | — |
| gateway HTTP :8080        | etradie-envoy (envoy-system)                             | Prometheus (/metrics) |
| engine HTTP :8000         | etradie-gateway, etradie-execution, etradie-management   | Prometheus (/metrics) |
| postgres :5432            | gateway, execution, management, engine                   | postgres-backup pod |
| redis :6379               | gateway, execution, management, engine                   | — |
| chromadb :8000            | engine                                                   | — |

## 5. Rollback

- Authz too tight (legitimate traffic denied): set
  `linkerdPolicy.enabled: false` in the affected service overlay and
  re-sync. The control-plane `defaultAllowPolicy: all-unauthenticated`
  still encrypts every meshed<->meshed hop — you lose per-service
  scoping but NOT encryption.
- Mesh itself problematic: remove `linkerd.io/inject` from the
  service's podAnnotations and re-sync to roll un-meshed pods. The
  NetworkPolicies (unchanged) still enforce L3/L4 segmentation.
- Full backout: prune the three linkerd-* Applications (manual, in
  order control-plane -> crds -> identity) after all workloads are
  un-injected.
