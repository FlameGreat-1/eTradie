I have a complete picture. Here is my honest, no-guessing audit.

# End-to-end audit findings

#### Critical issues that will break deployment

**1. Edge-ingress Deployment ↔ Cloudflare AOP namespace mismatch**

This is the single worst issue and it makes the entire mTLS chain non-functional in cluster.

- `deployments/edge-ingress/kubernetes/base/deployment.yaml` puts edge-ingress in `etradie-system` (line 4), and mounts a Secret named `cloudflare-aop-ca`.
- `deployments/cloudflare/kubernetes/externalsecret-aop-ca.yaml` materializes that Secret in `edge-ingress-system`.
- A pod in namespace A cannot mount a Secret from namespace B. `kubectl apply` will leave edge-ingress pods in `ContainerCreating` forever with the event `MountVolume.SetUp failed for volume "cloudflare-aop-ca": secret "cloudflare-aop-ca" not found`.
- Same break occurs for `cloudflare-ip-ranges` ConfigMap (the cloudflare kustomize creates it in both `etradie-system` and `edge-ingress-system`, but no consumer of `edge-ingress-system` exists today).

**2. Edge-ingress NetworkPolicy egress will silently drop all upstream traffic**

`deployments/edge-ingress/kubernetes/base/networkpolicy.yaml` egress rule targets `app.kubernetes.io/name: envoy` in namespace `name: etradie-system`. But:
- The envoy kustomize tree puts envoy in `envoy-system`, not `etradie-system`.
- The envoy pods carry label `app.kubernetes.io/name: etradie-envoy` (per `commonLabels` in `deployments/envoy/kubernetes/base/kustomization.yaml`), not `envoy`.

Both selectors miss. CNI silently drops every edge-ingress → envoy connection at the network layer. The same bug exists in `helm/edge-ingress/values.yaml`.

**3. Envoy NetworkPolicy ingress will silently drop all downstream traffic**

`deployments/envoy/kubernetes/base/networkpolicy.yaml` ingress rule expects edge-ingress pods in namespace labeled `name: etradie-system`, with pod label `app.kubernetes.io/name: edge-ingress`.

- Edge-ingress IS in `etradie-system` — that part lines up.
- BUT the namespace `etradie-system` is created by `deployments/edge-ingress/kubernetes/base/namespace.yaml` with label `name: etradie-system`, while the gateway-owned namespace.yaml at `deployments/gateway/kubernetes/base/namespace.yaml` creates it with `name: etradie-system` too — so two manifests claim ownership of the same namespace.
- More importantly, the envoy NetworkPolicy egress targets `app.kubernetes.io/name: etradie-gateway` in a namespace selected by `app.kubernetes.io/part-of: etradie`. The gateway namespace (`etradie-system`) has label `app.kubernetes.io/part-of: etradie` only when the gateway base owns it; if the edge-ingress base creates it first, that label is missing. Apply order determines whether traffic flows.

**4. Two namespaces create the same `etradie-system`**

- `deployments/gateway/kubernetes/base/namespace.yaml` → creates `etradie-system` with PSS=restricted, ResourceQuota=4 cpu, label `app.kubernetes.io/part-of: etradie`.
- `deployments/edge-ingress/kubernetes/base/namespace.yaml` → creates `etradie-system` with PSS=restricted, **ResourceQuota=50 cpu**, no `app.kubernetes.io/part-of` label.

Whichever applies last wins. ArgoCD will report drift forever because the two `kustomize build` outputs disagree on what the namespace looks like. This is a classic split-brain.

**5. Edge-ingress lives in the WRONG namespace**

The original design intent (visible in `helm/edge-ingress/values.yaml` and `deployments/cloudflare/kubernetes/externalsecret-aop-ca.yaml`) is that edge-ingress runs in `edge-ingress-system`. The kustomize base puts it in `etradie-system`. The chain has three different opinions:

