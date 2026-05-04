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









THIS IS EXACTLY WHERE WE STOPPED AND THE SESSION END WITHOUT COMMITING THIS TO THE REPO:


Now I need to verify what makes the local edge profile geoip path work. Looking at `deployments/edge-ingress/docker/config/edge-ingress.yaml` (read earlier), `geoip.database_path: "/data/geoip/GeoLite2-City.mmdb"`. The Dockerfile creates `/data/geoip` owned by user 1000. The top-level `docker-compose.yml` sets `read_only: true` and `tmpfs: /tmp`. The `/data/geoip` directory will be empty (no .mmdb file). The config file has no way to disable geoip.

There are two clean fixes:

1. **Add a geoip-data named volume** in docker-compose with a small init container or sidecar that downloads the .mmdb (mirrors what helm does).
2. **Make geoip optional in the local config** by removing the `geoip:` section — but this requires Rust code support.

Looking at the local config, the cleanest path is to add a geoip-init service to the compose stack (mirroring the helm init container) and a named volume. Let me read the edge-ingress.yaml once more — it's in `deployments/edge-ingress/docker/config/edge-ingress.yaml` and has `geoip.database_path` mandatory. So I will use option 1.

Now executing the final commit:

--- docker-compose.yml
+++ docker-compose.yml
@@ -1,5 +1,33 @@
+  # ─────────────────────────────────────────────────────────────────
+  # GEOIP INIT (opt-in, edge profile only)
+  # Populates the geoip-data named volume with GeoLite2-City.mmdb so the
+  # read-only edge-ingress container can mmap it. Runs once on `up` and
+  # exits 0; subsequent refreshes are handled by the production helm
+  # chart's init-container, not by this local-only service.
+  # ─────────────────────────────────────────────────────────────────
+  edge-geoip-init:
+    profiles: ["edge"]
+    image: maxmindinc/geoipupdate:v6.0
+    container_name: etradie-edge-geoip-init
+    environment:
+      - GEOIPUPDATE_ACCOUNT_ID=${MAXMIND_ACCOUNT_ID:?MAXMIND_ACCOUNT_ID must be set in .env to run the edge profile}
+      - GEOIPUPDATE_LICENSE_KEY=${MAXMIND_LICENSE_KEY:?MAXMIND_LICENSE_KEY must be set in .env to run the edge profile}
+      - GEOIPUPDATE_EDITION_IDS=GeoLite2-City
+      - GEOIPUPDATE_FREQUENCY=0
+    entrypoint: ["/usr/bin/geoipupdate"]
+    command: ["-d", "/data/geoip"]
+    volumes:
+      - geoip-data:/data/geoip
+    networks:
+      - etradie-net
+    deploy:
+      resources:
+        limits:
+          cpus: '0.5'
+          memory: 256M
+
   envoy:
     profiles: ["edge"]
     build:
       context: ./src/envoy
       dockerfile: ../../deployments/envoy/docker/Dockerfile.envoy
--- docker-compose.yml
+++ docker-compose.yml
@@ -1,14 +1,19 @@
     volumes:
       - ./deployments/edge-ingress/docker/config:/etc/edge-ingress/config:ro
       - ./deployments/edge-ingress/docker/certs:/etc/edge-ingress/certs:ro
-      # Local AOP CA placeholder. The committed file is a comment-only
-      # placeholder; populate with `curl -fsSL
-      # https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem`
-      # to exercise mTLS locally. Disabled in the local config by default.
+      # Local AOP CA + dev client cert produced by
+      # `make dev-certs` (deployments/cloudflare/origin-pull/generate-dev-certs.sh).
+      # The script is committed; the generated PEMs are gitignored.
       - ./deployments/cloudflare/origin-pull:/etc/edge-ingress/cloudflare:ro
