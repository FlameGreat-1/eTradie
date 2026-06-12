Run aquasecurity/trivy-action@master
Run aquasecurity/setup-trivy@3fb12ec12f41e471780db15c232d5dd185dcb514
Run echo "dir=$HOME/.local/bin/trivy-bin" >> $GITHUB_OUTPUT
Run actions/cache/restore@9255dc7a253b0ccc959486e2bca901246202afeb
Cache hit for: trivy-binary-v0.71.0-Linux-X64
Received 12582912 of 46008243 (27.3%), 12.0 MBs/sec
Received 46008243 of 46008243 (100.0%), 34.9 MBs/sec
Cache Size: ~44 MB (46008243 B)
/usr/bin/tar -xf /home/runner/work/_temp/d897e2b5-7b56-417e-8665-1c2a00379469/cache.tzst -P -C /home/runner/work/eTradie/eTradie --use-compress-program unzstd
Cache restored successfully
Cache restored from key: trivy-binary-v0.71.0-Linux-X64
Run echo /home/runner/.local/bin/trivy-bin >> $GITHUB_PATH
Run echo "date=$(date +'%Y-%m-%d')" >> $GITHUB_OUTPUT
Run actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae
Cache not found for input keys: cache-trivy-2026-06-12, cache-trivy-
Run echo "$GITHUB_ACTION_PATH" >> $GITHUB_PATH
Run rm -f trivy_envs.txt
Run # Note: There is currently no way to distinguish between undefined variables and empty strings in GitHub Actions.
Run entrypoint.sh
Running Trivy with options: trivy fs .
2026-06-12T23:11:40Z	INFO	[vulndb] Need to update DB
2026-06-12T23:11:40Z	INFO	[vulndb] Downloading vulnerability DB...
2026-06-12T23:11:40Z	INFO	[vulndb] Downloading artifact...	repo="mirror.gcr.io/aquasec/trivy-db:2"
13.55 MiB / 95.99 MiB [-------->____________________________________________________] 14.11% ? p/s ?59.11 MiB / 95.99 MiB [------------------------------------->_______________________] 61.58% ? p/s ?95.99 MiB / 95.99 MiB [----------------------------------------------------------->] 100.00% ? p/s ?95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 137.33 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 137.33 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 137.33 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 128.47 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 128.47 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 128.47 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 120.18 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 120.18 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 120.18 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 112.43 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 112.43 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 112.43 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 105.18 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [--------------------------------------------->] 100.00% 105.18 MiB p/s ETA 0s95.99 MiB / 95.99 MiB [-------------------------------------------------] 100.00% 28.73 MiB p/s 3.5s2026-06-12T23:11:45Z	INFO	[vulndb] Artifact successfully downloaded	repo="mirror.gcr.io/aquasec/trivy-db:2"
2026-06-12T23:11:45Z	INFO	[vuln] Vulnerability scanning is enabled
2026-06-12T23:11:45Z	INFO	[misconfig] Misconfiguration scanning is enabled
2026-06-12T23:11:45Z	INFO	[checks-client] Need to update the checks bundle
2026-06-12T23:11:45Z	INFO	[checks-client] Downloading the checks bundle...
234.65 KiB / 234.65 KiB [------------------------------------------------------] 100.00% ? p/s 100ms2026-06-12T23:11:48Z	INFO	[secret] Secret scanning is enabled
2026-06-12T23:11:48Z	INFO	[secret] If your scanning is slow, please try '--scanners vuln,misconfig' to disable secret scanning
2026-06-12T23:11:48Z	INFO	[secret] Please see https://trivy.dev/docs/v0.71/guide/scanner/secret#recommendation for faster secret detection
2026-06-12T23:11:50Z	WARN	[helm scanner] Skipping chart	file_path="helm/billing" err="parse chart: execution error at (billing/templates/deployment.yaml:31:28): helm/billing: .Values.config.billing.publicBaseUrl is required (set in values-*.yaml). Must match the URL registered in Paddle + LS dashboards."
2026-06-12T23:11:51Z	WARN	[helm scanner] Skipping chart	file_path="helm/engine" err="parse chart: execution error at (engine/templates/deployment.yaml:28:28): helm/engine: .Values.config.mtNode.image is REQUIRED. Set it in helm/engine/values-{staging,production}.yaml to the pinned mt-node image, e.g. ghcr.io/<your-org>/etradie-mt-node@sha256:<digest>."
2026-06-12T23:11:51Z	WARN	[helm scanner] Skipping chart	file_path="helm/envoy" err="parse chart: execution error at (etradie-envoy/templates/configmap-wasm.yaml:10:4): helm/envoy: .Values.wasm.base64 is required. CI must inject the base64-encoded WASM binary via --set-file or by setting wasm.base64 directly. The chart will not produce a working envoy without it."
2026-06-12T23:11:52Z	WARN	[helm scanner] Skipping chart	file_path="helm/mt-node" err="parse chart: execution error at (mt-node/templates/statefulset.yaml:2:4): helm/mt-node: .Values.mtConnection.connectionId is REQUIRED. The engine's HostedProvisioner must --set this to the canonical broker_connections.id (36-char UUID)."
2026-06-12T23:11:53Z	INFO	[npm] Run "npm install" to collect the license information of packages	dir="cotradee/node_modules"
2026-06-12T23:11:54Z	INFO	[terraform scanner] Scanning root module	file_path="infrastructure/cloudflare"
2026-06-12T23:11:54Z	WARN	[terraform parser] Variable values were not found in the environment or variable files. Evaluating may not work correctly.	module="root" variables="environment, hostnames, zone_id"
2026-06-12T23:11:54Z	INFO	[terraform scanner] Scanning root module	file_path="infrastructure/cluster/oci"
2026-06-12T23:11:54Z	WARN	[terraform parser] Variable values were not found in the environment or variable files. Evaluating may not work correctly.	module="root" variables="compartment_id, environment, kubernetes_api_subnet_id, kubernetes_worker_subnet_id, node_pool_availability_domains, node_pool_image_id, region, vcn_id"
2026-06-12T23:11:54Z	INFO	[terraform scanner] Scanning root module	file_path="infrastructure/cluster/vault-paths"
2026-06-12T23:11:54Z	WARN	[terraform parser] Variable values were not found in the environment or variable files. Evaluating may not work correctly.	module="root" variables="environment, k8s_ca_cert, k8s_host, vault_address"
2026-06-12T23:11:54Z	INFO	Suppressing dependencies for development and testing. To display them, try the '--include-dev-deps' flag.
2026-06-12T23:11:54Z	INFO	Number of language-specific files	num=4
2026-06-12T23:11:54Z	INFO	[cargo] Detecting vulnerabilities...
2026-06-12T23:11:54Z	INFO	[gomod] Detecting vulnerabilities...
2026-06-12T23:11:54Z	INFO	[npm] Detecting vulnerabilities...
2026-06-12T23:11:54Z	INFO	Detected config files	num=115