| Source | edge-ingress namespace |
|---|---|
| `deployments/edge-ingress/kubernetes/base/` | `etradie-system` |
| `helm/edge-ingress/values.yaml` (`namespace.name`) | `edge-ingress-system` |
| `deployments/cloudflare/kubernetes/externalsecret-aop-ca.yaml` | `edge-ingress-system` |
| `deployments/envoy/kubernetes/base/networkpolicy.yaml` ingress rule | expects `edge-ingress-system` (it uses label-matching, not name, but the comment in the file says edge-ingress is elsewhere) |

This isn't end-to-end wired. It's three half-wirings.

**6. Helm edge-ingress chart is internally inconsistent**

In the helm/edge-ingress `values.yaml` I just wrote:
- `serviceAccount.name: ""` (empty)
- The `_helpers.tpl` defaults to `include "edge-ingress.fullname" .` when `name` is empty
- But the Deployment template says `serviceAccountName: {{ include "edge-ingress.serviceAccountName" . }}`, which (if Release name is `edge-ingress`) renders as `edge-ingress`, but if the release name is `my-release`, renders as `my-release-edge-ingress`.

The `automountServiceAccountToken` field was set on both the SA and the pod spec. But the `serviceAccount` block in `values.yaml` mixes `automountServiceAccountToken: false` with the (intended) production SA name being `"edge-ingress"`. If a release is named anything other than `edge-ingress`, the SA created and the SA referenced disagree.

**7. WASM filter delivery is broken in cluster**

- `deployments/envoy/kubernetes/base/configmap-wasm.yaml` ships placeholder text in `data: integration-filter.wasm: |` — that's text, not binary. Envoy will try to load a "WASM" file containing the comment "PLACEHOLDER - This file is generated by..." and crash on startup.
- The kustomize tree references this placeholder directly. There is no CI hook that actually base64-encodes the WASM and substitutes it.
- The helm/envoy chart fixed this with `binaryData` + a `fail` template — but the kustomize tree still ships the broken stub.

**8. Helm `helm/values.yaml`, `helm/Chart.yaml`, `helm/values-staging.yaml`, `helm/values-production.yaml` at the repo root**

The repo has a top-level `helm/Chart.yaml` (named `edge-ingress`!) and three values files at `helm/` root. Listing shows:
```
helm/Chart.yaml          <- duplicate of helm/edge-ingress/Chart.yaml
helm/values.yaml         <- duplicate of helm/edge-ingress/values.yaml
helm/values-staging.yaml
helm/values-production.yaml
```
These are leftover orphans from the original "values-only" pattern. They aren't referenced by anything but they'll confuse anyone who finds them.

**9. Local docker-compose `edge` profile mTLS path is broken**

- `docker-compose.yml` mounts `./deployments/cloudflare/origin-pull` to `/etc/edge-ingress/cloudflare` in the edge-ingress container.
- The local edge-ingress YAML config (`src/edge-ingress/config/local/edge-ingress-local.yaml`) sets `client_auth.ca_path: /etc/edge-ingress/cloudflare/origin-pull-ca.pem`.
- The compose stack uses `deployments/edge-ingress/docker/config/edge-ingress.yaml` — which I updated to also point at `/etc/edge-ingress/cloudflare/origin-pull-ca.pem`. Good.
- BUT the local edge-ingress `read_only: true` filesystem combined with `tmpfs: /tmp` means the geoip-data path the rust code reads (`/data/geoip/GeoLite2-City.mmdb`) is unwritable AND not mounted from the host. There's no init container in compose. The local container will fail at startup the first time the geo-router tries to open the .mmdb.

**10. `helm/values-staging.yaml` overlay for envoy upstream points at non-existent service**

- `helm/edge-ingress/values.yaml` upstream endpoints: `etradie-envoy.envoy-system.svc.cluster.local:8080` (correct)
- `helm/edge-ingress/values-staging.yaml` upstream endpoints (overrides): `etradie-envoy.envoy-system.svc.cluster.local:8080` (correct)
- `deployments/edge-ingress/kubernetes/base/configmap.yaml` upstream endpoints: `envoy.etradie-system.svc.cluster.local:8080` ← **wrong service, wrong namespace**

The kustomize base config and the helm values disagree. Whichever is applied to a cluster, edge-ingress will not find envoy.

