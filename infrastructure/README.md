# infrastructure/

Terraform modules that own **cloud-side primitives** (Cloudflare zone
settings, Cloudflare Tunnel DNS, Vault path schema). Kubernetes
manifests live under `helm/<svc>/`; ArgoCD applications under
`deployments/argocd/` reconcile them onto whichever cluster the
operator brings up.

## Module layout

| Module | Owns | Does NOT own |
|--------|------|--------------|
| `cloudflare/` | Cloudflare zone TLS posture, Authenticated Origin Pulls, DNS records that CNAME to the Tunnel UUID. | The Tunnel itself, the Tunnel token, any K8s manifest. |
| `cluster/vault-paths/` | KV-v2 path schema in Vault (cloud-agnostic; only requires Vault provider). | Any cluster, any K8s manifest. |
| `cluster/oci/` | OCI OKE Enhanced cluster + autoscaled platform node pool + workload=etradie-system:NoSchedule taint. | Vault paths, K8s manifests, VCN/subnets. |
| `cluster/bootstrap/` | Manual bootstrap procedure for Contabo K3s, kubeadm, kind, k3d, or any conformant K8s. | (it's a README, not a module). |

## Edge strategy

The platform publishes via **Cloudflare Tunnel** — there is no public
LoadBalancer Service, no AWS NLB, no OCI LB, and no cert-manager
dependency. The cloudflared daemon runs as a pod in the
`edge-ingress-system` namespace and forwards inbound traffic to
edge-ingress on `:443` over the cluster network. Public DNS records
CNAME to `<tunnel-id>.cfargotunnel.com`.

This means:
  * No port is exposed from any cluster node to the internet.
  * No cloud LoadBalancer controller is required (works identically
    on Contabo K3s, OCI OKE, GKE, AKS, kubeadm, kind).
  * TLS termination at the edge is Cloudflare's job; mTLS between
    Cloudflare and the origin is automatic via the Tunnel; AOP at the
    zone level is enabled as belt-and-braces.

The edge-ingress chart's `service.cloudProvider` defaults to
`cloudflare-tunnel`. A `generic` mode (vanilla LoadBalancer Service,
no cloud-specific annotations) is also available for operators who
prefer a public LB; AWS-specific annotations and ACM ARNs were
deliberately removed in this revision.

## Apply order

```text
1. Cluster bootstrap
   - OCI:           cluster/oci/        (run terraform apply, then bootstrap step 1+)
   - Contabo / K3s: follow cluster/bootstrap/README.md
2. Install Vault (HCP, vault chart, or external VM)
3. Install ESO (helm chart `external-secrets/external-secrets`)
4. Apply cluster/vault-paths/  (creates KV path schema)
5. Operator populates Vault paths with real bytes
6. Create Cloudflare Tunnel in Zero Trust UI; copy UUID + token
7. Write the Tunnel token to
   secret/etradie/services/edge-ingress/<env>/cloudflare/tunnel
8. Apply cloudflare/ with hostnames={ ... = "<id>.cfargotunnel.com" }
9. Install ArgoCD; apply deployments/argocd/appproject.yaml + root-app.yaml
10. ArgoCD reconciles helm/edge-ingress (cloudflared + edge-ingress)
    + helm/envoy + helm/gateway + helm/{engine,execution,management,data-layer}
```

## Why no infrastructure/<svc>/ modules

The deleted `infrastructure/gateway/` module shelled out to
`kustomize build` and applied the rendered manifests via the
`gavinbunney/kubectl` provider. That made Terraform an unwitting
competitor with ArgoCD for ownership of Deployments,
NetworkPolicies, and HPAs. Removing it and giving ArgoCD exclusive
ownership of every Kubernetes resource eliminates the reconciliation
conflict by construction.

If a future service needs cloud-side primitives (e.g. an OCI Object
Storage bucket, a Cloudflare R2 bucket, a Tunnel rotation), those
go in a new module under `infrastructure/<svc>-cloud/` — never
`infrastructure/<svc>/` (which implies the module owns the running
service).