Report Summary

┌───────────────────────────────────────────────────────────────────┬────────────┬─────────────────┬───────────────────┬─────────┐
│                              Target                               │    Type    │ Vulnerabilities │ Misconfigurations │ Secrets │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ cotradee/package-lock.json                                        │    npm     │        8        │         -         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ go.mod                                                            │   gomod    │        3        │         -         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ src/edge-ingress/Cargo.lock                                       │   cargo    │        0        │         -         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ src/envoy/Cargo.lock                                              │   cargo    │        0        │         -         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ Dockerfile                                                        │ dockerfile │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/appproject.yaml                                │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/billing-production.yaml               │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/billing-staging.yaml                  │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/data-layer-production.yaml            │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/data-layer-staging.yaml               │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/edge-ingress-production.yaml          │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/edge-ingress-staging.yaml             │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/engine-production.yaml                │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/engine-staging.yaml                   │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/envoy-production.yaml                 │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/envoy-staging.yaml                    │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/execution-production.yaml             │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/execution-staging.yaml                │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/gateway-production.yaml               │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/gateway-staging.yaml                  │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/linkerd-control-plane-production.yaml │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/linkerd-crds-production.yaml          │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/linkerd-identity-production.yaml      │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/management-production.yaml            │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/management-staging.yaml               │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/mt-node-production.yaml               │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/mt-node-staging.yaml                  │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/observability-logs-production.yaml    │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/children/observability-logs-staging.yaml       │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/linkerd-appproject.yaml                        │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/optional/linkerd-viz-production.yaml           │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/argocd/root-app.yaml                                  │ kubernetes │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/edge-ingress/docker/Dockerfile.edge-ingress           │ dockerfile │        -        │         2         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ deployments/linkerd/templates/identity-externalsecret.yaml        │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ docker/mt-node/Dockerfile                                         │ dockerfile │        -        │         0         │    -    │
│ helm/data-layer/templates/chromadb-externalsecret.yaml            │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/chromadb-service.yaml                   │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/chromadb-statefulset.yaml               │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/namespace.yaml                          │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/networkpolicy.yaml                      │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/postgres-backup-cronjob.yaml            │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/postgres-externalsecret.yaml            │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/postgres-init-configmap.yaml            │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/postgres-service.yaml                   │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/postgres-statefulset.yaml               │    helm    │        -        │         1         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/prometheusrule.yaml                     │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/redis-configmap.yaml                    │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/redis-externalsecret.yaml               │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/redis-service.yaml                      │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/redis-statefulset.yaml                  │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/data-layer/templates/servicemonitor.yaml                     │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/cloudflared-deployment.yaml           │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/cloudflared-externalsecret.yaml       │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/cloudflared-networkpolicy.yaml        │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/cloudflared-service.yaml              │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/cloudflared-serviceaccount.yaml       │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/cloudflared-servicemonitor.yaml       │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/configmap.yaml                        │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/deployment.yaml                       │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/externalsecret-aop-ca.yaml            │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/externalsecret-maxmind.yaml           │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/externalsecret-tls.yaml               │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/hpa.yaml                              │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/namespace.yaml                        │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/networkpolicy.yaml                    │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/poddisruptionbudget.yaml              │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/priorityclass.yaml                    │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/service.yaml                          │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/serviceaccount.yaml                   │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/edge-ingress/templates/servicemonitor.yaml                   │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/execution/templates/configmap.yaml                           │    helm    │        -        │         1         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/execution/templates/deployment.yaml                          │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/execution/templates/externalsecret.yaml                      │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/execution/templates/hpa.yaml                                 │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/execution/templates/networkpolicy.yaml                       │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/execution/templates/poddisruptionbudget.yaml                 │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/execution/templates/prometheusrule.yaml                      │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/execution/templates/service.yaml                             │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/execution/templates/serviceaccount.yaml                      │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/execution/templates/servicemonitor.yaml                      │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/gateway/templates/configmap-cf-ranges.yaml                   │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/gateway/templates/configmap.yaml                             │    helm    │        -        │         1         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/gateway/templates/deployment.yaml                            │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/gateway/templates/externalsecret.yaml                        │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/gateway/templates/hpa.yaml                                   │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/gateway/templates/networkpolicy.yaml                         │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/gateway/templates/poddisruptionbudget.yaml                   │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/gateway/templates/prometheusrule.yaml                        │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/gateway/templates/service.yaml                               │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/gateway/templates/serviceaccount.yaml                        │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/gateway/templates/servicemonitor.yaml                        │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/management/templates/configmap.yaml                          │    helm    │        -        │         1         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/management/templates/deployment.yaml                         │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/management/templates/externalsecret.yaml                     │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/management/templates/networkpolicy.yaml                      │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/management/templates/prometheusrule.yaml                     │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/management/templates/service.yaml                            │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/management/templates/serviceaccount.yaml                     │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/management/templates/servicemonitor.yaml                     │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/observability-logs/templates/loki-config.yaml                │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/observability-logs/templates/loki-service.yaml               │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/observability-logs/templates/loki-statefulset.yaml           │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/observability-logs/templates/namespace.yaml                  │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/observability-logs/templates/networkpolicy-loki.yaml         │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/observability-logs/templates/networkpolicy-promtail.yaml     │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/observability-logs/templates/promtail-config.yaml            │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/observability-logs/templates/promtail-daemonset.yaml         │    helm    │        -        │         0         │    -    │
────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/observability-logs/templates/promtail-service.yaml           │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/observability-logs/templates/role.yaml                       │    helm    │        -        │         1         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/observability-logs/templates/rolebinding.yaml                │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/observability-logs/templates/serviceaccount.yaml             │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ helm/observability-logs/templates/servicemonitor.yaml             │    helm    │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ infrastructure/cloudflare                                         │ terraform  │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ infrastructure/cluster/oci                                        │ terraform  │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ infrastructure/cluster/vault-paths                                │ terraform  │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ src/billing/Dockerfile                                            │ dockerfile │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ src/execution/Dockerfile                                          │ dockerfile │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ src/gateway/Dockerfile                                            │ dockerfile │        -        │         0         │    -    │
├───────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼───────────────────┼─────────┤
│ src/management/Dockerfile                                         │ dockerfile │        -        │         0         │    -    │
└───────────────────────────────────────────────────────────────────┴────────────┴─────────────────┴───────────────────┴─────────┘
Legend:
- '-': Not scanned
- '0': Clean (no security findings detected)