**11. The orphan `deployments/docker/Dockerfile.envoy` + `exoper_envoy_integration_filter.wasm`**

The repo still has `deployments/docker/exoper_envoy_integration_filter.wasm` (note: **exoper**, not etradie — leftover from the EXOPER rebrand) and `deployments/docker/docker-compose.yml`. These were called out as orphans in the AUDIT.md from `!7` and were supposed to be removed. They're still there.

#### Issues with infrastructure/

**12. `infrastructure/gateway/main.tf` calls a binary the runner may not have**

The Terraform module shells out to `kustomize edit set image` and `kustomize build` via `local-exec`. There's no version pin, no preflight check, no fallback. If CI doesn't have kustomize installed, `terraform apply` produces an opaque shell error. A real IaC module would either use the `kubectl` provider's `kustomization` resource (which has built-in kustomize) or use a `null_resource` with a clear precondition.

**13. There is NO `infrastructure/envoy/`, NO `infrastructure/edge-ingress/`, NO `infrastructure/cloudflare/`**

The MR description claims a full IaC tree. There's only `infrastructure/gateway/`. The runbook references "the cloudflare module in infrastructure/cloudflare/" — it doesn't exist.

#### Plumbing inconsistencies

**14. Edge-ingress production overlay HARDCODES `arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/PRODUCTION_CERT_ID`**

This is committed in `deployments/edge-ingress/kubernetes/overlays/production/kustomization.yaml`. It will fail to attach a certificate to the NLB at apply time because `ACCOUNT_ID` and `PRODUCTION_CERT_ID` are not real ARN parts.

**15. Two ServiceMonitor selector strategies conflict**

- The kustomize base for edge-ingress puts edge-ingress in namespace `etradie-system` and the ServiceMonitor at `deployments/edge-ingress/kubernetes/base/servicemonitor.yaml` selects `namespaceSelector: matchNames: [etradie-system]`.
- The helm chart puts edge-ingress in `edge-ingress-system` and the ServiceMonitor template selects on `app.kubernetes.io/component: metrics`.
- Prometheus operator can't reconcile both.

**16. `make edge-test` won't actually validate AOP**