+      # GeoLite2 mmdb populated by the edge-geoip-init service above.
+      # Mounted read-only because the edge-ingress container runs with
+      # read_only=true and only mmap reads happen here at runtime.
+      - geoip-data:/data/geoip:ro
     ports:
       - "8443:443"   # TLS listener (host-side: https://localhost:8443)
       - "19902:9902" # Metrics / health
     depends_on:
       envoy:
-        condition: service_healthy
+        condition: service_healthy
+      edge-geoip-init:
+        condition: service_completed_successfully
--- docker-compose.yml
+++ docker-compose.yml
@@ -1,9 +1,11 @@
 volumes:
   postgres_data:
     driver: local
   prometheus_data:
     driver: local
   chromadb_data:
     driver: local
   grafana_data:
+    driver: local
+  geoip-data:
     driver: local
--- Makefile
+++ Makefile
@@ -1,14 +1,46 @@
 edge-test: ## Validate the local edge chain enforces mTLS (CI-friendly)
 	echo -e "$(BLUE)Validating local mTLS enforcement...$(NC)"
-	@echo -n "  unauthenticated curl must FAIL: " && \
-		( ! curl -sk --max-time 5 https://localhost:8443/auth/healthz >/dev/null 2>&1 ) \
-		&& echo -e "$(GREEN)ok (handshake rejected)$(NC)" \
-		|| { echo -e "$(RED)FAIL: unauthenticated request succeeded - mTLS broken$(NC)"; exit 1; }
+	@# 1) The edge-ingress process must be alive BEFORE we trust any
+	@#    handshake-rejection result. A crashed process also "rejects"
+	@#    handshakes (Connection refused), so without this check the
+	@#    test would false-green any time edge-ingress fails to boot.
+	@echo -n "  edge-ingress process is alive: " && \
+		curl -sf --max-time 3 http://localhost:19902/healthz >/dev/null \
+		&& echo -e "$(GREEN)ok$(NC)" \
+		|| { echo -e "$(RED)FAIL: edge-ingress not responding on :19902/healthz - process is down$(NC)"; exit 1; }
+	@# 2) The TLS listener must accept at least the TCP handshake. If
+	@#    we cannot connect, anything further is meaningless.
+	@echo -n "  edge-ingress TLS listener is open: " && \
+		timeout 3 bash -c 'cat </dev/tcp/localhost/8443' >/dev/null 2>&1 \
+		&& echo -e "$(GREEN)ok$(NC)" \
+		|| { echo -e "$(RED)FAIL: localhost:8443 is not accepting TCP connections$(NC)"; exit 1; }
+	@# 3) Authenticated curl must SUCCEED. Otherwise a passing #4 below
+	@#    is meaningless because the chain might be rejecting EVERY
+	@#    request, not just unauthenticated ones.
 	@echo -n "  authenticated   curl must SUCCEED: " && \
 		curl -sk --max-time 10 \
 		  --cert deployments/cloudflare/origin-pull/dev-client.crt \
 		  --key  deployments/cloudflare/origin-pull/dev-client.key \
 		  https://localhost:8443/auth/healthz >/dev/null \
 		&& echo -e "$(GREEN)ok$(NC)" \
-		|| { echo -e "$(RED)FAIL: authenticated request rejected$(NC)"; exit 1; }
+		|| { echo -e "$(RED)FAIL: authenticated request rejected (mTLS misconfigured or upstream broken)$(NC)"; exit 1; }
+	@# 4) Unauthenticated curl MUST fail at TLS, specifically. Test for
+	@#    "alert bad_certificate" / "alert handshake_failure" in the
+	@#    output - NOT just non-zero exit (which would also be true if
+	@#    the process crashed between #3 and #4).
+	@echo -n "  unauthenticated curl must FAIL at TLS: " && \
+		unauth_err=$$(curl -sk --max-time 5 https://localhost:8443/auth/healthz 2>&1 1>/dev/null) || true; \
+		if echo "$$unauth_err" | grep -qE 'alert (bad_certificate|handshake_failure|certificate_required)'; then \
+			echo -e "$(GREEN)ok (TLS handshake rejected)$(NC)"; \
+		elif echo "$$unauth_err" | grep -qiE 'connection refused|recv failure'; then \
+			echo -e "$(RED)FAIL: connection refused - edge-ingress crashed mid-test$(NC)"; exit 1; \
+		else \
+			echo -e "$(RED)FAIL: unauthenticated request did not fail at TLS layer (got: $$unauth_err)$(NC)"; exit 1; \
+		fi
+	@# 5) Process must STILL be alive after the test (the unauthenticated
+	@#    request must not have crashed the daemon).
+	@echo -n "  edge-ingress process still alive: " && \
+		curl -sf --max-time 3 http://localhost:19902/healthz >/dev/null \
+		&& echo -e "$(GREEN)ok$(NC)" \
+		|| { echo -e "$(RED)FAIL: edge-ingress crashed during validation$(NC)"; exit 1; }
 	echo -e "$(GREEN)✓ Local edge chain mTLS posture matches production$(NC)"
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: requirements/dev.txt
      - name: Install dependencies
        run: pip install -r requirements/dev.txt
      - name: Ruff lint
        run: ruff check src/ tests/
      - name: Ruff format check
        run: ruff format --check src/ tests/
      - name: Mypy type check
        run: mypy src/
      - name: Contract check (Go/Python ProcessorOutput parity)
        run: python scripts/validate_processor_contract.py

  helm:
    name: Helm chart lint + render + schema validation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install helm
        uses: azure/setup-helm@v4
        with:
          version: v3.14.0
      - name: Install kubeconform
        run: |
          curl -fsSL https://github.com/yannh/kubeconform/releases/download/v0.6.4/kubeconform-linux-amd64.tar.gz \
            | tar -xz -C /usr/local/bin kubeconform
      - name: Drift gate - chart-local cloudflare ranges match canonical files
        run: |
          diff -q deployments/cloudflare/ip-ranges/ipv4.txt helm/gateway/files/cloudflare/ipv4.txt
          diff -q deployments/cloudflare/ip-ranges/ipv6.txt helm/gateway/files/cloudflare/ipv6.txt
      - name: helm lint - edge-ingress
        run: helm lint helm/edge-ingress
      - name: helm lint - envoy
        run: helm lint helm/envoy
      - name: helm lint - gateway
        run: helm lint helm/gateway
      - name: helm template + kubeconform - edge-ingress staging
        run: |
          helm template edge-ingress helm/edge-ingress \
            -f helm/edge-ingress/values.yaml \
            -f helm/edge-ingress/values-staging.yaml \
            --set service.tlsCertificateArn=arn:aws:acm:us-east-1:000000000000:certificate/dummy \
            > /tmp/edge-ingress-staging.yaml
          kubeconform -strict -kubernetes-version 1.30.0 \
            -schema-location default \
            -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
            /tmp/edge-ingress-staging.yaml
      - name: helm template + kubeconform - edge-ingress production
        run: |
          helm template edge-ingress helm/edge-ingress \
            -f helm/edge-ingress/values.yaml \
            -f helm/edge-ingress/values-production.yaml \
            --set service.tlsCertificateArn=arn:aws:acm:us-east-1:000000000000:certificate/dummy \
            > /tmp/edge-ingress-production.yaml
          kubeconform -strict -kubernetes-version 1.30.0 \
            -schema-location default \
            -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
            /tmp/edge-ingress-production.yaml
      - name: helm template + kubeconform - envoy staging
        run: |
          # Inject 1 byte of valid base64 ("AA==" = 0x00) so the chart
          # template renders for CI; production must inject the real
          # WASM via --set-file at promotion time.
          helm template etradie-envoy helm/envoy \
            -f helm/envoy/values.yaml \
            -f helm/envoy/values-staging.yaml \
            --set wasm.base64=AA== \
            --set wasm.sha256=ci-placeholder \
            > /tmp/envoy-staging.yaml
          kubeconform -strict -kubernetes-version 1.30.0 \
            -schema-location default \
            -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
            /tmp/envoy-staging.yaml
      - name: helm template + kubeconform - envoy production
        run: |
          helm template etradie-envoy helm/envoy \
            -f helm/envoy/values.yaml \
            -f helm/envoy/values-production.yaml \
            --set wasm.base64=AA== \
            --set wasm.sha256=ci-placeholder \
            > /tmp/envoy-production.yaml
          kubeconform -strict -kubernetes-version 1.30.0 \
            -schema-location default \
            -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
            /tmp/envoy-production.yaml
      - name: helm template + kubeconform - gateway staging
        run: |
          helm template etradie-gateway helm/gateway \
            -f helm/gateway/values.yaml \
            -f helm/gateway/values-staging.yaml \
            > /tmp/gateway-staging.yaml
          kubeconform -strict -kubernetes-version 1.30.0 \
            -schema-location default \
            -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
            /tmp/gateway-staging.yaml
      - name: helm template + kubeconform - gateway production
        run: |
          helm template etradie-gateway helm/gateway \
            -f helm/gateway/values.yaml \
            -f helm/gateway/values-production.yaml \
            > /tmp/gateway-production.yaml
          kubeconform -strict -kubernetes-version 1.30.0 \
            -schema-location default \
            -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
            /tmp/gateway-production.yaml
      - name: argocd manifests parse
        run: |
          # ArgoCD CRDs are schema-checked separately. We only confirm
          # the YAML parses and the AppProject + Application docs are
          # syntactically valid Kubernetes manifests.
          for f in deployments/argocd/appproject.yaml \
                   deployments/argocd/root-app.yaml \
                   deployments/argocd/children/*.yaml; do
            python3 -c "import yaml,sys; list(yaml.safe_load_all(open('$f')))"
          done

  test:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: etradie_test
          POSTGRES_USER: etradie_test
          POSTGRES_PASSWORD: test_password
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U etradie_test"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql+asyncpg[REDACTED]localhost:5432/etradie_test
      REDIS_URL: redis://localhost:6379/0
      APP_ENV: testing
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: requirements/dev.txt
      - name: Install dependencies
        run: pip install -r requirements/dev.txt
      - name: Run tests
        run: pytest --timeout=60
      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: htmlcov/
          retention-days: 7

  test-go:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: etradie
          POSTGRES_USER: etradie
          POSTGRES_PASSWORD: etradie_dev
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U etradie"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgres[REDACTED]localhost:5432/etradie?sslmode=disable
      EXECUTION_DATABASE_URL: postgres[REDACTED]localhost:5432/etradie?sslmode=disable
      MANAGEMENT_DATABASE_URL: postgres[REDACTED]localhost:5432/etradie?sslmode=disable
      POSTGRES_HOST: localhost
      POSTGRES_USER: etradie
      POSTGRES_PASSWORD: etradie_dev
      POSTGRES_DB: etradie
      REDIS_URL: redis://localhost:6379/0
      REDIS_HOST: localhost
      EXECUTION_REDIS_URL: redis://localhost:6379/1
      GATEWAY_REDIS_URL: redis://localhost:6379/0
      MANAGEMENT_REDIS_URL: redis://localhost:6379/1
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: "1.23"
          cache: true
      - name: Run Go unit and integration tests
        run: |
          go test ./src/gateway/... -v -count=1 -timeout 120s
          go test ./src/execution/... -v -count=1 -timeout 120s
          go test ./src/management/... -v -count=1 -timeout 120s
      - name: Run Gateway gRPC integration tests
        run: go test ./src/gateway/grpctest/... -v -count=1 -timeout 120s
      - name: Run Execution broker integration tests
        run: go test ./src/execution/brokertest/... -v -count=1 -timeout 60s
      - name: Run Management broker integration tests
        run: go test ./src/management/brokertest/... -v -count=1 -timeout 60s
      - name: Run E2E pipeline tests
        run: go test ./src/gateway/e2etest/... -v -count=1 -time