For OSS Maintainers: VEX Notice
--------------------------------
If you're an OSS maintainer and Trivy has detected vulnerabilities in your project that you believe are not actually exploitable, consider issuing a VEX (Vulnerability Exploitability eXchange) statement.
VEX allows you to communicate the actual status of vulnerabilities in your project, improving security transparency and reducing false positives for your users.
Learn more and start using VEX: https://trivy.dev/docs/v0.71/guide/supply-chain/vex/repo#publishing-vex-documents

To disable this notice, set the TRIVY_DISABLE_VEX_NOTICE environment variable.


cotradee/package-lock.json (npm)
================================
Total: 8 (HIGH: 8, CRITICAL: 0)

┌─────────┬────────────────┬──────────┬────────┬───────────────────┬────────────────┬──────────────────────────────────────────────────────────┐
│ Library │ Vulnerability  │ Severity │ Status │ Installed Version │ Fixed Version  │                          Title                           │
├─────────┼────────────────┼──────────┼────────┼───────────────────┼────────────────┼──────────────────────────────────────────────────────────┤
│ axios   │ CVE-2026-42264 │ HIGH     │ fixed  │ 1.15.1            │ 1.15.2         │ Axios is a promise based HTTP client for the browser and │
│         │                │          │        │                   │                │ Node.js....                                              │
│         │                │          │        │                   │                │ https://avd.aquasec.com/nvd/cve-2026-42264               │
│         ├────────────────┤          │        │                   ├────────────────┼──────────────────────────────────────────────────────────┤
│         │ CVE-2026-44486 │          │        │                   │ 1.16.0, 0.32.0 │ Axios is a promise based HTTP client for the browser and │
│         │                │          │        │                   │                │ Node.js....                                              │
│         │                │          │        │                   │                │ https://avd.aquasec.com/nvd/cve-2026-44486               │
│         ├────────────────┤          │        │                   │                ├──────────────────────────────────────────────────────────┤
│         │ CVE-2026-44487 │          │        │                   │                │ Axios is a promise based HTTP client for the browser and │
│         │                │          │        │                   │                │ Node.js....                                              │
│         │                │          │        │                   │                │ https://avd.aquasec.com/nvd/cve-2026-44487               │
│         ├────────────────┤          │        │                   ├────────────────┼──────────────────────────────────────────────────────────┤
│         │ CVE-2026-44488 │          │        │                   │ 1.16.0         │ Axios is a promise based HTTP client for the browser and │
│         │                │          │        │                   │                │ Node.js....                                              │
│         │                │          │        │                   │                │ https://avd.aquasec.com/nvd/cve-2026-44488               │
│         ├────────────────┤          │        │                   ├────────────────┼──────────────────────────────────────────────────────────┤
│         │ CVE-2026-44492 │          │        │                   │ 1.16.0, 0.32.0 │ Axios is a promise based HTTP client for the browser and │
│         │                │          │        │                   │                │ Node.js....                                              │
│         │                │          │        │                   │                │ https://avd.aquasec.com/nvd/cve-2026-44492               │
│         ├────────────────┤          │        │                   ├────────────────┼──────────────────────────────────────────────────────────┤
│         │ CVE-2026-44494 │          │        │                   │ 1.16.0         │ Axios is a promise based HTTP client for the browser and │
│         │                │          │        │                   │                │ Node.js....                                              │
│         │                │          │        │                   │                │ https://avd.aquasec.com/nvd/cve-2026-44494               │
│         ├────────────────┤          │        │                   ├────────────────┼──────────────────────────────────────────────────────────┤
│         │ CVE-2026-44495 │          │        │                   │ 1.15.2, 0.31.1 │ Axios is a promise based HTTP client for the browser and │
│         │                │          │        │                   │                │ Node.js....                                              │
│         │                │          │        │                   │                │ https://avd.aquasec.com/nvd/cve-2026-44495               │
│         ├────────────────┤          │        │                   ├────────────────┼──────────────────────────────────────────────────────────┤
│         │ CVE-2026-44496 │          │        │                   │ 1.16.0, 0.32.0 │ Axios is a promise based HTTP client for the browser and │
│         │                │          │        │                   │                │ Node.js....                                              │
│         │                │          │        │                   │                │ https://avd.aquasec.com/nvd/cve-2026-44496               │
└─────────┴────────────────┴──────────┴────────┴───────────────────┴────────────────┴──────────────────────────────────────────────────────────┘