I wrote `make edge-test` to assert that an unauthenticated curl FAILS at TLS. But the local edge-ingress config uses a self-signed dev CA that mTLS-validates a dev client. If geoip init fails (per #9), edge-ingress doesn't start, both curls fail, and `make edge-test` reports "ok" because the unauthenticated one was supposed to fail. False green.

**17. Cloudflare AOP CA is mounted but the `--read-only` filesystem is wrong for write-back tests**

Edge-ingress production deployment has `readOnlyRootFilesystem: true`. The Rust binary embeds a hot-reload that periodically re-reads the CA file. That's fine — it doesn't write. But the `/tmp` mount only has 64Mi. If the process tries to spool a large request body it will OOM-tmpfs silently. Needs to be at least 256Mi for any realistic POST traffic.

#### Summary table

| # | Severity | Where | What |
|---|----------|-------|------|
| 1 | **CRITICAL** | edge-ingress deployment ↔ cloudflare AOP secret | Wrong namespace; pods stuck in ContainerCreating |
| 2 | **CRITICAL** | edge-ingress NetworkPolicy egress | Wrong label + namespace; all traffic to envoy dropped |
| 3 | **HIGH** | envoy NetworkPolicy | Namespace label / app label mismatch potential |
| 4 | **HIGH** | namespace ownership | Two manifests own `etradie-system` |
| 5 | **HIGH** | edge-ingress namespace | Three files disagree on which namespace |
| 6 | **MEDIUM** | helm/edge-ingress | SA name inconsistency for non-default releases |
| 7 | **CRITICAL** | envoy WASM ConfigMap | Ships placeholder text, not WASM bytes |
| 8 | **MEDIUM** | helm/ root files | Orphan duplicates of `helm/edge-ingress/` |
| 9 | **CRITICAL** | docker-compose edge profile | Geoip path missing → edge-ingress crashes |
| 10 | **CRITICAL** | edge-ingress kustomize configmap | Upstream points to non-existent service |
| 11 | **MEDIUM** | deployments/docker/ | EXOPER orphans still committed |
| 12 | **LOW** | infrastructure/gateway/main.tf | Shells out to kustomize without preflight |
| 13 | **HIGH** | infrastructure/ | Only gateway module exists; envoy/edge-ingress/cloudflare missing |
| 14 | **HIGH** | edge-ingress prod overlay | Placeholder ACM ARN baked into kustomize patch |
| 15 | **MEDIUM** | ServiceMonitor selectors | Helm and kustomize disagree |
| 16 | **HIGH** | `make edge-test` | False-green if edge-ingress crashes |
| 17 | **LOW** | edge-ingress /tmp size | 64Mi too small for real POST bodies |

# Direct answer to your second question

#### Did you build technical debt?

**For this MR, in this state: yes, partially.** Not the work itself — the chain of contracts is real and matters — but it isn't ready. As shown above, six of these issues will block any cluster apply (#1, #2, #7, #9, #10, plus the namespace split-brain). It's "right concept, broken plumbing" — which is the worst possible state to deploy money-handling code from.

#### Do `helm/`, `deployments/`, `infrastructure/` actually serve different purposes, or are two of them debt?

For an enterprise-grade financial system, **the three serve genuinely different consumers and you need them — but the way they currently overlap is debt.** Honest breakdown:

**`deployments/<svc>/kubernetes/`** (kustomize) — **necessary**. This is the source of truth that ArgoCD/Flux GitOps points at. Kustomize overlays are the standard way to express per-environment deltas without templating, and any real GitOps workflow consumes raw manifests. Removing this means giving up GitOps.

**`helm/<svc>/`** (Helm chart) — **necessary, but only if it's the *primary* deployment path**. Helm is what platform teams expect for `helm upgrade` rollbacks, what Argo CD sees in `Chart.yaml` releases, what dependency-management trees (sub-charts) require. **Right now both kustomize and helm exist in parallel and they disagree.** That's debt. Pick one as the source of truth and have the other be derived (e.g., `helm template` writes the kustomize base; or kustomize is the source and helm just packages it).

**`infrastructure/<svc>/`** (Terraform) — **necessary for cloud resources, NOT for k8s manifests**. Terraform's job is the AWS account, the EKS cluster, IAM roles, the Cloudflare zone, the Vault paths, the NLB. Using Terraform to apply Kubernetes manifests is an anti-pattern (resource ownership wars with Argo). My current `infrastructure/gateway/main.tf` does exactly that wrong thing. It should be replaced with: `infrastructure/cloudflare/` (the Cloudflare zone + AOP setup + R53 records) and `infrastructure/cluster/` (EKS + node groups + IAM for ESO + the Vault path schema).

**Verdict on tech debt:** as written, **`helm/` AND `deployments/` together = duplication = debt**. You need to decide which is the source of truth and reduce the other. `infrastructure/` is fine in *concept* but the only module shipped is solving the wrong problem.

#### What I recommend (no guessing — this is what production-grade looks like)

1. **Pick kustomize OR helm as the deployment source of truth. Not both.**
   - For a small/mid platform (this is one): **kustomize is simpler and fits ArgoCD natively**. Drop `helm/`. The values-only charts are pure debt.
   - For a multi-team platform with versioned releases: **keep helm**, generate kustomize bases from `helm template` in CI, drop the hand-rolled `deployments/*/kubernetes/base/`.
2. **Remove `infrastructure/gateway/`**. K8s manifests don't belong in Terraform.
3. **Keep `infrastructure/` for what it's actually for:** cloud accounts, EKS, Cloudflare zones, Vault path bootstrap. Build those modules properly.
4. **Fix the 17 issues above**, in order of severity, before any production traffic.

Want me to (a) execute the consolidation (delete `helm/`, fix kustomize as source of truth, fix all 17), (b) execute the inverse (keep helm, derive kustomize, fix all 17), or (c) just fix the 17 critical issues and leave the dual-source for later? My recommendation is **(a)** — kustomize wins, helm goes away, fix everything in one pass. Tell me which and I will execute.