go.mod (gomod)
==============
Total: 3 (HIGH: 2, CRITICAL: 1)

┌──────────────────────────────┬────────────────┬──────────┬────────┬───────────────────┬───────────────┬──────────────────────────────────────────────────────────────┐
│           Library            │ Vulnerability  │ Severity │ Status │ Installed Version │ Fixed Version │                            Title                             │
├──────────────────────────────┼────────────────┼──────────┼────────┼───────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ github.com/jackc/pgx/v5      │ CVE-2026-33816 │ CRITICAL │ fixed  │ v5.5.4            │ 5.9.0         │ github.com/jackc/pgx/v5: github.com/jackc/pgx: Memory-safety │
│                              │                │          │        │                   │               │ vulnerability                                                │
│                              │                │          │        │                   │               │ https://avd.aquasec.com/nvd/cve-2026-33816                   │
├──────────────────────────────┼────────────────┼──────────┤        ├───────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ go.opentelemetry.io/otel     │ CVE-2026-29181 │ HIGH     │        │ v1.40.0           │ 1.41.0        │ github.com/open-telemetry/opentelemetry-go:                  │
│                              │                │          │        │                   │               │ OpenTelemetry-Go: Denial of Service via crafted multi-value  │
│                              │                │          │        │                   │               │ baggage headers                                              │
│                              │                │          │        │                   │               │ https://avd.aquasec.com/nvd/cve-2026-29181                   │
├──────────────────────────────┼────────────────┤          │        │                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│ go.opentelemetry.io/otel/sdk │ CVE-2026-39883 │          │        │                   │ 1.43.0        │ github.com/open-telemetry/opentelemetry-go:                  │
│                              │                │          │        │                   │               │ OpenTelemetry-Go: Arbitrary code execution via PATH          │
│                              │                │          │        │                   │               │ hijacking on BSD/Solaris                                     │
│                              │                │          │        │                   │               │ https://avd.aquasec.com/nvd/cve-2026-39883                   │
└──────────────────────────────┴────────────────┴──────────┴────────┴───────────────────┴───────────────┴──────────────────────────────────────────────────────────────┘

deployments/edge-ingress/docker/Dockerfile.edge-ingress (dockerfile)
====================================================================
Tests: 21 (SUCCESSES: 19, FAILURES: 2)
Failures: 2 (HIGH: 2, CRITICAL: 0)

DS-0029 (HIGH): '--no-install-recommends' flag is missed: 'apt-get update && apt-get install -y     ca-certificates     libssl3     wget     && rm -rf /var/lib/apt/lists/*'
════════════════════════════════════════
'apt-get' install should use '--no-install-recommends' to minimize image size.

See https://avd.aquasec.com/misconfig/ds-0029
────────────────────────────────────────
 deployments/edge-ingress/docker/Dockerfile.edge-ingress:39-43
────────────────────────────────────────
  39 ┌ RUN apt-get update && apt-get install -y \
  40 │     ca-certificates \
  41 │     libssl3 \
  42 │     wget \
  43 └     && rm -rf /var/lib/apt/lists/*
────────────────────────────────────────


DS-0029 (HIGH): '--no-install-recommends' flag is missed: 'apt-get update && apt-get install -y     pkg-config     libssl-dev     ca-certificates     && rm -rf /var/lib/apt/lists/*'
════════════════════════════════════════
'apt-get' install should use '--no-install-recommends' to minimize image size.

See https://avd.aquasec.com/misconfig/ds-0029
────────────────────────────────────────
 deployments/edge-ingress/docker/Dockerfile.edge-ingress:6-10
────────────────────────────────────────
   6 ┌ RUN apt-get update && apt-get install -y \
   7 │     pkg-config \
   8 │     libssl-dev \
   9 │     ca-certificates \
  10 └     && rm -rf /var/lib/apt/lists/*
────────────────────────────────────────






helm/data-layer/templates/postgres-statefulset.yaml (helm)
==========================================================
Tests: 22 (SUCCESSES: 21, FAILURES: 1)
Failures: 1 (HIGH: 1, CRITICAL: 0)

KSV-0014 (HIGH): Container 'postgres' of StatefulSet 'postgres' should set 'securityContext.readOnlyRootFilesystem' to true
════════════════════════════════════════
An immutable root file system prevents applications from writing to their local disk. This can limit intrusions, as attackers will not be able to tamper with the file system or write foreign executables to disk.

See https://avd.aquasec.com/misconfig/ksv-0014
────────────────────────────────────────
 helm/data-layer/templates/postgres-statefulset.yaml:52-138
────────────────────────────────────────
  52 ┌         - name: postgres
  53 │           image: "postgres:16-alpine"
  54 │           imagePullPolicy: IfNotPresent
  55 │           securityContext:
  56 │             allowPrivilegeEscalation: false
  57 │             # Postgres needs writable /var/run/postgresql for the unix
  58 │             # socket; cannot run with readOnlyRootFilesystem=true. The
  59 │             # data dir is on the PVC and all caps are dropped.
  60 └             readOnlyRootFilesystem: false
  ..   
────────────────────────────────────────



helm/execution/templates/configmap.yaml (helm)
==============================================
Tests: 11 (SUCCESSES: 10, FAILURES: 1)
Failures: 1 (HIGH: 1, CRITICAL: 0)

KSV-0109 (HIGH): ConfigMap 'execution-config' in 'etradie-system' namespace stores secrets in key(s) or value(s) '{"AUTH_ACCESS_TOKEN_TTL_SECONDS", "AUTH_REFRESH_TOKEN_TTL_SECONDS", "AUTH_SERVICE_TOKEN_TTL_SECONDS"}'
════════════════════════════════════════
Storing secrets in configMaps is unsafe

See https://avd.aquasec.com/misconfig/ksv-0109
────────────────────────────────────────



helm/gateway/templates/configmap.yaml (helm)
============================================
Tests: 11 (SUCCESSES: 10, FAILURES: 1)
Failures: 1 (HIGH: 1, CRITICAL: 0)

KSV-0109 (HIGH): ConfigMap 'gateway-config' in 'etradie-system' namespace stores secrets in key(s) or value(s) '{"AUTH_ACCESS_TOKEN_TTL_SECONDS", "AUTH_REFRESH_TOKEN_TTL_SECONDS", "AUTH_RETURN_TOKENS_IN_BODY", "AUTH_SERVICE_TOKEN_TTL_SECONDS"}'
════════════════════════════════════════
Storing secrets in configMaps is unsafe

See https://avd.aquasec.com/misconfig/ksv-0109
────────────────────────────────────────



helm/management/templates/configmap.yaml (helm)
===============================================
Tests: 11 (SUCCESSES: 10, FAILURES: 1)
Failures: 1 (HIGH: 1, CRITICAL: 0)

KSV-0109 (HIGH): ConfigMap 'management-config' in 'etradie-system' namespace stores secrets in key(s) or value(s) '{"AUTH_ACCESS_TOKEN_TTL_SECONDS", "AUTH_REFRESH_TOKEN_TTL_SECONDS", "AUTH_SERVICE_TOKEN_TTL_SECONDS"}'
════════════════════════════════════════
Storing secrets in configMaps is unsafe

See https://avd.aquasec.com/misconfig/ksv-0109
────────────────────────────────────────



helm/observability-logs/templates/role.yaml (helm)
==================================================
Tests: 17 (SUCCESSES: 16, FAILURES: 1)
Failures: 1 (HIGH: 1, CRITICAL: 0)

KSV-0047 (HIGH): Role permits privilege escalation from node proxy
════════════════════════════════════════
Check whether role permits privilege escalation from node proxy

See https://avd.aquasec.com/misconfig/ksv-0047
────────────────────────────────────────
 helm/observability-logs/templates/role.yaml:14-24
────────────────────────────────────────
  14 ┌   - apiGroups: [""]
  15 │     resources:
  16 │       - nodes
  17 │       - nodes/proxy
  18 │       - services
  19 │       - endpoints
  20 │       - pods
  21 │     verbs:
  22 └       - get
  ..   
────────────────────────────────────────


Error: Process completed with exit code 1.
Run rm -f trivy_envs.txt
  
0s
